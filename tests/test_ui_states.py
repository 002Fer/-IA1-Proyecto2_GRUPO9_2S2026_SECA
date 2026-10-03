import unittest

from ui.states import RobotState, STATE_LABELS, get_state_label


class TestRobotState(unittest.TestCase):

    def test_required_states_exist(self):
        expected_states = {
            "IDLE",
            "GREETING",
            "DETECTING",
            "THINKING",
            "EXECUTING",
            "SUCCESS",
            "ERROR",
            "GOODBYE",
        }

        actual_states = {state.value for state in RobotState}

        self.assertEqual(actual_states, expected_states)

    def test_every_state_has_label(self):
        self.assertEqual(
            set(STATE_LABELS.keys()),
            set(RobotState)
        )

    def test_state_label(self):
        self.assertEqual(
            get_state_label(RobotState.IDLE),
            "Esperando"
        )

        self.assertEqual(
            get_state_label(RobotState.THINKING),
            "Interpretando"
        )

        self.assertEqual(
            get_state_label(RobotState.SUCCESS),
            "Exito"
        )


if __name__ == "__main__":
    unittest.main()
