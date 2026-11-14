#!/usr/bin/env python3
"""Generate a single-file browser UI (index.html) with ideas.json inlined.

No framework, no build step, no server: open the file and it works.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "ideas.json")))

# Flatten to one row per idea; keep the date + url for provenance.
rows = []
for issue in data:
    for n, idea in enumerate(issue["ideas"], 1):
        rows.append({"d": issue["date"], "u": issue["url"], "n": n, "t": idea})

payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>3 Ideas From Me</title>
<style>
  :root{
    --bg:#fbfaf7; --fg:#1a1a1a; --dim:#777; --line:#e6e3dc;
    --hit:#b58900; --hit-bg:#fff3c4; --sel:#f0ede6; --accent:#111;
    --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
  }
  @media (prefers-color-scheme:dark){
    :root{ --bg:#141414; --fg:#e8e6e1; --dim:#8a8a8a; --line:#2c2c2c;
           --hit:#e3b341; --hit-bg:#4a3c00; --sel:#232323; --accent:#f2f2f2; }
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  .wrap{max-width:760px;margin:0 auto;padding:28px 20px 100px}
  h1{font-size:20px;margin:0 0 2px;font-weight:650;letter-spacing:-.01em}
  .sub{color:var(--dim);font-size:13px;margin-bottom:18px}
  .sub a{color:var(--dim);text-decoration:underline;text-underline-offset:2px}
  .sub a:hover{color:var(--accent)}
  .bar{position:sticky;top:0;background:var(--bg);padding:8px 0 12px;border-bottom:1px solid var(--line);z-index:5}
  input{width:100%;font:inherit;font-size:17px;padding:10px 12px;border:1px solid var(--line);
        border-radius:8px;background:var(--bg);color:var(--fg);outline:none}
  input:focus{border-color:var(--accent)}
  .meta{display:flex;gap:14px;align-items:center;color:var(--dim);font-size:12.5px;margin:10px 0 0;font-family:var(--mono)}
  kbd{font-family:var(--mono);background:var(--sel);border:1px solid var(--line);
      border-radius:4px;padding:1px 5px;font-size:11px}
  .hints{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
  @media (max-width:620px){ .hints{display:none} #count{margin-left:auto} }
  #list{margin-top:8px}
  .item{padding:12px 10px;border-bottom:1px solid var(--line);border-radius:6px;cursor:pointer}
  .item:hover{background:var(--sel)}
  .item.sel{background:var(--sel);box-shadow:inset 2px 0 0 var(--accent)}
  .date{font-family:var(--mono);font-size:11.5px;color:var(--dim);letter-spacing:.02em}
  .txt{margin-top:3px;white-space:pre-wrap}
  mark{background:var(--hit-bg);color:inherit;border-radius:2px;padding:0 1px}
  .txt mark{font-weight:600;box-shadow:inset 0 -2px 0 var(--hit)}
  .empty{color:var(--dim);padding:40px 10px;text-align:center}
  .foot{margin-top:26px;padding-top:14px;border-top:1px solid var(--line);color:var(--dim);font-size:12px}
  .foot a{color:var(--dim);text-decoration:underline;text-underline-offset:2px}
  .foot a:hover{color:var(--accent)}
  a{color:inherit}
</style>
</head>
<body>
<div class="wrap">
  <h1>3 Ideas From Me</h1>
  <div class="sub" id="sub"></div>

  <div class="bar">
    <input id="q" type="search" placeholder="Press / to search…" autocomplete="off" spellcheck="false">
    <div class="meta">
      <span id="count"></span>
      <span style="flex:1"></span>
      <span class="hints">
        <span><kbd>/</kbd> search</span>
        <span><kbd>j</kbd><kbd>k</kbd> move</span>
        <span><kbd>y</kbd> copy</span>
        <span><kbd>o</kbd> open</span>
        <span><kbd>r</kbd> random</span>
        <span><kbd>Esc</kbd> clear</span>
      </span>
    </div>
  </div>

  <div id="list"></div>

  <div class="foot">
    Extracted from the James Clear <a href="https://jamesclear.com/3-2-1">3-2-1</a> newsletter.
    <kbd>y</kbd> copies an idea with its date and source link.
    <a href="https://github.com/thomasWos/3-ideas">Source on GitHub</a>.
  </div>
</div>

<script>
const DATA = __PAYLOAD__;

const qEl   = document.getElementById('q');
const listEl= document.getElementById('list');
const cntEl = document.getElementById('count');
const subEl = document.getElementById('sub');

const FIRST = DATA.reduce((a,r)=> r.d < a ? r.d : a, '9999');
const LAST  = DATA.reduce((a,r)=> r.d > a ? r.d : a, '0000');
subEl.innerHTML = `${DATA.length} ideas · ${FIRST.slice(0,4)}–${LAST.slice(0,4)} · <a href="https://github.com/thomasWos/3-ideas">Source on GitHub</a>`;

// Score a row against whitespace-separated query terms. All terms must match.
function score(row, terms){
  const hay = row.t.toLowerCase();
  let total = 0;
  for (const term of terms){
    let at = hay.indexOf(term);
    if (at === -1) return -1;          // AND semantics
    total += at;                        // earlier match = better
  }
  return total;
}

function esc(s){
  return s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

function highlight(text, terms){
  const re = new RegExp('(' + terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|') + ')', 'gi');
  return esc(text).replace(re, '<mark>$1</mark>');
}

let view = DATA.slice();      // rows currently rendered
let sel  = 0;                 // selected index within `view`

function render(){
  const terms = qEl.value.toLowerCase().trim().split(/\s+/).filter(Boolean);

  view = terms.length
    ? DATA.map(r => ({r, s: score(r, terms)})).filter(x => x.s >= 0)
             .sort((a,b) => a.s - b.s || (a.r.d < b.r.d ? 1 : -1))
             .map(x => x.r)
    : DATA.slice();

  sel = 0;
  listEl.innerHTML = view.length
    ? view.map((r,i) =>
        `<div class="item${i===0?' sel':''}" data-i="${i}">
           <div class="date">${r.d}${r.n>1 ? ` · #${r.n}` : ''}</div>
           <div class="txt">${terms.length ? highlight(r.t, terms) : esc(r.t)}</div>
         </div>`).join('')
    : `<div class="empty">No ideas match “${esc(qEl.value)}”.</div>`;

  cntEl.textContent = terms.length
    ? `${view.length} of ${DATA.length}`
    : `${DATA.length} ideas`;
}

function move(delta){
  if (!view.length) return;
  sel = Math.max(0, Math.min(view.length - 1, sel + delta));
  const nodes = listEl.children;
  if (nodes[sel]){
    nodes[sel].classList.add('sel');
    nodes[sel].scrollIntoView({block:'nearest'});
    if (nodes[sel-1]) nodes[sel-1].classList.remove('sel');
  }
}

function current(){ return view[sel]; }

function copy(){
  const r = current();
  if (!r) return;
  const text = `${r.t}\n\n— James Clear, 3-2-1 (${r.d})\n${r.u}`;
  const done = ok => { cntEl.textContent = ok ? 'copied ✓' : 'copy failed';
                       setTimeout(render, 900); };
  if (navigator.clipboard) navigator.clipboard.writeText(text).then(()=>done(true), ()=>done(false));
  else done(false);
}

listEl.addEventListener('click', e => {
  const el = e.target.closest('.item');
  if (!el) return;
  sel = +el.dataset.i;
  [...listEl.children].forEach(n => n.classList.remove('sel'));
  el.classList.add('sel');
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape'){ qEl.value = ''; qEl.blur(); render(); return; }
  if (e.target === qEl){
    if (e.key === 'Enter'){ e.preventDefault(); qEl.blur(); }
    return;                            // typing in the box: don't hijack arrows
  }
  if (e.key === '/'){ e.preventDefault(); qEl.focus(); qEl.select(); return; }
  if (e.key === 'j' || e.key === 'ArrowDown'){ e.preventDefault(); move(1); }
  if (e.key === 'k' || e.key === 'ArrowUp'){ e.preventDefault(); move(-1); }
  if (e.key === 'y'){ e.preventDefault(); copy(); }
  if (e.key === 'o'){ e.preventDefault(); const r = current(); if (r) window.open(r.u, '_blank'); }
  if (e.key === 'r'){ e.preventDefault(); random(); }
});

function random(){
  qEl.value = ''; render();
  const i = Math.floor(Math.random() * view.length);
  sel = i; move(0);
}

let t;
qEl.addEventListener('input', () => { clearTimeout(t); t = setTimeout(render, 60); });
render();
</script>
</body>
</html>
"""

out = HTML.replace("__PAYLOAD__", payload)
path = os.path.join(HERE, "index.html")
open(path, "w").write(out)
print(f"wrote {path}  ({os.path.getsize(path)/1024:.0f} KB, {len(rows)} ideas)")