import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import zipfile
import urllib.request
from pathlib import Path

POSE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"


def _ensure_valid_model(model_path: str, download_url: str) -> str:
    path = Path(model_path).resolve()
    needs_download = False

    if not path.exists() or path.stat().st_size < 10000:
        needs_download = True
    else:
        try:
            with zipfile.ZipFile(path, "r") as z:
                if z.testzip() is not None:
                    needs_download = True
        except Exception:
            needs_download = True

    if needs_download:
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[MediaPipe] Descargando modelo pose_landmarker en {path}...")
        urllib.request.urlretrieve(download_url, path)
        print(f"[MediaPipe] Modelo descargado ({path.stat().st_size} bytes).")

    return str(path)


class PoseLandmarks:

    def __init__(self, model_path="models/pose_landmarker.task"):
        valid_model_path = _ensure_valid_model(model_path, POSE_MODEL_URL)
        base_options = python.BaseOptions(
            model_asset_path=valid_model_path
        )
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.detector = vision.PoseLandmarker.create_from_options(
            options
        )

    def process(self, frame):
        """
        Procesa un frame y devuelve los landmarks corporales.
        """
        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )
        return self.detector.detect(mp_image)

    def draw(self, frame, results):
        """
        Dibuja los landmarks corporales sobre el frame.
        """
        if results.pose_landmarks:

            height, width, _ = frame.shape
            for pose_landmarks in results.pose_landmarks:
                for landmark in pose_landmarks:
                    x = int(landmark.x * width)
                    y = int(landmark.y * height)

                    cv2.circle(
                        frame,
                        (x, y),
                        5,
                        (255, 0, 0),
                        -1
                    )
        return frame

    def close(self):
        self.detector.close()