import unittest
from types import SimpleNamespace

import numpy as np

from core.states import RobotState
from ui.overlay import AugmentedRealityOverlay
from ui.robot import RobotRenderer


class TestAugmentedRealityOverlay(unittest.TestCase):

    def setUp(self):
        renderer = RobotRenderer(
            assets_dir="ui/assets",
            robot_width=100,
            margin=10
        )

        self.overlay = AugmentedRealityOverlay(
            robot_renderer=renderer
        )

    @staticmethod
    def landmark(x, y):
        return SimpleNamespace(
            x=x,
            y=y
        )

    def test_render_preserves_frame_shape(self):
        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8
        )

        result = {
            "frame": frame,
            "person_detected": True,
            "gesture": "THUMBS_UP",
            "confidence": 0.91,
            "proximity": "MEDIUM",
            "hand_results": None,
            "pose_results": None,
        }

        rendered = self.overlay.render(
            result,
            RobotState.DETECTING,
            interpretation="Aprobacion",
            action="Confirmar"
        )

        self.assertEqual(
            rendered.shape,
            frame.shape
        )

    def test_render_does_not_modify_original_frame(self):
        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8
        )

        original = frame.copy()

        result = {
            "frame": frame
        }

        self.overlay.render(
            result,
            RobotState.IDLE
        )

        self.assertTrue(
            np.array_equal(
                frame,
                original
            )
        )

    def test_render_changes_output(self):
        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8
        )

        result = {
            "frame": frame
        }

        rendered = self.overlay.render(
            result,
            RobotState.IDLE
        )

        self.assertFalse(
            np.array_equal(
                rendered,
                frame
            )
        )

    def test_hand_landmarks_are_drawn(self):
        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8
        )

        hand = [
            self.landmark(
                0.30 + (index * 0.005),
                0.30 + (index * 0.005)
            )
            for index in range(21)
        ]

        hand_results = SimpleNamespace(
            hand_landmarks=[hand]
        )

        before = frame.copy()

        result = self.overlay.draw_hand_landmarks(
            frame,
            hand_results
        )

        self.assertFalse(
            np.array_equal(
                before,
                result
            )
        )

    def test_pose_landmarks_are_drawn(self):
        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8
        )

        pose = [
            self.landmark(
                0.40 + (index * 0.003),
                0.20 + (index * 0.005)
            )
            for index in range(33)
        ]

        pose_results = SimpleNamespace(
            pose_landmarks=[pose]
        )

        before = frame.copy()

        result = self.overlay.draw_pose_landmarks(
            frame,
            pose_results
        )

        self.assertFalse(
            np.array_equal(
                before,
                result
            )
        )

    def test_bounding_box_is_inside_frame(self):
        landmarks = [
            self.landmark(0.0, 0.0),
            self.landmark(1.0, 1.0),
        ]

        bbox = self.overlay._bounding_box(
            landmarks,
            640,
            480,
            padding=20
        )

        x1, y1, x2, y2 = bbox

        self.assertGreaterEqual(x1, 0)
        self.assertGreaterEqual(y1, 0)
        self.assertLess(x2, 640)
        self.assertLess(y2, 480)

    def test_missing_frame_raises_error(self):
        with self.assertRaises(KeyError):
            self.overlay.render(
                {},
                RobotState.IDLE
            )


if __name__ == "__main__":
    unittest.main()
