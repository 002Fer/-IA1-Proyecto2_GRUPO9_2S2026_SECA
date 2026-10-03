from enum import Enum


class RobotState(str, Enum):
    """
    Estados visuales obligatorios del robot virtual AURA.

    Estos estados pertenecen exclusivamente a la representación
    visual del agente y no ejecutan acciones de negocio.
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
