// scripts/pwa_reload_count.mjs
/**
 * Control experiment: count how many times the document is created, using only
 * CDP events - no page-script instrumentation at all.
 *
 * This exists to rule out the previous script's own monkey-patching of
 * history/location being the cause of an apparent reload loop.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const URL_ = process.argv[2] || 'http://localhost:5173/login';
const WAIT_MS = Number(process.argv[3] || 6000);
const PORT = 9355;
const base = join(process.env.LOCALAPPDATA || '', 'ms-playwright');
let chromePath = null;
for (const dir of readdirSync(base)) {
  for (const rel of ['chrome-win64/chrome.exe', 'chrome-win/chrome.exe']) {
    const p = join(base, dir, rel);
    if (existsSync(p)) { chromePath = p; break; }
  }
  if (chromePath) break;
}
const profile = mkdtempSync(join(tmpdir(), 'scholaris-rc-'));
const chrome = spawn(chromePath, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
for (let i = 0; i < 60; i++) {
  try { await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; }
  catch { await sleep(250); }
}
const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 1;
const pending = new Map();
let documents = 0;
let navReasons = [];
const errs = [];
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id); pending.delete(m.id);
    m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    return;
  }
  if (m.method === 'Page.frameNavigated' && !m.params.frame.parentId) {
    documents++;
  }
  if (m.method === 'Page.frameRequestedNavigation') {
    navReasons.push(m.params.reason + ' ' + String(m.params.url).replace(/^https?:\/\/[^/]+/, ''));
  }
  if (m.method === 'Runtime.exceptionThrown') {
    errs.push(m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text);
  }
};
const send = (method, params = {}) => {
  const i = id++;
  ws.send(JSON.stringify({ id: i, method, params }));
  return new Promise((res, rej) => {
    pending.set(i, { resolve: res, reject: rej });
    setTimeout(() => { if (pending.has(i)) { pending.delete(i); rej(new Error('timeout ' + method)); } }, 30000);
  });
};

await send('Page.enable');
await send('Runtime.enable');
await send('Page.navigate', { url: URL_ });
await sleep(WAIT_MS);

let state = 'n/a';
try {
  const r = await send('Runtime.evaluate', {
    expression: `JSON.stringify({
      readyState: document.readyState,
      rootChildren: document.getElementById('root')?.children.length ?? -1,
      bodyLen: (document.body.innerText||'').length,
    })`,
    returnByValue: true,
  });
  state = r.result.value;
} catch (e) { state = 'eval failed: ' + e.message; }

const uniq = [...new Set(navReasons)];
console.log('URL:', URL_);
console.log('documents created in', WAIT_MS, 'ms:', documents);
console.log('navigation requests:', navReasons.length, uniq.length ? '| unique: ' + uniq.join(', ') : '');
console.log('state:', state);
console.log('page exceptions:', errs.length, errs.slice(0, 2).join(' | '));

ws.close(); chrome.kill();
try { rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(0);
