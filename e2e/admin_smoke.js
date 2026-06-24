/**
 * Headless smoke for the admin static SPA (#134).
 *
 * Does not require a valid ADMIN_TOKEN: asserts the login gate renders and the
 * page loads without console/page errors. With ADMIN_TOKEN, optionally verifies
 * the app shell appears after submit (best-effort; may fail if API host differs).
 *
 * Env:
 *   ADMIN_URL     default http://127.0.0.1:8766 or https://admin.alagoas.precospublicos.ia.br
 *   ADMIN_TOKEN   optional bearer for authenticated probe
 */
const fs = require('fs');
const path = require('path');
const { launchOpts, resolvePuppeteer } = require('./lib/chrome');
const puppeteer = resolvePuppeteer();

const ADMIN_URL = (process.env.ADMIN_URL || 'https://admin.alagoas.precospublicos.ia.br').replace(/\/$/, '') + '/';
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || process.env.LIVE_ADMIN_TOKEN || '';
const SHOTS = path.join(__dirname, 'screenshots');
fs.mkdirSync(SHOTS, { recursive: true });

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};

(async () => {
  const browser = await puppeteer.launch(launchOpts({ width: 1280, height: 900 }));
  const consoleErrors = [];
  const pageErrors = [];
  try {
    const page = await browser.newPage();
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    page.on('pageerror', (e) => pageErrors.push(e.message));

    const resp = await page.goto(ADMIN_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    ok('admin responds 2xx/3xx', resp && resp.status() >= 200 && resp.status() < 400, `status ${resp && resp.status()}`);

    await page.waitForSelector('#login, #app, #login-form', { timeout: 15000 })
      .then(() => ok('admin shell has login or app root', true))
      .catch(() => ok('admin shell has login or app root', false, 'missing #login/#app'));

    const hasLogin = await page.$('#login-form, #token, form.login-card');
    ok('login gate markup present (unauthenticated smoke)', !!hasLogin);

    // Structural: esc() helper exists in shipped app.js (XSS mitigation #133).
    const hasEsc = await page.evaluate(async () => {
      try {
        const r = await fetch('app.js');
        const t = await r.text();
        return /function esc\s*\(/.test(t) && /&amp;/.test(t);
      } catch (_) {
        return false;
      }
    });
    ok('app.js ships esc() HTML escape helper', hasEsc);

    await page.screenshot({ path: path.join(SHOTS, 'admin-smoke-01-gate.png') });

    if (ADMIN_TOKEN && hasLogin) {
      try {
        await page.type('#token', ADMIN_TOKEN, { delay: 5 });
        await Promise.all([
          page.click('#login-form button[type="submit"], #login-form button'),
          page.waitForSelector('#app:not([hidden]), #overview-cards, .topbar', { timeout: 12000 }).catch(() => null),
        ]);
        const appVisible = await page.evaluate(() => {
          const app = document.querySelector('#app');
          return app && !app.hidden;
        });
        ok('optional: login with ADMIN_TOKEN shows app', !!appVisible,
          appVisible ? '' : 'token rejected or API unreachable (ok if static-only host)');
        await page.screenshot({ path: path.join(SHOTS, 'admin-smoke-02-app.png') });
      } catch (e) {
        ok('optional: login with ADMIN_TOKEN shows app', false, String(e.message || e));
      }
    } else {
      ok('optional: login with ADMIN_TOKEN shows app', true, 'skipped (no ADMIN_TOKEN)');
    }

    const noisy = consoleErrors.filter((t) => !/favicon|ResizeObserver|Chart.*deprecated/i.test(t));
    ok('no severe console errors on load', noisy.length === 0, noisy.slice(0, 3).join(' | '));
    ok('no pageerror on load', pageErrors.length === 0, pageErrors.slice(0, 2).join(' | '));
  } finally {
    await browser.close();
  }

  const failed = checks.filter((c) => !c.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} passed`);
  process.exit(failed.length ? 1 : 0);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
