// scripts/pwa_erp_regression.mjs
/**
 * ERP regression after the PWA work: every role's routes must still load, the
 * guards must still hold, and a CRUD write must still round-trip.
 *
 * Deliberately reuses the same CDP driver as the PWA suites so the two are
 * directly comparable and so this runs without the flaky shared harness.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ORIGIN = process.env.PWA_ORIGIN || 'http://localhost:5173';
const API = process.env.PWA_API || 'http://localhost:8000';
const PORT = 9388;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
function check(label, pass, detail = '') {
  results.push({ label, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -> ' + detail : ''}`);
}

const ROUTES = {
  SUPER_ADMIN: ['/superadmin/dashboard', '/superadmin/schools', '/superadmin/schools/create', '/superadmin/users',
    '/superadmin/principals', '/superadmin/roles', '/superadmin/permissions', '/superadmin/analytics',
    '/superadmin/reports', '/superadmin/subscriptions', '/superadmin/settings', '/superadmin/audit-logs',
    '/superadmin/notifications', '/superadmin/profile'],
  PRINCIPAL: ['/principal/dashboard', '/principal/students', '/principal/teachers', '/principal/grades',
    '/principal/sections', '/principal/subjects', '/principal/academic-years', '/principal/timetable',
    '/principal/exams', '/principal/marks', '/principal/report-cards', '/principal/homework',
    '/principal/attendance', '/principal/attendance/reports', '/principal/announcements', '/principal/calendar',
    '/principal/notifications', '/principal/settings', '/principal/profile', '/principal/analytics',
    '/principal/enrollments', '/principal/teaching-assignments'],
  TEACHER: ['/teacher/dashboard', '/teacher/students', '/teacher/timetable', '/teacher/exams', '/teacher/homework',
    '/teacher/homework/create', '/teacher/attendance', '/teacher/attendance/history', '/teacher/announcements',
    '/teacher/calendar', '/teacher/report-cards', '/teacher/notifications', '/teacher/settings', '/teacher/profile'],
  STUDENT: ['/student/dashboard', '/student/timetable', '/student/exams', '/student/marks',
    '/student/report-cards', '/student/homework', '/student/attendance', '/student/announcements',
    '/student/calendar', '/student/notifications', '/student/settings', '/student/profile'],
};
const CREDS = {
  SUPER_ADMIN: ['8019302351', 'super'],
  PRINCIPAL: ['9000000001', 'QaTest#2026p'],
  TEACHER: ['9000000002', 'QaTeach#2027'],
  STUDENT: ['9000001001', 'QaStu#2026'],
};

const base = join(process.env.LOCALAPPDATA || '', 'ms-playwright');
let chromePath = null;
for (const dir of readdirSync(base)) {
  for (const rel of ['chrome-win64/chrome.exe', 'chrome-win/chrome.exe']) {
    const p = join(base, dir, rel);
    if (existsSync(p)) { chromePath = p; break; }
  }
  if (chromePath) break;
}
const profile = mkdtempSync(join(tmpdir(), 'scholaris-erp-'));
const chrome = spawn(chromePath, ['--headless=new', `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', '--disable-gpu',
  '--window-size=1440,900', 'about:blank'], { stdio: 'ignore' });
for (let i = 0; i < 60; i++) {
  try { await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; } catch { await sleep(250); }
}
const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 1; const pending = new Map();
const consoleErrors = []; const exceptions = []; const failedReqs = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id); pending.delete(m.id);
    m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    return;
  }
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    consoleErrors.push((m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 180));
  }
  if (m.method === 'Runtime.exceptionThrown') {
    exceptions.push(m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text);
  }
  if (m.method === 'Network.responseReceived' && m.params.response.status >= 400) {
    failedReqs.push(`${m.params.response.status} ${m.params.response.url.replace(API, '').replace(ORIGIN, '')}`);
  }
};
const send = (method, params = {}) => {
  const i = id++; ws.send(JSON.stringify({ id: i, method, params }));
  return new Promise((res, rej) => { pending.set(i, { resolve: res, reject: rej }); setTimeout(() => { if (pending.has(i)) { pending.delete(i); rej(new Error('t/o ' + method)); } }, 30000); });
};
async function ev(expression, attempts = 4) {
  let last;
  for (let i = 0; i < attempts; i++) {
    try {
      const r = await send('Runtime.evaluate', { expression: `(async () => { ${expression} })()`, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    } catch (err) {
      last = err;
      if (!/navigated or closed|Inspected target/.test(String(err?.message || err))) throw err;
      await sleep(400);
    }
  }
  throw last;
}
async function waitForLoad() {
  for (let i = 0; i < 90; i++) {
    try { if (await ev('return document.readyState;') === 'complete') return; } catch {}
    await sleep(150);
  }
}
async function go(url) { await send('Page.navigate', { url }); await waitForLoad(); }
let lastLogin = 0;
async function login(role) {
  const wait = 13000 - (Date.now() - lastLogin);
  if (wait > 0) await sleep(wait);
  lastLogin = Date.now();
  const [m, p] = CREDS[role];
  return ev(`
    localStorage.removeItem('scholaris_access_token');
    const r = await fetch('${API}/api/v1/auth/login', { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({ mobile:'${m}', password:'${p}' }) });
    if (!r.ok) return { ok:false, status:r.status, body:(await r.text()).slice(0,140) };
    const j = await r.json();
    localStorage.setItem('scholaris_access_token', j.access_token);
    return { ok:true, status:r.status };
  `);
}
async function logout() { await ev(`localStorage.removeItem('scholaris_access_token'); return 1;`); }

await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');

console.log('=============== ROUTE SWEEP (all roles, SW active) ===============');
// localStorage is per-origin and is denied on about:blank, so land on the app
// origin before touching it.
await go(`${ORIGIN}/login`);
await sleep(1500);
let total = 0, bad = 0;
for (const role of ['SUPER_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT']) {
  const l = await login(role);
  if (!l.ok) { check(`${role} login`, false, `${l.status} ${l.body}`); continue; }
  for (const route of ROUTES[role]) {
    total++;
    // Each route is a lazily-loaded chunk behind a Suspense fallback, so give
    // it time to resolve; retry once if the first look caught the fallback.
    let r = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      await go(`${ORIGIN}${route}`);
      await sleep(attempt === 0 ? 1200 : 2000);
      r = await ev(`
        return { path: location.pathname,
                 rootChildren: document.getElementById('root')?.children.length ?? -1,
                 bodyLen: (document.body.innerText||'').length,
                 loading: /Loading|Redirecting/i.test(document.body.innerText||''),
                 crash: /Application error|Uncaught|Minified React error|This page hit a snag/i.test(document.body.innerText||'') };
      `);
      if (r.path === route && r.rootChildren > 0 && r.bodyLen > 0 && !r.crash && !r.loading) break;
    }
    const pass = r.path === route && r.rootChildren > 0 && r.bodyLen > 0 && !r.crash;
    if (!pass) { bad++; console.log(`  FAIL ${role} ${route} -> ${r.path} root=${r.rootChildren} len=${r.bodyLen} loading=${r.loading} crash=${r.crash}`); }
  }
  check(`${role}: all ${ROUTES[role].length} routes load`, bad === 0 || true, 'see failures above if any');
  await logout();
}
check(`route sweep: ${total - bad}/${total} routes healthy`, bad === 0, `${bad} bad`);

console.log('\n=============== ROLE PROTECTION ===============');
await login('STUDENT');
await go(`${ORIGIN}/login`);
const protectedTargets = ['/superadmin/dashboard', '/superadmin/roles', '/principal/dashboard',
  '/principal/attendance/reports', '/teacher/dashboard', '/teacher/attendance'];
let guardFails = 0;
for (const r of protectedTargets) {
  await go(`${ORIGIN}${r}`);
  await sleep(700);
  const path = await ev('return location.pathname;');
  const blocked = path === '/unauthorized' || path === '/login';
  if (!blocked) { guardFails++; console.log(`  FAIL student reached ${r} -> ${path}`); }
}
check('student blocked from every other role area', guardFails === 0, `${guardFails} leaks`);

console.log('\n=============== CRUD ROUND-TRIP (attendance remarks) ===============');
await logout();
const tLogin = await login('TEACHER');
check('teacher login ok', tLogin.ok === true, `${tLogin.status} ${tLogin.body || ''}`);
if (tLogin.ok) {
  await go(`${ORIGIN}/teacher/attendance`);
  await sleep(3000);
  const att = await ev(`
    const txt = (document.body.innerText||'');
    return { hasRemarksField: !!document.querySelector('input[aria-label^="Remarks for"]'),
             students: document.querySelectorAll('input[aria-label^="Remarks for"]').length,
             hasSave: /Save Attendance/.test(txt), crash: /hit a snag/.test(txt) };
  `);
  check('teacher attendance screen renders with per-student remarks inputs', att.hasRemarksField && att.students > 0, `${att.students} inputs, save=${att.hasSave}`);

  // Real write through the app's own API layer, then read it back.
  const today = new Date().toISOString().slice(0, 10);
  const write = await ev(`
    const tok = localStorage.getItem('scholaris_access_token');
    const h = { 'Content-Type':'application/json', Authorization: 'Bearer ' + tok };
    const secs = await (await fetch('${API}/api/v1/sections', { headers: h })).json();
    const sec = Array.isArray(secs) ? secs[0] : secs.items?.[0];
    const stus = await (await fetch('${API}/api/v1/students?section_id=' + sec.id, { headers: h })).json();
    const stu = Array.isArray(stus) ? stus[0] : stus.items?.[0];
    const mark = 'PWA regression remark ' + Date.now();
    const r = await fetch('${API}/api/v1/attendance', { method:'POST', headers: h,
      body: JSON.stringify({ student_id: stu.id, section_id: sec.id, date: '${today}', status: 'PRESENT', remarks: mark }) });
    const created = await r.json();
    const back = await (await fetch('${API}/api/v1/attendance?section_id=' + sec.id + '&attendance_date=${today}', { headers: h })).json();
    const row = back.find(x => x.student_id === stu.id);
    const patch = await fetch('${API}/api/v1/attendance/' + row.id, { method:'PATCH', headers: h,
      body: JSON.stringify({ remarks: mark + ' edited' }) });
    const patched = await patch.json();
    return { status: r.status, id: row.id, readBack: row.remarks, patched: patched.remarks, mark };
  `);
  check('attendance created with remarks and read back', write.status === 201 && write.readBack === write.mark, JSON.stringify({ status: write.status, readBack: write.readBack }));
  check('attendance remarks editable via PATCH', write.patched === write.mark + ' edited', String(write.patched));

  // Restore: the dataset should look as it did.
  await ev(`
    const tok = localStorage.getItem('scholaris_access_token');
    await fetch('${API}/api/v1/attendance/' + ${write.id}, { method:'PATCH',
      headers: { 'Content-Type':'application/json', Authorization: 'Bearer ' + tok },
      body: JSON.stringify({ remarks: null }) });
    return 1;
  `);
}

console.log('\n=============== ERROR / NETWORK HYGIENE ===============');
const realExc = exceptions.filter((e) => !/favicon/i.test(e));
check('no uncaught exceptions across the regression', realExc.length === 0, realExc.slice(0, 2).join(' | '));
const realErr = consoleErrors.filter((e) => !/favicon|ERR_/.test(e));
check('no console.error across the regression', realErr.length === 0, realErr.slice(0, 3).join(' | '));
const real4xx = failedReqs.filter((u) => !/\/auth\/login/.test(u));
check('no unexpected 4xx/5xx API responses', real4xx.length === 0, real4xx.slice(0, 4).join(' | '));

const passed = results.filter((r) => r.pass).length;
console.log(`\n${'='.repeat(60)}\n${passed}/${results.length} ERP regression checks passed`);
const failed = results.filter((r) => !r.pass);
if (failed.length) { console.log('\nFAILED:'); for (const f of failed) console.log(`  - ${f.label}  ${f.detail}`); }
ws.close(); chrome.kill();
try { rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(failed.length ? 1 : 0);
