"""AI Pundit — public REST API (auto-documented via Swagger at /docs).

A single, documented backend that powers both the web app and the Telegram bot.
Sign in three ways (Solana wallet / demo / Telegram) — all issue a session token
used as `Authorization: Bearer <token>`.

Interactive docs:  /docs (Swagger UI)  ·  /redoc  ·  /openapi.json
"""
from __future__ import annotations

import base64
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query
from pydantic import BaseModel, Field

from .accounts import Account
from .state import ACCOUNTS, BOT_USERNAME, NOTIFIER, STORE

API_DESCRIPTION = """
**AI Pundit** turns the live TxLINE World Cup feed into a fan experience: live
scores, market-implied win probabilities and an AI commentator that flags goals,
red cards and **sharp-money** odds moves — on the web and in Telegram.

### Auth
Register (`POST /auth/register`) or log in (`POST /auth/login`) with a username and
password — or `POST /auth/demo` for instant access. Then send
`Authorization: Bearer <token>`. A Solana wallet and Telegram can be linked later
(both optional; wallet sign-in only signs a message and can never move funds).
""".strip()

TAGS = [
    {"name": "Auth", "description": "Register/login (username+password); demo; optional Solana & Telegram linking."},
    {"name": "Matches", "description": "World Cup fixtures, live scores and market odds."},
    {"name": "Pundit", "description": "The AI commentator feed."},
    {"name": "Me", "description": "Personalisation for the signed-in account."},
    {"name": "System", "description": "Health & status."},
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    from .live import start_engine
    STORE.source = start_engine(STORE, NOTIFIER)
    yield


app = FastAPI(
    title="AI Pundit API",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)



# ----------------------------- schemas -----------------------------------
class AccountOut(BaseModel):
    id: str
    display: str
    username: str | None = None
    solana: str | None = None
    solana_linked: bool = False
    telegram_linked: bool = False
    is_demo: bool = False
    favourites: list[int] = Field(default_factory=list)


class RegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=4, description="Kept server-side as a salted PBKDF2 hash.")


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str = Field(..., description="Session token; send as 'Authorization: Bearer <token>'.")
    account: AccountOut


class NonceOut(BaseModel):
    message: str = Field(..., description="Exact message the wallet must sign.")


class SolanaLoginIn(BaseModel):
    pubkey: str = Field(..., description="Base58 wallet public key.")
    signature: str = Field(..., description="Base64 ed25519 signature of the nonce message.")


class CodeIn(BaseModel):
    code: str


class LinkCodeOut(BaseModel):
    code: str
    deep_link: str = Field(..., description="Open this in Telegram to link your account.")
    expires_in: int = 600


class OddsOut(BaseModel):
    HOME: float | None = None
    DRAW: float | None = None
    AWAY: float | None = None


class MatchOut(BaseModel):
    fixture_id: str
    home_team: str
    away_team: str
    minute: int = 0
    home_goals: int = 0
    away_goals: int = 0
    status: str = "upcoming"          # upcoming | live | finished
    start: int = 0                    # kickoff time (epoch ms)
    competition: str | None = None
    prices: OddsOut = Field(default_factory=OddsOut)
    favourite: str | None = None


class PunditOut(BaseModel):
    fixture_id: str
    match: str
    minute: int
    kind: str                         # goal | red_card | sharp_shift
    text: str
    speech: str


class BoardOut(BaseModel):
    source: str
    matches: list[MatchOut]
    feed: list[PunditOut]


# ----------------------------- auth deps ---------------------------------
def _token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return None


def current_account(authorization: str | None = Header(None)) -> Account:
    acc = ACCOUNTS.session_account(_token(authorization))
    if acc is None:
        raise HTTPException(401, "login required — get a token from /auth/demo or /auth/solana")
    return acc


def optional_account(authorization: str | None = Header(None)) -> Account | None:
    return ACCOUNTS.session_account(_token(authorization))


def _acc_out(acc: Account) -> AccountOut:
    return AccountOut(**acc.public())


# ----------------------------- Auth --------------------------------------
@app.post("/api/v1/auth/register", response_model=LoginOut, tags=["Auth"],
          summary="Register with username + password")
def auth_register(body: RegisterIn) -> LoginOut:
    token = ACCOUNTS.register(body.username, body.password)
    if not token:
        raise HTTPException(409, "username taken or password too short")
    return LoginOut(token=token, account=_acc_out(ACCOUNTS.session_account(token)))


@app.post("/api/v1/auth/login", response_model=LoginOut, tags=["Auth"],
          summary="Log in with username + password")
def auth_login(body: LoginIn) -> LoginOut:
    token = ACCOUNTS.password_login(body.username, body.password)
    if not token:
        raise HTTPException(401, "invalid username or password")
    return LoginOut(token=token, account=_acc_out(ACCOUNTS.session_account(token)))


@app.post("/api/v1/auth/demo", response_model=LoginOut, tags=["Auth"],
          summary="Instant demo login")
def auth_demo() -> LoginOut:
    token = ACCOUNTS.demo_login()
    return LoginOut(token=token, account=_acc_out(ACCOUNTS.session_account(token)))


@app.get("/api/v1/auth/nonce", response_model=NonceOut, tags=["Auth"],
         summary="Get a nonce to sign (Solana, optional)")
def auth_nonce(pubkey: str = Query(..., description="Base58 wallet public key")) -> NonceOut:
    return NonceOut(message=ACCOUNTS.solana_nonce(pubkey))


@app.post("/api/v1/auth/solana", response_model=LoginOut, tags=["Auth"],
          summary="Sign in with a Solana wallet (optional)")
def auth_solana(body: SolanaLoginIn) -> LoginOut:
    """Optional wallet sign-in. Signing a message can't move funds — no transaction
    is created — but username/password is the primary path for wallet-shy users."""
    try:
        sig = base64.b64decode(body.signature)
    except Exception:
        raise HTTPException(400, "signature must be base64")
    token = ACCOUNTS.solana_login(body.pubkey, sig)
    if not token:
        raise HTTPException(401, "signature verification failed")
    return LoginOut(token=token, account=_acc_out(ACCOUNTS.session_account(token)))


@app.post("/api/v1/auth/solana/link", response_model=AccountOut, tags=["Auth"],
          summary="Link a wallet to the signed-in account (optional)")
def auth_link_solana(body: SolanaLoginIn, authorization: str | None = Header(None)) -> AccountOut:
    try:
        sig = base64.b64decode(body.signature)
    except Exception:
        raise HTTPException(400, "signature must be base64")
    if not ACCOUNTS.link_solana(_token(authorization), body.pubkey, sig):
        raise HTTPException(401, "login required or signature invalid")
    return _acc_out(ACCOUNTS.session_account(_token(authorization)))


@app.get("/api/v1/auth/me", response_model=AccountOut, tags=["Auth"], summary="Who am I")
def auth_me(acc: Account = Depends(current_account)) -> AccountOut:
    return _acc_out(acc)


@app.post("/api/v1/auth/telegram/link-code", response_model=LinkCodeOut, tags=["Auth"],
          summary="Mint a code to link Telegram to this account")
def auth_link_code(authorization: str | None = Header(None)) -> LinkCodeOut:
    token = _token(authorization)
    code = ACCOUNTS.mint_link_code(token)
    if not code:
        raise HTTPException(401, "login required")
    return LinkCodeOut(code=code, deep_link=f"https://t.me/{BOT_USERNAME}?start={code}")


@app.post("/api/v1/auth/telegram/web-login", response_model=LoginOut, tags=["Auth"],
          summary="Log in on the web using a code from the bot")
def auth_tg_web_login(body: CodeIn) -> LoginOut:
    token = ACCOUNTS.web_login_with_code(body.code)
    if not token:
        raise HTTPException(401, "invalid or expired code")
    return LoginOut(token=token, account=_acc_out(ACCOUNTS.session_account(token)))


# ----------------------------- Matches -----------------------------------
def _status_of(m: dict) -> str:
    if m.get("minute", 0) > 0 and (m.get("home_goals", 0) or m.get("away_goals", 0) or m.get("minute", 0) < 120):
        return "live" if m.get("minute", 0) < 120 else "finished"
    return "upcoming"


@app.get("/api/v1/matches", response_model=list[MatchOut], tags=["Matches"],
         summary="List World Cup matches")
def list_matches(
    status: str | None = Query(None, description="Filter: upcoming | live | finished"),
) -> list[MatchOut]:
    out = []
    for m in STORE.matches.values():
        card = {**m, "status": m.get("status") or _status_of(m)}
        if status and card["status"] != status:
            continue
        out.append(MatchOut(**card))
    return out


@app.get("/api/v1/matches/{fixture_id}", response_model=MatchOut, tags=["Matches"],
         summary="Match detail")
def match_detail(fixture_id: str = Path(...)) -> MatchOut:
    m = STORE.matches.get(fixture_id)
    if not m:
        raise HTTPException(404, "match not found")
    return MatchOut(**{**m, "status": m.get("status") or _status_of(m)})


@app.get("/api/v1/live", response_model=BoardOut, tags=["Matches"],
         summary="Live board (matches + pundit feed)")
def live_board() -> BoardOut:
    return BoardOut(**STORE.board())


# ----------------------------- Pundit ------------------------------------
@app.get("/api/v1/pundit", response_model=list[PunditOut], tags=["Pundit"],
         summary="Recent AI commentary")
def pundit_feed(
    fixture_id: str | None = Query(None, description="Only this fixture"),
    limit: int = Query(40, ge=1, le=80),
) -> list[PunditOut]:
    items = STORE.feed
    if fixture_id:
        items = [x for x in items if x.get("fixture_id") == fixture_id]
    return [PunditOut(**x) for x in items[:limit]]


# ----------------------------- Me ----------------------------------------
@app.post("/api/v1/me/favourites/{fixture_id}", response_model=AccountOut, tags=["Me"],
          summary="Follow a match")
def add_favourite(fixture_id: int, acc: Account = Depends(current_account)) -> AccountOut:
    acc.favourites.add(fixture_id)
    return _acc_out(acc)


@app.delete("/api/v1/me/favourites/{fixture_id}", response_model=AccountOut, tags=["Me"],
            summary="Unfollow a match")
def remove_favourite(fixture_id: int, acc: Account = Depends(current_account)) -> AccountOut:
    acc.favourites.discard(fixture_id)
    return _acc_out(acc)


# ----------------------------- System ------------------------------------
@app.get("/healthz", tags=["System"], summary="Health check")
def healthz() -> dict:
    return {"ok": True, "source": STORE.source, "matches": len(STORE.matches)}


# --- Web Companion (Next.js static export) -------------------------------
# Mounted last so /api/*, /docs and /healthz take precedence; everything else
# is served from the built Next.js `out/` folder (SPA + PWA assets).
from pathlib import Path as _Path  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

_WEB_OUT = _Path(__file__).resolve().parents[2] / "web" / "out"
if _WEB_OUT.exists():
    app.mount("/", StaticFiles(directory=str(_WEB_OUT), html=True), name="web")
