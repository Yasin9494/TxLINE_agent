"""SharpSignal / AI Pundit — live web dashboard + Telegram fan-out.

A single FastAPI app that:
  - replays World Cup matches in accelerated time (simulated feed now; the live
    TxLINE SSE feed drops into the same loop once we have an apiToken),
  - runs the PunditEngine over every frame,
  - shows the action on a live dashboard (scores, odds, scrolling pundit feed),
  - mirrors every pundit message to Telegram when a bot token is configured.

Run:  uvicorn txline_sharp.server:app --reload   (from the src/ dir)
   or: python scripts/run_web.py
"""
from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from .config import CONFIG
from .events import PunditEngine
from .simulate import simulate_match_timeline
from .siws import SIWS
from .telegram import TelegramNotifier

TICK_SECONDS = 0.5      # real seconds per match-minute (demo speed)
FEED_LIMIT = 60         # messages kept in the dashboard feed
SLATE_SEEDS = [3, 11, 17, 23]


@dataclass
class Store:
    source: str = "SIMULATED"
    telegram_on: bool = False
    matches: dict[str, dict] = field(default_factory=dict)
    feed: list[dict] = field(default_factory=list)

    def snapshot(self) -> dict:
        return {
            "source": self.source,
            "telegram_on": self.telegram_on,
            "matches": list(self.matches.values()),
            "feed": self.feed[:FEED_LIMIT],
        }


STORE = Store()
NOTIFIER = TelegramNotifier(token=CONFIG.tg_token, chat_id=CONFIG.tg_chat_id)
STORE.telegram_on = NOTIFIER.enabled
SIWS_AUTH = SIWS()


class VerifyBody(BaseModel):
    pubkey: str
    signature: str  # base64-encoded ed25519 signature of the issued message


def _match_card(frame) -> dict:
    fav = min(frame.prices, key=frame.prices.get)
    return {
        "fixture_id": frame.fixture_id,
        "home_team": frame.home_team,
        "away_team": frame.away_team,
        "minute": frame.minute,
        "home_goals": frame.home_goals,
        "away_goals": frame.away_goals,
        "prices": {k: round(v, 2) for k, v in frame.prices.items()},
        "favourite": fav,
    }


async def _run_engine() -> None:
    """Background loop: replay the slate forever, emitting pundit messages."""
    while True:
        engine = PunditEngine()
        timelines = {
            f"WC2026_M{i + 1:02d}": simulate_match_timeline(
                f"WC2026_M{i + 1:02d}", seed=s, pair_index=i
            )
            for i, s in enumerate(SLATE_SEEDS)
        }
        for minute in range(0, 91):
            for fid, frames in timelines.items():
                frame = frames[minute]
                STORE.matches[fid] = _match_card(frame)
                for msg in engine.observe(frame):
                    item = {
                        "fixture_id": fid,
                        "match": f"{frame.home_team} v {frame.away_team}",
                        "minute": msg.minute,
                        "kind": msg.kind,
                        "text": msg.text,
                        "speech": msg.speech,
                    }
                    STORE.feed.insert(0, item)
                    del STORE.feed[FEED_LIMIT:]
                    try:
                        NOTIFIER.send(msg.text)
                    except Exception as exc:  # never let delivery kill the loop
                        print(f"[telegram error] {exc}")
            await asyncio.sleep(TICK_SECONDS)
        await asyncio.sleep(2.0)  # short break, then a fresh slate


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if CONFIG.api_token:
        try:
            from .live import LiveEngine
            LiveEngine(STORE, NOTIFIER).start()
            print("[server] LIVE engine started — streaming the real TxLINE feed")
        except Exception as exc:
            print(f"[server] live engine failed ({exc}); falling back to simulator")
            task = asyncio.create_task(_run_engine())
    else:
        print("[server] no TXLINE_API_TOKEN — running simulator")
        task = asyncio.create_task(_run_engine())
    yield
    if task:
        task.cancel()


app = FastAPI(title="AI Pundit — TxLINE World Cup", lifespan=lifespan)


@app.get("/api/state")
async def api_state() -> JSONResponse:
    return JSONResponse(STORE.snapshot())


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "source": STORE.source, "telegram_on": STORE.telegram_on}


# --- Sign-In-With-Solana -------------------------------------------------
@app.get("/api/auth/nonce")
async def auth_nonce(pubkey: str) -> dict:
    return {"message": SIWS_AUTH.issue_nonce(pubkey)}


@app.post("/api/auth/verify")
async def auth_verify(body: VerifyBody) -> JSONResponse:
    try:
        sig = base64.b64decode(body.signature)
    except Exception:
        return JSONResponse({"ok": False, "error": "bad signature encoding"}, status_code=400)
    token = SIWS_AUTH.verify(body.pubkey, sig)
    if not token:
        return JSONResponse({"ok": False, "error": "verification failed"}, status_code=401)
    return JSONResponse({"ok": True, "token": token, "pubkey": body.pubkey})


# --- PWA shell -----------------------------------------------------------
@app.get("/manifest.webmanifest")
async def manifest() -> JSONResponse:
    return JSONResponse({
        "name": "AI Pundit — TxLINE World Cup",
        "short_name": "AI Pundit",
        "description": "Live World Cup co-commentator powered by TxLINE.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0b0f14",
        "theme_color": "#0b0f14",
        "icons": [
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"},
        ],
    })


@app.get("/icon.svg")
async def icon() -> Response:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'>"
        "<rect width='512' height='512' rx='96' fill='#0b0f14'/>"
        "<circle cx='256' cy='256' r='150' fill='none' stroke='#3fb950' stroke-width='28'/>"
        "<text x='256' y='300' font-size='180' text-anchor='middle' fill='#e6edf3'"
        " font-family='Arial' font-weight='bold'>⚽</text></svg>"
    )
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/sw.js")
async def service_worker() -> Response:
    js = (
        "self.addEventListener('install', e => self.skipWaiting());\n"
        "self.addEventListener('activate', e => self.clients.claim());\n"
        "self.addEventListener('fetch', e => { e.respondWith(fetch(e.request)"
        ".catch(() => caches.match(e.request))); });\n"
    )
    return Response(content=js, media_type="application/javascript")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0b0f14">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icon.svg">
<title>AI Pundit · TxLINE World Cup</title>
<style>
  :root { --bg:#0b0f14; --card:#141b24; --line:#26313d; --txt:#e6edf3; --mut:#8b9bb0;
          --acc:#3fb950; --red:#f85149; --blue:#58a6ff; --gold:#e3b341; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html,body { margin:0; }
  body { background:var(--bg); color:var(--txt); padding-bottom:env(safe-area-inset-bottom);
         font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
  .bar { position:sticky; top:0; z-index:5; display:flex; align-items:center; gap:8px;
         padding:12px 14px; padding-top:calc(12px + env(safe-area-inset-top));
         background:rgba(11,15,20,.92); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }
  .brand { font-weight:700; font-size:16px; margin-right:auto; }
  .brand small { color:var(--mut); font-weight:400; }
  .btn { font:inherit; font-size:13px; padding:8px 12px; border-radius:999px; border:1px solid var(--line);
         background:#0e151d; color:var(--txt); cursor:pointer; white-space:nowrap; }
  .btn.primary { border-color:var(--acc); color:var(--acc); }
  .btn.active { border-color:var(--gold); color:var(--gold); }
  .status { display:flex; gap:8px; flex-wrap:wrap; padding:10px 14px 0; }
  .pill { font-size:11px; padding:3px 9px; border-radius:999px; border:1px solid var(--line); color:var(--mut); }
  .pill.on { color:var(--acc); border-color:var(--acc); }
  main { padding:14px; display:grid; gap:18px; max-width:1100px; margin:0 auto; }
  h2 { font-size:12px; text-transform:uppercase; letter-spacing:.07em; color:var(--mut); margin:0 0 10px; }
  .matches { display:grid; grid-auto-flow:column; grid-auto-columns:80%; gap:12px;
             overflow-x:auto; scroll-snap-type:x mandatory; padding-bottom:6px; }
  .match { scroll-snap-align:start; background:var(--card); border:1px solid var(--line);
           border-radius:16px; padding:16px; }
  .teams { display:flex; justify-content:space-between; align-items:center; font-weight:600; gap:8px; }
  .score { font-size:26px; font-variant-numeric:tabular-nums; }
  .min { color:var(--mut); font-size:12px; margin-top:2px; }
  .odds { display:flex; gap:6px; margin-top:12px; }
  .odd { flex:1; text-align:center; background:#0e151d; border:1px solid var(--line);
         border-radius:10px; padding:8px 0; font-size:14px; }
  .odd .lab { display:block; color:var(--mut); font-size:10px; margin-bottom:2px; }
  .odd.fav { border-color:var(--gold); color:var(--gold); }
  .feed { background:var(--card); border:1px solid var(--line); border-radius:16px; overflow:hidden; }
  .msg { padding:13px 14px; border-bottom:1px solid var(--line); animation:fade .4s ease; }
  .msg:last-child { border-bottom:none; }
  .msg .meta { font-size:11px; color:var(--mut); margin-bottom:3px; }
  .msg.goal { border-left:3px solid var(--acc); }
  .msg.red_card { border-left:3px solid var(--red); }
  .msg.sharp_shift { border-left:3px solid var(--blue); }
  .msg .spk { color:var(--mut); font-size:12px; margin-top:5px; font-style:italic; }
  @keyframes fade { from{opacity:0; transform:translateY(-4px);} to{opacity:1;} }
  .empty { color:var(--mut); padding:24px; text-align:center; }
  @media (min-width:760px){
    main { grid-template-columns:1.1fr 1fr; align-items:start; }
    .matches { grid-auto-flow:row; grid-template-columns:1fr 1fr; overflow:visible; }
    .feed { max-height:78vh; overflow:auto; }
  }
</style></head>
<body>
<div class="bar">
  <div class="brand">⚽ AI Pundit <small>· World Cup</small></div>
  <button id="voice" class="btn" onclick="toggleVoice()">🔈 Voice</button>
  <button id="wallet" class="btn" onclick="connect()">Connect Wallet</button>
</div>
<div class="status">
  <span id="src" class="pill">feed: …</span>
  <span id="tg" class="pill">telegram: …</span>
  <span id="auth" class="pill">guest</span>
</div>
<main>
  <section>
    <h2>Live matches</h2>
    <div id="matches" class="matches"></div>
  </section>
  <section>
    <h2>Pundit feed</h2>
    <div id="feed" class="feed"><div class="empty">waiting for kick-off…</div></div>
  </section>
</main>
<script>
const SEL = ['HOME','DRAW','AWAY'];
function card(m){
  const odds = SEL.map(s => `<div class="odd ${m.favourite===s?'fav':''}">
      <span class="lab">${s==='HOME'?m.home_team:s==='AWAY'?m.away_team:'Draw'}</span>
      ${m.prices[s]?.toFixed(2) ?? '-'}</div>`).join('');
  return `<div class="match">
    <div class="teams"><span>${m.home_team}</span>
      <span class="score">${m.home_goals}–${m.away_goals}</span><span>${m.away_team}</span></div>
    <div class="min">${m.minute}'</div>
    <div class="odds">${odds}</div></div>`;
}
function msg(x){
  return `<div class="msg ${x.kind}">
    <div class="meta">${x.match} · ${x.minute}'</div>
    <div>${x.text.replace(/\\*(.+?)\\*/g,'<b>$1</b>').replace(/\\n/g,'<br>')}</div>
    <div class="spk">🔊 ${x.speech}</div></div>`;
}

// --- voice (Web Speech API) ---
let voiceOn = false, primed = false;
const spoken = new Set();
const keyOf = x => x.fixture_id+'|'+x.minute+'|'+x.kind+'|'+x.text;
function toggleVoice(){
  voiceOn = !voiceOn;
  const b = document.getElementById('voice');
  b.classList.toggle('active', voiceOn);
  b.textContent = voiceOn ? '🔊 Voice on' : '🔈 Voice';
  if (voiceOn && 'speechSynthesis' in window) speak('Pundit voice on.');
}
function speak(t){
  if (!('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(t); u.rate = 1.03; u.lang = 'en-US';
  window.speechSynthesis.speak(u);
}

// --- Sign-In-With-Solana ---
let auth = JSON.parse(localStorage.getItem('aip_auth') || 'null');
const shortAddr = a => a.slice(0,4)+'…'+a.slice(-4);
function renderWallet(){
  const b = document.getElementById('wallet'), p = document.getElementById('auth');
  if (auth){ b.textContent = '🟢 '+shortAddr(auth.pubkey); b.classList.add('primary');
             p.textContent = 'signed in · '+shortAddr(auth.pubkey); p.classList.add('on'); }
  else { b.textContent = 'Connect Wallet'; b.classList.remove('primary');
         p.textContent = 'guest'; p.classList.remove('on'); }
}
async function connect(){
  if (auth){ auth=null; localStorage.removeItem('aip_auth'); renderWallet(); return; }
  const prov = window.solana;
  if (!prov || !prov.isPhantom){ alert('Install a Solana wallet (e.g. Phantom) to sign in.'); return; }
  try{
    const res = await prov.connect();
    const pubkey = res.publicKey.toString();
    const { message } = await (await fetch('/api/auth/nonce?pubkey='+pubkey)).json();
    const signed = await prov.signMessage(new TextEncoder().encode(message), 'utf8');
    const sig = btoa(String.fromCharCode(...signed.signature));
    const vr = await (await fetch('/api/auth/verify', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ pubkey, signature: sig })})).json();
    if (vr.ok){ auth = { pubkey: vr.pubkey, token: vr.token };
      localStorage.setItem('aip_auth', JSON.stringify(auth)); renderWallet(); }
    else alert('Sign-in failed: '+(vr.error || 'unknown'));
  }catch(e){ console.error(e); }
}

async function tick(){
  try{
    const s = await (await fetch('/api/state')).json();
    document.getElementById('src').textContent = 'feed: '+s.source;
    const tg = document.getElementById('tg');
    tg.textContent = 'telegram: '+(s.telegram_on?'ON':'off');
    tg.className = 'pill'+(s.telegram_on?' on':'');
    document.getElementById('matches').innerHTML = s.matches.map(card).join('');
    document.getElementById('feed').innerHTML = s.feed.length
      ? s.feed.map(msg).join('') : '<div class="empty">waiting for kick-off…</div>';
    // voice: speak only genuinely new messages (chronological order)
    const fresh = [];
    for (const x of s.feed){ const k = keyOf(x); if (!spoken.has(k)){ spoken.add(k); fresh.push(x); } }
    if (primed && voiceOn){ for (const x of fresh.reverse()) speak(x.speech); }
    primed = true;
  }catch(e){}
}
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
renderWallet();
setInterval(tick, 1000); tick();
</script>
</body></html>"""
