/**
 * Full multi-format viewport capture for e2e/qa_matrix.json (screens × formats).
 *
 * Produces quality-hold PNGs under:
 *   e2e/screenshots/viewports/{format}_{shot_suffix}.png
 * and optional continuous VIDEO under:
 *   e2e/screenshots/web/e2e/recordings/{format}_{mouse|keyboard}.webm
 *
 * Defaults (ship path):
 *   MATRIX_FORMATS=all          — all formats in qa_matrix.json
 *   MATRIX_SCREENS=all          — all 7 product screens when APP_URL set
 *   RECORD_VIDEO=1
 *   CONCURRENCY=2               — parallel format capture (raise on big hosts)
 *
 * Debug / priority subset:
 *   MATRIX_FORMATS=priority     — phone_portrait,phone_android,laptop_hd,1080p
 *   MATRIX_FORMATS=desktop      — touch:false only
 *   MATRIX_FORMATS=handheld     — touch:true only
 *   MATRIX_FORMATS=comma,ids
 *   MATRIX_SCREENS=home,results,…
 *
 * Path classes:
 *   - Desktop/laptop (touch:false): ship-valid via Puppeteer + CDP screencast
 *   - Handheld (touch:true): this runner still writes layout PNGs via Chrome
 *     device metrics as a capture assist. Phase A ship-valid handheld VIDEO +
 *     OS-level touch requires matrix_emulator.js (adb screenrecord + adb input).
 *
 * Capture only (A4 CAPTURE_OK). Review is A4b/A6 under qa_success_criteria.json.
 *
 * Env: API_URL ADMIN_URL DOCS_URL APP_URL ADMIN_TOKEN MATRIX_HOLD_MS
 *      VERIFY_ONLY=1  — presence check for expected cells of this run
 *      MATRIX_STRICT=1 — fail if APP_URL missing for product screens
 *      MATRIX_SEARCH_ITEM — default "arroz"
 *      MATRIX_RESULTS_TIMEOUT_MS — default 120000
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { launchOpts, resolvePuppeteer } = require('./lib/chrome');
const puppeteer = resolvePuppeteer();

const ROOT = path.join(__dirname);
const MATRIX = JSON.parse(fs.readFileSync(path.join(ROOT, 'qa_matrix.json'), 'utf8'));

const API_URL = (process.env.API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const ADMIN_URL = (process.env.ADMIN_URL || 'http://127.0.0.1:8081').replace(/\/$/, '');
const DOCS_URL = (process.env.DOCS_URL || 'http://127.0.0.1:8082').replace(/\/$/, '');
const APP_URL = (process.env.APP_URL || '').replace(/\/$/, '');
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || 'test-admin-token-0123456789';
const HOLD_MS = Number(process.env.MATRIX_HOLD_MS || 600);
const RECORD_VIDEO = process.env.RECORD_VIDEO !== '0';
const VERIFY_ONLY = process.env.VERIFY_ONLY === '1';
const MATRIX_STRICT = process.env.MATRIX_STRICT === '1';
const CONCURRENCY = Math.max(1, Number(process.env.CONCURRENCY || 2));
const SEARCH_ITEM = process.env.MATRIX_SEARCH_ITEM || 'arroz';
const RESULTS_TIMEOUT_MS = Number(process.env.MATRIX_RESULTS_TIMEOUT_MS || 120000);

const VIEWPORTS_DIR = path.join(ROOT, 'screenshots', 'viewports');
const RECORDINGS_DIR = path.join(ROOT, 'screenshots', 'web', 'e2e', 'recordings');
const STILLS_DIR = path.join(ROOT, 'screenshots', 'web', 'e2e', 'stills');
fs.mkdirSync(VIEWPORTS_DIR, { recursive: true });
fs.mkdirSync(RECORDINGS_DIR, { recursive: true });

const PRIORITY_FORMAT_IDS = [
  'phone_portrait',
  'phone_android',
  'laptop_hd',
  '1080p',
];

const PRODUCT_SCREENS = ['home', 'results', 'map', 'settings', 'share'];
const ALL_SCREEN_IDS = MATRIX.screens.map((s) => s.id);

const SCREEN_BY_ID = Object.fromEntries(MATRIX.screens.map((s) => [s.id, s]));
const FORMAT_BY_ID = Object.fromEntries(MATRIX.formats.map((f) => [f.id, f]));

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function resolveFormats() {
  const raw = (process.env.MATRIX_FORMATS || 'all').trim();
  if (raw === 'priority') {
    return PRIORITY_FORMAT_IDS.map((id) => FORMAT_BY_ID[id]).filter(Boolean);
  }
  if (raw === 'all' || raw === '') return MATRIX.formats.slice();
  if (raw === 'desktop') return MATRIX.formats.filter((f) => !f.touch);
  if (raw === 'handheld') return MATRIX.formats.filter((f) => f.touch);
  return raw.split(',').map((s) => s.trim()).filter(Boolean).map((id) => {
    const f = FORMAT_BY_ID[id];
    if (!f) console.warn(`[matrix] unknown format id: ${id}`);
    return f;
  }).filter(Boolean);
}

function resolveScreens() {
  const raw = (process.env.MATRIX_SCREENS || 'all').trim();
  if (raw === 'all' || raw === '') {
    if (APP_URL) return ALL_SCREEN_IDS.slice();
    console.warn('[matrix] APP_URL unset — product screens (home/results/map/settings/share) skipped; admin+docs only');
    return ['admin', 'docs'];
  }
  if (raw === 'priority') {
    const list = ['admin', 'docs'];
    if (APP_URL) list.push('home');
    return list;
  }
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
}

function cellPath(formatId, shotSuffix) {
  return path.join(VIEWPORTS_DIR, `${formatId}_${shotSuffix}.png`);
}

function expectedCells(formats, screens) {
  const cells = [];
  for (const f of formats) {
    for (const sid of screens) {
      const sc = SCREEN_BY_ID[sid];
      if (!sc) {
        console.warn(`[matrix] unknown screen id: ${sid}`);
        continue;
      }
      cells.push({ formatId: f.id, shotSuffix: sc.shot_suffix, screenId: sid });
    }
  }
  return cells;
}

function verifyCells(cells) {
  let missing = 0;
  for (const c of cells) {
    const p = cellPath(c.formatId, c.shotSuffix);
    const st = fs.existsSync(p) ? fs.statSync(p) : null;
    const good = st && st.size > 0;
    ok(`verify ${c.formatId}_${c.shotSuffix}`, good, good ? `${st.size}b` : 'missing/empty');
    if (!good) missing += 1;
  }
  return missing;
}

function viewportFromFormat(fmt) {
  // Cap DPR for capture to reduce CDP/memory pressure on QHD/4K while keeping CSS size.
  const rawDpr = fmt.dpr || 1;
  const maxDpr = Number(process.env.MATRIX_MAX_DPR || 2);
  const dpr = Math.min(rawDpr, maxDpr);
  return {
    width: fmt.width,
    height: fmt.height,
    deviceScaleFactor: dpr,
    isMobile: !!fmt.touch,
    hasTouch: !!fmt.touch,
  };
}

async function hold(page) {
  await sleep(HOLD_MS);
}

async function shot(page, formatId, shotSuffix) {
  await hold(page);
  const out = cellPath(formatId, shotSuffix);
  await page.screenshot({ path: out, fullPage: false, captureBeyondViewport: false });
  const st = fs.existsSync(out) ? fs.statSync(out) : null;
  ok(`capture ${formatId}_${shotSuffix}`, st && st.size > 0, st ? `${st.size}b` : 'missing');
  return out;
}

async function captureAdmin(page, formatId) {
  const adminEntry = `${ADMIN_URL}/?api=${encodeURIComponent(API_URL + '/admin/api')}`;
  const resp = await page.goto(adminEntry, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('#login-form', { timeout: 10000 });
  await shot(page, formatId, SCREEN_BY_ID.admin.shot_suffix);
  return resp;
}

async function captureDocs(page, formatId) {
  const resp = await page.goto(DOCS_URL + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('.sidebar, nav.nav, aside, body', { timeout: 10000 }).catch(() => {});
  await shot(page, formatId, SCREEN_BY_ID.docs.shot_suffix);
  return resp;
}

/** Wait for Flutter first frame + glass pane. */
async function waitFlutter(page) {
  await page.waitForSelector('flutter-view, flt-glass-pane, canvas', { timeout: 45000 });
  await page.evaluate(() => new Promise((resolve) => {
    if (window._flutterFirstFrame || document.querySelector('flt-glass-pane')) {
      resolve();
      return;
    }
    window.addEventListener('flutter-first-frame', () => resolve(), { once: true });
    setTimeout(resolve, 2500);
  }));
  await sleep(1000);
}

/**
 * Force Maceió geolocation so LocationService never hangs on
 * requestPermission / getCurrentPosition ("Iniciando busca…").
 * Combines CDP grants + navigator.geolocation stub.
 */
function maceioGeoInstallScript(latitude, longitude) {
  // Shared body for evaluateOnNewDocument + live evaluate.
  return `(function(latitude, longitude){
    const pos = {
      coords: {
        latitude: latitude,
        longitude: longitude,
        accuracy: 25,
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null,
      },
      timestamp: Date.now(),
    };
    const geo = {
      getCurrentPosition(success, error, opts) {
        // Synchronous success — never leave Flutter waiting on permission.
        try { if (typeof success === 'function') success(pos); }
        catch (e) { if (typeof error === 'function') error(e); }
      },
      watchPosition(success) {
        if (typeof success === 'function') success(pos);
        return 1;
      },
      clearWatch() {},
    };
    try {
      Object.defineProperty(navigator, 'geolocation', {
        configurable: true,
        get() { return geo; },
      });
    } catch (_) {
      try { navigator.geolocation = geo; } catch (__) {}
    }
    // Permissions API: pretend geolocation already granted.
    try {
      const orig = navigator.permissions && navigator.permissions.query
        ? navigator.permissions.query.bind(navigator.permissions) : null;
      if (navigator.permissions) {
        navigator.permissions.query = (desc) => {
          if (desc && desc.name === 'geolocation') {
            return Promise.resolve({ state: 'granted', onchange: null });
          }
          return orig ? orig(desc) : Promise.resolve({ state: 'granted', onchange: null });
        };
      }
    } catch (_) {}
  })(${latitude}, ${longitude});`;
}

async function grantMaceioGeo(page) {
  const origin = APP_URL || 'http://127.0.0.1:8080';
  const lat = -9.6633;
  const lon = -35.7089;

  try {
    const client = await page.target().createCDPSession();
    await client.send('Browser.grantPermissions', {
      origin,
      permissions: ['geolocation'],
    }).catch(() => {});
    // Also grant without origin filter when supported
    await client.send('Browser.grantPermissions', {
      permissions: ['geolocation'],
    }).catch(() => {});
    await client.send('Emulation.setGeolocationOverride', {
      latitude: lat,
      longitude: lon,
      accuracy: 25,
    }).catch(() => {});
  } catch (_) { /* older chrome */ }

  try {
    await page.setGeolocation({ latitude: lat, longitude: lon, accuracy: 25 });
  } catch (_) { /* ignore */ }

  // MUST be registered before goto so Flutter's first geo call is mocked.
  await page.evaluateOnNewDocument(maceioGeoInstallScript(lat, lon));

  // Live page patch (already loaded / after navigation).
  await page.evaluate(maceioGeoInstallScript(lat, lon)).catch(() => {});
}

/** Absolute click (CSS px). */
async function clickXY(page, x, y) {
  await page.mouse.click(Math.round(x), Math.round(y));
  await sleep(180);
}

/** Normalized (0–1) click. */
async function flutterClick(page, nx, ny) {
  const vp = page.viewport();
  await clickXY(page, vp.width * nx, vp.height * ny);
}

/**
 * Layout helpers — chip/field/menu positions scale with absolute chrome height,
 * not fixed ratios (4k/qhd broke at chipY=0.42).
 */
function homeLayout(vp) {
  const h = vp.height;
  const w = vp.width;
  const short = h < 500; // phone landscape class — chips often below fold
  // Flutter web layout is TOP-ALIGNED with fixed Material chrome sizes, not
  // percentage-scaled. Measured (CSS px):
  //   1366×768: field ~y=220, Arroz chip ~y=320, VER PREÇOS ~y=728
  //   800×360 landscape: field ~y=210, VER PREÇOS ~y=320 (chips off-screen)
  const appBar = 56;
  const banner = short ? 52 : 56;
  const fieldAbsY = short
    ? Math.min(h - 130, appBar + banner + 100) // ~208 on 360h
    : appBar + banner + 48 + 50; // ~210–220
  const chipAbsY = short
    ? Math.min(h - 90, fieldAbsY + 55)
    : fieldAbsY + 100; // ~310–320
  const recentAbsY = chipAbsY + (short ? 30 : 90);
  // Bottom bar ~48–56px tall — pin near bottom edge in CSS px.
  const verAbsY = Math.max(h - 32, short ? h - 40 : h - 36);
  return {
    short,
    chipY: Math.min(0.78, chipAbsY / h),
    fieldY: Math.min(0.55, fieldAbsY / h),
    addY: Math.min(0.65, (fieldAbsY + 36) / h),
    addX: w < 600 ? 0.88 : 0.94,
    recentY: Math.min(0.85, recentAbsY / h),
    // ⋮ is the RIGHTMOST AppBar action — stay far right to avoid cloud sheet
    menuX: Math.min(0.995, (w - 10) / w),
    menuY: Math.min(0.09, 28 / h),
    cloudX: 0.90,
    verPrecosY: Math.min(0.98, verAbsY / h),
    // PopupMenu 2nd item (Configurações) under ⋮ — use absolute-ish Y (~78–95)
    settingsItemX: Math.min(0.97, (w - 70) / w),
    settingsItemY: Math.min(0.28, Math.max(70, Math.min(100, h * 0.12)) / h),
  };
}

/**
 * Add a basket item. Prefer recent-list / suggestion chip; keyboard as backup.
 * Retries several absolute Y bands so 4k/phone landscape still hit chips.
 */
async function flutterAddItem(page, text) {
  const vp = page.viewport();
  const L = homeLayout(vp);

  // Dismiss APK banner (X) so landscape has room for field/chips.
  await clickXY(page, vp.width - 28, L.short ? 70 : 90);
  await sleep(250);

  if (!L.short) {
    // Tall: chip first (more reliable than TextField focus on Flutter canvas).
    const chipX = vp.width < 500 ? 0.18 : 0.055;
    await flutterClick(page, chipX, L.chipY);
    await sleep(500);
    await flutterClick(page, chipX, Math.min(0.70, L.chipY + 0.03));
    await sleep(350);
  }

  // TextField onSubmitted → _addCurrent (critical for landscape)
  await clickXY(page, Math.min(vp.width * 0.4, 320), L.fieldY * vp.height);
  await sleep(400);
  const input = await page.$('input, textarea').catch(() => null);
  if (input) {
    await input.click({ clickCount: 3 }).catch(() => {});
    await sleep(80);
  } else {
    await page.keyboard.down('Control');
    await page.keyboard.press('KeyA');
    await page.keyboard.up('Control');
  }
  await page.keyboard.type(text, { delay: 35 });
  await sleep(150);
  await page.keyboard.press('Enter');
  await sleep(500);
  // Adicionar — avoid far-right (mic). Enter already commits via onSubmitted.
  if (!L.short) {
    await flutterClick(page, Math.min(0.85, L.addX), L.addY);
    await sleep(350);
  }
}

async function flutterTapVerPrecos(page) {
  // ONE click only. Extra bottom-bar clicks after navigation hit EDITAR LISTA
  // and pop straight back to home (was the dominant capture bug).
  const vp = page.viewport();
  const L = homeLayout(vp);
  await flutterClick(page, 0.50, L.verPrecosY);
  await sleep(900);
}

/**
 * Wait until search stream finishes with stores (or timeout).
 * Tracks /api/v1/search/stream NDJSON for type=done / partial with stores.
 * Does NOT early-exit at 15s with no traffic (that caused spinner-only shots).
 */
async function flutterWaitResults(page, timeoutMs = RESULTS_TIMEOUT_MS) {
  // IMPORTANT: never res.text()/buffer() on search responses — that steals the
  // body from Flutter's fetch and freezes UI on "Iniciando busca…".
  const start = Date.now();
  let lastSearchAt = 0;
  let searchHits = 0;
  let lastStatusCode = 0;
  let streamFinishedAt = 0;

  const onResp = (res) => {
    try {
      const url = res.url();
      if (!/\/api\/v1\/search/.test(url)) return;
      lastSearchAt = Date.now();
      searchHits += 1;
      lastStatusCode = res.status();
      // NDJSON stream: finished when response completes (headers+body delivered).
      // Puppeteer 'response' fires when headers received; pair with requestfinished.
    } catch (_) { /* ignore */ }
  };
  const onFinished = (req) => {
    try {
      if (/\/api\/v1\/search/.test(req.url())) {
        streamFinishedAt = Date.now();
        lastSearchAt = Date.now();
      }
    } catch (_) { /* ignore */ }
  };
  page.on('response', onResp);
  page.on('requestfinished', onFinished);
  page.on('requestfailed', onFinished);

  try {
    while (Date.now() - start < timeoutMs) {
      try {
        await page.waitForNetworkIdle({ idleTime: 1500, timeout: 6000 });
      } catch (_) { /* keep waiting */ }
      await sleep(1000);

      // Stream fully finished + quiet paint window
      if (streamFinishedAt && Date.now() - streamFinishedAt > 2500 && Date.now() - start > 5000) {
        break;
      }
      // Search traffic seen, idle long enough (covers non-stream fallback)
      if (searchHits > 0 && lastSearchAt && Date.now() - lastSearchAt > 5000 && Date.now() - start > 8000) {
        break;
      }
      // No search request at all after 18s → VER PREÇOS/basket likely missed; fail fast for retry
      if (searchHits === 0 && Date.now() - start > 18000) {
        break;
      }
    }
  } finally {
    page.off('response', onResp);
    page.off('requestfinished', onFinished);
    page.off('requestfailed', onFinished);
  }

  // Extra UI paint hold — progressive results need a beat after stream end
  await sleep(2500);
  const okSettle = searchHits > 0 && lastStatusCode === 200;
  console.log(
    `[matrix] waitResults ${Date.now() - start}ms hits=${searchHits} status=${lastStatusCode} finished=${!!streamFinishedAt} lastSearchAgo=${lastSearchAt ? Date.now() - lastSearchAt : -1}`,
  );
  return {
    sawStores: okSettle,
    sawDone: !!streamFinishedAt,
    waitedMs: Date.now() - start,
    searchHits,
  };
}

/** Open Configurações sheet from home AppBar ⋮ menu. */
async function flutterOpenSettings(page) {
  const vp = page.viewport();
  await page.keyboard.press('Escape').catch(() => {});
  await sleep(250);

  // Open ⋮ (rightmost). Absolute CSS px more stable than fractions on QHD/4K.
  // Do NOT spam extra clicks after Configurações — they hit the scrim and dismiss the sheet.
  await clickXY(page, vp.width - 12, 28);
  await sleep(700);
  // Configurações = 2nd PopupMenu row under ⋮ (compact items ~40px)
  await clickXY(page, Math.max(80, vp.width - 90), 88);
  await sleep(1100);
}

/** Open map from results AppBar map IconButton (only when !partial). */
async function flutterOpenMap(page) {
  const vp = page.viewport();
  const menuY = Math.min(28 / vp.height, 0.08);
  // Map IconButton is sole trailing action on results AppBar (far right).
  await flutterClick(page, Math.min(0.99, (vp.width - 24) / vp.width), menuY);
  await sleep(2500);
}

async function flutterBack(page) {
  const vp = page.viewport();
  const y = Math.min(28 / vp.height, 0.08);
  await flutterClick(page, 0.06, y);
  await sleep(800);
}

/**
 * Full product journey: home → settings (from home) → search → results → share → map → settings backup.
 * Captures quality-hold PNGs for requested product screens.
 */
async function captureProductJourney(page, formatId, screens) {
  const want = new Set(screens.filter((s) => PRODUCT_SCREENS.includes(s)));
  if (!want.size) return;
  if (!APP_URL) {
    for (const sid of want) {
      ok(`capture ${formatId}_${SCREEN_BY_ID[sid].shot_suffix}`, !MATRIX_STRICT,
        'APP_URL unset — skipped');
    }
    return;
  }

  await grantMaceioGeo(page);
  const resp = await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 90000 });
  // Re-apply live geo stub after navigation
  await grantMaceioGeo(page);
  await waitFlutter(page);
  ok(`flutter mounted ${formatId}`, true, `status ${resp && resp.status()}`);

  // --- HOME ---
  if (want.has('home')) {
    await shot(page, formatId, SCREEN_BY_ID.home.shot_suffix);
  }

  // --- SETTINGS from home (most reliable path) ---
  if (want.has('settings')) {
    await flutterOpenSettings(page);
    await shot(page, formatId, SCREEN_BY_ID.settings.shot_suffix);
    // Dismiss sheet
    await page.keyboard.press('Escape').catch(() => {});
    await sleep(250);
    await flutterClick(page, 0.5, 0.08); // tap scrim / appbar
    await sleep(250);
    await page.keyboard.press('Escape').catch(() => {});
    await sleep(400);
  }

  // Settings-only short path
  if (want.has('settings') && !want.has('results') && !want.has('map') && !want.has('share') && !want.has('home')) {
    return;
  }

  if (want.has('results') || want.has('map') || want.has('share')) {
    // Dismiss settings sheet / menus so home is interactive
    await page.keyboard.press('Escape').catch(() => {});
    await sleep(300);
    await page.keyboard.press('Escape').catch(() => {});
    await sleep(300);

    // Attach search listeners BEFORE Ver preços — stream can finish in <1s on mock.
    const settlePromise = flutterWaitResults(page);
    await flutterAddItem(page, SEARCH_ITEM);
    await flutterTapVerPrecos(page);
    let settle = await settlePromise;
    ok(
      `results settle ${formatId}`,
      settle.sawStores || settle.sawDone || settle.searchHits > 0,
      `stores=${settle.sawStores} done=${settle.sawDone} hits=${settle.searchHits} ${settle.waitedMs}ms`,
    );

    // Retry only when no search traffic at all
    if (!settle.searchHits) {
      console.log(`[matrix] ${formatId}: retry search path via reload`);
      await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 90000 });
      await grantMaceioGeo(page);
      await waitFlutter(page);
      const retryPromise = flutterWaitResults(page);
      await flutterAddItem(page, SEARCH_ITEM);
      await flutterTapVerPrecos(page);
      settle = await retryPromise;
      ok(
        `results settle retry ${formatId}`,
        settle.sawStores || settle.sawDone || settle.searchHits > 0,
        `stores=${settle.sawStores} done=${settle.sawDone} hits=${settle.searchHits} ${settle.waitedMs}ms`,
      );
    }

    if (want.has('results')) {
      // Scroll top so savings + prices visible
      await page.mouse.wheel({ deltaY: -1200 });
      await sleep(400);
      await shot(page, formatId, SCREEN_BY_ID.results.shot_suffix);
    }

    if (want.has('share')) {
      // Share CTA is COMPARTILHAR ECONOMIA on savings banner — same results surface
      await page.mouse.wheel({ deltaY: -1200 });
      await sleep(500);
      await shot(page, formatId, SCREEN_BY_ID.share.shot_suffix);
    }

    if (want.has('map')) {
      await flutterOpenMap(page);
      await shot(page, formatId, SCREEN_BY_ID.map.shot_suffix);
      await flutterBack(page);
      await sleep(600);
    }
  }
}

/**
 * CDP screencast → JPEG frames → ffmpeg webm.
 * Full journey: home → add item → search → results settle → map peek.
 */
async function recordFormatJourney(browser, fmt) {
  const inputPath = fmt.touch ? 'touch' : 'mouse';
  const recName = `${fmt.id}_${inputPath}`;
  const webmPath = path.join(RECORDINGS_DIR, `${recName}.webm`);
  const stillsOut = path.join(STILLS_DIR, recName);
  fs.mkdirSync(stillsOut, { recursive: true });

  const page = await browser.newPage();
  await page.setViewport(viewportFromFormat(fmt));
  // Cap protocol timeout for large viewports
  page.setDefaultTimeout(120000);
  const client = await page.target().createCDPSession();

  const frames = [];
  let frameCount = 0;
  const onFrame = async (event) => {
    try {
      frames.push(Buffer.from(event.data, 'base64'));
      frameCount += 1;
      if (frameCount === 1 || frameCount % 10 === 0) {
        const idx = String(Math.floor(frameCount / 10)).padStart(3, '0');
        fs.writeFileSync(path.join(stillsOut, `frame_${idx}.jpg`), Buffer.from(event.data, 'base64'));
      }
      await client.send('Page.screencastFrameAck', { sessionId: event.sessionId });
    } catch (_) { /* session may close */ }
  };
  client.on('Page.screencastFrame', onFrame);

  try {
    await client.send('Page.startScreencast', {
      format: 'jpeg',
      quality: 55,
      maxWidth: Math.min(fmt.width, 1920),
      maxHeight: Math.min(fmt.height, 1080),
      everyNthFrame: 2,
    });

    if (APP_URL) {
      await grantMaceioGeo(page);
      await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 90000 });
      await grantMaceioGeo(page);
      await waitFlutter(page);
      await sleep(500);
      const waitP = flutterWaitResults(page, RESULTS_TIMEOUT_MS);
      await flutterAddItem(page, SEARCH_ITEM);
      await sleep(500);
      await flutterTapVerPrecos(page);
      await waitP;
      // Hold on results so continuous video frames show prices (not only spinner)
      await sleep(3500);
      // Open map briefly so journey shows map surface
      await flutterOpenMap(page);
      await sleep(2500);
      await flutterBack(page);
      await sleep(1200);
    } else {
      await page.goto(DOCS_URL + '/', { waitUntil: 'networkidle2', timeout: 30000 });
      await sleep(500);
      const arch = await page.$('a[href="#architecture"]');
      if (arch) { await arch.click(); await sleep(400); }
      const adminEntry = `${ADMIN_URL}/?api=${encodeURIComponent(API_URL + '/admin/api')}`;
      await page.goto(adminEntry, { waitUntil: 'networkidle2', timeout: 30000 });
      await page.waitForSelector('#login-form', { timeout: 10000 }).catch(() => {});
      const token = await page.$('#token');
      if (token) {
        await token.click({ clickCount: 3 });
        await page.keyboard.type('matrix-video-probe', { delay: 20 });
      }
      await sleep(400);
    }

    await client.send('Page.stopScreencast').catch(() => {});
  } catch (err) {
    ok(`record ${recName}`, false, String(err).slice(0, 200));
    await page.close().catch(() => {});
    return null;
  }

  await page.close().catch(() => {});

  if (frames.length < 3) {
    ok(`record ${recName} frames`, false, `only ${frames.length} frames`);
    return null;
  }

  const encoded = await new Promise((resolve) => {
    const args = [
      '-y', '-f', 'image2pipe', '-framerate', '8', '-i', 'pipe:0',
      '-c:v', 'libvpx', '-b:v', '1M', '-auto-alt-ref', '0', webmPath,
    ];
    const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'ignore', 'pipe'] });
    let err = '';
    ff.stderr.on('data', (d) => { err += d.toString(); });
    ff.on('close', (code) => {
      if (code === 0 && fs.existsSync(webmPath) && fs.statSync(webmPath).size > 0) {
        resolve(true);
      } else {
        console.warn('[matrix] ffmpeg failed:', err.slice(-400));
        resolve(false);
      }
    });
    for (const buf of frames) ff.stdin.write(buf);
    ff.stdin.end();
  });

  ok(`record ${recName}.webm`, encoded,
    encoded ? `${frames.length} frames → ${fs.statSync(webmPath).size}b` : 'encode failed');
  return encoded ? webmPath : null;
}

async function captureFormat(browser, fmt, screens) {
  console.log(`\n=== format ${fmt.id} (${fmt.width}×${fmt.height} dpr=${fmt.dpr} touch=${!!fmt.touch}) ===`);
  const page = await browser.newPage();
  page.setDefaultTimeout(120000);
  await page.setViewport(viewportFromFormat(fmt));
  try {
    const product = screens.filter((s) => PRODUCT_SCREENS.includes(s));
    const statics = screens.filter((s) => !PRODUCT_SCREENS.includes(s));

    if (product.length) {
      await captureProductJourney(page, fmt.id, product);
    }
    for (const sid of statics) {
      if (sid === 'admin') await captureAdmin(page, fmt.id);
      else if (sid === 'docs') await captureDocs(page, fmt.id);
      else console.warn(`[matrix] skip unknown screen: ${sid}`);
    }
  } finally {
    await page.close().catch(() => {});
  }
}

async function mapPool(items, limit, worker) {
  const results = [];
  let i = 0;
  async function run() {
    while (i < items.length) {
      const idx = i++;
      results[idx] = await worker(items[idx], idx);
    }
  }
  const runners = Array.from({ length: Math.min(limit, items.length) }, () => run());
  await Promise.all(runners);
  return results;
}

(async () => {
  const formats = resolveFormats();
  const screens = resolveScreens();
  const cells = expectedCells(formats, screens);

  console.log('Matrix capture (full path)');
  console.log(`  API_URL   = ${API_URL}`);
  console.log(`  ADMIN_URL = ${ADMIN_URL}`);
  console.log(`  DOCS_URL  = ${DOCS_URL}`);
  console.log(`  APP_URL   = ${APP_URL || '(none — product screens limited)'}`);
  console.log(`  formats   = ${formats.map((f) => f.id).join(', ')} (${formats.length})`);
  console.log(`  screens   = ${screens.join(', ')} (${screens.length})`);
  console.log(`  cells     = ${cells.length} (matrix expected_cells=${MATRIX.expected_cells})`);
  console.log(`  CONCURRENCY = ${CONCURRENCY}`);
  console.log(`  RECORD_VIDEO = ${RECORD_VIDEO}`);
  console.log(`  RESULTS_TIMEOUT_MS = ${RESULTS_TIMEOUT_MS}`);
  console.log(`  filters: MATRIX_FORMATS=all|priority|desktop|handheld|ids  MATRIX_SCREENS=all|…`);

  if (MATRIX_STRICT && !APP_URL && screens.some((s) => PRODUCT_SCREENS.includes(s))) {
    ok('APP_URL required for product screens', false, 'set APP_URL or build+serve Flutter web');
    process.exit(1);
  }

  if (VERIFY_ONLY) {
    const verifyFormats = (process.env.MATRIX_FORMATS || 'all') === 'all'
      ? MATRIX.formats
      : formats;
    const verifyScreens = (process.env.MATRIX_SCREENS || 'all') === 'all'
      ? ALL_SCREEN_IDS
      : screens;
    const fullCells = expectedCells(verifyFormats, verifyScreens);
    const missing = verifyCells(fullCells);
    const failed = checks.filter((c) => !c.pass);
    console.log(`\nVERIFY ${fullCells.length - missing}/${fullCells.length} cells present (expected full=${MATRIX.expected_cells})`);
    process.exit(failed.length ? 1 : 0);
  }

  let browser;
  try {
    const opts = launchOpts({ width: 1280, height: 900 });
    opts.protocolTimeout = Number(process.env.PUPPETEER_PROTOCOL_TIMEOUT_MS || 300000);
    browser = await puppeteer.launch(opts);
  } catch (err) {
    ok('browser launched', false, String(err));
    process.exit(1);
  }

  try {
    await mapPool(formats, CONCURRENCY, async (fmt) => {
      try {
        await captureFormat(browser, fmt, screens);
      } catch (err) {
        ok(`format ${fmt.id} journey`, false, String(err).slice(0, 200));
      }
    });

    if (RECORD_VIDEO) {
      const videoRaw = (process.env.MATRIX_VIDEO_FORMATS || '').trim();
      let videoFormats = formats;
      if (videoRaw === 'desktop') videoFormats = formats.filter((f) => !f.touch);
      else if (videoRaw === 'priority') {
        videoFormats = formats.filter((f) => PRIORITY_FORMAT_IDS.includes(f.id));
      } else if (videoRaw === 'all') {
        videoFormats = formats;
      } else if (videoRaw) {
        videoFormats = videoRaw.split(',').map((s) => FORMAT_BY_ID[s.trim()]).filter(Boolean);
      } else if (formats.length > 8) {
        const desk = formats.filter((f) => !f.touch);
        const handPri = formats.filter((f) => PRIORITY_FORMAT_IDS.includes(f.id) && f.touch);
        videoFormats = [...desk, ...handPri];
        console.log(`[matrix] RECORD_VIDEO auto-subset (${videoFormats.length} formats) — set MATRIX_VIDEO_FORMATS=all for every format`);
      }
      console.log(`\n=== VIDEO journeys (${videoFormats.length}) ===`);
      for (const fmt of videoFormats) {
        console.log(`--- record ${fmt.id} ---`);
        try {
          await recordFormatJourney(browser, fmt);
        } catch (err) {
          ok(`record ${fmt.id}`, false, String(err).slice(0, 200));
        }
      }
    }
  } catch (err) {
    ok('harness ran without throwing', false, String(err));
  } finally {
    await browser.close().catch(() => {});
  }

  verifyCells(cells);

  const failed = checks.filter((c) => !c.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed (CAPTURE_OK — not visual review)`);
  console.log(`PNGs: ${VIEWPORTS_DIR}`);
  if (RECORD_VIDEO) console.log(`VIDEO: ${RECORDINGS_DIR}`);
  console.log(`Coverage this run: ${cells.length} cells; full matrix target: ${MATRIX.expected_cells}`);
  console.log('Next: A4b video_critique.md + A6 matrix_critique.md (open artifacts; cite qa_success_criteria.json)');
  console.log('Handheld ship-valid path: node matrix_emulator.js (adb screenrecord + adb shell input)');
  if (failed.length) {
    for (const f of failed) console.log(`  - ${f.name}${f.detail ? ': ' + f.detail : ''}`);
  }
  process.exit(failed.length ? 1 : 0);
})();
