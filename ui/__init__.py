"""
Interfaz visual del agente AURA.

Este paquete expone los componentes públicos necesarios para
integrar Realidad Aumentada, Robot 2D y estados visuales.
"""

from core.states import RobotState, RobotStateController
from ui.overlay import AuraUI, AugmentedRealityOverlay
from ui.robot import RobotRenderer


__all__ = [
    "AuraUI",
    "AugmentedRealityOverlay",
    "RobotRenderer",
    "RobotState",
    "RobotStateController",
]
