# AI Pundit — your live World Cup co-commentator, powered by TxLINE

> Built for the **TxLINE World Cup Hackathon 2026** (Superteam Earn) — consumer/fan track.

Most fans watch the World Cup with a phone in their hand. **AI Pundit** is the
second screen that talks back: a Telegram bot + live web dashboard that watches the
TxLINE real-time feed and reacts the instant something matters — a goal, a red card,
or **sharp money** moving the odds before anything has even happened on the pitch.

Every event becomes a punchy, human message ("⚽ GOAL! Brazil 1-1 Argentina (83') —
market now favours Argentina") with a spoken-audio version for hands-free, second-screen
viewing.

## What makes it different

- **It explains the market, not just the score.** Anyone can show a scoreline. AI Pundit
  reads the *consensus odds* and tells fans what the smart money thinks — and flags
  "sharp" moves that often precede goals.
- **Real-time and reactive.** Driven by TxLINE's SSE odds & scores streams.
- **Voice-ready.** Every message ships with a TTS-friendly script (track bonus).
- **Deterministic engine.** Same feed in → same commentary out; easy to audit and test.

## See it now (simulated feed, no setup)

```bash
pip install -r requirements.txt
python scripts/run_web.py          # open http://127.0.0.1:8000
# or, console-only previews:
python scripts/demo_pundit.py      # a single match, minute-by-minute
```

The dashboard replays World Cup matches in accelerated time so you can watch the
scoreboard, live odds and the pundit feed update together. Swap the simulator for the
live TxLINE feed (one adapter) and the exact same commentary streams from real matches.

## Connect Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather) → copy the token.
2. Put it in `.env` (copy from `.env.example`):
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_CHAT_ID=          # message your bot once, we auto-discover it
   ```
3. Run the dashboard — every pundit message now also posts to Telegram.

Without a token everything still runs in **dry-run** (messages print to the console),
so the pipeline is fully testable with no secrets.

## Architecture

```
TxLINE SSE (odds + scores)  ─►  Normalizer  ─►  PunditEngine  ─►  PunditMessage
        │  (live)                                   │
   simulate.py (offline demo) ──────────────────────┤
                                                     ├─►  Web dashboard (FastAPI + SSE/poll)
                                                     └─►  Telegram bot (TTS-ready)
```

Core modules in `src/txline_sharp/`: `events.py` (commentary), `simulate.py` (feed
simulator), `stream.py` (TxLINE SSE), `auth.py` (guest + activation), `telegram.py`
(delivery), `server.py` (dashboard). Build status and verified TxLINE API facts: [PLAN.md](PLAN.md).

## Sibling project

`SharpSignal` — an autonomous sharp-odds detector with an on-chain verifiable track
record — shares this same engine and targets the hackathon's builder/agentic track.
See `detector.py` / `grading.py`.

## Tech

Python · httpx (SSE) · FastAPI (dashboard) · solders/solana-py (TxLINE on-chain activation).
