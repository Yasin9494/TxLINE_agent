"""Accounts, sessions and cross-platform (web <-> Telegram) linking.

One account, three ways in — all issuing the same kind of session token:

  * Solana wallet  (Sign-In-With-Solana; required by the hackathon rules)
  * Demo           (instant "Try Demo" — zero friction for judges)
  * Telegram       (link an existing web account to a chat, or log in from one)

Linking uses short one-time codes:
  web -> telegram : web account mints a code; the bot's /start <code> binds the chat
  telegram -> web : bot mints a code; the web pastes it to adopt that account

In-memory for now (single-process); swap for a store later without touching callers.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field

from .siws import SIWS


def _hash_pw(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}:{dk.hex()}"


def _verify_pw(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000)
    return secrets.compare_digest(dk.hex(), dk_hex)


@dataclass
class Account:
    id: str
    display: str
    username: str | None = None
    password_hash: str | None = None
    solana_pubkey: str | None = None
    telegram_chat_id: str | None = None
    is_demo: bool = False
    favourites: set[int] = field(default_factory=set)  # fixture ids the user follows

    def public(self) -> dict:
        return {
            "id": self.id,
            "display": self.display,
            "username": self.username,
            "solana": self.solana_pubkey,
            "solana_linked": self.solana_pubkey is not None,
            "telegram_linked": self.telegram_chat_id is not None,
            "is_demo": self.is_demo,
            "favourites": sorted(self.favourites),
        }


@dataclass
class _Code:
    account_id: str
    created: float


class Accounts:
    LINK_TTL_S = 600

    def __init__(self) -> None:
        self._by_id: dict[str, Account] = {}
        self._by_username: dict[str, str] = {}  # username(lower) -> account_id
        self._by_pubkey: dict[str, str] = {}
        self._by_tg: dict[str, str] = {}
        self._sessions: dict[str, str] = {}     # token -> account_id
        self._codes: dict[str, _Code] = {}      # link code -> account
        self._siws = SIWS()
        self._demo_id: str | None = None

    # --- internals --------------------------------------------------------
    def _new_account(self, display: str, **kw) -> Account:
        aid = "acc_" + secrets.token_hex(8)
        acc = Account(id=aid, display=display, **kw)
        self._by_id[aid] = acc
        return acc

    def _session_for(self, account_id: str) -> str:
        token = "sess_" + secrets.token_urlsafe(24)
        self._sessions[token] = account_id
        return token

    # --- Username / password (primary) ------------------------------------
    def register(self, username: str, password: str) -> str | None:
        key = username.strip().lower()
        if not key or len(password) < 4 or key in self._by_username:
            return None
        acc = self._new_account(display=username.strip(), username=username.strip(),
                                password_hash=_hash_pw(password))
        self._by_username[key] = acc.id
        return self._session_for(acc.id)

    def password_login(self, username: str, password: str) -> str | None:
        aid = self._by_username.get(username.strip().lower())
        if aid is None:
            return None
        acc = self._by_id[aid]
        if not acc.password_hash or not _verify_pw(password, acc.password_hash):
            return None
        return self._session_for(aid)

    # --- Solana (optional link / sign-in) ---------------------------------
    def solana_nonce(self, pubkey: str) -> str:
        return self._siws.issue_nonce(pubkey)

    def solana_login(self, pubkey: str, signature: bytes) -> str | None:
        if self._siws.verify(pubkey, signature) is None:
            return None
        aid = self._by_pubkey.get(pubkey)
        if aid is None:
            acc = self._new_account(display=pubkey[:4] + "…" + pubkey[-4:], solana_pubkey=pubkey)
            self._by_pubkey[pubkey] = acc.id
            aid = acc.id
        return self._session_for(aid)

    def link_solana(self, token: str, pubkey: str, signature: bytes) -> bool:
        """Attach a verified wallet to the already-signed-in account (optional)."""
        acc = self.session_account(token)
        if acc is None or self._siws.verify(pubkey, signature) is None:
            return False
        acc.solana_pubkey = pubkey
        self._by_pubkey[pubkey] = acc.id
        return True

    # --- Demo -------------------------------------------------------------
    def demo_login(self) -> str:
        if self._demo_id is None or self._demo_id not in self._by_id:
            self._demo_id = self._new_account(display="Demo Fan", is_demo=True).id
        return self._session_for(self._demo_id)

    # --- Telegram linking -------------------------------------------------
    def mint_link_code(self, token: str) -> str | None:
        acc = self.session_account(token)
        if acc is None:
            return None
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._codes[code] = _Code(acc.id, time.time())
        return code

    def _pop_code(self, code: str) -> str | None:
        c = self._codes.pop(code, None)
        if c is None or time.time() - c.created > self.LINK_TTL_S:
            return None
        return c.account_id

    def link_telegram(self, code: str, chat_id: str) -> bool:
        """Bot side: bind a chat to the web account that minted `code`."""
        aid = self._pop_code(code)
        if aid is None:
            return False
        self._by_id[aid].telegram_chat_id = chat_id
        self._by_tg[chat_id] = aid
        return True

    def telegram_get_or_create(self, chat_id: str, display: str) -> Account:
        """Bot side: an account keyed by chat (for users who start from Telegram)."""
        aid = self._by_tg.get(chat_id)
        if aid is None:
            acc = self._new_account(display=display, telegram_chat_id=chat_id)
            self._by_tg[chat_id] = acc.id
            return acc
        return self._by_id[aid]

    def mint_web_code_for_chat(self, chat_id: str, display: str) -> str:
        """Bot side: give a code the user pastes on the web to log in as this account."""
        acc = self.telegram_get_or_create(chat_id, display)
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._codes[code] = _Code(acc.id, time.time())
        return code

    def web_login_with_code(self, code: str) -> str | None:
        """Web side: adopt the Telegram account behind a bot-issued code."""
        aid = self._pop_code(code)
        return self._session_for(aid) if aid else None

    # --- lookups ----------------------------------------------------------
    def session_account(self, token: str | None) -> Account | None:
        aid = self._sessions.get(token) if token else None
        return self._by_id.get(aid) if aid else None

    def account_by_chat(self, chat_id: str) -> Account | None:
        aid = self._by_tg.get(chat_id)
        return self._by_id.get(aid) if aid else None

    def all_telegram_chats(self) -> list[str]:
        return list(self._by_tg.keys())
