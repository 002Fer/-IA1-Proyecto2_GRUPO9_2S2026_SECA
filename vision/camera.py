import cv2

class Camera:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.camera = None

    def open(self):
        self.camera = cv2.VideoCapture(self.camera_index)

        if not self.camera.isOpened():
            raise RuntimeError(
                f"No se pudo abrir la cámara con índice {self.camera_index}"
            )

    def read(self):
        if self.camera is None:
            raise RuntimeError("La cámara no está abierta.")
        success, frame = self.camera.read()

        if not success:
            raise RuntimeError("No se pudo obtener un frame de la cámara.")
        return frame

    def release(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None