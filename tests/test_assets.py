import hashlib
import unittest
from pathlib import Path

import cv2

from core.states import RobotState
from ui.robot import RobotRenderer


class TestRobotAssets(unittest.TestCase):

    def setUp(self):
        self.assets_dir = Path("ui/assets")

        self.expected_files = {
            "idle.png",
            "greeting.png",
            "detecting.png",
            "thinking.png",
            "executing.png",
            "success.png",
            "error.png",
            "goodbye.png",
        }

    def test_all_required_assets_exist(self):
        actual_files = {
            path.name
            for path in self.assets_dir.glob("*.png")
        }

        self.assertEqual(
            actual_files,
            self.expected_files
        )

    def test_assets_are_valid_rgba_images(self):
        for filename in self.expected_files:
            path = self.assets_dir / filename

            image = cv2.imread(
                str(path),
                cv2.IMREAD_UNCHANGED
            )

            self.assertIsNotNone(
                image,
                msg=f"No se pudo leer {filename}"
            )

            self.assertEqual(
                image.shape,
                (512, 512, 4),
                msg=f"Dimensiones inválidas en {filename}"
            )

    def test_assets_have_transparency(self):
        for filename in self.expected_files:
            path = self.assets_dir / filename

            image = cv2.imread(
                str(path),
                cv2.IMREAD_UNCHANGED
            )

            alpha = image[:, :, 3]

            self.assertTrue(
                (alpha < 255).any(),
                msg=f"{filename} no contiene transparencia"
            )

    def test_all_assets_are_unique(self):
        hashes = []

        for filename in sorted(self.expected_files):
            path = self.assets_dir / filename

            digest = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

            hashes.append(digest)

        self.assertEqual(
            len(set(hashes)),
            len(self.expected_files)
        )

    def test_renderer_loads_asset_for_every_state(self):
        renderer = RobotRenderer(
            assets_dir=self.assets_dir
        )

        for state in RobotState:
            sprite = renderer.load_sprite(state)

            self.assertIsNotNone(
                sprite,
                msg=f"No se cargó el asset de {state.value}"
            )

            self.assertEqual(
                sprite.shape[2],
                4
            )


if __name__ == "__main__":
    unittest.main()
