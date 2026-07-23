/**
 * Focused e2e smoke for the search wait UI (rotating phrases, ETA, notify copy).
 *
 * Not the full viewport matrix — only phone portrait 390×844:
 *   1) boot Flutter web
 *   2) add basket item + VER PREÇOS
 *   3) delay /api/v1/search ~7.5s so the loading surface is visible
 *   4) screenshot at ~1.5s and ~5s into loading, then results
 *
 * Env:
 *   APP_URL              default http://127.0.0.1:8090
 *   API_URL              default http://127.0.0.1:8000
 *   SEARCH_DELAY_MS      default 7500
 *   SEARCH_ITEM          default arroz
 *   RESULTS_TIMEOUT_MS   default 60000
 *
 * Exit 0 = all hard checks passed.
 */

const fs = require('fs');
const path = require('path');
const { launchOpts, resolvePuppeteer } = require('./lib/chrome');
const puppeteer = resolvePuppeteer();

const APP_URL = (process.env.APP_URL || 'http://127.0.0.1:8090').replace(/\/$/, '');
const API_URL = (process.env.API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const SEARCH_DELAY_MS = Number(process.env.SEARCH_DELAY_MS || 7500);
const SEARCH_ITEM = process.env.SEARCH_ITEM || 'arroz';
const RESULTS_TIMEOUT_MS = Number(process.env.RESULTS_TIMEOUT_MS || 60000);
const VP = { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 };

const SHOTS = path.join(__dirname, 'screenshots');
fs.mkdirSync(SHOTS, { recursive: true });

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function maceioGeoInstallScript(latitude, longitude) {
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
      getCurrentPosition(success, error) {
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
  const lat = -9.6633;
  const lon = -35.7089;
  try {
    const client = await page.target().createCDPSession();
    await client.send('Browser.grantPermissions', {
      origin: APP_URL,
      permissions: ['geolocation'],
    }).catch(() => {});
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
  await page.evaluateOnNewDocument(maceioGeoInstallScript(lat, lon));
  await page.evaluate(maceioGeoInstallScript(lat, lon)).catch(() => {});
}

async function waitFlutter(page) {
  await page.waitForSelector('flutter-view, flt-glass-pane, canvas', { timeout: 45000 });
  const painted = await page
    .waitForFunction(
      () => {
        function allCanvases(root, out = []) {
          if (!root) return out;
          if (root.querySelectorAll) {
            for (const c of root.querySelectorAll('canvas')) out.push(c);
            for (const el of root.querySelectorAll('*')) {
              if (el.shadowRoot) allCanvases(el.shadowRoot, out);
            }
          }
          return out;
        }
        const canvases = allCanvases(document).filter((c) => c.width > 16 && c.height > 16);
        if (!canvases.length) return false;
        for (const c of canvases) {
          try {
            const t = document.createElement('canvas');
            t.width = 32;
            t.height = 32;
            const ctx = t.getContext('2d');
            if (!ctx) continue;
            ctx.drawImage(c, 0, 0, 32, 32);
            const data = ctx.getImageData(0, 0, 32, 32).data;
            let nonWhite = 0;
            for (let i = 0; i < data.length; i += 4) {
              if (data[i] < 250 || data[i + 1] < 250 || data[i + 2] < 250) nonWhite++;
            }
            if (nonWhite > 40) return true;
          } catch (_) { /* next */ }
        }
        return false;
      },
      { timeout: Number(process.env.FLUTTER_PAINT_TIMEOUT_MS || 90000) },
    )
    .then(() => true)
    .catch(() => false);
  if (!painted) {
    throw new Error('Flutter did not paint product UI');
  }
  await sleep(800);
}

async function clickXY(page, x, y) {
  await page.mouse.click(Math.round(x), Math.round(y));
  await sleep(180);
}

async function flutterClick(page, nx, ny) {
  const vp = page.viewport();
  await clickXY(page, vp.width * nx, vp.height * ny);
}

function homeLayout(vp) {
  const h = vp.height;
  const w = vp.width;
  const short = h < 500;
  const appBar = short ? 48 : 56;
  const banner = short ? 40 : 52;
  const fieldAbsY = short
    ? Math.min(h - 150, appBar + banner + 42)
    : appBar + banner + 72;
  const chipAbsY = short
    ? Math.min(h - 100, fieldAbsY + 48)
    : fieldAbsY + 90;
  const recentAbsY = chipAbsY + (short ? 42 : 110);
  const verAbsY = Math.max(h - 32, short ? h - 40 : h - 36);
  return {
    short,
    chipY: Math.min(0.78, chipAbsY / h),
    fieldY: Math.min(0.55, fieldAbsY / h),
    addX: w < 600 ? 0.88 : 0.94,
    recentY: Math.min(0.85, recentAbsY / h),
    verPrecosY: Math.min(0.98, verAbsY / h),
  };
}

async function flutterAddItem(page, text) {
  const vp = page.viewport();
  const L = homeLayout(vp);

  await clickXY(page, vp.width - 28, L.short ? 58 : 90);
  await sleep(250);

  const chipX = L.short
    ? (vp.width < 500 ? 0.12 : 0.08)
    : (vp.width < 500 ? 0.18 : 0.055);
  await flutterClick(page, chipX, L.chipY);
  await sleep(450);
  await flutterClick(page, chipX, Math.min(0.78, L.chipY + (L.short ? 0.02 : 0.03)));
  await sleep(300);
  if (L.short) {
    await flutterClick(page, 0.25, L.recentY);
    await sleep(350);
  }

  await clickXY(page, Math.min(vp.width * 0.35, 280), L.fieldY * vp.height);
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
  await sleep(400);
  const addBtnX = L.short
    ? Math.min(0.90, (vp.width - 100) / vp.width)
    : Math.min(0.85, L.addX);
  await flutterClick(page, addBtnX, L.fieldY);
  await sleep(350);
}

async function flutterTapVerPrecos(page, yAdjust = 0) {
  const vp = page.viewport();
  const L = homeLayout(vp);
  const ny = Math.min(0.99, Math.max(0.90, L.verPrecosY + yAdjust));
  await flutterClick(page, 0.50, ny);
  await sleep(900);
}

function shotPath(name) {
  return path.join(SHOTS, name);
}

async function takeShot(page, name) {
  const p = shotPath(name);
  await page.screenshot({ path: p, fullPage: false });
  const st = fs.statSync(p);
  return { path: p, bytes: st.size };
}

(async () => {
  console.log(`[search_wait_smoke] APP_URL=${APP_URL} API_URL=${API_URL} delay=${SEARCH_DELAY_MS}ms`);
  console.log(`[search_wait_smoke] viewport ${VP.width}x${VP.height}`);

  // Preflight API
  try {
    const r = await fetch(`${API_URL}/health`);
    const body = await r.json();
    ok('mock API healthy', r.status === 200 && body.status === 'ok',
      `source=${body.data_source} mock_sefaz=${body.use_mock_sefaz}`);
  } catch (e) {
    ok('mock API healthy', false, String(e));
  }

  const browser = await puppeteer.launch(launchOpts(VP));
  const consoleErrors = [];
  const pageErrors = [];
  let searchRequestSeen = 0;
  let searchFinished = 0;
  let firstSearchAt = 0;
  let lastSearchFinishedAt = 0;
  let pendingSearch = 0;

  try {
    const page = await browser.newPage();
    await page.setViewport(VP);
    page.setDefaultTimeout(90000);
    page.on('console', (m) => {
      if (m.type() === 'error') consoleErrors.push(m.text());
    });
    page.on('pageerror', (e) => pageErrors.push(e.message));

    // Delay search so wait UI is visible (mock is otherwise instant).
    // Only delay the *first* search so a follow-up stream does not restuck loading.
    await page.setRequestInterception(true);
    page.on('request', async (req) => {
      try {
        const url = req.url();
        if (/\/api\/v1\/search/.test(url)) {
          searchRequestSeen += 1;
          pendingSearch += 1;
          if (!firstSearchAt) firstSearchAt = Date.now();
          const n = searchRequestSeen;
          if (n === 1) {
            console.log(`[search_wait_smoke] delaying search #${n}: ${url.slice(0, 120)}`);
            await sleep(SEARCH_DELAY_MS);
          } else {
            console.log(`[search_wait_smoke] passthrough search #${n}: ${url.slice(0, 120)}`);
          }
        }
        if (!req.isInterceptResolutionHandled()) {
          await req.continue();
        }
      } catch (err) {
        try {
          if (!req.isInterceptResolutionHandled()) await req.continue();
        } catch (_) { /* closed */ }
      }
    });
    const onSearchDone = (req) => {
      if (/\/api\/v1\/search/.test(req.url())) {
        searchFinished += 1;
        pendingSearch = Math.max(0, pendingSearch - 1);
        lastSearchFinishedAt = Date.now();
        console.log(`[search_wait_smoke] search finished #${searchFinished} pending=${pendingSearch}`);
      }
    };
    page.on('requestfinished', onSearchDone);
    page.on('requestfailed', onSearchDone);

    await grantMaceioGeo(page);
    const resp = await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 90000 });
    await grantMaceioGeo(page);
    ok('web app responds 200', resp && resp.status() === 200, `status ${resp && resp.status()}`);

    await waitFlutter(page);
    ok('flutter mounted + painted', true);

    // Journey: add item + VER PREÇOS (with one retry + adjusted Y).
    async function runSearchPath(attempt, yAdjust) {
      searchRequestSeen = 0;
      searchFinished = 0;
      firstSearchAt = 0;
      lastSearchFinishedAt = 0;
      pendingSearch = 0;
      console.log(`[search_wait_smoke] attempt ${attempt} yAdjust=${yAdjust}`);
      await flutterAddItem(page, SEARCH_ITEM);
      await flutterTapVerPrecos(page, yAdjust);

      const loadingStart = Date.now();

      // Shot ~1.5s into loading
      const wait1 = Math.max(0, 1500 - (Date.now() - loadingStart));
      await sleep(wait1);
      const s1 = await takeShot(page, 'wait-01-loading.png');
      console.log(`[search_wait_smoke] shot1 ${s1.bytes}B @ ${Date.now() - loadingStart}ms`);

      // Shot ~5s into loading (phrase should have rotated once at 3.2s)
      const wait2 = Math.max(0, 5000 - (Date.now() - loadingStart));
      await sleep(wait2);
      const s2 = await takeShot(page, 'wait-02-phrase-rotate.png');
      console.log(`[search_wait_smoke] shot2 ${s2.bytes}B @ ${Date.now() - loadingStart}ms`);

      // Wait until all search requests finish + quiet paint window
      const deadline = Date.now() + RESULTS_TIMEOUT_MS;
      while (Date.now() < deadline) {
        if (
          searchFinished > 0 &&
          pendingSearch === 0 &&
          lastSearchFinishedAt &&
          Date.now() - lastSearchFinishedAt > 2800
        ) {
          break;
        }
        // If no request after 12s, VER PREÇOS likely missed
        if (searchRequestSeen === 0 && Date.now() - loadingStart > 12000) {
          break;
        }
        await sleep(400);
      }
      // Extra paint settle for store cards
      await sleep(1500);
      try {
        await page.waitForNetworkIdle({ idleTime: 800, timeout: 5000 });
      } catch (_) { /* ok */ }
      const s3 = await takeShot(page, 'wait-03-results.png');
      console.log(
        `[search_wait_smoke] shot3 ${s3.bytes}B hits=${searchRequestSeen} ` +
        `finished=${searchFinished} pending=${pendingSearch}`,
      );

      return { s1, s2, s3, hits: searchRequestSeen, finished: searchFinished };
    }

    let result = await runSearchPath(1, 0);

    if (result.hits === 0) {
      console.log('[search_wait_smoke] no search traffic — retry with adjusted VER PREÇOS Y');
      await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 90000 });
      await grantMaceioGeo(page);
      await waitFlutter(page);
      // Slightly higher CTA (basket bar may sit above absolute bottom)
      result = await runSearchPath(2, -0.02);
    }

    ok('search request seen', result.hits > 0, `hits=${result.hits}`);
    ok('loading shot non-empty', result.s1.bytes > 5000, `${result.s1.bytes}B ${result.s1.path}`);
    ok('phrase-rotate shot non-empty', result.s2.bytes > 5000, `${result.s2.bytes}B ${result.s2.path}`);
    ok('results shot non-empty', result.s3.bytes > 5000, `${result.s3.bytes}B ${result.s3.path}`);
    ok('search finished after delay', result.finished > 0, `finished=${result.finished}`);

    // Severe page errors only (ignore benign Flutter web noise)
    const severePage = pageErrors.filter((m) =>
      !/ResizeObserver|Loading chunk|Failed to load/i.test(m));
    const severeConsole = consoleErrors.filter((m) =>
      !/favicon|DevTools|CORS|net::ERR|ResizeObserver|third-party/i.test(m));
    ok('no severe page errors', severePage.length === 0, severePage.slice(0, 2).join(' | '));
    // Console noise is soft — report but do not fail hard unless many
    ok('console errors tolerable', severeConsole.length < 8,
      severeConsole.slice(0, 3).join(' | ') || 'clean');

    console.log(`[search_wait_smoke] screenshots:`);
    console.log(`  ${result.s1.path}`);
    console.log(`  ${result.s2.path}`);
    console.log(`  ${result.s3.path}`);
  } catch (err) {
    ok('harness ran without throwing', false, String(err && err.stack || err));
  } finally {
    await browser.close();
  }

  const hard = checks.filter((c) =>
    !['console errors tolerable'].includes(c.name));
  const failed = hard.filter((c) => !c.pass);
  console.log(`\n${checks.filter((c) => c.pass).length}/${checks.length} checks passed (${failed.length} hard fails)`);
  process.exit(failed.length ? 1 : 0);
})();
