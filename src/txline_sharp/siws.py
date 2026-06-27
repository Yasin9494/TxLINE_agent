"""Sign-In-With-Solana (SIWS) — wallet-based signup/login.

Closes the track's mandatory "sign up through Solana" requirement with a real,
non-custodial flow (no passwords, no private keys server-side):

  1. client connects a wallet (Phantom/Solflare) and gets its public key
  2. GET  /api/auth/nonce  -> server returns a one-time message to sign
  3. wallet signs the message (ed25519)
  4. POST /api/auth/verify -> server verifies the signature against the pubkey
     and issues a session token

Verification uses the wallet's ed25519 key directly, so only the real key holder
can authenticate.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from solders.pubkey import Pubkey

APP_NAME = "AI Pundit"
NONCE_TTL_S = 300


def build_message(nonce: str) -> str:
    """The exact text the wallet signs. Must match on client and server."""
    return f"Sign in to {APP_NAME}.\nThis proves you own this wallet.\nnonce: {nonce}"


@dataclass
class SIWS:
    # pubkey -> (nonce, issued_at)
    _nonces: dict[str, tuple[str, float]] = field(default_factory=dict)
    # session token -> pubkey
    _sessions: dict[str, str] = field(default_factory=dict)

    def issue_nonce(self, pubkey: str) -> str:
        nonce = secrets.token_hex(16)
        self._nonces[pubkey] = (nonce, time.time())
        return build_message(nonce)

    def verify(self, pubkey: str, signature: bytes) -> str | None:
        """Verify a signed nonce. On success returns a new session token."""
        entry = self._nonces.get(pubkey)
        if entry is None:
            return None
        nonce, issued = entry
        if time.time() - issued > NONCE_TTL_S:
            self._nonces.pop(pubkey, None)
            return None

        message = build_message(nonce).encode("utf-8")
        try:
            verify_key = VerifyKey(bytes(Pubkey.from_string(pubkey)))
            verify_key.verify(message, signature)
        except (BadSignatureError, ValueError):
            return None

        self._nonces.pop(pubkey, None)  # one-time use
        token = secrets.token_urlsafe(24)
        self._sessions[token] = pubkey
        return token

    def session_pubkey(self, token: str | None) -> str | None:
        return self._sessions.get(token) if token else None
