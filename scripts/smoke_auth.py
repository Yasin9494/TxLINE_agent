"""Smoke test: confirm we can open a guest session against the live TxLINE API.

Run:  python scripts/smoke_auth.py
This needs no wallet or apiToken — it only exercises POST /auth/guest/start.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from txline_sharp.auth import start_guest_session  # noqa: E402
from txline_sharp.config import CONFIG  # noqa: E402


def main() -> int:
    print(f"base_url = {CONFIG.base_url}")
    session = start_guest_session(CONFIG.base_url)
    jwt = session.jwt
    print(f"guest JWT acquired: {jwt[:24]}... ({len(jwt)} chars)")
    print("OK — guest session works. Next: activation (needs wallet + on-chain tx).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
