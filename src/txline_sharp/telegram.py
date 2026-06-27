"""Telegram delivery for pundit messages.

Works in two modes:
  - configured (token + chat_id present)  -> sends to Telegram via the Bot API
  - dry-run (anything missing)            -> prints to stdout, so the pipeline runs
                                             end-to-end with no secrets.
Get a token from @BotFather; get the chat_id by messaging the bot then reading
GET /getUpdates (helper below).
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class TelegramNotifier:
    token: str | None = None
    chat_id: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        """Send one message. Returns True if delivered to Telegram, False if dry-run."""
        if not self.enabled:
            print(f"[telegram dry-run] {text}")
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        r = httpx.post(
            url,
            json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
        r.raise_for_status()
        return True

    def discover_chat_id(self) -> str | None:
        """Convenience: read the most recent chat id from getUpdates.

        Message your bot once in Telegram, then call this to find the chat_id.
        """
        if not self.token:
            return None
        r = httpx.get(f"https://api.telegram.org/bot{self.token}/getUpdates", timeout=15)
        r.raise_for_status()
        results = r.json().get("result", [])
        for upd in reversed(results):
            msg = upd.get("message") or upd.get("channel_post")
            if msg and "chat" in msg:
                return str(msg["chat"]["id"])
        return None
