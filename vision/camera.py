import sys
import time
import subprocess
import numpy as np
import cv2

if sys.platform != "win32":
    import os
    import fcntl

WIDTH = 640
HEIGHT = 480
CAMERA_FPS = 15


class Camera:
    """
    Captura video de la cámara de la Raspberry Pi usando rpicam-vid
    en modo MJPEG por pipe.

    Utiliza lectura no bloqueante y polling con timeout para obtener SIEMPRE
    el último frame sin acumular latencia y sin fallar al encender la cámara.
    """

    def __init__(self, camera_index=0):
        self._process = None
        self._buffer = b""

    def open(self):
        """Lanza rpicam-vid y conecta su salida MJPEG al pipe interno."""
        cmd = [
            "rpicam-vid",
            "--width",     str(WIDTH),
            "--height",    str(HEIGHT),
            "--framerate", str(CAMERA_FPS),
            "--codec",     "mjpeg",
            "--timeout",   "0",       # sin límite de tiempo
            "--output",    "-",       # stdout
            "--nopreview",
        ]
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self._buffer = b""

        # Configurar stdout como no bloqueante en Linux / Raspberry Pi
        if sys.platform != "win32":
            fd = self._process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def read(self):
        """
        Lee el ÚLTIMO frame JPEG completo disponible en el pipe.
        Descarta automáticamente cualquier frame antiguo o demorado.
        """
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("La cámara no está abierta o el proceso rpicam-vid terminó.")

        start_time = time.monotonic()
        timeout = 6.0  # Tiempo para dar margen al encendido inicial de la cámara

        while time.monotonic() - start_time < timeout:
            # 1. Leer todo el búfer disponible de forma no bloqueante
            if sys.platform != "win32":
                while True:
                    try:
                        chunk = os.read(self._process.stdout.fileno(), 65536)
                        if not chunk:
                            break
                        self._buffer += chunk
                    except (BlockingIOError, OSError):
                        break
            else:
                try:
                    chunk = self._process.stdout.read(65536)
                    if chunk:
                        self._buffer += chunk
                except Exception:
                    pass

            # 2. Extraer TODOS los frames en el búfer y conservar SOLO el último
            last_frame_bytes = None
            while True:
                start = self._buffer.find(b"\xff\xd8")
                if start == -1:
                    self._buffer = b""
                    break

                end = self._buffer.find(b"\xff\xd9", start + 2)
                if end == -1:
                    self._buffer = self._buffer[start:]
                    break

                last_frame_bytes = self._buffer[start:end + 2]
                self._buffer = self._buffer[end + 2:]

            if last_frame_bytes is not None:
                arr = np.frombuffer(last_frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    return frame

            # Esperar brevemente (10ms) a que rpicam-vid genere datos
            time.sleep(0.01)

        raise RuntimeError("No se pudo obtener un frame de la cámara dentro del tiempo límite.")

    def release(self):
        """Termina el proceso rpicam-vid y libera recursos."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._buffer = b""