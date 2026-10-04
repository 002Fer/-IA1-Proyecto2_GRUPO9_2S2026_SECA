import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from core.states import RobotState
from ui.robot import RobotRenderer


class TestRobotRenderer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.assets_dir = Path(self.temp_dir.name)

        for filename in RobotRenderer.ASSET_FILES.values():
            sprite = np.zeros(
                (100, 80, 4),
                dtype=np.uint8
            )

            sprite[:, :, :3] = 255
            sprite[:, :, 3] = 255

            cv2.imwrite(
                str(self.assets_dir / filename),
                sprite
            )

        self.renderer = RobotRenderer(
            assets_dir=self.assets_dir,
            robot_width=80,
            margin=10
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_states_have_asset_mapping(self):
        self.assertEqual(
            set(RobotRenderer.ASSET_FILES.keys()),
            set(RobotState)
        )

    def test_asset_path_matches_state(self):
        path = self.renderer.get_asset_path(
            RobotState.IDLE
        )

        self.assertEqual(
            path.name,
            "idle.png"
        )

    def test_load_sprite_uses_cache(self):
        first = self.renderer.load_sprite(
            RobotState.IDLE
        )

        second = self.renderer.load_sprite(
            RobotState.IDLE
        )

        self.assertIs(first, second)

    def test_missing_asset_raises_error(self):
        renderer = RobotRenderer(
            assets_dir=self.assets_dir / "missing"
        )

        with self.assertRaises(FileNotFoundError):
            renderer.load_sprite(
                RobotState.IDLE
            )

    def test_render_preserves_frame_shape(self):
        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8
        )

        result = self.renderer.render(
            frame,
            RobotState.IDLE
        )

        self.assertEqual(
            result.shape,
            (480, 640, 3)
        )

    def test_render_changes_frame(self):
        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8
        )

        before = frame.copy()

        result = self.renderer.render(
            frame,
            RobotState.SUCCESS
        )

        self.assertFalse(
            np.array_equal(before, result)
        )

    def test_small_frame_is_supported(self):
        frame = np.zeros(
            (120, 160, 3),
            dtype=np.uint8
        )

        result = self.renderer.render(
            frame,
            RobotState.GREETING
        )

        self.assertEqual(
            result.shape,
            (120, 160, 3)
        )


if __name__ == "__main__":
    unittest.main()
