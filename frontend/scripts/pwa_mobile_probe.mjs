// scripts/pwa_mobile_probe.mjs
/** Pinpoint what causes horizontal overflow on a page at a given viewport. */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ROUTE = process.argv[2] || '/principal/calendar';
const W = Number(process.argv[3] || 390);
const H = Number(process.argv[4] || 844);
const ORIGIN = process.env.PWA_ORIGIN || 'http://localhost:5173';
const API = process.env.PWA_API || 'http://localhost:8000';
const PORT = 9377;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const base = join(process.env.LOCALAPPDATA || '', 'ms-playwright');
let chromePath = null;
for (const dir of readdirSync(base)) {
  for (const rel of ['chrome-win64/chrome.exe', 'chrome-win/chrome.exe']) {
    const p = join(base, dir, rel);
    if (existsSync(p)) { chromePath = p; break; }
  }
  if (chromePath) break;
}
const profile = mkdtempSync(join(tmpdir(), 'scholaris-mp-'));
const chrome = spawn(chromePath, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', 'about:blank',
], { stdio: 'ignore' });
for (let i = 0; i < 60; i++) {
  try { await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; } catch { await sleep(250); }
}
const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 1; const pending = new Map();
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id); pending.delete(m.id);
    m.error ? reject(new Error(m.error.message)) : resolve(m.result);
  }
};
const send = (method, params = {}) => {
  const i = id++; ws.send(JSON.stringify({ id: i, method, params }));
  return new Promise((res, rej) => { pending.set(i, { resolve: res, reject: rej }); setTimeout(() => { if (pending.has(i)) { pending.delete(i); rej(new Error('t/o')); } }, 20000); });
};
const ev = async (x) => {
  const r = await send('Runtime.evaluate', { expression: `(async () => { ${x} })()`, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};

await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 2, mobile: true });
await send('Page.navigate', { url: `${ORIGIN}/login` });
await sleep(2500);
await ev(`
  const r = await fetch('${API}/api/v1/auth/login', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ mobile: '9000000001', password: 'QaTest#2026p' }) });
  const j = await r.json();
  localStorage.setItem('scholaris_access_token', j.access_token);
  return 1;
`);
await send('Page.navigate', { url: ORIGIN + ROUTE });
await sleep(4000);

const out = await ev(`
  const vw = window.innerWidth;
  const de = document.documentElement;
  const contained = (el) => {
    let p = el.parentElement;
    while (p && p !== document.documentElement) {
      const st = getComputedStyle(p);
      if (/(auto|scroll|hidden|clip)/.test(st.overflowX)) return p.tagName + '.' + String(p.className).slice(0,70);
      p = p.parentElement;
    }
    return null;
  };
  const bad = [];
  for (const el of document.querySelectorAll('body *')) {
    const b = el.getBoundingClientRect();
    if (!b.width || !b.height) continue;
    if (b.right > vw + 0.5) {
      const c = contained(el);
      if (!c) bad.push({
        tag: el.tagName, cls: String(el.className).slice(0, 90),
        right: Math.round(b.right), over: Math.round(b.right - vw),
        text: (el.innerText||'').replace(/\\s+/g,' ').slice(0, 50),
      });
    }
  }
  return { vw, scrollW: de.scrollWidth, clientW: de.clientWidth, overflow: de.scrollWidth - de.clientWidth, unclipped: bad.slice(0, 12) };
`);
console.log('route:', ROUTE, `${W}x${H}`);
console.log(JSON.stringify(out, null, 1));
ws.close(); chrome.kill();
try { rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(0);
