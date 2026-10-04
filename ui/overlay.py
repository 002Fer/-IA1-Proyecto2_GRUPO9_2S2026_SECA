import cv2
import numpy as np

from core.states import RobotState, get_state_label
from ui.robot import RobotRenderer


class AugmentedRealityOverlay:
    """
    Construye la capa de Realidad Aumentada de AURA.

    Recibe resultados previamente procesados por el módulo de visión.
    Este módulo no ejecuta MediaPipe ni clasifica gestos.
    """

    HAND_CONNECTIONS = (
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20),
        (0, 17),
    )

    POSE_CONNECTIONS = (
        (11, 12),
        (11, 13),
        (13, 15),
        (12, 14),
        (14, 16),
        (11, 23),
        (12, 24),
        (23, 24),
    )

    def __init__(
        self,
        robot_renderer=None,
        panel_alpha=0.65
    ):
        self.robot_renderer = (
            robot_renderer
            if robot_renderer is not None
            else RobotRenderer()
        )

        self.panel_alpha = panel_alpha

    @staticmethod
    def _normalized_to_pixel(
        landmark,
        frame_width,
        frame_height
    ):
        x = int(landmark.x * frame_width)
        y = int(landmark.y * frame_height)

        x = max(0, min(frame_width - 1, x))
        y = max(0, min(frame_height - 1, y))

        return x, y

    @staticmethod
    def _bounding_box(
        landmarks,
        frame_width,
        frame_height,
        padding=15
    ):
        if landmarks is None or len(landmarks) == 0:
            return None

        points = [
            AugmentedRealityOverlay._normalized_to_pixel(
                landmark,
                frame_width,
                frame_height
            )
            for landmark in landmarks
        ]

        xs = [point[0] for point in points]
        ys = [point[1] for point in points]

        x1 = max(0, min(xs) - padding)
        y1 = max(0, min(ys) - padding)
        x2 = min(frame_width - 1, max(xs) + padding)
        y2 = min(frame_height - 1, max(ys) + padding)

        return x1, y1, x2, y2

    def draw_hand_landmarks(
        self,
        frame,
        hand_results
    ):
        if (
            hand_results is None
            or not getattr(
                hand_results,
                "hand_landmarks",
                None
            )
        ):
            return frame

        frame_height, frame_width = frame.shape[:2]

        for hand_landmarks in hand_results.hand_landmarks:
            points = [
                self._normalized_to_pixel(
                    landmark,
                    frame_width,
                    frame_height
                )
                for landmark in hand_landmarks
            ]

            for start, end in self.HAND_CONNECTIONS:
                if (
                    start < len(points)
                    and end < len(points)
                ):
                    cv2.line(
                        frame,
                        points[start],
                        points[end],
                        (0, 220, 255),
                        2,
                        cv2.LINE_AA
                    )

            for point in points:
                cv2.circle(
                    frame,
                    point,
                    4,
                    (0, 255, 120),
                    -1,
                    cv2.LINE_AA
                )

            bbox = self._bounding_box(
                hand_landmarks,
                frame_width,
                frame_height,
                padding=12
            )

            if bbox is not None:
                x1, y1, x2, y2 = bbox

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 220, 255),
                    2
                )

                cv2.putText(
                    frame,
                    "MANO",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 220, 255),
                    2,
                    cv2.LINE_AA
                )

        return frame

    def draw_pose_landmarks(
        self,
        frame,
        pose_results
    ):
        if (
            pose_results is None
            or not getattr(
                pose_results,
                "pose_landmarks",
                None
            )
        ):
            return frame

        frame_height, frame_width = frame.shape[:2]

        for pose_landmarks in pose_results.pose_landmarks:
            points = [
                self._normalized_to_pixel(
                    landmark,
                    frame_width,
                    frame_height
                )
                for landmark in pose_landmarks
            ]

            for start, end in self.POSE_CONNECTIONS:
                if (
                    start < len(points)
                    and end < len(points)
                ):
                    cv2.line(
                        frame,
                        points[start],
                        points[end],
                        (255, 170, 0),
                        2,
                        cv2.LINE_AA
                    )

            for index in (
                11, 12, 13, 14,
                15, 16, 23, 24
            ):
                if index < len(points):
                    cv2.circle(
                        frame,
                        points[index],
                        5,
                        (255, 120, 0),
                        -1,
                        cv2.LINE_AA
                    )

            bbox = self._bounding_box(
                pose_landmarks,
                frame_width,
                frame_height,
                padding=20
            )

            if bbox is not None:
                x1, y1, x2, y2 = bbox

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 170, 0),
                    2
                )

                cv2.putText(
                    frame,
                    "PERSONA",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 170, 0),
                    2,
                    cv2.LINE_AA
                )

        return frame

    def draw_info_panel(
        self,
        frame,
        perception,
        state,
        interpretation="Pendiente",
        action="Ninguna"
    ):
        overlay = frame.copy()

        panel_width = min(
            520,
            frame.shape[1] - 20
        )

        panel_height = min(
            285,
            frame.shape[0] - 20
        )

        cv2.rectangle(
            overlay,
            (10, 10),
            (10 + panel_width, 10 + panel_height),
            (20, 20, 20),
            -1
        )

        cv2.addWeighted(
            overlay,
            self.panel_alpha,
            frame,
            1.0 - self.panel_alpha,
            0,
            frame
        )

        person_detected = perception.get(
            "person_detected",
            False
        )

        gesture = perception.get(
            "gesture",
            "UNKNOWN"
        )

        confidence = perception.get(
            "confidence",
            0.0
        )

        proximity = perception.get(
            "proximity",
            "UNKNOWN"
        )

        lines = (
            ("AURA", 0.85),
            (
                f"Estado: {get_state_label(state)}",
                0.62
            ),
            (
                "Persona: "
                + (
                    "Detectada"
                    if person_detected
                    else "No detectada"
                ),
                0.62
            ),
            (
                f"Gesto: {gesture}",
                0.62
            ),
            (
                f"Confianza: {confidence:.2f}",
                0.62
            ),
            (
                f"Proximidad: {proximity}",
                0.62
            ),
            (
                f"Interpretacion: {interpretation}",
                0.56
            ),
            (
                f"Accion: {action}",
                0.56
            ),
        )

        y = 42

        for text, scale in lines:
            cv2.putText(
                frame,
                text,
                (28, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                (245, 245, 245),
                2,
                cv2.LINE_AA
            )

            y += 32

        return frame

    def render(
        self,
        result,
        state=RobotState.IDLE,
        interpretation="Pendiente",
        action="Ninguna"
    ):
        if result is None:
            raise ValueError(
                "El resultado de visión no puede ser None."
            )

        if "frame" not in result:
            raise KeyError(
                "El resultado debe contener la clave 'frame'."
            )

        frame = result["frame"]

        if frame is None:
            raise ValueError(
                "El frame de visión no puede ser None."
            )

        frame = frame.copy()

        perception = {
            "person_detected": result.get(
                "person_detected",
                False
            ),
            "gesture": result.get(
                "gesture",
                "UNKNOWN"
            ),
            "confidence": result.get(
                "confidence",
                0.0
            ),
            "proximity": result.get(
                "proximity",
                "UNKNOWN"
            ),
        }

        frame = self.draw_pose_landmarks(
            frame,
            result.get("pose_results")
        )

        frame = self.draw_hand_landmarks(
            frame,
            result.get("hand_results")
        )

        frame = self.draw_info_panel(
            frame,
            perception,
            state,
            interpretation,
            action
        )

        frame = self.robot_renderer.render(
            frame,
            state
        )

        return frame
