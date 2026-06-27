"""Shared, process-wide application state.

Kept in one place so the API layer, the live engine and the Telegram bot all read
and write the same store without import cycles.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .accounts import Accounts
from .config import CONFIG
from .telegram import TelegramNotifier

FEED_LIMIT = 80


@dataclass
class Store:
    source: str = "OFFLINE"          # OFFLINE | SIMULATED | LIVE
    matches: dict[str, dict] = field(default_factory=dict)   # fixture_id -> live card
    feed: list[dict] = field(default_factory=list)           # newest-first pundit messages
    fixtures: dict[str, dict] = field(default_factory=dict)  # fixture_id -> static fixture info

    def board(self) -> dict:
        return {
            "source": self.source,
            "matches": list(self.matches.values()),
            "feed": self.feed[:FEED_LIMIT],
        }

    def push_message(self, item: dict) -> None:
        self.feed.insert(0, item)
        del self.feed[FEED_LIMIT:]


STORE = Store()
NOTIFIER = TelegramNotifier(token=CONFIG.tg_token, chat_id=CONFIG.tg_chat_id)
ACCOUNTS = Accounts()
BOT_USERNAME = "TxLINEFUN_bot"
