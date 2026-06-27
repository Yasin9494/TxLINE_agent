"""Web Companion — mobile-first, cached PWA fan site served by the API app.

Top-nav sections (Home / Matches / Teams / Insights), responsive layout, and a
service worker doing stale-while-revalidate so the app opens instantly from cache
and refreshes in the background. One self-contained HTML string — nothing to build.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, Response

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    return WEB_HTML


@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> JSONResponse:
    return JSONResponse({
        "name": "AI Pundit — World Cup Companion",
        "short_name": "AI Pundit",
        "description": "Live World Cup scores, odds and an AI commentator.",
        "start_url": "/", "display": "standalone",
        "background_color": "#0a0e17", "theme_color": "#0a0e17",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml",
                   "purpose": "any maskable"}],
    })


@router.get("/icon.svg", include_in_schema=False)
def icon() -> Response:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'>"
        "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0' stop-color='#12351f'/><stop offset='1' stop-color='#0a0e17'/></linearGradient></defs>"
        "<rect width='512' height='512' rx='112' fill='url(#g)'/>"
        "<circle cx='256' cy='256' r='150' fill='none' stroke='#34d399' stroke-width='26'/>"
        "<text x='256' y='314' font-size='190' text-anchor='middle'>⚽</text></svg>"
    )
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/sw.js", include_in_schema=False)
def sw() -> Response:
    js = """
const SHELL='aip-shell-v3', API='aip-api-v3';
self.addEventListener('install',e=>{e.waitUntil(
  caches.open(SHELL).then(c=>c.addAll(['/','/manifest.webmanifest','/icon.svg'])));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(
  caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==SHELL&&k!==API).map(k=>caches.delete(k)))));
  self.clients.claim();});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET')return;
  if(u.pathname.startsWith('/api/')&&!u.pathname.includes('/auth/')){
    // stale-while-revalidate: serve cache instantly, refresh in background
    e.respondWith(caches.open(API).then(async c=>{
      const cached=await c.match(e.request);
      const net=fetch(e.request).then(r=>{if(r&&r.status===200)c.put(e.request,r.clone());return r;}).catch(()=>cached);
      return cached||net;
    }));
  } else if(u.origin===location.origin){
    e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
  }
});
"""
    return Response(content=js, media_type="application/javascript")


WEB_HTML = ("""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0a0e17">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icon.svg">
<title>AI Pundit · World Cup Companion</title>
<style>
  :root{--bg:#0a0e17;--bg2:#0f1420;--card:#141b2b;--card2:#1a2234;--line:#232c40;
    --txt:#eaf0f7;--mut:#8494ad;--acc:#34d399;--acc2:#22c55e;--blue:#60a5fa;
    --gold:#fbbf24;--red:#f87171;--home:#34d399;--draw:#64748b;--away:#60a5fa;
    --shadow:0 8px 30px rgba(0,0,0,.35)}
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0}
  body{background:radial-gradient(1200px 600px at 50% -10%, #12351f22, transparent 60%),var(--bg);
    color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,Arial,sans-serif;
    -webkit-font-smoothing:antialiased}
  .hidden{display:none!important}
  a{color:inherit;text-decoration:none}

  /* login */
  #login{min-height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:26px}
  .hero{font-size:56px;line-height:1;filter:drop-shadow(0 6px 18px #34d39955)}
  #login h1{font-size:30px;margin:14px 0 2px;letter-spacing:-.02em}
  #login .sub{color:var(--mut);text-align:center;margin:0 0 22px;font-size:14px;line-height:1.5}
  .card-lg{width:100%;max-width:360px;background:linear-gradient(180deg,var(--card),var(--bg2));
    border:1px solid var(--line);border-radius:20px;padding:18px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:11px}
  input{font:inherit;font-size:15px;padding:13px 14px;border-radius:13px;border:1px solid var(--line);background:#0c1220;color:var(--txt);width:100%}
  input:focus{outline:none;border-color:var(--acc)}
  .btn{font:inherit;font-size:15px;padding:13px 14px;border-radius:13px;border:1px solid var(--line);
    background:#0c1220;color:var(--txt);cursor:pointer;text-align:center;font-weight:500;transition:.15s}
  .btn:active{transform:scale(.985)}
  .btn.primary{background:linear-gradient(180deg,var(--acc),var(--acc2));border-color:transparent;color:#04160c;font-weight:700}
  .btn.ghost{background:transparent}
  .divider{display:flex;align-items:center;gap:10px;color:var(--mut);font-size:12px;margin:2px 0}
  .divider::before,.divider::after{content:"";flex:1;height:1px;background:var(--line)}
  .muted{color:var(--mut);font-size:13px;text-align:center}
  .link{color:var(--acc);cursor:pointer;font-weight:600}
  .err{color:var(--red);font-size:13px;text-align:center;min-height:15px}

  /* header + nav */
  header{position:sticky;top:0;z-index:8;background:rgba(10,14,23,.86);backdrop-filter:saturate(140%) blur(12px);
    border-bottom:1px solid var(--line);padding-top:env(safe-area-inset-top)}
  .hrow{display:flex;align-items:center;gap:12px;padding:11px 16px;max-width:1080px;margin:0 auto}
  .logo{font-weight:800;letter-spacing:-.02em;font-size:17px;display:flex;align-items:center;gap:7px;white-space:nowrap}
  .logo .dot{width:7px;height:7px;border-radius:50%;background:var(--acc);box-shadow:0 0 0 3px #34d39933}
  nav{display:flex;gap:4px;margin-left:8px;overflow-x:auto;scrollbar-width:none;flex:1}
  nav::-webkit-scrollbar{display:none}
  nav a{display:flex;align-items:center;gap:6px;padding:8px 13px;border-radius:11px;color:var(--mut);
    font-size:14px;font-weight:600;white-space:nowrap;cursor:pointer}
  nav a.on{background:var(--card);color:var(--txt)}
  nav a .ic{font-size:15px}
  .hactions{display:flex;gap:8px;margin-left:auto}
  .iconbtn{width:38px;height:38px;border-radius:50%;border:1px solid var(--line);background:var(--card);
    color:var(--txt);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;flex:none}
  .iconbtn.active{border-color:var(--gold);color:var(--gold)}
  @media(max-width:640px){
    .hrow{flex-wrap:wrap;gap:8px;padding:10px 12px}
    nav{order:3;width:100%;margin:2px 0 0}
    nav a .lab{display:none}
    nav a{padding:9px 15px;font-size:16px}
    .hactions{margin-left:auto}
  }

  main{max-width:1080px;margin:0 auto;padding:16px 16px 60px}
  h2.sec{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin:22px 4px 12px}

  /* generic cards / grid */
  .grid{display:grid;gap:12px}
  @media(min-width:720px){.grid.two{grid-template-columns:1fr 1fr}}

  /* tabs */
  .tabs{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;margin-bottom:4px}
  .tabs::-webkit-scrollbar{display:none}
  .tab{font:inherit;font-size:13px;padding:9px 15px;border-radius:999px;border:1px solid var(--line);
    background:var(--card);color:var(--mut);cursor:pointer;white-space:nowrap;font-weight:600}
  .tab .n{opacity:.7;margin-left:5px}
  .tab.on{background:var(--txt);color:#0a0e17;border-color:var(--txt)}

  /* match card */
  .m{background:linear-gradient(180deg,var(--card),var(--card2));border:1px solid var(--line);
    border-radius:18px;padding:15px 16px;cursor:pointer;box-shadow:var(--shadow);transition:.15s}
  .m:active{transform:scale(.99)}
  .comp{font-size:11px;color:var(--mut);display:flex;align-items:center;justify-content:space-between;margin-bottom:9px}
  .badge{font-size:10.5px;font-weight:800;letter-spacing:.04em;padding:3px 8px;border-radius:999px;text-transform:uppercase}
  .badge.live{background:#f8717122;color:var(--red)}.badge.up{background:#60a5fa1f;color:var(--blue)}.badge.ft{background:#8494ad22;color:var(--mut)}
  .badge .lp{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--red);margin-right:5px;animation:pulse 1.3s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  .fix{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px}
  .team{display:flex;align-items:center;gap:9px;min-width:0}.team.away{justify-content:flex-end}
  .flag{width:30px;height:22px;object-fit:cover;border-radius:4px;box-shadow:0 1px 4px #0007;flex:none}
  .flag.big{width:62px;height:46px;border-radius:8px}
  .flag.sm{width:22px;height:16px}
  .flag.noflag{display:inline-flex;align-items:center;justify-content:center;background:#0c1220;color:var(--mut);font-size:11px;font-weight:800;border:1px solid var(--line)}
  .tn{font-weight:650;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .cen{text-align:center;min-width:56px}.cen .sc{font-size:22px;font-weight:800;font-variant-numeric:tabular-nums}
  .cen .vs{font-size:12px;color:var(--mut);font-weight:700}.cen .ko{font-size:11px;color:var(--mut);margin-top:2px}
  .stack{display:flex;height:8px;border-radius:6px;overflow:hidden;margin-top:13px;background:#0c1220}
  .stack i{display:block;height:100%}
  .legend{display:flex;justify-content:space-between;margin-top:7px;font-size:11px;color:var(--mut)}
  .legend b{color:var(--txt)}
  .star{background:none;border:none;color:#3a445c;font-size:17px;cursor:pointer;padding:0 2px}.star.on{color:var(--gold)}
  .empty{color:var(--mut);text-align:center;padding:44px 20px;line-height:1.6}.empty .big{font-size:34px;margin-bottom:8px}

  /* home hero + tiles */
  .homehero{background:linear-gradient(135deg,#12351f,#0f1420);border:1px solid var(--line);border-radius:20px;
    padding:20px;box-shadow:var(--shadow);margin-bottom:6px}
  .homehero h1{margin:0 0 6px;font-size:22px;letter-spacing:-.02em}
  .homehero p{margin:0;color:#b8c6d8;font-size:13.5px;line-height:1.5}
  .insight{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--blue);border-radius:14px;padding:14px 15px}
  .insight .k{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--blue);font-weight:800;margin-bottom:5px}

  /* team grid */
  .teams{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px}
  .tcard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:flex;
    align-items:center;gap:10px;cursor:pointer}
  .tcard .tn{font-size:14px}

  /* detail */
  .dhero{padding:22px 8px 14px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px}
  .dteam{display:flex;flex-direction:column;align-items:center;gap:8px}.dteam .tn{font-size:15px;text-align:center}
  .dscore{font-size:40px;font-weight:900;text-align:center;font-variant-numeric:tabular-nums}
  .prob{display:flex;flex-direction:column;gap:9px}
  .prow{display:flex;align-items:center;gap:10px;font-size:13px}
  .prow .lab{width:96px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .track{flex:1;height:9px;background:#0c1220;border-radius:6px;overflow:hidden}.fill{height:100%;border-radius:6px}
  .prow .pc{width:70px;text-align:right;color:var(--mut);font-variant-numeric:tabular-nums}
  .msg{background:var(--card);border:1px solid var(--line);border-left-width:3px;border-radius:12px;padding:12px 14px;margin-bottom:9px}
  .msg .mm{font-size:11px;color:var(--mut);margin-bottom:4px;display:flex;align-items:center;gap:8px}
  .play{font:inherit;font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);background:#0c1220;color:var(--blue);cursor:pointer}
  .msg.goal{border-left-color:var(--acc)}.msg.red_card{border-left-color:var(--red)}.msg.sharp_shift{border-left-color:var(--blue)}
  .backbtn{margin-bottom:8px}

  /* sheet */
  #sheet{position:fixed;inset:0;z-index:30;background:rgba(0,0,0,.55);display:flex;align-items:flex-end}
  .sheetbox{background:var(--card);border-top-left-radius:22px;border-top-right-radius:22px;width:100%;max-width:520px;margin:0 auto;
    padding:20px 18px calc(20px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:11px;box-shadow:var(--shadow)}
  .sheetbox .who{font-size:18px;font-weight:800}
</style></head>
<body>

<div id="login">
  <div class="hero">⚽</div>
  <h1>AI Pundit</h1>
  <p class="sub">The whole World Cup in one place — live scores, the odds as win-chances,<br>
    and an AI pundit that reads the market for you. Web &amp; Telegram.</p>
  <div class="card-lg">
    <input id="u" placeholder="Username" autocomplete="username">
    <input id="p" type="password" placeholder="Password" autocomplete="current-password">
    <div class="err" id="loginErr"></div>
    <button class="btn primary" onclick="doAuth()" id="authBtn">Log in</button>
    <div class="muted"><span id="switchTxt">New here?</span>
      <span class="link" onclick="toggleMode()" id="switchLink">Create account</span></div>
    <div class="divider">or</div>
    <button class="btn" onclick="doDemo()">⚡ Explore as guest</button>
    <button class="btn ghost muted" onclick="connectWallet()" style="font-size:13px">🔐 Continue with Solana wallet</button>
  </div>
</div>

<div id="app" class="hidden">
  <header>
    <div class="hrow">
      <div class="logo"><span class="dot"></span>AI Pundit</div>
      <nav id="nav">
        <a data-v="home" onclick="go('home')"><span class="ic">🏠</span><span class="lab">Home</span></a>
        <a data-v="matches" onclick="go('matches')"><span class="ic">⚽</span><span class="lab">Matches</span></a>
        <a data-v="teams" onclick="go('teams')"><span class="ic">🌍</span><span class="lab">Teams</span></a>
        <a data-v="insights" onclick="go('insights')"><span class="ic">🔮</span><span class="lab">Insights</span></a>
      </nav>
      <div class="hactions">
        <button class="iconbtn" id="voiceBtn" onclick="toggleVoice()" title="Voice">🔈</button>
        <button class="iconbtn" onclick="openSheet()" title="Account">👤</button>
      </div>
    </div>
  </header>
  <main id="main"></main>
</div>

<div id="sheet" class="hidden"></div>

<script>
const SEL=['HOME','DRAW','AWAY'];
const FLAGS={Argentina:'ar',Spain:'es',Austria:'at',USA:'us','United States':'us','Bosnia & Herzegovina':'ba',
 'Cape Verde':'cv',Australia:'au',Egypt:'eg',Colombia:'co',Ghana:'gh',Vietnam:'vn',Myanmar:'mm',Croatia:'hr',
 Germany:'de',Paraguay:'py',Portugal:'pt',England:'gb-eng',France:'fr',Brazil:'br',Netherlands:'nl',Morocco:'ma',
 Mexico:'mx',Iran:'ir','Saudi Arabia':'sa',Belgium:'be','New Zealand':'nz',Jordan:'jo',Algeria:'dz',Panama:'pa',
 Canada:'ca',Japan:'jp','Korea Republic':'kr','South Korea':'kr',Senegal:'sn',Uruguay:'uy',Switzerland:'ch',
 Poland:'pl',Denmark:'dk',Serbia:'rs',Ecuador:'ec',Qatar:'qa',Tunisia:'tn',Nigeria:'ng',Cameroon:'cm',Italy:'it',
 Norway:'no',Ukraine:'ua',Turkey:'tr','Ivory Coast':'ci',Peru:'pe',Chile:'cl',Scotland:'gb-sct',Wales:'gb-wls'};
function flag(n,cls){const c=FLAGS[n];cls=cls||'';
  if(!c)return `<span class="flag noflag ${cls}">${(n||'?').slice(0,2).toUpperCase()}</span>`;
  return `<img class="flag ${cls}" src="https://flagcdn.com/w80/${c}.png" alt="" loading="lazy">`;}

let token=localStorage.getItem('aip_token');
let account=JSON.parse(localStorage.getItem('aip_account')||'null');
let mode='login', view='home', arg=null, matchTab='all';
let ALL=[], FEED=[];
let voiceOn=false, primed=false; const spoken=new Set();
// warm from cache for instant paint
try{const c=JSON.parse(localStorage.getItem('aip_m')||'null');if(c)ALL=c.d;}catch(e){}

async function api(path,{method='GET',body=null,auth=true}={}){
  const h={'Content-Type':'application/json'};
  if(auth&&token)h['Authorization']='Bearer '+token;
  const r=await fetch('/api/v1'+path,{method,headers:h,body:body?JSON.stringify(body):null});
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw{status:r.status,data};return data;
}
const val=id=>document.getElementById(id).value;
function setAuth(res){token=res.token;account=res.account;
  localStorage.setItem('aip_token',token);localStorage.setItem('aip_account',JSON.stringify(account));showApp();}
function logout(){token=null;account=null;localStorage.removeItem('aip_token');localStorage.removeItem('aip_account');
  closeSheet();document.getElementById('app').classList.add('hidden');document.getElementById('login').classList.remove('hidden');}
function toggleMode(){mode=mode==='login'?'register':'login';
  document.getElementById('authBtn').textContent=mode==='login'?'Log in':'Create account';
  document.getElementById('switchTxt').textContent=mode==='login'?'New here?':'Have an account?';
  document.getElementById('switchLink').textContent=mode==='login'?'Create account':'Log in';
  document.getElementById('loginErr').textContent='';}
async function doAuth(){const ep=mode==='login'?'/auth/login':'/auth/register';
  try{setAuth(await api(ep,{auth:false,method:'POST',body:{username:val('u'),password:val('p')}}));}
  catch(e){document.getElementById('loginErr').textContent=(e.data&&e.data.detail&&(''+e.data.detail))||'Failed — check your details';}}
async function doDemo(){try{setAuth(await api('/auth/demo',{auth:false,method:'POST'}));}catch(e){}}
function showApp(){document.getElementById('login').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');go(view);refresh();}

/* ---- data ---- */
async function refresh(){
  try{ALL=await api('/matches',{auth:false});localStorage.setItem('aip_m',JSON.stringify({t:Date.now(),d:ALL}));}catch(e){}
  try{const b=await api('/live',{auth:false});FEED=b.feed||[];
    const fresh=[];for(const x of FEED){const k=x.fixture_id+'|'+x.minute+'|'+x.kind+'|'+x.text;
      if(!spoken.has(k)){spoken.add(k);fresh.push(x);}}
    if(primed&&voiceOn)for(const x of fresh.reverse())speak(x.speech);primed=true;
  }catch(e){}
  render();
}

/* ---- helpers ---- */
function fairProbs(o){if(!o||!o.HOME)return null;const inv={};let t=0;
  for(const s of SEL){inv[s]=o[s]?1/o[s]:0;t+=inv[s];}if(!t)return null;
  const r={};for(const s of SEL)r[s]=inv[s]/t;return r;}
const teamName=(m,s)=>s==='HOME'?m.home_team:s==='AWAY'?m.away_team:'Draw';
const isFav=id=>account&&(account.favourites||[]).map(String).includes(String(id));
function kickoff(ms){if(!ms)return '';const d=new Date(ms);
  return d.toLocaleDateString([], {month:'short',day:'numeric'})+' '+d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});}
const short=n=>(n||'').split(' ')[0];
const rank={live:0,upcoming:1,finished:2};
function fmt(t){return t.replace(/\\*(.+?)\\*/g,'<b>$1</b>').replace(/\\n/g,'<br>');}

/* ---- nav ---- */
function go(v,a){view=v;arg=a||null;
  document.querySelectorAll('#nav a').forEach(el=>el.classList.toggle('on',el.dataset.v===v));
  window.scrollTo(0,0);render();}
function render(){
  const el=document.getElementById('main');if(!el)return;
  if(view==='home')el.innerHTML=viewHome();
  else if(view==='matches')el.innerHTML=viewMatches();
  else if(view==='teams')el.innerHTML=viewTeams();
  else if(view==='team')el.innerHTML=viewTeam(arg);
  else if(view==='insights')el.innerHTML=viewInsights();
  else if(view==='match')el.innerHTML=viewMatch(arg);
  else el.innerHTML=viewHome();
}

/* ---- match card ---- */
function card(m){
  const fp=fairProbs(m.prices);
  const badge=m.status==='live'?`<span class="badge live"><span class="lp"></span>LIVE ${m.minute}'</span>`
    :m.status==='finished'?`<span class="badge ft">Full time</span>`:`<span class="badge up">Upcoming</span>`;
  const cen=m.status==='upcoming'?`<div class="vs">VS</div><div class="ko">${kickoff(m.start)||'TBD'}</div>`
    :`<div class="sc">${m.home_goals}–${m.away_goals}</div>`;
  let bars='';
  if(fp){const cols={HOME:'var(--home)',DRAW:'var(--draw)',AWAY:'var(--away)'};
    bars=`<div class="stack">${SEL.map(s=>`<i style="width:${(fp[s]*100).toFixed(1)}%;background:${cols[s]}"></i>`).join('')}</div>
      <div class="legend"><span><b>${Math.round(fp.HOME*100)}%</b> ${short(m.home_team)}</span>
      <span><b>${Math.round(fp.DRAW*100)}%</b> Draw</span>
      <span>${short(m.away_team)} <b>${Math.round(fp.AWAY*100)}%</b></span></div>`;
  }else bars=`<div class="legend" style="margin-top:12px">Win-chances open closer to kick-off</div>`;
  return `<div class="m" onclick="go('match','${m.fixture_id}')">
    <div class="comp"><span>${m.competition||'World Cup'}</span>
      <span style="display:flex;gap:8px;align-items:center">${badge}
      <button class="star ${isFav(m.fixture_id)?'on':''}" onclick="event.stopPropagation();toggleFav('${m.fixture_id}')">★</button></span></div>
    <div class="fix"><div class="team">${flag(m.home_team)}<span class="tn">${m.home_team}</span></div>
      <div class="cen">${cen}</div>
      <div class="team away"><span class="tn">${m.away_team}</span>${flag(m.away_team)}</div></div>${bars}</div>`;
}

/* ---- views ---- */
function viewHome(){
  const up=[...ALL].filter(m=>m.status!=='finished').sort((a,b)=>(rank[a.status]-rank[b.status])||((a.start||0)-(b.start||0)));
  const next=up.slice(0,4).map(card).join('')||'<div class="empty">Schedule loading…</div>';
  // AI insight: latest sharp move, else biggest favourite
  let insight='';
  if(FEED.length){const x=FEED[0];insight=`<div class="k">🔮 AI Insight · live</div><div>${fmt(x.text)}</div>`;}
  else{
    const fav=ALL.map(m=>({m,fp:fairProbs(m.prices)})).filter(o=>o.fp).sort((a,b)=>Math.max(b.fp.HOME,b.fp.AWAY)-Math.max(a.fp.HOME,a.fp.AWAY))[0];
    if(fav){const s=fav.fp.HOME>fav.fp.AWAY?'HOME':'AWAY';const t=teamName(fav.m,s);
      insight=`<div class="k">🔮 AI Insight</div><div>The market's strongest pick right now: <b>${t}</b> at ~${Math.round(Math.max(fav.fp.HOME,fav.fp.AWAY)*100)}% to win vs ${teamName(fav.m,s==='HOME'?'AWAY':'HOME')}.</div>`;}
    else insight=`<div class="k">🔮 AI Insight</div><div>Win-chances arrive as the odds open. I'll flag every sharp move live.</div>`;}
  return `<div class="homehero"><h1>👋 ${account&&!account.is_demo?('Welcome, '+account.display):'Welcome to AI Pundit'}</h1>
    <p>Your World Cup companion. See the market's <b>win-chances</b>, get AI alerts on goals, red cards
    and <b>sharp money</b> — and never miss a moment across all 104 games.</p></div>
    <div class="insight" style="margin-top:12px">${insight}</div>
    <h2 class="sec">Next up</h2><div class="grid two">${next}</div>
    <div style="text-align:center;margin-top:16px"><button class="btn" onclick="go('matches')">See all matches →</button></div>`;
}
function viewMatches(){
  const counts={all:ALL.length,live:0,upcoming:0,finished:0,fav:0};
  for(const m of ALL){counts[m.status]=(counts[m.status]||0)+1;if(isFav(m.fixture_id))counts.fav++;}
  const tab=(t,l)=>`<button class="tab ${matchTab===t?'on':''}" onclick="matchTab='${t}';render()">${l}<span class="n">${counts[t]||''}</span></button>`;
  let list;
  if(matchTab==='all')list=[...ALL].sort((a,b)=>(rank[a.status]-rank[b.status])||((a.start||0)-(b.start||0)));
  else if(matchTab==='fav')list=ALL.filter(m=>isFav(m.fixture_id));
  else list=ALL.filter(m=>m.status===matchTab).sort((a,b)=>(a.start||0)-(b.start||0));
  const body=list.length?`<div class="grid two">${list.map(card).join('')}</div>`:emptyMatches();
  return `<div class="tabs">${tab('all','All')}${tab('live','🔴 Live')}${tab('upcoming','Upcoming')}${tab('finished','Finished')}${tab('fav','★')}</div>${body}`;
}
function emptyMatches(){const map={live:['🕒','No matches in play right now.','Check Upcoming for what’s next.'],
  finished:['📅','No finished matches yet.','They show here after full time.'],
  fav:['★','You’re not following any matches.','Tap ★ on a match to follow it.'],all:['⚽','Loading…','']};
  const [i,a,b]=map[matchTab]||map.all;return `<div class="empty"><div class="big">${i}</div><div>${a}</div><div class="muted">${b}</div></div>`;}

function viewTeams(){
  const set={};for(const m of ALL){set[m.home_team]=1;set[m.away_team]=1;}
  const names=Object.keys(set).sort();
  if(!names.length)return '<div class="empty"><div class="big">🌍</div>Teams load with the schedule…</div>';
  return `<h2 class="sec">All teams</h2><div class="teams">${names.map(n=>
    `<div class="tcard" onclick="go('team','${encodeURIComponent(n)}')">${flag(n)}<span class="tn">${n}</span></div>`).join('')}</div>`;
}
function viewTeam(enc){const name=decodeURIComponent(enc||'');
  const ms=ALL.filter(m=>m.home_team===name||m.away_team===name)
    .sort((a,b)=>(rank[a.status]-rank[b.status])||((a.start||0)-(b.start||0)));
  const body=ms.length?`<div class="grid two">${ms.map(card).join('')}</div>`:'<div class="empty">No fixtures found.</div>';
  return `<button class="btn backbtn" onclick="go('teams')">‹ Teams</button>
    <div class="dhero"><div></div><div class="dteam">${flag(name,'big')}<span class="tn" style="font-size:20px">${name}</span></div><div></div></div>
    <h2 class="sec">Fixtures</h2>${body}`;
}
function viewInsights(){
  if(!FEED.length)return `<div class="empty"><div class="big">🔮</div>No AI calls yet.<div class="muted">I flag goals, red cards and sharp-money moves as they happen — live.</div></div>`;
  window._dfeed=FEED;
  return `<div class="homehero"><h1>🔮 AI Insights</h1><p>Real-time reads on the market — goals, cards and
    <b>sharp money</b> (big moves in the odds before anything happens on the pitch).</p></div>
    <h2 class="sec">Live feed</h2>${FEED.map((x,i)=>`<div class="msg ${x.kind}">
      <div class="mm">${x.match} · ${x.minute>0?x.minute+"'":'pre-match'}
      <button class="play" onclick="speak(window._dfeed[${i}].speech)">🔊 listen</button></div>
      <div>${fmt(x.text)}</div></div>`).join('')}`;
}
function viewMatch(id){
  const m=ALL.find(x=>String(x.fixture_id)===String(id));
  if(!m)return '<div class="empty">Loading match…</div>';
  const feed=FEED.filter(x=>String(x.fixture_id)===String(id));window._dfeed=feed;
  const fp=fairProbs(m.prices);const cols={HOME:'var(--home)',DRAW:'var(--draw)',AWAY:'var(--away)'};
  const bars=fp?`<div class="prob">${SEL.map(s=>{const pc=Math.round(fp[s]*100);
    return `<div class="prow"><span class="lab">${teamName(m,s)}</span>
      <div class="track"><div class="fill" style="width:${pc}%;background:${cols[s]}"></div></div>
      <span class="pc">${pc}% · ${m.prices[s]?m.prices[s].toFixed(2):'-'}</span></div>`;}).join('')}</div>`
    :`<div class="empty" style="padding:16px">Win-chances open closer to kick-off.</div>`;
  const msgs=feed.length?feed.map((x,i)=>`<div class="msg ${x.kind}">
      <div class="mm">${x.minute>0?x.minute+"'":'pre-match'}
      <button class="play" onclick="speak(window._dfeed[${i}].speech)">🔊 listen</button></div>
      <div>${fmt(x.text)}</div></div>`).join('')
    :`<div class="empty" style="padding:20px"><div class="big">🎙️</div>No commentary yet — I’ll narrate goals, cards &amp; sharp money live.</div>`;
  const status=m.status==='live'?`<span class="badge live"><span class="lp"></span>LIVE ${m.minute}'</span>`
    :m.status==='finished'?`<span class="badge ft">Full time</span>`:`<span class="badge up">${kickoff(m.start)||'Upcoming'}</span>`;
  const foll=isFav(id)?'★ Following':'☆ Follow this match';
  return `<button class="btn backbtn" onclick="go('matches')">‹ Matches</button>
    <div class="comp" style="justify-content:center">${m.competition||'World Cup'}</div>
    <div class="dhero"><div class="dteam">${flag(m.home_team,'big')}<span class="tn">${m.home_team}</span></div>
      <div><div class="dscore">${m.status==='upcoming'?'vs':m.home_goals+' – '+m.away_goals}</div>
        <div style="text-align:center;margin-top:8px">${status}</div></div>
      <div class="dteam">${flag(m.away_team,'big')}<span class="tn">${m.away_team}</span></div></div>
    <h2 class="sec">What the market thinks</h2>${bars}
    <button class="btn ${isFav(id)?'':'primary'}" style="width:100%;margin-top:14px" onclick="toggleFav('${id}');render()">${foll}</button>
    <h2 class="sec">AI Pundit</h2>${msgs}`;
}

async function toggleFav(id){try{const method=isFav(id)?'DELETE':'POST';account=await api('/me/favourites/'+id,{method});
  localStorage.setItem('aip_account',JSON.stringify(account));render();}catch(e){}}

/* ---- voice ---- */
let _voices=[];
function loadVoices(){try{_voices=speechSynthesis.getVoices()||[];}catch(e){}}
if('speechSynthesis'in window){loadVoices();speechSynthesis.onvoiceschanged=loadVoices;}
function toggleVoice(){voiceOn=!voiceOn;const b=document.getElementById('voiceBtn');
  b.classList.toggle('active',voiceOn);b.textContent=voiceOn?'🔊':'🔈';
  if(voiceOn)speak('AI Pundit voice is on. I will read out goals, cards and sharp money.');}
function speak(t){if(!('speechSynthesis'in window)){alert('Your browser has no text-to-speech.');return;}
  try{if(!_voices.length)loadVoices();speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);
    const v=_voices.find(v=>/en[-_]?(us|gb)/i.test(v.lang))||_voices.find(v=>/^en/i.test(v.lang));
    if(v)u.voice=v;u.lang=(v&&v.lang)||'en-US';u.rate=1.03;speechSynthesis.speak(u);}catch(e){console.error(e);}}

/* ---- account sheet ---- */
function openSheet(){const s=document.getElementById('sheet');s.classList.remove('hidden');
  const tg=account&&account.telegram_linked,w=account&&account.solana_linked;
  s.innerHTML=`<div class="sheetbox" onclick="event.stopPropagation()">
    <div class="who">${account?account.display:''}</div>
    <div class="muted" style="text-align:left;margin-top:-4px">${account&&account.is_demo?'Guest session':account&&account.username?('@'+account.username):''}</div>
    <button class="btn" onclick="linkTelegram()">${tg?'✅ Telegram linked':'💬 Link Telegram for live alerts'}</button>
    <button class="btn" onclick="connectWallet()">${w?'✅ Wallet linked':'🔐 Link Solana wallet (optional)'}</button>
    <button class="btn ghost" onclick="closeSheet()">Close</button>
    <button class="btn ghost" style="color:var(--red)" onclick="logout()">Log out</button></div>`;
  s.onclick=closeSheet;}
function closeSheet(){document.getElementById('sheet').classList.add('hidden');}
async function linkTelegram(){try{const r=await api('/auth/telegram/link-code',{method:'POST'});
  document.querySelector('.sheetbox').innerHTML=`<div class="who">Link Telegram</div>
    <div class="muted" style="text-align:left">Open the bot below — it links automatically.
    Or send this code to it: <b style="color:var(--txt);font-size:16px">${r.code}</b></div>
    <a class="btn primary" href="${r.deep_link}" target="_blank">Open Telegram bot</a>
    <button class="btn ghost" onclick="closeSheet()">Done</button>`;}catch(e){alert('Please log in first');}}
async function connectWallet(){const prov=window.solana;
  if(!prov||!prov.isPhantom){alert('Install a Solana wallet (e.g. Phantom) to use this.');return;}
  try{const res=await prov.connect();const pubkey=res.publicKey.toString();
    const {message}=await api('/auth/nonce?pubkey='+pubkey,{auth:false});
    const signed=await prov.signMessage(new TextEncoder().encode(message),'utf8');
    const sig=btoa(String.fromCharCode(...signed.signature));
    if(token){account=await api('/auth/solana/link',{method:'POST',body:{pubkey,signature:sig}});
      localStorage.setItem('aip_account',JSON.stringify(account));closeSheet();alert('Wallet linked ✓');}
    else setAuth(await api('/auth/solana',{auth:false,method:'POST',body:{pubkey,signature:sig}}));
  }catch(e){console.error(e);}}

if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
if(token)showApp();
setInterval(()=>{if(token&&!document.hidden)refresh();},6000);
</script>
</body></html>""")
