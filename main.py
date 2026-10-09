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
# Gestos que disparan un proceso RPA
# ---------------------------------------------------------------------------
RPA_GESTURES = {
    "INDEX_UP":      "horario",
    "INDEX_DOWN":    "material",
    "WRITE_GESTURE": "formulario",
}

# Tiempo mínimo entre dos ejecuciones del mismo RPA (segundos)
RPA_COOLDOWN = 15.0
_last_rpa_time: dict = {}
_rpa_lock = threading.Lock()


def _trigger_rpa(gesture: str, aura_ui: AuraUI) -> None:
    """Ejecuta el proceso RPA correspondiente en un hilo aparte."""
    import asyncio
    from rpa.service import RPAService

    proceso = RPA_GESTURES.get(gesture)
    if proceso is None:
        return

    now = time.monotonic()
    with _rpa_lock:
        last = _last_rpa_time.get(proceso, 0.0)
        if now - last < RPA_COOLDOWN:
            return
        _last_rpa_time[proceso] = now

    def run():
        logger.info(f"[RPA] Iniciando proceso: {proceso}")
        result = asyncio.run(RPAService.ejecutar_por_gesto(gesture))
        status = "success" if result.get("success") else "error"
        msg = result.get("message", "")
        logger.info(f"[RPA] {proceso} → {status}: {msg}")

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
            try:
                result = detector.process()
            except RuntimeError as e:
                logger.error(f"Error de cámara: {e}")
                break

            gesture = result.get("gesture", "UNKNOWN")
            person = result.get("person_detected", False)
            confidence = result.get("confidence", 0.0)

            # Disparar RPA si corresponde
            if gesture in RPA_GESTURES:
                _trigger_rpa(gesture, aura_ui)
                execution_status = None  # El hilo RPA maneja su propio estado
            else:
                execution_status = None

            # Actualizar UI
            ui_result = aura_ui.process(
                vision_result=result,
                execution_status=execution_status,
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
