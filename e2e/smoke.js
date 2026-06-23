/**
 * Headless browser smoke test for Compre Barato Alagoas.
 *
 * The user app is Flutter web (CanvasKit) — it renders into a <canvas>, so reliable
 * DOM-level tap-driving isn't possible here; full tap-by-tap flows live in the Flutter
 * `integration_test/` suite run on-device. This harness instead covers what a browser
 * does well and what tap-tests can't:
 *
 *   1. boots the web app and fails on any console error / unhandled page error
 *      (catches broken builds, missing assets, bad base href, CSP/CORS surprises);
 *   2. drives the public API from *inside* the page (same origin/headers a real client
 *      uses) and asserts the response shape — including the requested-quantity scaling
 *      (line_total = price * requested_quantity) and a present X-Request-ID header.
 *
 * Config via env:
 *   APP_URL  web app to load          (default https://alagoas.precospublicos.ia.br/)
 *   API_URL  backend base for fetches  (default = APP_URL origin)
 *   PUPPETEER_EXECUTABLE_PATH  system Chrome (default /usr/bin/google-chrome)
 *
 * Exit code 0 = all checks passed, 1 = a check failed.
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const APP_URL = process.env.APP_URL || 'https://alagoas.precospublicos.ia.br/';
const API_URL = (process.env.API_URL || new URL(APP_URL).origin).replace(/\/$/, '');
const { launchOpts } = require('./lib/chrome');
const SHOTS = path.join(__dirname, 'screenshots');
fs.mkdirSync(SHOTS, { recursive: true });

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};

(async () => {
  const browser = await puppeteer.launch(launchOpts({
    width: 390, height: 820, isMobile: true, hasTouch: true,
  }));

  const consoleErrors = [];
  const pageErrors = [];
  try {
    const page = await browser.newPage();
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    page.on('pageerror', (e) => pageErrors.push(e.message));

    // 1) Boot the web app.
    const resp = await page.goto(APP_URL, { waitUntil: 'networkidle2', timeout: 45000 });
    ok('web app responds 200', resp && resp.status() === 200, `status ${resp && resp.status()}`);

    // Flutter mounts a <flutter-view> / glass pane once the engine is up.
    await page.waitForSelector('flutter-view, flt-glass-pane', { timeout: 30000 })
      .then(() => ok('flutter engine mounted', true))
      .catch(() => ok('flutter engine mounted', false, 'no flutter-view after 30s'));
    await page.screenshot({ path: path.join(SHOTS, 'smoke-01-home.png') });

    // 2) Health endpoint, fetched from inside the page.
    const health = await page.evaluate(async (api) => {
      const r = await fetch(api + '/health');
      return { status: r.status, rid: r.headers.get('x-request-id'), body: await r.json() };
    }, API_URL);
    ok('health ok', health.status === 200 && health.body.status === 'ok');
    ok('X-Request-ID header present', !!health.rid, health.rid || '(missing)');

    // 3) Search with quantities — asserts the new scaling end-to-end.
    const search = await page.evaluate(async (api) => {
      const r = await fetch(api + '/api/v1/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: ['3 arroz', 'meia duzia de ovos', 'feijao'] }),
      });
      return { status: r.status, body: await r.json() };
    }, API_URL);
    ok('search returns 200', search.status === 200, `status ${search.status}`);

    const store = (search.body.stores || [])[0];
    ok('search produced a store', !!store);
    if (store) {
      const arroz = store.items.find((i) => i.query.includes('arroz'));
      ok('arroz line carries requested_quantity', arroz && arroz.requested_quantity === 3,
        arroz ? `req=${arroz.requested_quantity}` : 'no arroz line');
      ok('arroz line_total = price * quantity',
        arroz && Math.abs(arroz.line_total - arroz.price * 3) < 0.011,
        arroz ? `price=${arroz.price} line=${arroz.line_total}` : '');
    }

    ok('no console errors', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' | '));
    ok('no page errors', pageErrors.length === 0, pageErrors.slice(0, 3).join(' | '));
  } catch (err) {
    ok('harness ran without throwing', false, String(err));
  } finally {
    await browser.close();
  }

  const failed = checks.filter((c) => !c.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
})();
