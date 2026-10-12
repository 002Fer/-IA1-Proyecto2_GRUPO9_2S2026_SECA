import unittest

import numpy as np

from core.states import RobotState, RobotStateController
from ui.overlay import AuraUI
from ui.robot import RobotRenderer


class TestAuraUI(unittest.TestCase):

    def setUp(self):
        controller = RobotStateController(
            presence_confirm=0.0,
            absence_confirm=0.0,
            greeting_duration=0.0,
            goodbye_duration=0.0,
            thinking_hold=0.0,
            success_duration=1.0,
            error_duration=1.0
        )

        renderer = RobotRenderer(
            assets_dir="ui/assets",
            robot_width=100,
            margin=10
        )

        self.ui = AuraUI(
            state_controller=controller,
            robot_renderer=renderer
        )

    @staticmethod
    def vision_result(
        person=False,
        gesture="UNKNOWN"
    ):
        return {
            "frame": np.zeros(
                (480, 640, 3),
                dtype=np.uint8
            ),
            "person_detected": person,
            "gesture": gesture,
            "confidence": 0.0,
            "proximity": "UNKNOWN",
            "hand_results": None,
            "pose_results": None,
        }

    def test_no_person_returns_idle(self):
        result = self.ui.process(
            self.vision_result(
                person=False
            ),
            now=0.0
        )

        self.assertEqual(
            result["state"],
            RobotState.IDLE
        )

        self.assertEqual(
            result["interpretation"],
            "Esperando usuario"
        )

    def test_person_can_trigger_greeting(self):
        result = self.ui.process(
            self.vision_result(
                person=True
            ),
            now=0.0
        )

        self.assertEqual(
            result["state"],
            RobotState.GREETING
        )

        self.assertEqual(
            result["action"],
            "Saludar"
        )

    def test_gesture_is_presented_as_thinking(self):
        self.ui.process(
            self.vision_result(
                person=True
            ),
            now=0.0
        )

        result = self.ui.process(
            self.vision_result(
                person=True,
                gesture="THUMBS_UP"
            ),
            now=0.1
        )

        self.assertEqual(
            result["state"],
            RobotState.THINKING
        )

        self.assertEqual(
            result["interpretation"],
            "Aprobacion"
        )

        self.assertEqual(
            result["action"],
            "Confirmar"
        )

    def test_running_execution_returns_executing(self):
        result = self.ui.process(
            self.vision_result(
                person=True
            ),
            execution_status="running",
            now=0.0
        )

        self.assertEqual(
            result["state"],
            RobotState.EXECUTING
        )

        self.assertEqual(
            result["action"],
            "Ejecutando proceso"
        )

    def test_success_execution_returns_success(self):
        result = self.ui.process(
            self.vision_result(
                person=True
            ),
            execution_status="success",
            now=0.0
        )

        self.assertEqual(
            result["state"],
            RobotState.SUCCESS
        )

        self.assertEqual(
            result["interpretation"],
            "Accion completada"
        )

    def test_error_execution_returns_error(self):
        result = self.ui.process(
            self.vision_result(
                person=True
            ),
            execution_status="error",
            now=0.0
        )

        self.assertEqual(
            result["state"],
            RobotState.ERROR
        )

        self.assertEqual(
            result["interpretation"],
            "Fallo en la accion"
        )

    def test_custom_text_has_priority(self):
        result = self.ui.process(
            self.vision_result(
                person=True
            ),
            execution_status="running",
            interpretation="Consultando portal",
            action="Obtener horario",
            now=0.0
        )

        self.assertEqual(
            result["interpretation"],
            "Consultando portal"
        )

        self.assertEqual(
            result["action"],
            "Obtener horario"
        )

    def test_result_contains_rendered_frame(self):
        vision = self.vision_result(
            person=False
        )

        original = vision["frame"].copy()

        result = self.ui.process(
            vision,
            now=0.0
        )

        self.assertEqual(
            result["frame"].shape,
            original.shape
        )

        self.assertFalse(
            np.array_equal(
                result["frame"],
                original
            )
        )


if __name__ == "__main__":
    unittest.main()
