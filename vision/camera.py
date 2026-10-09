import subprocess
import numpy as np
import cv2

WIDTH = 640
HEIGHT = 480
CAMERA_FPS = 10


class Camera:
    """
    Captura video de la cámara de la Raspberry Pi usando rpicam-vid
    en modo MJPEG por pipe. Compatible con RPi 3A+ y libcamera.

    Mantiene la misma interfaz open / read / release que la versión
    original basada en cv2.VideoCapture.
    """

    def __init__(self, camera_index=0):
        # camera_index se conserva para mantener compatibilidad con el
        # resto del código, pero no se utiliza con rpicam-vid.
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
        )
        self._buffer = b""

    def read(self):
        """
        Lee el siguiente frame JPEG completo del pipe.
        Bloquea hasta tener un frame decodificable.
        """
        if self._process is None:
            raise RuntimeError("La cámara no está abierta.")

        while True:
            chunk = self._process.stdout.read(65536)
            if not chunk:
                raise RuntimeError(
                    "No se pudo obtener un frame de la cámara."
                )
            self._buffer += chunk

            # Buscar markers JPEG: SOI = FF D8, EOI = FF D9
            start = self._buffer.find(b"\xff\xd8")
            if start == -1:
                # Descartar basura antes del primer SOI
                self._buffer = b""
                continue

            end = self._buffer.find(b"\xff\xd9", start + 2)
            if end == -1:
                # Aún no tenemos el frame completo
                continue

            jpg_bytes = self._buffer[start:end + 2]
            # Guardar el resto del buffer para el siguiente frame
            self._buffer = self._buffer[end + 2:]

            arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if frame is not None:
                return frame
            # Si el frame era inválido, intentar con el siguiente

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