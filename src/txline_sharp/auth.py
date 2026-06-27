"""TxLINE authentication.

Two-layer auth, confirmed against the live API (2026-06-26):

  1. Guest session  -> POST /auth/guest/start                 returns { token: <JWT> }
  2. Activation     -> POST /api/token/activate (Bearer jwt)  returns { apiToken }
       body: { txSig, walletSignature, leagues }
       Requires a Solana wallet signature + an on-chain registration tx.
       World Cup tier is free (no TxL tokens; the tx just registers the sub).

Data requests then send BOTH headers:
  Authorization: Bearer <jwt>
  X-Api-Token:   <apiToken>
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class Session:
    jwt: str
    api_token: str | None = None

    def headers(self) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.jwt}"}
        if self.api_token:
            h["X-Api-Token"] = self.api_token
        return h


def start_guest_session(base_url: str, client: httpx.Client | None = None) -> Session:
    """Open an anonymous guest session and return its JWT (valid ~30 days)."""
    owns = client is None
    client = client or httpx.Client(timeout=20)
    try:
        r = client.post(f"{base_url}/auth/guest/start", json={})
        r.raise_for_status()
        token = r.json()["token"]
        return Session(jwt=token)
    finally:
        if owns:
            client.close()


def activate_token(
    base_url: str,
    jwt: str,
    tx_sig: str,
    wallet_signature: str,
    leagues: str,
    client: httpx.Client | None = None,
) -> str:
    """Exchange a completed on-chain registration for a long-lived apiToken.

    `tx_sig`           : signature of the broadcast registration transaction.
    `wallet_signature` : NaCl-detached signature over "{txSig}:{leagues}:{jwt}".
    Returns the apiToken string.
    """
    owns = client is None
    client = client or httpx.Client(timeout=30)
    try:
        r = client.post(
            f"{base_url}/api/token/activate",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"txSig": tx_sig, "walletSignature": wallet_signature, "leagues": leagues},
        )
        r.raise_for_status()
        return r.json()["apiToken"]
    finally:
        if owns:
            client.close()
