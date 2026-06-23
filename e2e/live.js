/**
 * Post-deploy live verification — public app + API + docs on production hosts.
 * Does NOT log into admin (would need prod ADMIN_TOKEN in CI secrets); admin gate
 * is covered in full:local. Set LIVE_ADMIN_TOKEN to optionally exercise admin on live.
 *
 * Env (defaults point at production):
 *   APP_URL / API_URL  https://alagoas.precospublicos.ia.br
 *   DOCS_URL           https://docs.alagoas.precospublicos.ia.br
 *   LIVE_ADMIN_URL     https://admin.alagoas.precospublicos.ia.br (optional gate screenshot)
 *   LIVE_ADMIN_TOKEN   optional — only if secret is provisioned
 */

process.env.APP_URL = (process.env.APP_URL || 'https://alagoas.precospublicos.ia.br').replace(/\/$/, '');
process.env.API_URL = (process.env.API_URL || process.env.APP_URL).replace(/\/$/, '');
process.env.DOCS_URL = (process.env.DOCS_URL || 'https://docs.alagoas.precospublicos.ia.br').replace(/\/$/, '');
// Admin panel on live: login gate only unless token provided
process.env.ADMIN_URL = (process.env.LIVE_ADMIN_URL || process.env.ADMIN_URL || 'https://admin.alagoas.precospublicos.ia.br').replace(/\/$/, '');
process.env.LIVE_SKIP_DEVICE_DELETE = process.env.LIVE_SKIP_DEVICE_DELETE || '0';

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const { launchOpts } = require('./lib/chrome');

const APP_URL = process.env.APP_URL;
const API_URL = process.env.API_URL;
const DOCS_URL = process.env.DOCS_URL;
const ADMIN_URL = process.env.ADMIN_URL;
const LIVE_ADMIN_TOKEN = process.env.LIVE_ADMIN_TOKEN || process.env.ADMIN_TOKEN || '';

const SHOTS = path.join(__dirname, 'screenshots');
fs.mkdirSync(SHOTS, { recursive: true });

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};
const shot = async (page, name) => {
  await page.screenshot({ path: path.join(SHOTS, `live-${name}.png`) });
};

(async () => {
  console.log('Live production suite');
  console.log(`  APP_URL   = ${APP_URL}`);
  console.log(`  API_URL   = ${API_URL}`);
  console.log(`  DOCS_URL  = ${DOCS_URL}`);
  console.log(`  ADMIN_URL = ${ADMIN_URL}`);

  let browser;
  try {
    browser = await puppeteer.launch(launchOpts({ width: 390, height: 820, isMobile: true, hasTouch: true }));
  } catch (err) {
    ok('browser launched', false, String(err));
    process.exit(1);
  }

  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(45000);

    // --- User app ---
    const appResp = await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 45000 });
    ok('live app responds 200', appResp && appResp.status() === 200, `status ${appResp && appResp.status()}`);
    await page.waitForSelector('flutter-view, flt-glass-pane, canvas', { timeout: 35000 })
      .then(() => ok('live app flutter mounted', true))
      .catch(() => ok('live app flutter mounted', false));
    await new Promise((r) => setTimeout(r, 1500));
    await shot(page, '01-app-home');

    // --- API journeys in-page (same as full.js subset) ---
    await page.goto(API_URL + '/health', { waitUntil: 'networkidle2' }).catch(() => {});
    const health = await page.evaluate(async (api) => {
      const r = await fetch(api + '/health');
      return { status: r.status, rid: r.headers.get('x-request-id'), body: await r.json().catch(() => null) };
    }, API_URL);
    ok('live api health', health.status === 200 && health.body?.status === 'ok');
    ok('live api request-id', !!health.rid);

    const suggestions = await page.evaluate(async (api) => {
      const r = await fetch(api + '/api/v1/suggestions');
      return { status: r.status, n: ((await r.json().catch(() => ({}))).items || []).length };
    }, API_URL);
    ok('live api suggestions', suggestions.status === 200 && suggestions.n > 0, `n=${suggestions.n}`);

    const search = await page.evaluate(async (api) => {
      const r = await fetch(api + '/api/v1/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: ['3 arroz', 'feijao'] }),
      });
      const body = await r.json().catch(() => null);
      return { status: r.status, stores: (body && body.stores) || [], list_id: body && body.list_id };
    }, API_URL);
    ok('live api search', search.status === 200 && search.stores.length > 0,
      `status=${search.status} stores=${search.stores.length}`);
    if (search.stores[0]) {
      const arroz = (search.stores[0].items || []).find((i) => (i.query || '').includes('arroz'));
      ok('live qty scaling', arroz && arroz.requested_quantity === 3 &&
        Math.abs(arroz.line_total - arroz.price * 3) < 0.02);
    }

    const deviceToken = Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
    const consent = await page.evaluate(async (api, token) => {
      const r = await fetch(api + '/api/v1/device/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Device-Token': token },
        body: JSON.stringify({ accepted: true, policy_version: 'live-e2e' }),
      });
      return { status: r.status, body: await r.json().catch(() => null) };
    }, API_URL, deviceToken);
    ok('live device consent', consent.status === 200 && consent.body?.consented);

    const fb = await page.evaluate(async (api) => {
      const r = await fetch(api + '/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'helpful', helpful: true, note: 'live-e2e' }),
      });
      return r.status;
    }, API_URL);
    ok('live feedback', fb === 200 || fb === 201, `status ${fb}`);

    // cleanup device on live (ephemeral token)
    await page.evaluate(async (api, token) => {
      await fetch(api + '/api/v1/device/me', { method: 'DELETE', headers: { 'X-Device-Token': token } });
    }, API_URL, deviceToken);

    await shot(page, '02-api-done');

    // --- Docs (desktop viewport) ---
    await page.setViewport({ width: 1280, height: 900 });
    const docsResp = await page.goto(DOCS_URL + '/', { waitUntil: 'networkidle2', timeout: 30000 });
    ok('live docs 200', docsResp && docsResp.status() === 200);
    ok('live docs brand', await page.$eval('body', (b) => /Compre Barato/i.test(b.innerText)).catch(() => false));
    const link = await page.$('a[href="#arquitetura"]');
    if (link) { await link.click(); await new Promise((r) => setTimeout(r, 200)); }
    await shot(page, '03-docs');

    // --- Admin gate (always); full login only if token in env ---
    const adminEntry = LIVE_ADMIN_TOKEN
      ? `${ADMIN_URL}/?api=${encodeURIComponent(API_URL + '/admin/api')}`
      : ADMIN_URL + '/';
    const adminResp = await page.goto(adminEntry, { waitUntil: 'networkidle2', timeout: 30000 }).catch(() => null);
    if (!adminResp) {
      ok('live admin reachable', false, 'navigation failed (host may differ)');
    } else {
      ok('live admin responds', adminResp.status() === 200 || adminResp.status() === 401,
        `status ${adminResp.status()}`);
      const hasLogin = await page.$('#login-form');
      ok('live admin login gate present', !!hasLogin);
      await shot(page, '04-admin-gate');
      if (LIVE_ADMIN_TOKEN && hasLogin) {
        await page.type('#token', LIVE_ADMIN_TOKEN);
        await page.click('#login-form button[type="submit"]');
        await page.waitForFunction(() => {
          const app = document.querySelector('#app');
          return app && !app.hidden;
        }, { timeout: 10000 }).catch(() => {});
        ok('live admin login works', await page.$eval('#app', (el) => !el.hidden).catch(() => false));
        await shot(page, '05-admin-in');
        await page.click('#logout').catch(() => {});
      } else {
        ok('live admin full login (optional)', true, 'LIVE_ADMIN_TOKEN unset — gate only');
      }
    }

    await page.close();
  } catch (err) {
    ok('live harness no throw', false, String(err));
  } finally {
    await browser.close().catch(() => {});
  }

  const failed = checks.filter((c) => !c.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} live checks passed`);
  process.exit(failed.length ? 1 : 0);
})();
