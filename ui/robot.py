from pathlib import Path

import cv2
import numpy as np

from core.states import RobotState


class RobotRenderer:
    """
    Renderiza el robot virtual 2D de AURA sobre un frame de OpenCV.

    Cada estado visual está asociado a un asset PNG diferente.
    Los assets pueden contener transparencia mediante canal alfa.
    """

    ASSET_FILES = {
        RobotState.IDLE: "idle.png",
        RobotState.GREETING: "greeting.png",
        RobotState.DETECTING: "detecting.png",
        RobotState.THINKING: "thinking.png",
        RobotState.EXECUTING: "executing.png",
        RobotState.SUCCESS: "success.png",
        RobotState.ERROR: "error.png",
        RobotState.GOODBYE: "goodbye.png",
    }

    def __init__(
        self,
        assets_dir="ui/assets",
        robot_width=180,
        margin=20
    ):
        self.assets_dir = Path(assets_dir)
        self.robot_width = robot_width
        self.margin = margin
        self._cache = {}

    def get_asset_path(self, state: RobotState) -> Path:
        """
        Devuelve la ruta del asset correspondiente al estado indicado.
        """
        if state not in self.ASSET_FILES:
            raise ValueError(
                f"Estado visual no soportado: {state}"
            )

        return self.assets_dir / self.ASSET_FILES[state]

    def load_sprite(self, state: RobotState):
        """
        Carga el sprite asociado al estado y lo mantiene en memoria
        para evitar lecturas repetitivas desde disco.
        """
        if state in self._cache:
            return self._cache[state]

        asset_path = self.get_asset_path(state)

        if not asset_path.exists():
            raise FileNotFoundError(
                f"No se encontró el asset del robot: {asset_path}"
            )

        sprite = cv2.imread(
            str(asset_path),
            cv2.IMREAD_UNCHANGED
        )

        if sprite is None:
            raise RuntimeError(
                f"No se pudo cargar el asset del robot: {asset_path}"
            )

        if sprite.ndim != 3 or sprite.shape[2] not in (3, 4):
            raise ValueError(
                f"Formato de asset no soportado: {asset_path}"
            )

        self._cache[state] = sprite

        return sprite

    def resize_sprite(self, sprite):
        """
        Redimensiona el sprite manteniendo su proporción.
        """
        height, width = sprite.shape[:2]

        if width <= 0 or height <= 0:
            raise ValueError(
                "El sprite posee dimensiones inválidas."
            )

        scale = self.robot_width / width

        new_width = self.robot_width
        new_height = max(1, int(height * scale))

        return cv2.resize(
            sprite,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )

    @staticmethod
    def _overlay_rgba(frame, sprite, x, y):
        """
        Superpone una imagen BGRA sobre un frame BGR respetando
        el canal alfa.
        """
        sprite_height, sprite_width = sprite.shape[:2]

        roi = frame[
            y:y + sprite_height,
            x:x + sprite_width
        ]

        rgb = sprite[:, :, :3].astype(np.float32)

        alpha = (
            sprite[:, :, 3].astype(np.float32) / 255.0
        )
        alpha = np.expand_dims(alpha, axis=2)

        blended = (
            alpha * rgb
            + (1.0 - alpha) * roi.astype(np.float32)
        )

        frame[
            y:y + sprite_height,
            x:x + sprite_width
        ] = blended.astype(np.uint8)

    @staticmethod
    def _overlay_bgr(frame, sprite, x, y):
        """
        Superpone directamente un sprite BGR sin transparencia.
        """
        sprite_height, sprite_width = sprite.shape[:2]

        frame[
            y:y + sprite_height,
            x:x + sprite_width
        ] = sprite

    def render(
        self,
        frame,
        state: RobotState
    ):
        """
        Dibuja el robot en la esquina inferior derecha del frame.

        Si el sprite excede el tamaño disponible, se reduce
        automáticamente para mantenerse dentro de la imagen.
        """
        if frame is None:
            raise ValueError("El frame no puede ser None.")

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                "El frame debe tener formato BGR de tres canales."
            )

        sprite = self.load_sprite(state)
        sprite = self.resize_sprite(sprite)

        frame_height, frame_width = frame.shape[:2]
        sprite_height, sprite_width = sprite.shape[:2]

        max_width = max(
            1,
            frame_width - (self.margin * 2)
        )
        max_height = max(
            1,
            frame_height - (self.margin * 2)
        )

        if (
            sprite_width > max_width
            or sprite_height > max_height
        ):
            scale = min(
                max_width / sprite_width,
                max_height / sprite_height
            )

            sprite_width = max(
                1,
                int(sprite_width * scale)
            )
            sprite_height = max(
                1,
                int(sprite_height * scale)
            )

            sprite = cv2.resize(
                sprite,
                (sprite_width, sprite_height),
                interpolation=cv2.INTER_AREA
            )

        x = max(
            0,
            frame_width - sprite_width - self.margin
        )
        y = max(
            0,
            frame_height - sprite_height - self.margin
        )

        if sprite.shape[2] == 4:
            self._overlay_rgba(
                frame,
                sprite,
                x,
                y
            )
        else:
            self._overlay_bgr(
                frame,
                sprite,
                x,
                y
            )

        return frame
