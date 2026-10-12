"""Definición de comandos y utilidades de parsing para Telegram."""

COMMANDS = {
    "/status": "Mostrar CPU, RAM y estado del agente",
    "/iniciar": "Iniciar reconocimiento e interacción",
    "/apagar": "Detener reconocimiento e interacción",
    "/history": "Consultar historial de gestos",
    "/gestures": "Listar gestos registrados",
    "/addGesture": "Registrar una nueva seña",
    "/deleteGesture": "Deshabilitar una seña",
    "/actions": "Mostrar acciones disponibles",
    "/addAction": "Crear una acción",
    "/linkAction": "Asociar un gesto con una acción",
    "/sendMessage": "Configurar un mensaje para un gesto",
    "/rpa": "Consultar procesos RPA disponibles",
    "/logs": "Mostrar últimos eventos, errores y acciones",
}

# Telegram recomienda comandos en minúsculas para el menú oficial.
# Los nombres del proyecto se conservan como aliases y el parser es case-insensitive.
TELEGRAM_MENU_COMMANDS = {
    "status": "Mostrar CPU, RAM y estado",
    "iniciar": "Iniciar AURA",
    "apagar": "Detener AURA",
    "history": "Historial de gestos",
    "gestures": "Gestos registrados",
    "addgesture": "Registrar gesto",
    "deletegesture": "Deshabilitar gesto",
    "actions": "Acciones disponibles",
    "addaction": "Crear acción",
    "linkaction": "Vincular gesto con acción",
    "sendmessage": "Configurar mensaje por gesto",
    "rpa": "Procesos RPA",
    "logs": "Últimos eventos y errores",
}


def parse_command(text):
    """Devuelve (comando_canonico, argumentos) o (None, None)."""
    if not text or not text.startswith("/"):
        return None, None

    parts = text.strip().split(maxsplit=1)
    raw = parts[0].split("@", 1)[0].lower()
    args = parts[1].strip() if len(parts) == 2 else ""

    for command in COMMANDS:
        if command.lower() == raw:
            return command, args
    return None, None
