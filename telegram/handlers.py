"""Handlers de los comandos de AURA.

Esta capa no conoce la Raspberry Pi. Solo depende de AgentService.
"""

try:
    from .commands import parse_command
except ImportError:  # Ejecucion directa: python bot.py
    from commands import parse_command


class TelegramHandlers:
    def __init__(self, telegram, agent, allowed_chat_id=None):
        self.telegram = telegram
        self.agent = agent
        self.allowed_chat_id = str(allowed_chat_id).strip() if allowed_chat_id else ""

    def handle_message(self, message):
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        text = (message.get("text") or "").strip()
        if not text:
            return

        self.last_chat_id = chat_id
        if hasattr(self.agent, "set_last_chat_id"):
            self.agent.set_last_chat_id(chat_id)

        if self.allowed_chat_id and chat_id != self.allowed_chat_id:
            self.telegram.send_message(chat_id, "⛔ Chat no autorizado.")
            return

        command, args = parse_command(text)
        if not command:
            self.telegram.send_message(chat_id, "Comando no reconocido. Usa /help o selecciona un comando del menú.")
            return

        try:
            response = self.dispatch(command, args)
        except Exception as exc:
            response = f"❌ Error procesando {command}: {exc}"
        self.telegram.send_message(chat_id, response)

    def dispatch(self, command, args):
        methods = {
            "/status": self.status,
            "/iniciar": self.iniciar,
            "/apagar": self.apagar,
            "/history": self.history,
            "/gestures": self.gestures,
            "/addGesture": self.add_gesture,
            "/deleteGesture": self.delete_gesture,
            "/actions": self.actions,
            "/addAction": self.add_action,
            "/linkAction": self.link_action,
            "/sendMessage": self.send_message,
            "/rpa": self.rpa,
            "/logs": self.logs,
        }
        return methods[command](args)

    @staticmethod
    def _required(args, usage):
        if not args:
            return f"Uso: {usage}"
        return None

    def status(self, _):
        s = self.agent.get_status()
        return (
            "📊 Estado de AURA\n"
            f"CPU: {s['cpu']}%\n"
            f"RAM: {s['ram']}%\n"
            f"Estado: {s['status']}\n"
            f"Reconocimiento: {s.get('recognition', 'N/D')}"
        )

    def iniciar(self, _):
        self.agent.start()
        return "▶️ AURA iniciado. El reconocimiento está activo."

    def apagar(self, _):
        self.agent.stop()
        return "⏹️ AURA detenido correctamente."

    def history(self, _):
        items = self.agent.get_history()
        if not items:
            return "📜 Historial vacío."
        lines = ["📜 Historial de gestos"]
        for item in items[:10]:
            lines.append(
                f"• {item['date']} | {item['gesture']} | "
                f"confianza: {item['confidence']}% | acción: {item['action']}"
            )
        return "\n".join(lines)

    def gestures(self, _):
        items = self.agent.get_gestures()
        if not items:
            return "✋ No hay gestos registrados."
        lines = ["✋ Gestos registrados"]
        for item in items:
            state = "activo" if item.get("enabled") else "deshabilitado"
            lines.append(f"• {item['name']} ({state})")
        return "\n".join(lines)

    def add_gesture(self, args):
        error = self._required(args, "/addGesture nombre_gesto")
        if error:
            return error
        ok, message = self.agent.add_gesture(args.split()[0])
        return ("✅ " if ok else "❌ ") + message

    def delete_gesture(self, args):
        error = self._required(args, "/deleteGesture nombre_gesto")
        if error:
            return error
        ok, message = self.agent.delete_gesture(args.split()[0])
        return ("✅ " if ok else "❌ ") + message

    def actions(self, _):
        items = self.agent.get_actions()
        if not items:
            return "⚙️ No hay acciones registradas."
        lines = ["⚙️ Acciones disponibles"]
        for item in items:
            lines.append(f"• {item['name']}: {item.get('description', '')}")
        return "\n".join(lines)

    def add_action(self, args):
        error = self._required(args, "/addAction nombre_accion")
        if error:
            return error
        ok, message = self.agent.add_action(args.split()[0])
        return ("✅ " if ok else "❌ ") + message

    def link_action(self, args):
        error = self._required(args, "/linkAction gesto|accion")
        if error:
            return error
        try:
            gesture, action = [x.strip() for x in args.split("|", 1)]
        except ValueError:
            return "Uso: /linkAction gesto|accion"
        if not gesture or not action:
            return "Uso: /linkAction gesto|accion"
        ok, message = self.agent.link_action(gesture, action)
        return ("🔗 " if ok else "❌ ") + message

    def send_message(self, args):
        error = self._required(args, "/sendMessage gesto|mensaje")
        if error:
            return error
        try:
            gesture, message = [x.strip() for x in args.split("|", 1)]
        except ValueError:
            return "Uso: /sendMessage gesto|mensaje"
        if not gesture or not message:
            return "Uso: /sendMessage gesto|mensaje"
        ok, result = self.agent.set_gesture_message(gesture, message)
        return ("💬 " if ok else "❌ ") + result

    def rpa(self, _):
        items = self.agent.get_rpa_processes()
        lines = ["🤖 Procesos RPA disponibles"]
        for item in items:
            lines.append(f"• {item['name']}: {item['description']}")
        return "\n".join(lines)

    def logs(self, _):
        items = self.agent.get_logs(10)
        if not items:
            return "🧾 No hay logs."
        lines = ["🧾 Últimos eventos"]
        for item in items:
            lines.append(f"• [{item['date']}] {item['level']}: {item['message']}")
        return "\n".join(lines)
