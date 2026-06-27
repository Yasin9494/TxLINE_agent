"""Activate the free World Cup live feed: on-chain subscribe -> apiToken.

Runs the TxLINE `subscribe(service_level_id, weeks)` Anchor instruction on Solana
mainnet (free World Cup tier — no TxL tokens, just fees), then exchanges the tx
signature for a long-lived apiToken via POST /api/token/activate.

Usage:  .venv/bin/python scripts/activate_live.py [service_level_id]
        service_level_id: 12 = real-time (default), 1 = 60s delay. Both free.

Writes TXLINE_API_TOKEN into .env on success.
"""
from __future__ import annotations

import base64
import json
import os
import struct
import sys
import time
from pathlib import Path

import httpx
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from txline_sharp.config import CONFIG  # noqa: E402

# --- mainnet constants ---------------------------------------------------
PROGRAM_ID = Pubkey.from_string("9ExbZjAapQww1vfcisDmrngPinHTEfpjYRWMunJgcKaA")
TXL_MINT = Pubkey.from_string("Zhw9TVKp68a1QrftncMSd6ELXKDtpVMNuMGr1jNwdeL")
TOKEN_2022 = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
SYS_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")

SUBSCRIBE_DISC = bytes([254, 28, 191, 138, 156, 179, 183, 53])
WEEKS = 4


def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_2022), bytes(mint)], ATA_PROGRAM
    )[0]


def load_keypair(path: str) -> Keypair:
    data = json.loads(Path(path).read_text())
    return Keypair.from_bytes(bytes(data))


def build_subscribe_ix(user: Pubkey, service_level_id: int) -> Instruction:
    pricing_matrix = Pubkey.find_program_address([b"pricing_matrix"], PROGRAM_ID)[0]
    treasury_pda = Pubkey.find_program_address([b"token_treasury_v2"], PROGRAM_ID)[0]
    treasury_vault = ata(treasury_pda, TXL_MINT)
    user_ata = ata(user, TXL_MINT)
    data = SUBSCRIBE_DISC + struct.pack("<H", service_level_id) + struct.pack("<B", WEEKS)
    metas = [
        AccountMeta(user, True, True),
        AccountMeta(pricing_matrix, False, False),
        AccountMeta(TXL_MINT, False, False),
        AccountMeta(user_ata, False, True),
        AccountMeta(treasury_vault, False, True),
        AccountMeta(treasury_pda, False, False),
        AccountMeta(TOKEN_2022, False, False),
        AccountMeta(SYS_PROGRAM, False, False),
        AccountMeta(ATA_PROGRAM, False, False),
    ]
    return Instruction(PROGRAM_ID, data, metas)


def create_ata_idempotent_ix(payer: Pubkey, mint: Pubkey) -> Instruction:
    user_ata = ata(payer, mint)
    metas = [
        AccountMeta(payer, True, True),
        AccountMeta(user_ata, False, True),
        AccountMeta(payer, False, False),
        AccountMeta(mint, False, False),
        AccountMeta(SYS_PROGRAM, False, False),
        AccountMeta(TOKEN_2022, False, False),
    ]
    return Instruction(ATA_PROGRAM, bytes([1]), metas)  # 1 = CreateIdempotent


def rpc(url: str, method: str, params: list) -> dict:
    r = httpx.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                   timeout=30)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"RPC {method} error: {json.dumps(body['error'])[:500]}")
    return body["result"]


def get_balance(url: str, pubkey: Pubkey) -> int:
    return rpc(url, "getBalance", [str(pubkey)])["value"]


def send(url: str, kp: Keypair, ixs: list[Instruction]) -> str:
    blockhash = rpc(url, "getLatestBlockhash", [{"commitment": "finalized"}])["value"]["blockhash"]
    tx = Transaction.new_signed_with_payer(ixs, kp.pubkey(), [kp], Hash.from_string(blockhash))
    b64 = base64.b64encode(bytes(tx)).decode()
    return rpc(url, "sendTransaction",
               [b64, {"encoding": "base64", "skipPreflight": False, "preflightCommitment": "confirmed"}])


def confirm(url: str, sig: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = rpc(url, "getSignatureStatuses", [[sig], {"searchTransactionHistory": True}])["value"][0]
        if st is not None:
            if st.get("err") is not None:
                raise RuntimeError(f"tx failed on-chain: {st['err']}")
            if st.get("confirmationStatus") in ("confirmed", "finalized"):
                return True
        time.sleep(2)
    return False


def write_env_token(token: str) -> None:
    env_path = ROOT / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    out, found = [], False
    for ln in lines:
        if ln.startswith("TXLINE_API_TOKEN="):
            out.append(f"TXLINE_API_TOKEN={token}"); found = True
        else:
            out.append(ln)
    if not found:
        out.append(f"TXLINE_API_TOKEN={token}")
    env_path.write_text("\n".join(out) + "\n")


def main() -> int:
    service_level_id = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    kp = load_keypair(CONFIG.keypair_path)
    user = kp.pubkey()
    print(f"wallet: {user}")
    print(f"service level: {service_level_id} (12=realtime, 1=60s delay), weeks={WEEKS}")

    url = CONFIG.rpc_url
    bal = get_balance(url, user)
    print(f"balance: {bal/1e9:.6f} SOL")
    if bal < 3_000_000:
        print("WARNING: low balance, tx may fail")

    ixs = [create_ata_idempotent_ix(user, TXL_MINT), build_subscribe_ix(user, service_level_id)]
    print("sending subscribe tx...")
    try:
        sig = send(url, kp, ixs)
    except Exception as exc:
        print(f"send failed with ATA-create prepended ({exc});\nretrying subscribe-only...")
        sig = send(url, kp, [build_subscribe_ix(user, service_level_id)])
    print(f"tx signature: {sig}")
    print(f"  explorer: https://solscan.io/tx/{sig}")

    print("confirming...")
    if not confirm(url, sig):
        print("ERROR: not confirmed in time"); return 1
    print("on-chain subscription confirmed")

    # --- exchange for apiToken ---
    base = CONFIG.base_url
    jwt = httpx.post(f"{base}/auth/guest/start", json={}, timeout=20).json()["token"]
    leagues: list[int] = []
    message = f"{sig}:{','.join(map(str, leagues))}:{jwt}"
    wallet_sig = base64.b64encode(bytes(kp.sign_message(message.encode()))).decode()
    r = httpx.post(
        f"{base}/api/token/activate",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"txSig": sig, "walletSignature": wallet_sig, "leagues": leagues},
        timeout=30,
    )
    print(f"activate HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        return 1
    # the activate endpoint returns the token as a plain string (not JSON)
    try:
        body = r.json()
        api_token = body.get("token") or body.get("apiToken") or json.dumps(body)
    except (json.JSONDecodeError, ValueError):
        api_token = r.text.strip().strip('"')
    write_env_token(api_token)
    print("API TOKEN ACTIVATED ✓ (saved to .env as TXLINE_API_TOKEN)")
    print(f"token preview: {api_token[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
