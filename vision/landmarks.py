import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import zipfile
import urllib.request
from pathlib import Path

HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"


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
        print(f"[MediaPipe] Descargando modelo hand_landmarker en {path}...")
        urllib.request.urlretrieve(download_url, path)
        print(f"[MediaPipe] Modelo descargado ({path.stat().st_size} bytes).")

    return str(path)


class HandLandmarks:
    def __init__(self, model_path="models/hand_landmarker.task"):
        valid_model_path = _ensure_valid_model(model_path, HAND_MODEL_URL)
        base_options = python.BaseOptions(
            model_asset_path=valid_model_path
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def process(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )
        return self.detector.detect(mp_image)

    def draw(self, frame, results):
        if results.hand_landmarks:
            for hand_landmarks in results.hand_landmarks:
                for landmark in hand_landmarks:
                    height, width, _ = frame.shape

                    x = int(landmark.x * width)
                    y = int(landmark.y * height)

                    cv2.circle(
                        frame,
                        (x, y),
                        5,
                        (0, 255, 0),
                        -1
                    )
        return frame

    def close(self):
        self.detector.close()