"""Punto de entrada del bot Telegram de AURA."""

import os
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent

try:
    from .agent_service import MockAgentService, RaspberryAgentService
    from .commands import TELEGRAM_MENU_COMMANDS
    from .handlers import TelegramHandlers
    from .telegram_service import TelegramService
except ImportError:  # Permite ejecutar: python bot.py desde telegram/
    from agent_service import MockAgentService, RaspberryAgentService
    from commands import TELEGRAM_MENU_COMMANDS
    from handlers import TelegramHandlers
    from telegram_service import TelegramService


def load_env(path=None):
    """Carga un .env mínimo."""
    env_path = Path(path) if path else MODULE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def build_agent():
    mode = os.getenv("AURA_MODE", "pc").lower()
    data_dir = Path(os.getenv("AURA_DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = MODULE_DIR / data_dir
    if mode == "rpi":
        return RaspberryAgentService(data_dir)
    return MockAgentService(data_dir)


def main():
    load_env()
    token = os.getenv("AURA_BOT_TOKEN", "").strip()
    if not token or token == "PEGAR_TOKEN_AQUI":
        raise SystemExit("Configura AURA_BOT_TOKEN en .env antes de ejecutar el bot.")

    poll_timeout = int(os.getenv("AURA_POLL_TIMEOUT", "25"))
    allowed_chat_id = os.getenv("AURA_ALLOWED_CHAT_ID", "").strip()

    telegram = TelegramService(token, poll_timeout=poll_timeout)
    agent = build_agent()
    handlers = TelegramHandlers(telegram, agent, allowed_chat_id=allowed_chat_id)

    commands = [
        {"command": name, "description": description}
        for name, description in TELEGRAM_MENU_COMMANDS.items()
    ]
    telegram.set_my_commands(commands)

    me = telegram.get_me()
    print(f"AURA Telegram conectado como @{me.get('username', me.get('first_name', 'bot'))}")
    print(f"Modo: {os.getenv('AURA_MODE', 'pc').lower()}")
    print("Esperando mensajes. Ctrl+C para salir.")
    telegram.run_polling(handlers.handle_message)


if __name__ == "__main__":
    main()
