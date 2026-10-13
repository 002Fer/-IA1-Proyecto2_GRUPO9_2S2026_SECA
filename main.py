"""
AURA — Punto de entrada principal.

Modo de uso (desde SSH en la Raspberry Pi):
    python main.py

Luego abre en tu PC:
    http://<IP_DE_LA_RASPBERRY>:8080

El stream MJPEG muestra el video en tiempo real con el overlay
de Realidad Aumentada y el robot virtual 2D de AURA.

Ctrl+C para detener.
"""

import sys
import time
import signal
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

import cv2

from vision.detector import VisionDetector
from ui import AuraUI

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AURA")

# ---------------------------------------------------------------------------
# Frame compartido entre el loop principal y el servidor HTTP
# ---------------------------------------------------------------------------
_stream_lock = threading.Lock()
_latest_jpeg: bytes | None = None          # Último frame codificado como JPEG
_running = True                            # Flag global de ejecución


def _set_frame(frame) -> None:
    """Codifica el frame BGR a JPEG y lo guarda para el servidor."""
    global _latest_jpeg
    ret, buf = cv2.imencode(
        ".jpg", frame,
        [cv2.IMWRITE_JPEG_QUALITY, 75]
    )
    if ret:
        with _stream_lock:
            _latest_jpeg = buf.tobytes()


# ---------------------------------------------------------------------------
# Servidor MJPEG HTTP
# ---------------------------------------------------------------------------
class _MJPEGHandler(BaseHTTPRequestHandler):
    """Handler HTTP minimalista que sirve un stream MJPEG."""

    def log_message(self, fmt, *args):
        pass  # silenciar logs de acceso HTTP

    def do_GET(self):
        if self.path not in ("/", "/stream"):
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "multipart/x-mixed-replace; boundary=frame"
        )
        self.end_headers()

        try:
            while _running:
                with _stream_lock:
                    jpeg = _latest_jpeg

                if jpeg is None:
                    time.sleep(0.05)
                    continue

                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                time.sleep(0.1)  # ~10 fps al cliente

        except (BrokenPipeError, ConnectionResetError):
            pass


def _start_http_server(port: int = 8080) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), _MJPEGHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------------------------------------------------------------------------
# Gestos que disparan un proceso RPA y sincronización de estado
# ---------------------------------------------------------------------------
RPA_GESTURES = {
    "INDEX_UP":      ("horario", "Consultando horario"),
    "INDEX_DOWN":    ("material", "Descargando material UEDI"),
    "WRITE_GESTURE": ("formulario", "Completando formulario"),
}

_rpa_lock = threading.Lock()
_rpa_state = {
    "running": False,
    "current_action": "",
    "status": None,       # "running", "success", "error"
    "message": "",
    "finished_at": 0.0,
}


def _trigger_rpa(gesture: str) -> None:
    """Ejecuta el proceso RPA correspondiente de forma segura y exclusiva."""
    import asyncio
    from rpa.service import RPAService

    if gesture not in RPA_GESTURES:
        return

    rpa_id, rpa_label = RPA_GESTURES[gesture]

    with _rpa_lock:
        if _rpa_state["running"]:
            return  # Ya hay un RPA en ejecución, no saturar la Raspberry Pi

        _rpa_state["running"] = True
        _rpa_state["current_action"] = rpa_label
        _rpa_state["status"] = "running"
        _rpa_state["message"] = f"Ejecutando {rpa_label}..."

    def run():
        logger.info(f"[RPA] Iniciando proceso: {rpa_id} ({rpa_label})")
        try:
            result = asyncio.run(RPAService.ejecutar_por_gesto(gesture))
            success = result.get("success", False)
            msg = result.get("message", "")
            status = "success" if success else "error"
        except Exception as e:
            status = "error"
            msg = f"Error inesperado: {str(e)}"

        with _rpa_lock:
            _rpa_state["running"] = False
            _rpa_state["status"] = status
            _rpa_state["message"] = msg[:38]  # Truncar para que quepa en el panel AR
            _rpa_state["finished_at"] = time.monotonic()

        logger.info(f"[RPA] {rpa_id} → {status}: {msg}")

    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
GESTURE_LABELS = {
    "HAND_RAISED":   "Mano levantada",
    "THUMBS_UP":     "Pulgar arriba",
    "THUMBS_DOWN":   "Pulgar abajo",
    "POINT_LEFT":    "Señalar izquierda",
    "POINT_RIGHT":   "Señalar derecha",
    "ARMS_CROSSED":  "Brazos cruzados",
    "INDEX_UP":      "Indice arriba",
    "INDEX_DOWN":    "Indice abajo",
    "WRITE_GESTURE": "Gesto escritura",
    "UNKNOWN":       "—",
}


def main():
    global _running

    stream_port = 8080

    detector = VisionDetector(
        hand_model_path="models/hand_landmarker.task",
        pose_model_path="models/pose_landmarker.task",
    )
    aura_ui = AuraUI()

    # Manejador de Ctrl+C
    def _shutdown(sig, frame):
        global _running
        logger.info("Señal de interrupción recibida. Cerrando AURA...")
        _running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Abriendo cámara con rpicam-vid...")
    try:
        detector.open()
    except Exception as e:
        logger.error(f"No se pudo abrir la cámara: {e}")
        sys.exit(1)

    logger.info(f"Servidor MJPEG iniciado en http://0.0.0.0:{stream_port}")
    logger.info(f"Abre en tu PC: http://<IP_RASPBERRY>:{stream_port}")
    http_server = _start_http_server(stream_port)

    logger.info("AURA corriendo. Ctrl+C para detener.\n")

    last_gesture = "UNKNOWN"
    last_state_label = ""
    frame_count = 0

    try:
        while _running:
            with _rpa_lock:
                is_rpa_running = _rpa_state["running"]
                rpa_status = _rpa_state["status"]
                rpa_action = _rpa_state["message"] or _rpa_state["current_action"]
                finished_at = _rpa_state["finished_at"]

            # Si terminó un RPA hace menos de 5 segundos, mantener el estado visual de Exito/Error
            if not is_rpa_running and rpa_status in ("success", "error"):
                if time.monotonic() - finished_at > 5.0:
                    with _rpa_lock:
                        _rpa_state["status"] = None
                        rpa_status = None

            # OPTIMIZACIÓN CLAVE PARA RASPBERRY PI 3A+ (512MB RAM):
            # Mientras Chromium corre el proceso RPA, pausar la inferencia pesada de MediaPipe.
            # Solo leemos la cámara para mantener el stream en vivo fluido.
            if is_rpa_running:
                try:
                    frame = detector.camera.read()
                except RuntimeError as e:
                    logger.error(f"Error de cámara: {e}")
                    break

                result = {
                    "frame": frame,
                    "person_detected": True,
                    "gesture": "UNKNOWN",
                    "confidence": 0.0,
                    "proximity": "NEAR",
                    "hand_results": None,
                    "pose_results": None,
                }
                gesture = "UNKNOWN"
                person = True
                confidence = 0.0
                exec_status = "running"
                ui_action = rpa_action
                ui_interp = "RPA en curso"

            else:
                try:
                    result = detector.process()
                except RuntimeError as e:
                    logger.error(f"Error de cámara: {e}")
                    break

                gesture = result.get("gesture", "UNKNOWN")
                person = result.get("person_detected", False)
                confidence = result.get("confidence", 0.0)

                # Disparar RPA si corresponde y no hay otro corriendo
                if gesture in RPA_GESTURES and rpa_status is None:
                    _trigger_rpa(gesture)

                exec_status = rpa_status
                ui_action = rpa_action if rpa_status else None
                ui_interp = "Accion completada" if rpa_status == "success" else None

            # Actualizar UI y superponer Realidad Aumentada + Robot 2D
            ui_result = aura_ui.process(
                vision_result=result,
                execution_status=exec_status,
                interpretation=ui_interp,
                action=ui_action,
            )

            # Publicar frame al stream HTTP
            _set_frame(ui_result["frame"])

            # Log en terminal (solo cuando cambia algo relevante)
            state_label = ui_result["state_label"]
            gesture_label = GESTURE_LABELS.get(gesture, gesture)

            if gesture != last_gesture or state_label != last_state_label:
                logger.info(
                    f"Persona={'Sí' if person else 'No':3s} | "
                    f"Estado={state_label:<12s} | "
                    f"Gesto={gesture_label:<18s} | "
                    f"Conf={confidence:.2f}"
                )
                last_gesture = gesture
                last_state_label = state_label

            frame_count += 1

    finally:
        logger.info(f"Frames procesados: {frame_count}")
        detector.release()
        try:
            http_server.server_close()
        except Exception:
            pass
        logger.info("AURA detenida correctamente.")


if __name__ == "__main__":
    main()
