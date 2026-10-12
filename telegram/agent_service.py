"""Contrato y adaptadores del agente AURA.

Los handlers de Telegram dependen únicamente de AgentService. Esto permite
probar todo desde una PC y luego conectar el agente real de Raspberry Pi sin
reescribir la capa Telegram.
"""

import json
import time
from datetime import datetime
from pathlib import Path


class AgentService:
    """Interfaz común que debe implementar el agente de AURA."""

    def get_status(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def get_history(self):
        raise NotImplementedError

    def get_gestures(self):
        raise NotImplementedError

    def add_gesture(self, name):
        raise NotImplementedError

    def delete_gesture(self, name):
        raise NotImplementedError

    def get_actions(self):
        raise NotImplementedError

    def add_action(self, name):
        raise NotImplementedError

    def link_action(self, gesture, action):
        raise NotImplementedError

    def set_gesture_message(self, gesture, message):
        raise NotImplementedError

    def get_rpa_processes(self):
        raise NotImplementedError

    def get_logs(self, limit=10):
        raise NotImplementedError

    def execute_gesture(self, gesture, confidence=0):
        """Punto de integración con visión/RPA.

        El módulo de visión puede llamar este método después de clasificar un
        gesto. La implementación debe resolver gesto -> acción -> RPA/mensaje.
        """
        raise NotImplementedError


class JsonStore:
    """Persistencia pequeña y sin dependencias para desarrollo del proyecto."""

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "agent_state.json"

    def load(self, defaults):
        if not self.path.exists():
            self.save(defaults)
            return defaults
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data
        except (OSError, ValueError):
            self.save(defaults)
            return defaults

    def save(self, data):
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        temp.replace(self.path)


class MockAgentService(AgentService):
    """Implementación para trabajar completamente desde PC."""

    def __init__(self, data_dir="data"):
        self.store = JsonStore(data_dir)
        defaults = {
            "status": "RUNNING",
            "recognition": "ACTIVE",
            "cpu": 35,
            "ram": 48,
            "gestures": [
                {"name": "mano_levantada", "enabled": True},
                {"name": "pulgar_arriba", "enabled": True},
                {"name": "pulgar_abajo", "enabled": True},
                {"name": "señalar_izquierda", "enabled": True},
                {"name": "señalar_derecha", "enabled": True},
                {"name": "brazos_cruzados", "enabled": True},
            ],
            "actions": [
                {"name": "saludar", "description": "Responder al usuario"},
                {"name": "confirmar", "description": "Confirmar una interacción"},
                {"name": "rechazar", "description": "Responder a un rechazo"},
            ],
            "links": {},
            "messages": {},
            "history": [],
            "logs": [],
        }
        self.state = self.store.load(defaults)
        self._log("Servicio MockAgentService iniciado")

    def _save(self):
        self.store.save(self.state)

    def _log(self, message, level="INFO"):
        self.state.setdefault("logs", []).insert(0, {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "message": message,
        })
        self.state["logs"] = self.state["logs"][:100]

    def get_status(self):
        return {
            "cpu": self.state.get("cpu", 35),
            "ram": self.state.get("ram", 48),
            "status": self.state.get("status", "STOPPED"),
            "recognition": self.state.get("recognition", "INACTIVE"),
        }

    def start(self):
        self.state["status"] = "RUNNING"
        self.state["recognition"] = "ACTIVE"
        self._log("AURA iniciado")
        self._save()
        return True

    def stop(self):
        self.state["status"] = "STOPPED"
        self.state["recognition"] = "INACTIVE"
        self._log("AURA detenido")
        self._save()
        return True

    def get_history(self):
        return list(self.state.get("history", []))

    def get_gestures(self):
        return list(self.state.get("gestures", []))

    def add_gesture(self, name):
        if not name:
            return False, "El nombre del gesto es obligatorio."
        if any(g["name"].lower() == name.lower() for g in self.state["gestures"]):
            return False, "El gesto ya existe."
        self.state["gestures"].append({"name": name, "enabled": True})
        self._log(f"Gesto registrado: {name}")
        self._save()
        return True, f"Gesto '{name}' registrado correctamente."

    def delete_gesture(self, name):
        for gesture in self.state["gestures"]:
            if gesture["name"].lower() == name.lower():
                gesture["enabled"] = False
                self._log(f"Gesto deshabilitado: {name}")
                self._save()
                return True, f"Gesto '{name}' deshabilitado."
        return False, "Gesto no encontrado."

    def get_actions(self):
        return list(self.state.get("actions", []))

    def add_action(self, name):
        if not name:
            return False, "El nombre de la acción es obligatorio."
        if any(a["name"].lower() == name.lower() for a in self.state["actions"]):
            return False, "La acción ya existe."
        self.state["actions"].append({"name": name, "description": "Acción definida por el usuario"})
        self._log(f"Acción registrada: {name}")
        self._save()
        return True, f"Acción '{name}' creada correctamente."

    def link_action(self, gesture, action):
        gestures = {g["name"].lower(): g for g in self.state["gestures"]}
        actions = {a["name"].lower(): a for a in self.state["actions"]}
        if gesture.lower() not in gestures:
            return False, f"No existe el gesto '{gesture}'."
        if action.lower() not in actions:
            return False, f"No existe la acción '{action}'."
        self.state["links"][gesture] = action
        self._log(f"Vinculación: {gesture} -> {action}")
        self._save()
        return True, f"'{gesture}' ahora ejecuta '{action}'."

    def set_gesture_message(self, gesture, message):
        if not any(g["name"].lower() == gesture.lower() for g in self.state["gestures"]):
            return False, f"No existe el gesto '{gesture}'."
        self.state["messages"][gesture] = message
        self._log(f"Mensaje configurado para gesto: {gesture}")
        self._save()
        return True, f"Mensaje configurado para '{gesture}'."

    def get_rpa_processes(self):
        return [
            {"name": "consultar_horario", "description": "Consultar horario académico"},
            {"name": "descargar_material", "description": "Descargar material desde UEDI"},
            {"name": "completar_formulario", "description": "Completar formulario automáticamente"},
        ]

    def get_logs(self, limit=10):
        return self.state.get("logs", [])[:limit]

    def execute_gesture(self, gesture, confidence=0):
        action = self.state.get("links", {}).get(gesture)
        message = self.state.get("messages", {}).get(gesture)
        event = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gesture": gesture,
            "confidence": confidence,
            "action": action or "sin_accion",
        }
        self.state.setdefault("history", []).insert(0, event)
        self.state["history"] = self.state["history"][:100]
        self._log(f"Gesto detectado: {gesture}; acción: {action or 'sin_accion'}")
        self._save()
        return {"action": action, "message": message, "event": event}


class RaspberryAgentService(MockAgentService):
    """Adaptador base para Raspberry Pi.

    Mantiene la administración de gestos/acciones y sustituye únicamente las
    métricas y los puntos de control del agente. Los módulos reales de visión
    y RPA pueden inyectarse mediante set_runtime_adapter().
    """

    def __init__(self, data_dir="data"):
        super().__init__(data_dir)
        self.runtime_adapter = None

    def set_runtime_adapter(self, adapter):
        """Adapter esperado: get_status(), start(), stop()."""
        self.runtime_adapter = adapter

    def get_status(self):
        if self.runtime_adapter:
            return self.runtime_adapter.get_status()
        return {
            "cpu": self._linux_cpu_percent(),
            "ram": self._linux_ram_percent(),
            "status": self.state.get("status", "STOPPED"),
            "recognition": self.state.get("recognition", "INACTIVE"),
        }

    def start(self):
        if self.runtime_adapter:
            result = self.runtime_adapter.start()
            self.state["status"] = "RUNNING"
            self.state["recognition"] = "ACTIVE"
            self._log("AURA iniciado mediante runtime adapter")
            self._save()
            return result
        return super().start()

    def stop(self):
        if self.runtime_adapter:
            result = self.runtime_adapter.stop()
            self.state["status"] = "STOPPED"
            self.state["recognition"] = "INACTIVE"
            self._log("AURA detenido mediante runtime adapter")
            self._save()
            return result
        return super().stop()

    @staticmethod
    def _linux_cpu_percent():
        def read_cpu():
            with open("/proc/stat", "r", encoding="utf-8") as fh:
                values = fh.readline().split()[1:]
            numbers = [int(x) for x in values]
            idle = numbers[3] + (numbers[4] if len(numbers) > 4 else 0)
            total = sum(numbers)
            return idle, total

        try:
            idle1, total1 = read_cpu()
            time.sleep(0.15)
            idle2, total2 = read_cpu()
            total_delta = total2 - total1
            idle_delta = idle2 - idle1
            if total_delta <= 0:
                return 0
            return round((1 - idle_delta / total_delta) * 100, 1)
        except (OSError, ValueError, IndexError):
            return 0

    @staticmethod
    def _linux_ram_percent():
        try:
            mem = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    key, value = line.split(":", 1)
                    mem[key] = int(value.strip().split()[0])
            total = mem.get("MemTotal", 0)
            available = mem.get("MemAvailable", 0)
            if not total:
                return 0
            return round((total - available) / total * 100, 1)
        except (OSError, ValueError):
            return 0
