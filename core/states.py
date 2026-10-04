import time
from enum import Enum


class RobotState(str, Enum):
    """
    Estados visuales obligatorios del robot virtual AURA.
    """

    IDLE = "IDLE"
    GREETING = "GREETING"
    DETECTING = "DETECTING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    GOODBYE = "GOODBYE"


STATE_LABELS = {
    RobotState.IDLE: "Esperando",
    RobotState.GREETING: "Saludando",
    RobotState.DETECTING: "Detectando",
    RobotState.THINKING: "Interpretando",
    RobotState.EXECUTING: "Ejecutando",
    RobotState.SUCCESS: "Exito",
    RobotState.ERROR: "Error",
    RobotState.GOODBYE: "Despedida",
}


def get_state_label(state: RobotState) -> str:
    """
    Devuelve el texto visible asociado a un estado del robot.
    """
    return STATE_LABELS[state]


class RobotStateController:
    """
    Controla los estados visuales del robot AURA a partir de
    la percepción recibida.

    Incluye estabilización temporal para evitar que detecciones
    intermitentes de presencia provoquen cambios visuales bruscos.
    """

    def __init__(
        self,
        presence_confirm=0.5,
        absence_confirm=1.0,
        greeting_duration=2.0,
        goodbye_duration=2.0,
        thinking_hold=0.6
    ):
        durations = (
            presence_confirm,
            absence_confirm,
            greeting_duration,
            goodbye_duration,
            thinking_hold,
        )

        if any(value < 0 for value in durations):
            raise ValueError(
                "Las duraciones del controlador no pueden ser negativas."
            )

        self.presence_confirm = presence_confirm
        self.absence_confirm = absence_confirm
        self.greeting_duration = greeting_duration
        self.goodbye_duration = goodbye_duration
        self.thinking_hold = thinking_hold

        self.state = RobotState.IDLE
        self._state_since = None

        self._stable_present = False
        self._presence_candidate_since = None
        self._absence_candidate_since = None
        self._last_gesture_at = None

    @staticmethod
    def _resolve_time(now):
        if now is None:
            return time.monotonic()

        return float(now)

    def reset(self, now=None):
        """
        Restablece el controlador al estado inicial.
        """
        now = self._resolve_time(now)

        self.state = RobotState.IDLE
        self._state_since = now

        self._stable_present = False
        self._presence_candidate_since = None
        self._absence_candidate_since = None
        self._last_gesture_at = None

        return self.state

    @property
    def stable_present(self):
        """
        Indica si la presencia de una persona ya fue confirmada.
        """
        return self._stable_present

    def _set_state(self, state, now):
        if state != self.state:
            self.state = state
            self._state_since = now

    def update(
        self,
        person_detected,
        gesture="UNKNOWN",
        now=None
    ):
        """
        Actualiza el estado visual usando la percepción actual.

        person_detected:
            Presencia reportada por Computer Vision.

        gesture:
            Gesto actualmente reconocido.

        now:
            Tiempo opcional para pruebas deterministas.
            En ejecución real se utiliza time.monotonic().
        """
        now = self._resolve_time(now)

        if self._state_since is None:
            self._state_since = now

        person_detected = bool(person_detected)
        gesture = gesture or "UNKNOWN"

        # --------------------------------------------------
        # PERSONA YA CONFIRMADA
        # --------------------------------------------------
        if self._stable_present:
            self._presence_candidate_since = None

            if person_detected:
                self._absence_candidate_since = None

            else:
                if self._absence_candidate_since is None:
                    self._absence_candidate_since = now

                absence_time = (
                    now - self._absence_candidate_since
                )

                if absence_time >= self.absence_confirm:
                    self._stable_present = False
                    self._absence_candidate_since = None
                    self._last_gesture_at = None

                    self._set_state(
                        RobotState.GOODBYE,
                        now
                    )

                    return self.state

        # --------------------------------------------------
        # PERSONA TODAVÍA NO CONFIRMADA
        # --------------------------------------------------
        else:
            self._absence_candidate_since = None

            if person_detected:
                if self._presence_candidate_since is None:
                    self._presence_candidate_since = now

                presence_time = (
                    now - self._presence_candidate_since
                )

                if presence_time >= self.presence_confirm:
                    self._stable_present = True
                    self._presence_candidate_since = None

                    self._set_state(
                        RobotState.GREETING,
                        now
                    )

                    return self.state

            else:
                self._presence_candidate_since = None

            if not self._stable_present:
                if self.state == RobotState.GOODBYE:
                    goodbye_time = (
                        now - self._state_since
                    )

                    if goodbye_time >= self.goodbye_duration:
                        self._set_state(
                            RobotState.IDLE,
                            now
                        )

                else:
                    self._set_state(
                        RobotState.IDLE,
                        now
                    )

                return self.state

        # --------------------------------------------------
        # SALUDO
        # --------------------------------------------------
        if self.state == RobotState.GREETING:
            greeting_time = (
                now - self._state_since
            )

            if greeting_time < self.greeting_duration:
                return self.state

            self._set_state(
                RobotState.DETECTING,
                now
            )

        # --------------------------------------------------
        # INTERPRETACIÓN DE GESTO
        # --------------------------------------------------
        if gesture != "UNKNOWN":
            self._last_gesture_at = now

            self._set_state(
                RobotState.THINKING,
                now
            )

            return self.state

        # Mantener THINKING brevemente aunque Vision pierda
        # el gesto durante uno o varios frames.
        if (
            self.state == RobotState.THINKING
            and self._last_gesture_at is not None
        ):
            gesture_elapsed = (
                now - self._last_gesture_at
            )

            if gesture_elapsed < self.thinking_hold:
                return self.state

        self._last_gesture_at = None

        self._set_state(
            RobotState.DETECTING,
            now
        )

        return self.state
