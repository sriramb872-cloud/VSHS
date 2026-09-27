// scripts/pwa_cdp_deep.mjs
/**
 * Deeper PWA scenarios over CDP:
 *   A. Update flow  - simulate a deploy, prove the user is told and chooses.
 *   B. Install UX   - beforeinstallprompt handling and dismissal persistence.
 *   C. Cross-role   - one role's private data must never reach another.
 *   D. Mobile pages - real ERP screens at 390x844, not just the login page.
 *
 * Requires a production preview already serving `dist` on PWA_ORIGIN.
 * Run: node scripts/pwa_cdp_deep.mjs
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ORIGIN = process.env.PWA_ORIGIN || 'http://localhost:5173';
const API = process.env.PWA_API || 'http://localhost:8000';
const PORT = 9366;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
function check(label, pass, detail = '') {
  results.push({ label, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -> ' + detail : ''}`);
}

const base = join(process.env.LOCALAPPDATA || '', 'ms-playwright');
let chromePath = null;
for (const dir of readdirSync(base)) {
  for (const rel of ['chrome-win64/chrome.exe', 'chrome-win/chrome.exe']) {
    const p = join(base, dir, rel);
    if (existsSync(p)) { chromePath = p; break; }
  }
  if (chromePath) break;
}

const profile = mkdtempSync(join(tmpdir(), 'scholaris-deep-'));
const chrome = spawn(chromePath, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', 'about:blank',
], { stdio: 'ignore' });

for (let i = 0; i < 60; i++) {
  try { await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; }
  catch { await sleep(250); }
}
const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 1;
const pending = new Map();
const consoleErrors = [];
const exceptions = [];
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id); pending.delete(m.id);
    m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    return;
  }
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    consoleErrors.push((m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 200));
  }
  if (m.method === 'Runtime.exceptionThrown') {
    exceptions.push(m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text);
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
async function ev(expression, attempts = 4) {
  let last;
  for (let i = 0; i < attempts; i++) {
    try {
      const r = await send('Runtime.evaluate', {
        expression: `(async () => { ${expression} })()`, awaitPromise: true, returnByValue: true,
      });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    } catch (e) {
      last = e;
      if (!/navigated or closed|Inspected target/.test(String(e?.message || e))) throw e;
      await sleep(400);
    }
  }
  throw last;
}
async function waitForLoad() {
  for (let i = 0; i < 80; i++) {
    try { if (await ev('return document.readyState;') === 'complete') return; } catch {}
    await sleep(150);
  }
}
async function waitForText(text, timeoutMs = 12000) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    try { if (await ev(`return (document.body.innerText||'').includes(${JSON.stringify(text)});`)) return true; }
    catch {}
    await sleep(200);
  }
  return false;
}
async function go(url) { await send('Page.navigate', { url }); await waitForLoad(); }

await send('Page.enable');
await send('Runtime.enable');
await send('Network.enable');

// POST /auth/login is rate limited to 5/minute on the backend, so space the
// logins out rather than tripping the limiter and silently losing a session.
let lastLoginAt = 0;
const login = async (mobile, password) => {
  const since = Date.now() - lastLoginAt;
  if (since < 13000) await sleep(13000 - since);
  lastLoginAt = Date.now();
  return ev(`
  const r = await fetch('${API}/api/v1/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mobile: '${mobile}', password: '${password}' }),
  });
  if (!r.ok) return { ok: false, status: r.status, body: (await r.text()).slice(0, 160) };
  const j = await r.json();
  localStorage.setItem('scholaris_access_token', j.access_token);
  return { ok: true, status: r.status };
`);
};

console.log('=============== A. INSTALL UX ===============');
await go(`${ORIGIN}/login`);
await waitForText('Portal Sign In');
// Give Chrome a moment to decide the app is installable and fire the event.
let installSeen = false;
for (let i = 0; i < 25; i++) {
  installSeen = await ev(`return !!document.querySelector('[data-testid=pwa-install-prompt]');`);
  if (installSeen) break;
  await sleep(400);
}
check('beforeinstallprompt fired and the install card rendered', installSeen);
if (installSeen) {
  const labels = await ev(`
    const c = document.querySelector('[data-testid=pwa-install-prompt]');
    return { text: c.innerText.replace(/\\s+/g,' ').slice(0,160),
             buttons: Array.from(c.querySelectorAll('button')).map(b => b.innerText.trim() || b.getAttribute('aria-label') || b.querySelector('span')?.innerText || '(icon)'),
             hasAltImg: !!c.querySelector('img[alt=""]') };
  `);
  check('install card has a labelled Install action', labels.buttons.some((b) => /install/i.test(b)), labels.buttons.join('|'));
  check('install card dismiss control has an accessible name',
    labels.buttons.some((b) => /dismiss|not now/i.test(b)), labels.buttons.join('|'));
  check('install card logo image is decorative (empty alt)', labels.hasAltImg === true);

  // Dismiss and confirm it stays dismissed.
  await ev(`
    const c = document.querySelector('[data-testid=pwa-install-prompt]');
    const b = Array.from(c.querySelectorAll('button')).find(x => /not now|dismiss/i.test(x.innerText + (x.getAttribute('aria-label')||'')));
    b.click(); return 1;
  `);
  await sleep(500);
  const gone = await ev(`return !document.querySelector('[data-testid=pwa-install-prompt]');`);
  check('dismiss removes the install card immediately', gone === true);
  const stored = await ev(`return localStorage.getItem('scholaris_pwa_install_dismissed_at') !== null;`);
  check('dismissal is persisted in localStorage', stored === true);
  await go(`${ORIGIN}/login`);
  await waitForText('Portal Sign In');
  await sleep(1200);
  const stillGone = await ev(`return !document.querySelector('[data-testid=pwa-install-prompt]');`);
  check('dismissal survives a reload (does not nag every refresh)', stillGone === true);
}

console.log('\n=============== B. UPDATE FLOW ===============');
// Log in so we are on a real, data-backed page.
const pLogin = await login('9000000001', 'QaTest#2026p');
check('principal login succeeded (not rate limited)', pLogin.ok === true, `${pLogin.status} ${pLogin.body || ''}`);
await go(`${ORIGIN}/`);
await waitForText('Dashboard', 15000);
await sleep(1500);

const sw0 = await ev(`
  const r = await navigator.serviceWorker.getRegistration();
  return { state: r?.active?.state, controller: !!navigator.serviceWorker.controller, waiting: !!r?.waiting };
`);
check('baseline: worker active and controlling, nothing waiting', sw0.state === 'activated' && sw0.controller && !sw0.waiting, JSON.stringify(sw0));

// Simulate a real deployment.
//
// Editing files inside dist/ is not enough: the precache manifest is baked into
// sw.js at BUILD time, so the worker script would be byte-identical and the
// browser would install nothing. A genuine deploy means a new build, so we do
// one: mark the source, rebuild, restore the source.
//
// The original is captured with any leftover marker from a previous aborted run
// already stripped, so repeated runs always start from the real file.
const srcIndex = join(process.cwd(), 'index.html');
const marker = 'pwa-deep-deploy-marker';
const markerLine = new RegExp(`^\\s*<meta name="${marker}"[^>]*>\\r?\\n`, 'gm');
const srcOriginal = readFileSync(srcIndex, 'utf8').replace(markerLine, '');
if (srcOriginal !== readFileSync(srcIndex, 'utf8')) {
  writeFileSync(srcIndex, srcOriginal);
  console.log('(stripped a leftover deploy marker from a previous run)');
}
const runBuild = () => new Promise((resolve, reject) => {
  const p = spawn('npm', ['run', 'build'], {
    cwd: process.cwd(),
    env: { ...process.env, VITE_API_BASE_URL: 'http://localhost:8000/api/v1' },
    stdio: 'ignore',
    shell: true,
  });
  p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error('build exit ' + code))));
});

let restoreDone = false;
const restoreSource = () => {
  if (restoreDone) return;
  restoreDone = true;
  writeFileSync(srcIndex, srcOriginal);
};
process.on('exit', restoreSource);
process.on('SIGINT', () => { restoreSource(); process.exit(130); });

writeFileSync(srcIndex, srcOriginal.replace('</head>', `  <meta name="${marker}" content="v2" />\n  </head>`));
try {
  await runBuild();
  check('deployed a new build (v2)', true);
} catch (e) {
  restoreSource();
  check('deployed a new build (v2)', false, e.message);
}

// A deployment check. `updateViaCache: 'none'` forces the worker script to be
// re-fetched rather than served from the HTTP cache - the same effect a CDN
// with a short/no-cache policy for sw.js gives for free, and what the app's own
// hourly `registration.update()` relies on.
await ev(`await navigator.serviceWorker.getRegistration().then(r => r && r.update({ updateViaCache: 'none' })); return 1;`);

let sawWaiting = false;
for (let i = 0; i < 40; i++) {
  const s = await ev(`
    const r = await navigator.serviceWorker.getRegistration();
    return { waiting: !!r?.waiting, updatePrompt: !!document.querySelector('[data-testid=pwa-update-prompt]') };
  `);
  if (s.waiting) sawWaiting = true;
  if (s.updatePrompt) break;
  await sleep(400);
}
check('new worker detected and left waiting (not auto-activated)', sawWaiting === true);

const prompt = await ev(`
  const p = document.querySelector('[data-testid=pwa-update-prompt]');
  if (!p) return null;
  return { text: p.innerText.replace(/\\s+/g,' ').slice(0,200),
           role: p.getAttribute('role'), live: p.getAttribute('aria-live'),
           buttons: Array.from(p.querySelectorAll('button')).map(b => b.innerText.trim() || b.querySelector('span')?.innerText || b.getAttribute('aria-label') || '(icon)') };
`);
check('update prompt is shown to the user', prompt !== null, prompt ? prompt.text : 'not rendered');
if (prompt) {
  check('update prompt is a polite live region (screen-reader friendly)', prompt.role === 'status' && prompt.live === 'polite', `${prompt.role}/${prompt.live}`);
  check('update prompt offers an explicit Update action', prompt.buttons.some((b) => /update/i.test(b)), prompt.buttons.join('|'));
  check('update prompt offers a dismiss/Later action', prompt.buttons.some((b) => /later|dismiss/i.test(b)), prompt.buttons.join('|'));
}

// The user must NOT be auto-reloaded, and must still be on their page.
const beforeClick = await ev(`
  return { path: location.pathname,
           rootChildren: document.getElementById('root')?.children.length ?? -1 };
`);
check('app is NOT force-reloaded before the user accepts', beforeClick.rootChildren > 0, `still on ${beforeClick.path}`);

if (prompt) {
  await ev(`
    const p = document.querySelector('[data-testid=pwa-update-prompt]');
    Array.from(p.querySelectorAll('button')).find(b => /^update$/i.test(b.innerText.trim())).click();
    return 1;
  `);
  // The click posts SKIP_WAITING; the app reloads once the new worker controls.
  await sleep(4000);
  await waitForLoad();
  await sleep(1500);
  const after = await ev(`
    const r = await navigator.serviceWorker.getRegistration();
    return { markerLive: !!document.querySelector('meta[name="${marker}"]'),
             waiting: !!r?.waiting, state: r?.active?.state, controller: !!navigator.serviceWorker.controller,
             promptGone: !document.querySelector('[data-testid=pwa-update-prompt]'),
             appAlive: (document.getElementById('root')?.children.length ?? -1) > 0 };
  `);
  check('after Update: the new build is live', after.markerLive === true, `marker=${after.markerLive}`);
  check('after Update: no worker left waiting', after.waiting === false, JSON.stringify(after));
  check('after Update: update prompt dismissed', after.promptGone === true);
  check('after Update: the app still works', after.appAlive === true);
}

console.log('\n=============== C. CROSS-ROLE ISOLATION ===============');
const privateStrings = ['QAPrincipal Test', 'QA Student', 'QA Teacher'];
async function readPrivateSurface(label) {
  await go(`${ORIGIN}/`);
  await waitForText('Dashboard', 15000);
  await sleep(1500);
  const txt = await ev(`return (document.body.innerText||'');`);
  return {
    label,
    path: await ev('return location.pathname;'),
    hits: privateStrings.filter((s) => txt.includes(s)),
  };
}

const asPrincipal = await readPrivateSurface('principal');
check('principal sees their own school data', asPrincipal.hits.length > 0, asPrincipal.hits.join(','));

await ev(`localStorage.removeItem('scholaris_access_token'); return 1;`);
await go(`${ORIGIN}/principal/dashboard`);
await waitForLoad();
await sleep(1200);
const afterLogout = await ev(`
  return { path: location.pathname,
           hasPrivate: /QAPrincipal Test|QA Student|QA Teacher/.test(document.body.innerText||'') };
`);
check('logout: protected route bounces to /login', afterLogout.path === '/login', afterLogout.path);
check('logout: no principal data in the cached shell', afterLogout.hasPrivate === false);

await login('9000000002', 'QaTeach#2027');
const asTeacher = await readPrivateSurface('teacher');
check('teacher lands on the teacher area', asTeacher.path.startsWith('/teacher'), asTeacher.path);
const teacherSeesPrincipal = asTeacher.hits.some((h) => h === 'QAPrincipal Test');
check('teacher does not see principal-only content', teacherSeesPrincipal === false, asTeacher.hits.join(','));

await ev(`localStorage.removeItem('scholaris_access_token'); return 1;`);
const sLogin = await login('9000001001', 'QaStu#2026');
check('student login succeeded (not rate limited)', sLogin.ok === true, `${sLogin.status} ${sLogin.body || ''}`);
const asStudent = await readPrivateSurface('student');
check('student lands on the student area', asStudent.path.startsWith('/student'), asStudent.path);
const studentSeesStaff = asStudent.hits.some((h) => h === 'QAPrincipal Test' || h === 'QA Teacher');
check('student does not see staff-only content', studentSeesStaff === false, asStudent.hits.join(','));

console.log('\n=============== D. MOBILE PAGES (390x844) ===============');
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
const pLoginM = await login('9000000001', 'QaTest#2026p');
check('mobile login succeeded (not rate limited)', pLoginM.ok === true, `${pLoginM.status} ${pLoginM.body || ''}`);

const pages = [
  ['/principal/dashboard', 'Dashboard'],
  ['/principal/students', null],
  ['/principal/attendance', null],
  ['/principal/attendance/reports', null],
  ['/principal/exams', null],
  ['/principal/notifications', null],
  ['/principal/profile', null],
  ['/principal/settings', null],
  ['/principal/calendar', null],
];
for (const [route, marker] of pages) {
  await go(`${ORIGIN}${route}`);
  if (marker) await waitForText(marker, 15000);
  await sleep(1200);
  const r = await ev(`
    // True horizontal overflow is scrollWidth > innerWidth. Comparing against
    // clientWidth instead would count the vertical scrollbar as overflow.
    const de = document.documentElement;
    const vw = window.innerWidth;
    // Widest element that overflows and is NOT clipped/scrolled by an ancestor.
    const container = (el) => {
      let p = el.parentElement;
      while (p && p !== de) {
        const st = getComputedStyle(p);
        if (/(auto|scroll|hidden|clip)/.test(st.overflowX)) return p.tagName;
        p = p.parentElement;
      }
      return null;
    };
    let worst = null, worstW = 0, worstClippedBy = null;
    for (const el of document.querySelectorAll('body *')) {
      const b = el.getBoundingClientRect();
      if (!b.width || !b.height) continue;
      if (b.right > vw + 1.5) {
        const by = container(el);
        const over = b.right - vw;
        if (!by) {
          if (over > worstW) { worstW = over; worst = el.tagName + '.' + String(el.className).slice(0, 60); }
        } else if (!worstClippedBy && over > 0) {
          worstClippedBy = by;
        }
      }
    }
    return {
      overflowX: de.scrollWidth - vw,
      worst: worst, worstOver: Math.round(worstW),
      clippedBy: worstClippedBy,
      bodyLen: (document.body.innerText||'').length,
      vw,
    };
  `);
  const ok = r.overflowX <= 1 && r.worstOver === 0;
  check(`mobile ${route}: no horizontal page overflow`, ok,
    `overflowX=${r.overflowX} unclippedWorst=${r.worst || '-'} (+${r.worstOver}px) bodyLen=${r.bodyLen}`);
  if (r.clippedBy) {
    check(`mobile ${route}: wide content is clipped by a container (${r.clippedBy})`, true, 'expected for tables/calendars');
  }
}
await send('Emulation.clearDeviceMetricsOverride');

console.log('\n=============== E. ERROR HYGIENE ===============');
const realExc = exceptions.filter((e) => !/favicon/i.test(e));
check('no uncaught exceptions during the deep run', realExc.length === 0, realExc.slice(0, 2).join(' | '));
const realErr = consoleErrors.filter((e) => !/favicon|ERR_/.test(e));
check('no console.error during the deep run', realErr.length === 0, realErr.slice(0, 2).join(' | '));

// Put the source back and rebuild so the repo/serve tree is left clean.
restoreSource();
try { await runBuild(); console.log('\n(restored index.html and rebuilt)'); } catch (e) { console.log('\nWARNING: restore build failed: ' + e.message); }

const passed = results.filter((r) => r.pass).length;
console.log(`\n${'='.repeat(60)}\n${passed}/${results.length} deep checks passed`);
const failed = results.filter((r) => !r.pass);
if (failed.length) { console.log('\nFAILED:'); for (const f of failed) console.log(`  - ${f.label}  ${f.detail}`); }

ws.close(); chrome.kill();
try { rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(failed.length ? 1 : 0);
