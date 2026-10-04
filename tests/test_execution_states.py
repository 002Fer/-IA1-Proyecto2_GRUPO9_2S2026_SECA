import unittest

from core.states import RobotState, RobotStateController


class TestExecutionStates(unittest.TestCase):

    def setUp(self):
        self.controller = RobotStateController(
            presence_confirm=0.5,
            absence_confirm=1.0,
            greeting_duration=2.0,
            goodbye_duration=2.0,
            thinking_hold=0.6,
            success_duration=2.0,
            error_duration=2.0
        )

    def test_running_changes_to_executing(self):
        state = self.controller.update(
            False,
            execution_status="running",
            now=0.0
        )

        self.assertEqual(
            state,
            RobotState.EXECUTING
        )

    def test_success_changes_to_success(self):
        state = self.controller.update(
            False,
            execution_status="success",
            now=0.0
        )

        self.assertEqual(
            state,
            RobotState.SUCCESS
        )

    def test_error_changes_to_error(self):
        state = self.controller.update(
            False,
            execution_status="error",
            now=0.0
        )

        self.assertEqual(
            state,
            RobotState.ERROR
        )

    def test_execution_status_is_case_insensitive(self):
        state = self.controller.update(
            False,
            execution_status="RUNNING",
            now=0.0
        )

        self.assertEqual(
            state,
            RobotState.EXECUTING
        )

    def test_success_is_held_after_status_clears(self):
        self.controller.update(
            False,
            execution_status="success",
            now=0.0
        )

        state = self.controller.update(
            False,
            execution_status=None,
            now=1.0
        )

        self.assertEqual(
            state,
            RobotState.SUCCESS
        )

        state = self.controller.update(
            False,
            execution_status=None,
            now=2.0
        )

        self.assertEqual(
            state,
            RobotState.IDLE
        )

    def test_error_is_held_after_status_clears(self):
        self.controller.update(
            False,
            execution_status="error",
            now=0.0
        )

        state = self.controller.update(
            False,
            execution_status=None,
            now=1.0
        )

        self.assertEqual(
            state,
            RobotState.ERROR
        )

        state = self.controller.update(
            False,
            execution_status=None,
            now=2.0
        )

        self.assertEqual(
            state,
            RobotState.IDLE
        )

    def test_running_can_finish_successfully(self):
        self.controller.update(
            True,
            execution_status="running",
            now=0.0
        )

        state = self.controller.update(
            True,
            execution_status="success",
            now=1.0
        )

        self.assertEqual(
            state,
            RobotState.SUCCESS
        )

    def test_invalid_execution_status_raises_error(self):
        with self.assertRaises(ValueError):
            self.controller.update(
                True,
                execution_status="invalid",
                now=0.0
            )


if __name__ == "__main__":
    unittest.main()
