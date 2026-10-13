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

import os
import sys
import time
import math
import signal
import threading
import logging
from pathlib import Path
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
    """Codifica el frame BGR a JPEG y lo guarda para el servidor.

    Añade un reloj HH:MM:SS en la esquina superior derecha del frame para que
    el usuario siempre pueda confirmar visualmente que el feed está vivo,
    incluso cuando la escena parece estática.
    """
    global _latest_jpeg
    # Reloj en tiempo real — cambia cada segundo en cualquier estado de AURA
    ts = time.strftime("%H:%M:%S")
    h, w = frame.shape[:2]
    # Sombra negra + texto blanco para legibilidad sobre cualquier fondo
    cv2.putText(frame, ts, (w - 88, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(frame, ts, (w - 89, 21),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
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

GESTURE_TO_AGENT = {
    "HAND_RAISED":   "mano_levantada",
    "THUMBS_UP":     "pulgar_arriba",
    "THUMBS_DOWN":   "pulgar_abajo",
    "POINT_LEFT":    "señalar_izquierda",
    "POINT_RIGHT":   "señalar_derecha",
    "ARMS_CROSSED":  "brazos_cruzados",
    "INDEX_UP":      "indice_arriba",
    "INDEX_DOWN":    "indice_abajo",
    "WRITE_GESTURE": "escritura",
}

_rpa_lock = threading.Lock()
_rpa_state = {
    "running": False,
    "current_action": "",
    "status": None,       # "running", "success", "error"
    "message": "",
    "finished_at": 0.0,
    "started_at": 0.0,    # Timestamp de inicio para el contador visual
}


def _trigger_rpa(gesture: str, agent=None, telegram=None) -> None:
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
        _rpa_state["started_at"] = time.monotonic()

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

        # Notificar al Bot de Telegram si está activo
        if agent:
            agent._log(f"RPA {rpa_id} finalizado ({status}): {msg}")
            chat_id = agent.get_last_chat_id()
            if chat_id and telegram:
                emoji = "✅" if status == "success" else "❌"
                try:
                    telegram.send_message(
                        chat_id,
                        f"🤖 [AURA RPA] {emoji} Proceso '{rpa_label}' finalizado.\nResultado: {msg}"
                    )
                except Exception:
                    pass

    threading.Thread(target=run, daemon=True).start()


def _init_telegram(runtime_adapter):
    """Inicializa el bot de Telegram en segundo plano si hay token configurado."""
    try:
        from telegram.bot import load_env, build_agent
        from telegram.telegram_service import TelegramService
        from telegram.handlers import TelegramHandlers
        from telegram.commands import TELEGRAM_MENU_COMMANDS

        load_env()
        token = os.getenv("AURA_BOT_TOKEN", "").strip()
        if not token or token == "PEGAR_TOKEN_AQUI":
            logger.info("[Telegram] No se encontró AURA_BOT_TOKEN válido en telegram/.env. Bot desactivado.")
            return None, None

        agent = build_agent()
        agent.set_runtime_adapter(runtime_adapter)

        poll_timeout = int(os.getenv("AURA_POLL_TIMEOUT", "25"))
        allowed_chat_id = os.getenv("AURA_ALLOWED_CHAT_ID", "").strip()

        telegram_srv = TelegramService(token, poll_timeout=poll_timeout)
        handlers = TelegramHandlers(telegram_srv, agent, allowed_chat_id=allowed_chat_id)

        commands = [
            {"command": name, "description": desc}
            for name, desc in TELEGRAM_MENU_COMMANDS.items()
        ]
        telegram_srv.set_my_commands(commands)

        def run_bot():
            logger.info("[Telegram] Bot conectado e iniciando polling de comandos...")
            try:
                telegram_srv.run_polling(handlers.handle_message)
            except Exception as ex:
                logger.error(f"[Telegram] Error en loop del bot: {ex}")

        thread = threading.Thread(target=run_bot, daemon=True)
        thread.start()
        logger.info("[Telegram] Bot activo en segundo plano.")
        return agent, telegram_srv
    except Exception as e:
        logger.error(f"[Telegram] Error al inicializar bot: {e}")
        return None, None


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

    # Estado de interacción controlado desde Telegram (/iniciar y /apagar)
    _recognition_active = True

    class RuntimeAdapter:
        def get_status(self):
            from telegram.agent_service import RaspberryAgentService
            return {
                "cpu": RaspberryAgentService._linux_cpu_percent(),
                "ram": RaspberryAgentService._linux_ram_percent(),
                "status": "RUNNING" if _recognition_active else "PAUSED",
                "recognition": "ACTIVE" if _recognition_active else "INACTIVE",
            }

        def start(self):
            nonlocal _recognition_active
            _recognition_active = True
            logger.info("[Telegram] Comando /iniciar recibido: Reconocimiento activado.")
            return True

        def stop(self):
            nonlocal _recognition_active
            _recognition_active = False
            logger.info("[Telegram] Comando /apagar recibido: Reconocimiento pausado.")
            return True

    adapter = RuntimeAdapter()
    agent, telegram_srv = _init_telegram(adapter)

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
            # Control por Telegram: Si se envió /apagar, pausar MediaPipe y dejar AURA en reposo
            if not _recognition_active:
                try:
                    frame = detector.camera.read()
                except RuntimeError as e:
                    logger.error(f"Error de cámara: {e}")
                    break

                result = {
                    "frame": frame,
                    "person_detected": False,
                    "gesture": "UNKNOWN",
                    "confidence": 0.0,
                    "proximity": "UNKNOWN",
                    "hand_results": None,
                    "pose_results": None,
                }
                ui_result = aura_ui.process(
                    vision_result=result,
                    execution_status=None,
                    interpretation="AURA en reposo",
                    action="Usa /iniciar en Telegram",
                )
                _set_frame(ui_result["frame"])
                time.sleep(0.1)
                continue

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

            # OPTIMIZACIÓN PARA RASPBERRY PI 3A+:
            # Mientras Chromium corre el proceso RPA, pausar MediaPipe para ceder CPU.
            # Se mantiene la cámara activa a ~5 FPS con un indicador visual animado
            # para que el usuario sepa que el sistema está funcionando.
            if is_rpa_running:
                try:
                    frame = detector.camera.read()
                except RuntimeError as e:
                    logger.error(f"Error de cámara: {e}")
                    break

                # --- Indicador visual animado de RPA en curso ---
                # Dibujamos directamente sobre el frame con OpenCV antes de enviarlo
                # al overlay de AuraUI, de modo que el usuario vea claramente que
                # AURA está trabajando aunque MediaPipe esté pausado.
                with _rpa_lock:
                    rpa_started = _rpa_state["started_at"]
                elapsed_s = int(time.monotonic() - rpa_started)
                now_t = time.monotonic()

                # Punto verde pulsante: radio oscila entre 6 y 14 px con una onda senoidal
                pulse_r = int(6 + 8 * abs(math.sin(now_t * 2.5)))
                h_f, w_f = frame.shape[:2]
                dot_x, dot_y = 28, h_f - 28
                # Sombra negra para que se vea sobre fondos claros u oscuros
                cv2.circle(frame, (dot_x, dot_y), pulse_r + 3, (0, 0, 0), -1)
                cv2.circle(frame, (dot_x, dot_y), pulse_r, (0, 210, 0), -1)

                # Texto de estado con tiempo transcurrido
                label = f"RPA en curso  {elapsed_s}s"
                text_x = dot_x + pulse_r + 8
                text_y = h_f - 20
                cv2.putText(frame, label, (text_x + 1, text_y + 1),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(frame, label, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 1, cv2.LINE_AA)

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

                # 200ms: 5 FPS — el usuario ve el feed actualizado sin quitar
                # demasiada CPU a Chromium que está corriendo en paralelo.
                time.sleep(0.2)

            else:
                try:
                    result = detector.process()
                except RuntimeError as e:
                    logger.error(f"Error de cámara: {e}")
                    break

                gesture = result.get("gesture", "UNKNOWN")
                person = result.get("person_detected", False)
                confidence = result.get("confidence", 0.0)

                # Verificar si el gesto está habilitado en Telegram
                agent_gesture = GESTURE_TO_AGENT.get(gesture)
                if agent and agent_gesture:
                    if not agent.is_gesture_enabled(agent_gesture):
                        gesture = "UNKNOWN"

                # Registrar en Telegram el gesto cuando es detectado por primera vez
                if gesture != "UNKNOWN" and gesture != last_gesture and agent:
                    exec_res = agent.execute_gesture(agent_gesture or gesture, confidence)
                    # Si tiene mensaje configurado con /sendMessage, notificar al chat
                    if exec_res.get("message") and telegram_srv:
                        chat_id = agent.get_last_chat_id()
                        if chat_id:
                            try:
                                telegram_srv.send_message(chat_id, f"💬 [AURA]: {exec_res['message']}")
                            except Exception:
                                pass

                # Disparar RPA si corresponde y no hay otro corriendo
                if gesture in RPA_GESTURES and rpa_status is None:
                    _trigger_rpa(gesture, agent=agent, telegram=telegram_srv)

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
