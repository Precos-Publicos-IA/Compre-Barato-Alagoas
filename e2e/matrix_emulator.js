/**
 * Phase A handheld matrix runner — Android emulator + adb.
 *
 * For every touch:true format in qa_matrix.json (or MATRIX_FORMATS filter):
 *   1. Set emulator wm size/density to match CSS × dpr
 *   2. adb reverse host ports (app/api/admin/docs)
 *   3. Open Chrome to APP_URL
 *   4. adb shell screenrecord (full display) during journey
 *   5. adb shell input tap/text for touch journey
 *   6. adb exec-out screencap quality-hold PNGs per screen
 *
 * Chrome page.emulate alone is NOT ship-valid for handhelds — this runner is.
 *
 * Env:
 *   ADB_SERIAL          default: first emulator-* device
 *   APP_URL             default http://127.0.0.1:8080 (host; reversed into emulator)
 *   API_URL ADMIN_URL DOCS_URL  used for reverse map
 *   MATRIX_FORMATS      all|priority|handheld|comma ids (default: handheld)
 *   MATRIX_SCREENS      all|comma (default: all product + admin + docs where reachable)
 *   MATRIX_HOLD_MS      settle before screencap
 *   RECORD_VIDEO=1|0
 *   SKIP_WM_RESET=1     leave custom size after run (debug)
 *
 * Artifacts:
 *   e2e/screenshots/viewports/{format}_{shot_suffix}.png
 *   e2e/screenshots/web/e2e/recordings/{format}_touch.mp4  (screenrecord)
 *   e2e/screenshots/web/phone/emulator_results.json
 */

const fs = require('fs');
const path = require('path');
const { spawnSync, spawn } = require('child_process');

const ROOT = path.join(__dirname);
const MATRIX = JSON.parse(fs.readFileSync(path.join(ROOT, 'qa_matrix.json'), 'utf8'));

const APP_HOST_PORT = Number(process.env.APP_PORT || 8080);
const API_HOST_PORT = Number(process.env.API_PORT || 8000);
const ADMIN_HOST_PORT = Number(process.env.ADMIN_PORT || 8081);
const DOCS_HOST_PORT = Number(process.env.DOCS_PORT || 8082);

const APP_URL = (process.env.APP_URL || `http://127.0.0.1:${APP_HOST_PORT}`).replace(/\/$/, '');
const HOLD_MS = Number(process.env.MATRIX_HOLD_MS || 600);
const RECORD_VIDEO = process.env.RECORD_VIDEO !== '0';
const SEARCH_ITEM = process.env.MATRIX_SEARCH_ITEM || 'arroz';

const VIEWPORTS_DIR = path.join(ROOT, 'screenshots', 'viewports');
const RECORDINGS_DIR = path.join(ROOT, 'screenshots', 'web', 'e2e', 'recordings');
const PHONE_DIR = path.join(ROOT, 'screenshots', 'web', 'phone');
fs.mkdirSync(VIEWPORTS_DIR, { recursive: true });
fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
fs.mkdirSync(PHONE_DIR, { recursive: true });

const SCREEN_BY_ID = Object.fromEntries(MATRIX.screens.map((s) => [s.id, s]));
const FORMAT_BY_ID = Object.fromEntries(MATRIX.formats.map((f) => [f.id, f]));
const PRIORITY_FORMAT_IDS = ['phone_portrait', 'phone_android', 'laptop_hd', '1080p'];

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function adbBase(serial) {
  return serial ? ['-s', serial] : [];
}

function adb(serial, args, opts = {}) {
  const full = [...adbBase(serial), ...args];
  const r = spawnSync('adb', full, {
    encoding: 'utf8',
    timeout: opts.timeout || 60000,
    maxBuffer: 32 * 1024 * 1024,
    ...opts,
  });
  if (r.error) throw r.error;
  return r;
}

function adbOk(serial, args, opts = {}) {
  const r = adb(serial, args, opts);
  if (r.status !== 0) {
    const err = (r.stderr || r.stdout || '').trim().slice(0, 300);
    throw new Error(`adb ${args.join(' ')} failed (${r.status}): ${err}`);
  }
  return r;
}

function resolveSerial() {
  if (process.env.ADB_SERIAL) return process.env.ADB_SERIAL;
  const r = spawnSync('adb', ['devices'], { encoding: 'utf8' });
  const lines = (r.stdout || '').split('\n').map((l) => l.trim()).filter(Boolean);
  const emus = [];
  const phys = [];
  for (const line of lines.slice(1)) {
    const [id, state] = line.split(/\s+/);
    if (state !== 'device') continue;
    if (id.startsWith('emulator-')) emus.push(id);
    else phys.push(id);
  }
  if (emus.length) return emus[0];
  if (process.env.ALLOW_PHYSICAL_HANDHELD === '1' && phys.length) return phys[0];
  return null;
}

function resolveFormats() {
  const raw = (process.env.MATRIX_FORMATS || 'handheld').trim();
  if (raw === 'priority') {
    return PRIORITY_FORMAT_IDS.map((id) => FORMAT_BY_ID[id]).filter((f) => f && f.touch);
  }
  if (raw === 'all') return MATRIX.formats.filter((f) => f.touch);
  if (raw === 'handheld' || raw === '') return MATRIX.formats.filter((f) => f.touch);
  if (raw === 'desktop') return [];
  return raw.split(',').map((s) => s.trim()).filter(Boolean).map((id) => {
    const f = FORMAT_BY_ID[id];
    if (!f) console.warn(`[emu] unknown format: ${id}`);
    if (f && !f.touch) console.warn(`[emu] ${id} is not touch — skipping in emulator runner`);
    return f && f.touch ? f : null;
  }).filter(Boolean);
}

function resolveScreens() {
  const raw = (process.env.MATRIX_SCREENS || 'all').trim();
  if (raw === 'all' || raw === '') return MATRIX.screens.map((s) => s.id);
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
}

function cellPath(formatId, shotSuffix) {
  return path.join(VIEWPORTS_DIR, `${formatId}_${shotSuffix}.png`);
}

/** Physical pixels for CSS viewport */
function physicalSize(fmt) {
  const dpr = fmt.dpr || 2;
  return {
    w: Math.round(fmt.width * dpr),
    h: Math.round(fmt.height * dpr),
    density: Math.round(160 * dpr),
  };
}

function setupReverse(serial) {
  const ports = [APP_HOST_PORT, API_HOST_PORT, ADMIN_HOST_PORT, DOCS_HOST_PORT];
  for (const p of ports) {
    adb(serial, ['reverse', `tcp:${p}`, `tcp:${p}`]);
  }
  ok('adb reverse ports', true, ports.join(','));
}

function setWm(serial, fmt) {
  const { w, h, density } = physicalSize(fmt);
  adbOk(serial, ['shell', 'wm', 'size', `${w}x${h}`]);
  adbOk(serial, ['shell', 'wm', 'density', String(density)]);
  // Disable auto-rotate; set portrait/landscape
  adb(serial, ['shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0']);
  const landscape = fmt.width > fmt.height;
  adb(serial, ['shell', 'settings', 'put', 'system', 'user_rotation', landscape ? '1' : '0']);
  ok(`wm ${fmt.id}`, true, `${w}x${h} dens=${density} land=${landscape}`);
  return { w, h, density, landscape };
}

function resetWm(serial) {
  adb(serial, ['shell', 'wm', 'size', 'reset']);
  adb(serial, ['shell', 'wm', 'density', 'reset']);
  adb(serial, ['shell', 'settings', 'put', 'system', 'accelerometer_rotation', '1']);
}

function inputTap(serial, x, y) {
  adbOk(serial, ['shell', 'input', 'tap', String(Math.round(x)), String(Math.round(y))]);
}

function inputText(serial, text) {
  // adb input text: spaces as %s, limited charset
  const escaped = text.replace(/ /g, '%s').replace(/'/g, "\\'");
  adbOk(serial, ['shell', 'input', 'text', escaped]);
}

function inputKey(serial, keycode) {
  adbOk(serial, ['shell', 'input', 'keyevent', String(keycode)]);
}

async function screencapTo(serial, dest) {
  await sleep(HOLD_MS);
  const r = spawnSync('adb', [...adbBase(serial), 'exec-out', 'screencap', '-p'], {
    encoding: 'buffer',
    maxBuffer: 32 * 1024 * 1024,
    timeout: 30000,
  });
  if (r.status !== 0 || !r.stdout || r.stdout.length < 100) {
    ok(`screencap ${path.basename(dest)}`, false, 'empty/failed');
    return false;
  }
  fs.writeFileSync(dest, r.stdout);
  ok(`screencap ${path.basename(dest)}`, true, `${r.stdout.length}b`);
  return true;
}

function openChrome(serial, url) {
  // Force-stop then start Chrome with URL
  adb(serial, ['shell', 'am', 'force-stop', 'com.android.chrome']);
  const r = adb(serial, [
    'shell', 'am', 'start', '-a', 'android.intent.action.VIEW',
    '-d', url,
    'com.android.chrome',
  ]);
  if (r.status !== 0) {
    // Fallback: any browser
    adbOk(serial, [
      'shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', url,
    ]);
  }
}

function startScreenrecord(serial, devicePath) {
  // screenrecord max ~180s; run in background
  adb(serial, ['shell', 'rm', '-f', devicePath]);
  const child = spawn('adb', [...adbBase(serial), 'shell', 'screenrecord', '--time-limit', '90', devicePath], {
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  return child;
}

async function stopScreenrecord(serial, child, devicePath, hostPath) {
  if (child && !child.killed) {
    // SIGINT to stop gracefully
    try { child.kill('SIGINT'); } catch (_) {}
    await sleep(800);
    try { adb(serial, ['shell', 'pkill', '-INT', 'screenrecord']); } catch (_) {}
    await sleep(1200);
  }
  const pull = adb(serial, ['pull', devicePath, hostPath]);
  const good = pull.status === 0 && fs.existsSync(hostPath) && fs.statSync(hostPath).size > 0;
  ok(`screenrecord ${path.basename(hostPath)}`, good, good ? `${fs.statSync(hostPath).size}b` : 'pull failed');
  adb(serial, ['shell', 'rm', '-f', devicePath]);
  return good;
}

/**
 * Coordinate helper: CSS-relative → physical using current wm size.
 */
function physTap(serial, phys, nx, ny) {
  const x = phys.w * nx;
  const y = phys.h * ny;
  inputTap(serial, x, y);
}

async function journeyFormat(serial, fmt, screens) {
  const want = new Set(screens);
  const phys = setWm(serial, fmt);
  await sleep(500);

  const deviceRec = `/sdcard/cba_matrix_${fmt.id}.mp4`;
  const hostRec = path.join(RECORDINGS_DIR, `${fmt.id}_touch.mp4`);
  let recChild = null;
  if (RECORD_VIDEO) {
    recChild = startScreenrecord(serial, deviceRec);
    await sleep(400);
  }

  // --- App product journey ---
  if (want.has('home') || want.has('results') || want.has('map') || want.has('settings') || want.has('share')) {
    openChrome(serial, APP_URL + '/');
    await sleep(5000); // Flutter web cold load on emulator

    // Dismiss any Chrome first-run / password if present (best-effort)
    inputKey(serial, 4); // BACK once if interstitial
    await sleep(300);
    // Tap center to focus app
    physTap(serial, phys, 0.5, 0.5);
    await sleep(800);

    if (want.has('home')) {
      await screencapTo(serial, cellPath(fmt.id, SCREEN_BY_ID.home.shot_suffix));
    }

    // Focus search field (upper-mid)
    const fieldY = phys.h < 900 ? 0.40 : 0.28;
    physTap(serial, phys, 0.40, fieldY);
    await sleep(500);
    inputText(serial, SEARCH_ITEM);
    await sleep(300);
    inputKey(serial, 66); // ENTER
    await sleep(600);

    // VER PREÇOS bottom
    physTap(serial, phys, 0.50, phys.h < 900 ? 0.88 : 0.93);
    await sleep(6000); // search

    if (want.has('results')) {
      await screencapTo(serial, cellPath(fmt.id, SCREEN_BY_ID.results.shot_suffix));
    }
    if (want.has('share')) {
      // Share CTA near top of results (savings banner)
      await screencapTo(serial, cellPath(fmt.id, SCREEN_BY_ID.share.shot_suffix));
    }
    if (want.has('map')) {
      physTap(serial, phys, 0.92, 0.06);
      await sleep(2000);
      await screencapTo(serial, cellPath(fmt.id, SCREEN_BY_ID.map.shot_suffix));
      physTap(serial, phys, 0.06, 0.06); // back
      await sleep(800);
    }
    if (want.has('settings')) {
      physTap(serial, phys, 0.50, 0.94); // EDITAR LISTA → home
      await sleep(1000);
      physTap(serial, phys, 0.92, 0.06); // overflow
      await sleep(500);
      physTap(serial, phys, 0.70, 0.18); // Configurações
      await sleep(800);
      await screencapTo(serial, cellPath(fmt.id, SCREEN_BY_ID.settings.shot_suffix));
      inputKey(serial, 4); // back dismiss
    }
  }

  // --- Admin (Chrome) ---
  if (want.has('admin')) {
    const adminUrl = `http://127.0.0.1:${ADMIN_HOST_PORT}/?api=${encodeURIComponent(`http://127.0.0.1:${API_HOST_PORT}/admin/api`)}`;
    openChrome(serial, adminUrl);
    await sleep(2500);
    await screencapTo(serial, cellPath(fmt.id, SCREEN_BY_ID.admin.shot_suffix));
  }

  // --- Docs ---
  if (want.has('docs')) {
    openChrome(serial, `http://127.0.0.1:${DOCS_HOST_PORT}/`);
    await sleep(2000);
    await screencapTo(serial, cellPath(fmt.id, SCREEN_BY_ID.docs.shot_suffix));
  }

  if (RECORD_VIDEO) {
    await stopScreenrecord(serial, recChild, deviceRec, hostRec);
  }
}

(async () => {
  const serial = resolveSerial();
  const formats = resolveFormats();
  const screens = resolveScreens();

  console.log('Matrix emulator capture (Phase A handheld)');
  console.log(`  ADB_SERIAL = ${serial || '(none)'}`);
  console.log(`  APP_URL    = ${APP_URL}`);
  console.log(`  formats    = ${formats.map((f) => f.id).join(', ')} (${formats.length})`);
  console.log(`  screens    = ${screens.join(', ')}`);
  console.log(`  RECORD_VIDEO = ${RECORD_VIDEO}`);

  if (!serial) {
    ok('emulator device present', false, 'no emulator-* in adb devices (set ADB_SERIAL or boot AVD)');
    fs.writeFileSync(path.join(PHONE_DIR, 'emulator_results.json'), JSON.stringify({
      ok: false, reason: 'no_emulator', checks,
    }, null, 2));
    process.exit(1);
  }
  ok('emulator device present', true, serial);

  if (!formats.length) {
    console.log('[emu] no touch formats selected — nothing to do');
    process.exit(0);
  }

  try {
    setupReverse(serial);
  } catch (err) {
    ok('adb reverse', false, String(err));
    process.exit(1);
  }

  // Save original size for restore
  const origSize = adb(serial, ['shell', 'wm', 'size']);
  const origDensity = adb(serial, ['shell', 'wm', 'density']);

  try {
    for (const fmt of formats) {
      console.log(`\n=== emulator format ${fmt.id} (${fmt.width}×${fmt.height} dpr=${fmt.dpr}) ===`);
      try {
        await journeyFormat(serial, fmt, screens);
      } catch (err) {
        ok(`journey ${fmt.id}`, false, String(err));
      }
    }
  } finally {
    if (process.env.SKIP_WM_RESET !== '1') {
      try { resetWm(serial); } catch (_) {}
      console.log('[emu] wm size/density reset');
      console.log('[emu] prior size:', (origSize.stdout || '').trim());
      console.log('[emu] prior density:', (origDensity.stdout || '').trim());
    }
  }

  // Presence summary for touch cells
  let missing = 0;
  let present = 0;
  for (const fmt of formats) {
    for (const sid of screens) {
      const sc = SCREEN_BY_ID[sid];
      if (!sc) continue;
      const p = cellPath(fmt.id, sc.shot_suffix);
      if (fs.existsSync(p) && fs.statSync(p).size > 0) present += 1;
      else missing += 1;
    }
  }

  const failed = checks.filter((c) => !c.pass);
  const summary = {
    ok: failed.length === 0 && missing === 0,
    serial,
    formats: formats.map((f) => f.id),
    screens,
    present,
    missing,
    checks_passed: checks.length - failed.length,
    checks_total: checks.length,
    capture_only: true,
  };
  fs.writeFileSync(path.join(PHONE_DIR, 'emulator_results.json'), JSON.stringify(summary, null, 2));

  console.log(`\n${checks.length - failed.length}/${checks.length} checks (CAPTURE_OK)`);
  console.log(`Cells present: ${present}; missing: ${missing}`);
  console.log(`PNGs: ${VIEWPORTS_DIR}`);
  console.log(`VIDEO: ${RECORDINGS_DIR} (*_touch.mp4)`);
  console.log('Next: A4b/A6 under qa_success_criteria.json — CAPTURE_OK ≠ A7');
  process.exit(failed.length || missing ? 1 : 0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
