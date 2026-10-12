import unittest

from core.states import RobotState, RobotStateController


class TestRobotStateController(unittest.TestCase):

    def setUp(self):
        self.controller = RobotStateController(
            presence_confirm=0.5,
            absence_confirm=1.0,
            greeting_duration=2.0,
            goodbye_duration=2.0,
            thinking_hold=0.6
        )

    def test_initial_state_is_idle(self):
        self.assertEqual(
            self.controller.state,
            RobotState.IDLE
        )

        self.assertFalse(
            self.controller.stable_present
        )

    def test_transient_presence_does_not_trigger_greeting(self):
        state = self.controller.update(
            True,
            now=0.0
        )

        self.assertEqual(
            state,
            RobotState.IDLE
        )

        state = self.controller.update(
            False,
            now=0.2
        )

        self.assertEqual(
            state,
            RobotState.IDLE
        )

        self.assertFalse(
            self.controller.stable_present
        )

    def test_confirmed_presence_triggers_greeting(self):
        self.controller.update(
            True,
            now=0.0
        )

        state = self.controller.update(
            True,
            now=0.5
        )

        self.assertEqual(
            state,
            RobotState.GREETING
        )

        self.assertTrue(
            self.controller.stable_present
        )

    def test_greeting_changes_to_detecting(self):
        self.controller.update(
            True,
            now=0.0
        )

        self.controller.update(
            True,
            now=0.5
        )

        state = self.controller.update(
            True,
            now=2.4
        )

        self.assertEqual(
            state,
            RobotState.GREETING
        )

        state = self.controller.update(
            True,
            now=2.5
        )

        self.assertEqual(
            state,
            RobotState.DETECTING
        )

    def test_gesture_changes_to_thinking(self):
        self.controller.update(
            True,
            now=0.0
        )

        self.controller.update(
            True,
            now=0.5
        )

        self.controller.update(
            True,
            now=2.5
        )

        state = self.controller.update(
            True,
            gesture="THUMBS_UP",
            now=3.0
        )

        self.assertEqual(
            state,
            RobotState.THINKING
        )

    def test_thinking_is_held_briefly(self):
        self.controller.update(
            True,
            now=0.0
        )

        self.controller.update(
            True,
            now=0.5
        )

        self.controller.update(
            True,
            now=2.5
        )

        self.controller.update(
            True,
            gesture="THUMBS_UP",
            now=3.0
        )

        state = self.controller.update(
            True,
            gesture="UNKNOWN",
            now=3.4
        )

        self.assertEqual(
            state,
            RobotState.THINKING
        )

        state = self.controller.update(
            True,
            gesture="UNKNOWN",
            now=3.6
        )

        self.assertEqual(
            state,
            RobotState.DETECTING
        )

    def test_transient_absence_does_not_trigger_goodbye(self):
        self.controller.update(
            True,
            now=0.0
        )

        self.controller.update(
            True,
            now=0.5
        )

        self.controller.update(
            True,
            now=2.5
        )

        state = self.controller.update(
            False,
            now=3.0
        )

        self.assertEqual(
            state,
            RobotState.DETECTING
        )

        state = self.controller.update(
            True,
            now=3.4
        )

        self.assertEqual(
            state,
            RobotState.DETECTING
        )

        self.assertTrue(
            self.controller.stable_present
        )

    def test_confirmed_absence_triggers_goodbye(self):
        self.controller.update(
            True,
            now=0.0
        )

        self.controller.update(
            True,
            now=0.5
        )

        self.controller.update(
            True,
            now=2.5
        )

        self.controller.update(
            False,
            now=3.0
        )

        state = self.controller.update(
            False,
            now=4.0
        )

        self.assertEqual(
            state,
            RobotState.GOODBYE
        )

        self.assertFalse(
            self.controller.stable_present
        )

    def test_goodbye_changes_to_idle(self):
        self.controller.update(
            True,
            now=0.0
        )

        self.controller.update(
            True,
            now=0.5
        )

        self.controller.update(
            True,
            now=2.5
        )

        self.controller.update(
            False,
            now=3.0
        )

        self.controller.update(
            False,
            now=4.0
        )

        state = self.controller.update(
            False,
            now=5.9
        )

        self.assertEqual(
            state,
            RobotState.GOODBYE
        )

        state = self.controller.update(
            False,
            now=6.0
        )

        self.assertEqual(
            state,
            RobotState.IDLE
        )

    def test_reentry_after_goodbye_triggers_new_greeting(self):
        self.controller.update(
            True,
            now=0.0
        )

        self.controller.update(
            True,
            now=0.5
        )

        self.controller.update(
            True,
            now=2.5
        )

        self.controller.update(
            False,
            now=3.0
        )

        self.controller.update(
            False,
            now=4.0
        )

        self.controller.update(
            False,
            now=6.0
        )

        self.controller.update(
            True,
            now=7.0
        )

        state = self.controller.update(
            True,
            now=7.5
        )

        self.assertEqual(
            state,
            RobotState.GREETING
        )

        self.assertTrue(
            self.controller.stable_present
        )


if __name__ == "__main__":
    unittest.main()
