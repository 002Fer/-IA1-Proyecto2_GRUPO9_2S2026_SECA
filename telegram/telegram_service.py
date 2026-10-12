"""Cliente HTTP nativo para Telegram Bot API."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TelegramAPIError(RuntimeError):
    pass


class TelegramService:
    def __init__(self, token, poll_timeout=25):
        if not token:
            raise ValueError("AURA_BOT_TOKEN no está configurado.")
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.poll_timeout = int(poll_timeout)

    def request(self, method, params=None, timeout=None):
        data = urlencode(params or {}).encode("utf-8")
        request = Request(
            f"{self.base_url}/{method}",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout or self.poll_timeout + 10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise TelegramAPIError(str(exc)) from exc

        if not payload.get("ok"):
            raise TelegramAPIError(payload.get("description", "Error desconocido de Telegram."))
        return payload.get("result")

    def get_me(self):
        return self.request("getMe")

    def get_updates(self, offset=None):
        params = {"timeout": self.poll_timeout, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            params["offset"] = offset
        return self.request("getUpdates", params, timeout=self.poll_timeout + 10)

    def send_message(self, chat_id, text):
        return self.request("sendMessage", {"chat_id": chat_id, "text": text})

    def set_my_commands(self, commands):
        return self.request("setMyCommands", {"commands": json.dumps(commands, ensure_ascii=False)})

    def run_polling(self, on_message):
        offset = None
        while True:
            try:
                updates = self.get_updates(offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if message:
                        on_message(message)
            except KeyboardInterrupt:
                raise
            except TelegramAPIError as exc:
                print(f"[Telegram] {exc}")
                time.sleep(3)
