// scripts/pwa_cdp_check.mjs
/**
 * PWA verification driver for SCHOLARIS, over the Chrome DevTools Protocol.
 *
 * Why not the shared browser-automation harness: it could not reliably hold a
 * page open long enough to exercise a service worker, and it offers no way to
 * simulate a hard network failure. Both are essential here (offline shell,
 * "never fake success" behaviour, update flow), so this script drives Chrome
 * directly instead. Node 24 has a global WebSocket, so there is no dependency.
 *
 * Usage:
 *   node scripts/pwa_cdp_check.mjs            # run the whole suite
 *   node scripts/pwa_cdp_check.mjs --keep     # leave the browser running
 *
 * The frontend must be served by a production build for the service worker to
 * exist at all (it is intentionally disabled in `npm run dev`).
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ORIGIN = process.env.PWA_ORIGIN || 'http://localhost:5173';
const API = process.env.PWA_API || 'http://localhost:8000';
const KEEP = process.argv.includes('--keep');

const CHROME_CANDIDATES = [
  join(process.env.LOCALAPPDATA || '', 'ms-playwright', 'chromium-1148', 'chrome-win', 'chrome.exe'),
  join(process.env.LOCALAPPDATA || '', 'ms-playwright', 'chromium-1194', 'chrome-win', 'chrome.exe'),
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
];

function findChrome() {
  // Prefer any chromium build under ms-playwright if the pinned path moved.
  const base = join(process.env.LOCALAPPDATA || '', 'ms-playwright');
  if (existsSync(base)) {
    const { readdirSync } = await_import_fs();
    for (const dir of readdirSync(base)) {
      for (const rel of ['chrome-win/chrome.exe', 'chrome-win64/chrome.exe', 'chrome-linux/chrome']) {
        const p = join(base, dir, rel);
        if (existsSync(p)) return p;
      }
    }
  }
  for (const c of CHROME_CANDIDATES) if (existsSync(c)) return c;
  throw new Error('No Chrome/Chromium binary found');
}
function await_import_fs() {
  return { readdirSync: (p) => require_fs().readdirSync(p) };
}
function require_fs() {
  return globalThis.__fs || (globalThis.__fs = fsMod);
}
import * as fsMod from 'node:fs';

const PORT = 9333;
const profile = mkdtempSync(join(tmpdir(), 'scholaris-pwa-'));

let chrome;
let ws;
let nextId = 1;
const pending = new Map();
const consoleLog = [];
const pageErrors = [];
const failedRequests = [];
const swEvents = [];

function send(method, params = {}, sessionId) {
  const id = nextId++;
  const msg = { id, method, params };
  if (sessionId) msg.sessionId = sessionId;
  ws.send(JSON.stringify(msg));
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id);
        reject(new Error(`CDP timeout: ${method}`));
      }
    }, 30000);
  });
}

async function evaluate(expression) {
  const res = await send('Runtime.evaluate', {
    expression: `(async () => { ${expression} })()`,
    awaitPromise: true,
    returnByValue: true,
  });
  if (res.exceptionDetails) {
    throw new Error(
      'page error: ' +
        (res.exceptionDetails.exception?.description || res.exceptionDetails.text)
    );
  }
  return res.result.value;
}

/**
 * Evaluate, retrying across navigations.
 *
 * The service worker can take control (or a redirect can land) while a
 * Runtime.evaluate is in flight, which aborts it with "Inspected target
 * navigated or closed". That is a benign race, not a page failure, so retry.
 */
async function evaluateStable(expression, attempts = 4) {
  let last;
  for (let i = 0; i < attempts; i++) {
    try {
      return await evaluate(expression);
    } catch (e) {
      last = e;
      const msg = String(e?.message || e);
      if (!/navigated or closed|Inspected target/.test(msg)) throw e;
      await sleep(400);
    }
  }
  throw last;
}

/** Poll until `text` is present in the document (handles React.lazy). */
async function waitForText(text, timeoutMs = 12000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const found = await evaluateStable(
        `return (document.body.innerText||'').includes(${JSON.stringify(text)});`
      );
      if (found) return true;
    } catch { /* mid-navigation */ }
    await sleep(200);
  }
  return false;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --------------------------------------------------------------------------
// tiny assertion harness
// --------------------------------------------------------------------------
const results = [];
function check(label, pass, detail = '') {
  results.push({ label, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -> ' + detail : ''}`);
}

// --------------------------------------------------------------------------
async function main() {
  const chromePath = findChrome();
  console.log(`chrome: ${chromePath}`);
  chrome = spawn(
    chromePath,
    [
      '--headless=new',
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${profile}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-gpu',
      '--window-size=1440,900',
      'about:blank',
    ],
    { stdio: 'ignore' }
  );

  // Wait for the debugging endpoint.
  let version = null;
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      version = await r.json();
      break;
    } catch {
      await sleep(250);
    }
  }
  if (!version) throw new Error('Chrome debugging endpoint never came up');
  console.log(`browser: ${version.Browser}`);

  const targetRes = await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' });
  const target = await targetRes.json();

  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = () => rej(new Error('CDP websocket failed'));
  });

  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? reject(new Error(`${m.error.message} (${JSON.stringify(m.error.data ?? '')})`)) : resolve(m.result);
      return;
    }
    switch (m.method) {
      case 'Runtime.consoleAPICalled':
        consoleLog.push({
          type: m.params.type,
          text: (m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' '),
        });
        break;
      case 'Runtime.exceptionThrown':
        pageErrors.push(
          m.params.exceptionDetails?.exception?.description ||
            m.params.exceptionDetails?.text ||
            'unknown'
        );
        break;
      case 'Log.entryAdded':
        if (m.params.entry.level === 'error') pageErrors.push(`[log] ${m.params.entry.text}`);
        break;
      case 'Network.loadingFailed':
        failedRequests.push({ type: m.params.type, error: m.params.errorText });
        break;
      case 'ServiceWorker.workerRegistrationUpdated':
        swEvents.push(m.params.registrations?.length ?? 0);
        break;
      default:
        break;
    }
  };

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Log.enable');
  await send('Network.enable');
  await send('ServiceWorker.enable');
  await send('Page.setLifecycleEventsEnabled', { enabled: true });

  console.log('\n================ 1. manifest + metadata ================');
  await send('Page.navigate', { url: `${ORIGIN}/login` });
  await waitForLoad();
  const signInReady = await waitForText('Portal Sign In', 15000);

  const meta = await evaluateStable(`
    const q = (s) => document.querySelector(s);
    return {
      manifestHref: q('link[rel=manifest]')?.getAttribute('href') ?? null,
      themeColor: q('meta[name=theme-color]')?.getAttribute('content') ?? null,
      viewport: q('meta[name=viewport]')?.getAttribute('content') ?? null,
      appleCapable: q('meta[name=apple-mobile-web-app-capable]')?.getAttribute('content') ?? null,
      appleTitle: q('meta[name=apple-mobile-web-app-title]')?.getAttribute('content') ?? null,
      appleStatusBar: q('meta[name=apple-mobile-web-app-status-bar-style]')?.getAttribute('content') ?? null,
      appleIcon: q('link[rel=apple-touch-icon]')?.getAttribute('href') ?? null,
      icon192: q('link[rel=icon][sizes="192x192"]')?.getAttribute('href') ?? null,
      title: document.title,
      description: q('meta[name=description]')?.getAttribute('content') ?? null,
      rootChildren: document.getElementById('root')?.children.length ?? -1,
      hasSignIn: (document.body.innerText||'').includes('Portal Sign In'),
    };
  `);
  check('manifest link present', meta.manifestHref === '/manifest.webmanifest', meta.manifestHref);
  check('theme-color set', meta.themeColor === '#1e1b4b', meta.themeColor);
  check('viewport-fit=cover', (meta.viewport || '').includes('viewport-fit=cover'), meta.viewport);
  check('apple-mobile-web-app-capable', meta.appleCapable === 'yes', meta.appleCapable);
  check('apple-mobile-web-app-title', meta.appleTitle === 'SCHOLARIS', meta.appleTitle);
  check('apple touch icon', meta.appleIcon === '/icons/apple-touch-icon.png', meta.appleIcon);
  check('192 icon link', meta.icon192 === '/icons/icon-192.png', meta.icon192);
  check('app actually rendered', meta.rootChildren > 0 && meta.hasSignIn, `rootChildren=${meta.rootChildren} signInText=${signInReady}`);

  // Manifest is fetched and parsed by the browser?
  const man = await evaluateStable(`
    const r = await fetch('/manifest.webmanifest');
    const j = await r.json();
    return { ok: r.ok, type: r.headers.get('content-type'), name: j.name, short: j.short_name,
             start: j.start_url, scope: j.scope, display: j.display, theme: j.theme_color,
             bg: j.background_color, id: j.id, icons: j.icons.map(i => i.sizes + ':' + i.purpose) };
  `);
  check('manifest fetchable + JSON', man.ok && man.name === 'SCHOLARIS School ERP', man.name);
  check('short_name = SCHOLARIS', man.short === 'SCHOLARIS', man.short);
  check('start_url = /', man.start === '/', man.start);
  check('scope = /', man.scope === '/', man.scope);
  check('display = standalone', man.display === 'standalone', man.display);
  check('theme_color in manifest', man.theme === '#1e1b4b', man.theme);
  check('background_color in manifest', man.bg === '#0f172a', man.bg);
  check('has 192 + 512 any icons', man.icons.some((i) => i === '192x192:any') && man.icons.some((i) => i === '512x512:any'), man.icons.join(' '));
  check('has maskable icons', man.icons.some((i) => i.endsWith(':maskable')), man.icons.join(' '));

  const iconFetches = await evaluateStable(`
    const paths = ['/icons/icon-192.png','/icons/icon-512.png','/icons/icon-192-maskable.png',
                   '/icons/icon-512-maskable.png','/icons/apple-touch-icon.png','/icons/favicon.png'];
    const out = [];
    for (const p of paths) {
      const r = await fetch(p);
      const b = await r.blob();
      out.push(p + ' ' + r.status + ' ' + b.size);
    }
    return out;
  `);
  check('all 6 icons resolve over HTTP', iconFetches.every((s) => s.includes(' 200 ')), iconFetches.join(' | '));

  console.log('\n================ 2. service worker ================');
  // A first visit installs the worker; with `clientsClaim` it should control
  // this page too, so the very first visit is already offline-capable.
  const sw = await (async () => {
    for (let i = 0; i < 40; i++) {
      const s = await evaluateStable(`
        const reg = await navigator.serviceWorker.getRegistration();
        if (!reg) return { registered: false };
        return { registered: true, scope: reg.scope, active: !!reg.active,
                 state: reg.active?.state ?? (reg.installing ? reg.installing.state : 'none'),
                 controller: !!navigator.serviceWorker.controller };
      `);
      if (s.registered && s.state === 'activated' && s.controller) return s;
      await sleep(250);
    }
    return await evaluateStable(`
      const reg = await navigator.serviceWorker.getRegistration();
      return { registered: !!reg, scope: reg?.scope, active: !!reg?.active,
               state: reg?.active?.state ?? 'none', controller: !!navigator.serviceWorker.controller };
    `);
  })();
  check('service worker registered', sw.registered, sw.scope || '');
  check('service worker active', sw.active && sw.state === 'activated', sw.state);
  check('scope covers the app root', sw.scope === `${ORIGIN}/`, sw.scope);
  check('page is controlled by the worker', sw.controller, 'navigator.serviceWorker.controller');

  const caches1 = await evaluateStable(`
    const names = await caches.keys();
    const detail = {};
    for (const n of names) {
      const c = await caches.open(n);
      detail[n] = (await c.keys()).map(r => new URL(r.url).pathname);
    }
    return { names, detail };
  `);
  const allCached = Object.values(caches1.detail).flat();
  check('precache created', caches1.names.some((n) => n.includes('precache')), caches1.names.join(','));
  check('index.html precached', allCached.some((p) => p === '/index.html' || p.endsWith('/index.html')));
  check('JS chunks precached', allCached.filter((p) => p.endsWith('.js')).length > 10, String(allCached.filter((p) => p.endsWith('.js')).length) + ' js files');
  const leaked = allCached.filter((p) => p.startsWith('/api/') || p.includes('localhost:8000') || p.includes('scholaris.in'));
  check('NO authenticated API responses in any cache', leaked.length === 0, leaked.join(',') || 'none');

  console.log('\n================ 3. navigation + scope ================');
  for (const route of ['/superadmin', '/principal', '/teacher', '/student', '/principal/attendance/reports', '/login']) {
    await send('Page.navigate', { url: `${ORIGIN}${route}` });
    await waitForLoad();
    await sleep(700);
    const r = await evaluateStable(`
      return { url: location.pathname, rootChildren: document.getElementById('root')?.children.length ?? -1,
               text: (document.body.innerText||'').slice(0,80).replace(/\\s+/g,' ') };
    `);
    check(`direct nav ${route} renders`, r.rootChildren > 0, `${r.url} rootChildren=${r.rootChildren}`);
  }

  console.log('\n================ 4. nested-route refresh ================');
  await send('Page.navigate', { url: `${ORIGIN}/login` });
  await waitForLoad();
  await sleep(600);
  await send('Page.reload', { ignoreCache: false });
  await waitForLoad();
  await sleep(800);
  const afterReload = await evaluateStable(`
    return { rootChildren: document.getElementById('root')?.children.length ?? -1,
             text: (document.body.innerText||'').slice(0,60).replace(/\\s+/g,' ') };
  `);
  check('refresh on a nested route keeps the SPA alive', afterReload.rootChildren > 0, afterReload.text);

  console.log('\n================ 5. auth + PWA interaction ================');
  const loginRes = await evaluateStable(`
    const r = await fetch('${API}/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mobile: '9000000001', password: 'QaTest#2026p' }),
    });
    if (!r.ok) return { ok: false, status: r.status, body: (await r.text()).slice(0,200) };
    const j = await r.json();
    localStorage.setItem('scholaris_access_token', j.access_token);
    return { ok: true, role: j.user?.role ?? null };
  `);
  check('principal login via API works', loginRes.ok, `role=${loginRes.role} ${loginRes.body || ''}`);

  await send('Page.navigate', { url: `${ORIGIN}/` });
  await waitForLoad();
  await waitForText('Dashboard', 15000);
  await sleep(600);
  const authed = await evaluateStable(`
    return { path: location.pathname, token: !!localStorage.getItem('scholaris_access_token'),
             text: (document.body.innerText||'').slice(0,120).replace(/\\s+/g,' ') };
  `);
  check('restored session redirects to the principal dashboard', authed.path === '/principal/dashboard', authed.path);
  check('session survives a reload with the SW installed', authed.token, 'token present');

  const apiCached = await evaluateStable(`
    const names = await caches.keys();
    const out = [];
    for (const n of names) {
      const c = await caches.open(n);
      for (const r of await c.keys()) {
        const p = new URL(r.url).pathname;
        if (p.startsWith('/api/')) out.push(n + ' ' + p);
      }
    }
    return out;
  `);
  check('after loading private data, still no API cache entries', apiCached.length === 0, apiCached.join(',') || 'none');

  console.log('\n================ 6. offline behaviour ================');
  await send('Network.emulateNetworkConditions', {
    offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0,
  });
  await sleep(400);

  await send('Page.navigate', { url: `${ORIGIN}/principal/dashboard` });
  await waitForLoad();
  await sleep(1500);
  const off = await evaluateStable(`
    return { path: location.pathname, rootChildren: document.getElementById('root')?.children.length ?? -1,
             hasOfflineBanner: !!document.querySelector('[data-testid=offline-indicator]'),
             bannerText: document.querySelector('[data-testid=offline-indicator]')?.innerText?.replace(/\\s+/g,' ').slice(0,120) ?? null,
             body: (document.body.innerText||'').replace(/\\s+/g,' ').slice(0,200) };
  `);
  check('offline: app shell still loads', off.rootChildren > 0, `rootChildren=${off.rootChildren} path=${off.path}`);
  check('offline: indicator is shown', off.hasOfflineBanner, off.bannerText || '');

  const mutation = await evaluateStable(`
    // A write must FAIL, not look like it succeeded.
    const t = localStorage.getItem('scholaris_access_token');
    try {
      const r = await fetch('${API}/api/v1/notifications', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t },
        body: JSON.stringify({ title: 'offline probe', message: 'x', notification_type: 'PUBLIC' }),
      });
      return { reachedServer: true, status: r.status };
    } catch (e) {
      return { reachedServer: false, error: String(e).slice(0,120) };
    }
  `);
  check('offline: mutation cannot reach the server (no fake success)', mutation.reachedServer === false, JSON.stringify(mutation));

  await send('Network.emulateNetworkConditions', {
    offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1,
  });
  // Two real recovery paths must both clear the banner:
  //   a) the app's own request layer succeeding, and
  //   b) the tab being focused again while the browser reports being online
  //      (navigator.onLine only reports link state, and CDP emulation does not
  //      reliably fire an `online` event).
  let recovered = false;
  for (let i = 0; i < 20; i++) {
    await sleep(300);
    try {
      recovered = await evaluateStable(`
        try { await fetch('${API}/health', { cache: 'no-store' }); } catch (e) {}
        window.dispatchEvent(new Event('focus'));
        return !document.querySelector('[data-testid=offline-indicator]');
      `);
    } catch { /* mid-navigation */ }
    if (recovered) break;
  }
  const back = await evaluateStable(`
    return { hasOfflineBanner: !!document.querySelector('[data-testid=offline-indicator]'), online: navigator.onLine };
  `);
  check('back online: indicator clears itself (no reload needed)', back.hasOfflineBanner === false, `navigator.onLine=${back.online}`);

  console.log('\n================ 7. logout + no cached private content ================');
  await send('Page.navigate', { url: `${ORIGIN}/principal/dashboard` });
  await waitForLoad();
  await sleep(1200);
  await evaluateStable(`localStorage.removeItem('scholaris_access_token'); return 1;`);
  await send('Page.navigate', { url: `${ORIGIN}/principal/dashboard` });
  await waitForLoad();
  await sleep(1200);
  const afterLogout = await evaluateStable(`
    return { path: location.pathname, rootChildren: document.getElementById('root')?.children.length ?? -1,
             leakedNames: /QAPrincipal|QA Student|QaTest/.test(document.body.innerText||'') };
  `);
  check('after logout, protected route is not served', afterLogout.path === '/login', afterLogout.path);
  check('no previous user data visible from the cached shell', afterLogout.leakedNames === false, 'no private strings in DOM');

  console.log('\n================ 8. error hygiene ================');
  const realErrors = pageErrors.filter((e) => !/favicon|ERR_INTERNET_DISCONNECTED|ERR_FAILED.*favicon/i.test(e));
  check('no uncaught page errors', realErrors.length === 0, realErrors.slice(0, 3).join(' | '));
  const errLogs = consoleLog.filter((c) => c.type === 'error');
  check('no console.error during the run', errLogs.length === 0, errLogs.slice(0, 3).map((c) => c.text.slice(0, 120)).join(' | '));

  console.log('\n================ 9. viewport / mobile ================');
  for (const [w, h, label] of [[390, 844, 'mobile'], [768, 1024, 'tablet'], [1440, 900, 'desktop']]) {
    await send('Emulation.setDeviceMetricsOverride', {
      width: w, height: h, deviceScaleFactor: 1, mobile: w < 700,
    });
    await send('Page.navigate', { url: `${ORIGIN}/login` });
    await waitForLoad();
    await sleep(1400);
    const m = await evaluateStable(`
      return { path: location.pathname,
               overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
               hasSignIn: (document.body.innerText||'').includes('Portal Sign In') };
    `);
    check(`${label} ${w}x${h}: login renders, no horizontal overflow`,
      m.overflowX <= 1 && m.hasSignIn, `overflowX=${m.overflowX}`);
  }
  await send('Emulation.clearDeviceMetricsOverride');

  // ---- summary ----
  const passed = results.filter((r) => r.pass).length;
  console.log(`\n${'='.repeat(60)}\n${passed}/${results.length} checks passed`);
  const failed = results.filter((r) => !r.pass);
  if (failed.length) {
    console.log('\nFAILED:');
    for (const f of failed) console.log(`  - ${f.label}  ${f.detail}`);
  }
  return failed.length === 0 ? 0 : 1;
}

async function waitForLoad() {
  for (let i = 0; i < 80; i++) {
    try {
      const r = await evaluateStable(`return document.readyState;`);
      if (r === 'complete') return;
    } catch { /* mid-navigation */ }
    await sleep(150);
  }
}

let exitCode = 1;
try {
  exitCode = await main();
} catch (e) {
  console.error('\nDRIVER ERROR:', e.message);
  exitCode = 2;
} finally {
  try { ws?.close(); } catch {}
  try { chrome?.kill(); } catch {}
  if (!KEEP) { try { rmSync(profile, { recursive: true, force: true }); } catch {} }
}
process.exit(exitCode);
