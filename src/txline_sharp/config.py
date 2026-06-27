"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    base_url: str
    leagues: str
    api_token: str | None
    keypair_path: str
    cluster: str
    rpc_url: str
    tg_token: str | None
    tg_chat_id: str | None

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            base_url=os.getenv("TXLINE_BASE_URL", "https://txline.txodds.com").rstrip("/"),
            leagues=os.getenv("TXLINE_LEAGUES", ""),
            api_token=os.getenv("TXLINE_API_TOKEN") or None,
            keypair_path=os.getenv("SOLANA_KEYPAIR_PATH", "./.secrets/wallet.json"),
            cluster=os.getenv("SOLANA_CLUSTER", "devnet"),
            rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com"),
            tg_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            tg_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        )


CONFIG = Config.from_env()
