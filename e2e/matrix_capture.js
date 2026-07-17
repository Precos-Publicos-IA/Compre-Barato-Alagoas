/**
 * Prioritized multi-format viewport capture (subset of e2e/qa_matrix.json).
 *
 * Captures quality-hold PNGs under e2e/screenshots/viewports/{format}_{shot_suffix}.png
 * and optionally a short desktop CDP screencast → webm under
 * e2e/screenshots/web/e2e/recordings/.
 *
 * Default formats (priority subset — expand via MATRIX_FORMATS):
 *   phone_portrait, phone_android, laptop_hd, 1080p
 *
 * Surfaces (practical without full Flutter matrix):
 *   admin login (06_admin), docs home (07_docs), API health document (api_health)
 *   + app home (01_home) when APP_URL is set / Flutter web is served
 *
 * Env:
 *   API_URL, ADMIN_URL, DOCS_URL, APP_URL, ADMIN_TOKEN  — same as full.js
 *   MATRIX_FORMATS=comma ids | "priority" (default) | "all"
 *   MATRIX_SCREENS=admin,docs,api,home  (default: admin,docs,api + home if APP_URL)
 *   RECORD_VIDEO=1 (default) | 0  — desktop 1080p journey webm
 *   MATRIX_HOLD_MS=450
 *   VERIFY_ONLY=1 — only check expected subset files exist
 *
 * Does NOT write critiques (capture only — A4 CAPTURE_OK). Review is A4b/A6.
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
const HOLD_MS = Number(process.env.MATRIX_HOLD_MS || 450);
const RECORD_VIDEO = process.env.RECORD_VIDEO !== '0';
const VERIFY_ONLY = process.env.VERIFY_ONLY === '1';

const VIEWPORTS_DIR = path.join(ROOT, 'screenshots', 'viewports');
const RECORDINGS_DIR = path.join(ROOT, 'screenshots', 'web', 'e2e', 'recordings');
const STILLS_DIR = path.join(ROOT, 'screenshots', 'web', 'e2e', 'stills');
fs.mkdirSync(VIEWPORTS_DIR, { recursive: true });
fs.mkdirSync(RECORDINGS_DIR, { recursive: true });

/** Prioritized subset — practical first pass; expand with MATRIX_FORMATS=all */
const PRIORITY_FORMAT_IDS = [
  'phone_portrait',
  'phone_android',
  'laptop_hd',
  '1080p',
];

const SCREEN_BY_ID = Object.fromEntries(MATRIX.screens.map((s) => [s.id, s]));
const FORMAT_BY_ID = Object.fromEntries(MATRIX.formats.map((f) => [f.id, f]));

function resolveFormats() {
  const raw = (process.env.MATRIX_FORMATS || 'priority').trim();
  if (raw === 'priority' || raw === '') {
    return PRIORITY_FORMAT_IDS.map((id) => FORMAT_BY_ID[id]).filter(Boolean);
  }
  if (raw === 'all') return MATRIX.formats.slice();
  return raw.split(',').map((s) => s.trim()).filter(Boolean).map((id) => {
    const f = FORMAT_BY_ID[id];
    if (!f) console.warn(`[matrix] unknown format id: ${id}`);
    return f;
  }).filter(Boolean);
}

function resolveScreens() {
  const defaultList = ['admin', 'docs', 'api'];
  if (APP_URL) defaultList.push('home');
  const raw = (process.env.MATRIX_SCREENS || '').trim();
  const ids = raw ? raw.split(',').map((s) => s.trim()).filter(Boolean) : defaultList;
  return ids;
}

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function cellPath(formatId, shotSuffix) {
  return path.join(VIEWPORTS_DIR, `${formatId}_${shotSuffix}.png`);
}

function expectedCells(formats, screens) {
  const cells = [];
  for (const f of formats) {
    for (const sid of screens) {
      if (sid === 'api') {
        cells.push({ formatId: f.id, shotSuffix: 'api_health', screenId: 'api' });
      } else {
        const sc = SCREEN_BY_ID[sid];
        if (!sc) {
          console.warn(`[matrix] unknown screen id: ${sid}`);
          continue;
        }
        cells.push({ formatId: f.id, shotSuffix: sc.shot_suffix, screenId: sid });
      }
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
  return {
    width: fmt.width,
    height: fmt.height,
    deviceScaleFactor: fmt.dpr || 1,
    isMobile: !!fmt.touch,
    hasTouch: !!fmt.touch,
  };
}

async function hold(page) {
  await sleep(HOLD_MS);
}

async function captureAdmin(page, formatId) {
  const adminEntry = `${ADMIN_URL}/?api=${encodeURIComponent(API_URL + '/admin/api')}`;
  const resp = await page.goto(adminEntry, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('#login-form', { timeout: 10000 });
  await hold(page);
  const out = cellPath(formatId, SCREEN_BY_ID.admin.shot_suffix);
  await page.screenshot({ path: out, fullPage: false });
  ok(`capture ${formatId}_${SCREEN_BY_ID.admin.shot_suffix}`, fs.statSync(out).size > 0,
    `status ${resp && resp.status()}`);
  return out;
}

async function captureDocs(page, formatId) {
  const resp = await page.goto(DOCS_URL + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('.sidebar, nav.nav, aside, body', { timeout: 10000 }).catch(() => {});
  await hold(page);
  const out = cellPath(formatId, SCREEN_BY_ID.docs.shot_suffix);
  await page.screenshot({ path: out, fullPage: false });
  ok(`capture ${formatId}_${SCREEN_BY_ID.docs.shot_suffix}`, fs.statSync(out).size > 0,
    `status ${resp && resp.status()}`);
  return out;
}

async function captureApiHealth(page, formatId) {
  const resp = await page.goto(API_URL + '/health', { waitUntil: 'networkidle2', timeout: 20000 }).catch(() => null);
  await hold(page);
  const out = cellPath(formatId, 'api_health');
  await page.screenshot({ path: out, fullPage: false });
  ok(`capture ${formatId}_api_health`, fs.statSync(out).size > 0,
    `status ${resp && resp.status()}`);
  return out;
}

async function captureAppHome(page, formatId) {
  if (!APP_URL) {
    ok(`capture ${formatId}_01_home`, true, 'APP_URL unset — skipped');
    return null;
  }
  const resp = await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await page.waitForSelector('flutter-view, flt-glass-pane, canvas, body', { timeout: 30000 }).catch(() => {});
  await sleep(1200);
  await hold(page);
  const out = cellPath(formatId, SCREEN_BY_ID.home.shot_suffix);
  await page.screenshot({ path: out, fullPage: false });
  ok(`capture ${formatId}_${SCREEN_BY_ID.home.shot_suffix}`, fs.statSync(out).size > 0,
    `status ${resp && resp.status()}`);
  return out;
}

/**
 * CDP screencast → JPEG frames → ffmpeg webm (vp8).
 * Short desktop journey: docs home → nav click → admin login gate.
 */
async function recordDesktopJourney(browser) {
  const formatId = '1080p';
  const fmt = FORMAT_BY_ID[formatId] || { width: 1920, height: 1080, dpr: 1, touch: false };
  const recName = `${formatId}_mouse`;
  const webmPath = path.join(RECORDINGS_DIR, `${recName}.webm`);
  const stillsOut = path.join(STILLS_DIR, recName);
  fs.mkdirSync(stillsOut, { recursive: true });

  const page = await browser.newPage();
  await page.setViewport(viewportFromFormat(fmt));
  const client = await page.target().createCDPSession();

  const frames = [];
  let frameCount = 0;
  const onFrame = async (event) => {
    try {
      frames.push(Buffer.from(event.data, 'base64'));
      frameCount += 1;
      // Keep a few stills across the timeline for A4b review
      if (frameCount === 1 || frameCount % 15 === 0) {
        const idx = String(Math.floor(frameCount / 15)).padStart(3, '0');
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
      maxWidth: fmt.width,
      maxHeight: fmt.height,
      everyNthFrame: 2,
    });

    // Journey: docs → sidebar click → admin login
    await page.goto(DOCS_URL + '/', { waitUntil: 'networkidle2', timeout: 30000 });
    await sleep(600);
    const arch = await page.$('a[href="#architecture"]');
    if (arch) {
      await arch.click();
      await sleep(500);
    }
    const apiLink = await page.$('a[href="#api"]');
    if (apiLink) {
      await apiLink.click();
      await sleep(500);
    }

    const adminEntry = `${ADMIN_URL}/?api=${encodeURIComponent(API_URL + '/admin/api')}`;
    await page.goto(adminEntry, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('#login-form', { timeout: 10000 }).catch(() => {});
    await sleep(400);
    // Type into token field to prove input changes UI (VID-INPUT-WORKS)
    const token = await page.$('#token');
    if (token) {
      await token.click({ clickCount: 3 });
      await page.keyboard.type('matrix-video-probe', { delay: 20 });
      await sleep(300);
    }
    await sleep(400);

    await client.send('Page.stopScreencast').catch(() => {});
  } catch (err) {
    ok('record desktop journey', false, String(err));
    await page.close().catch(() => {});
    return null;
  }

  await page.close().catch(() => {});

  if (frames.length < 3) {
    ok('record desktop journey frames', false, `only ${frames.length} frames`);
    return null;
  }

  // Encode JPEG sequence → webm via ffmpeg image2pipe
  const encoded = await new Promise((resolve) => {
    const args = [
      '-y',
      '-f', 'image2pipe',
      '-framerate', '8',
      '-i', 'pipe:0',
      '-c:v', 'libvpx',
      '-b:v', '1M',
      '-auto-alt-ref', '0',
      webmPath,
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
    for (const buf of frames) {
      ff.stdin.write(buf);
    }
    ff.stdin.end();
  });

  ok(`record ${recName}.webm`, encoded, encoded ? `${frames.length} frames → ${fs.statSync(webmPath).size}b` : 'encode failed');
  return encoded ? webmPath : null;
}

async function captureFormat(browser, fmt, screens) {
  console.log(`\n=== format ${fmt.id} (${fmt.width}×${fmt.height} dpr=${fmt.dpr}) ===`);
  const page = await browser.newPage();
  await page.setViewport(viewportFromFormat(fmt));
  try {
    for (const sid of screens) {
      if (sid === 'admin') await captureAdmin(page, fmt.id);
      else if (sid === 'docs') await captureDocs(page, fmt.id);
      else if (sid === 'api') await captureApiHealth(page, fmt.id);
      else if (sid === 'home') await captureAppHome(page, fmt.id);
      else console.warn(`[matrix] skip unknown screen: ${sid}`);
    }
  } finally {
    await page.close().catch(() => {});
  }
}

(async () => {
  const formats = resolveFormats();
  const screens = resolveScreens();
  const cells = expectedCells(formats, screens);

  console.log('Matrix capture (prioritized subset)');
  console.log(`  API_URL   = ${API_URL}`);
  console.log(`  ADMIN_URL = ${ADMIN_URL}`);
  console.log(`  DOCS_URL  = ${DOCS_URL}`);
  console.log(`  APP_URL   = ${APP_URL || '(none — skip home)'}`);
  console.log(`  formats   = ${formats.map((f) => f.id).join(', ')}`);
  console.log(`  screens   = ${screens.join(', ')}`);
  console.log(`  cells     = ${cells.length} (full matrix expected_cells=${MATRIX.expected_cells})`);
  console.log(`  RECORD_VIDEO = ${RECORD_VIDEO}`);
  console.log(`  expand: MATRIX_FORMATS=all or comma ids; MATRIX_SCREENS=…`);

  if (VERIFY_ONLY) {
    const missing = verifyCells(cells);
    const failed = checks.filter((c) => !c.pass);
    console.log(`\nVERIFY ${cells.length - missing}/${cells.length} cells present`);
    process.exit(failed.length ? 1 : 0);
  }

  let browser;
  try {
    browser = await puppeteer.launch(launchOpts({ width: 1280, height: 900 }));
  } catch (err) {
    ok('browser launched', false, String(err));
    process.exit(1);
  }

  try {
    for (const fmt of formats) {
      await captureFormat(browser, fmt, screens);
    }
    if (RECORD_VIDEO) {
      console.log('\n=== desktop VIDEO (1080p mouse journey) ===');
      await recordDesktopJourney(browser);
    }
  } catch (err) {
    ok('harness ran without throwing', false, String(err));
  } finally {
    await browser.close().catch(() => {});
  }

  // Presence check for this subset
  verifyCells(cells);

  const failed = checks.filter((c) => !c.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed (CAPTURE_OK layer — not visual review)`);
  console.log(`PNGs: ${VIEWPORTS_DIR}`);
  if (RECORD_VIDEO) console.log(`VIDEO: ${RECORDINGS_DIR}`);
  console.log('Next: A4b video_critique.md + A6 matrix_critique.md (open artifacts; cite qa_success_criteria.json)');
  if (failed.length) {
    for (const f of failed) console.log(`  - ${f.name}${f.detail ? ': ' + f.detail : ''}`);
  }
  process.exit(failed.length ? 1 : 0);
})();
