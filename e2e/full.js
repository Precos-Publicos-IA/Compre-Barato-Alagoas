/**
 * Full headless suite — all surfaces, simulated user input, screenshots.
 * See AGENTS.md. Prefer `npm run full:local` to boot mock backend + static hosts.
 */

const fs = require('fs');
const path = require('path');
const { launchOpts, resolvePuppeteer } = require('./lib/chrome');
const puppeteer = resolvePuppeteer();

const API_URL = (process.env.API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const ADMIN_URL = (process.env.ADMIN_URL || 'http://127.0.0.1:8081').replace(/\/$/, '');
const DOCS_URL = (process.env.DOCS_URL || 'http://127.0.0.1:8082').replace(/\/$/, '');
const APP_URL = (process.env.APP_URL || '').replace(/\/$/, '');
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || 'test-admin-token-0123456789';

const SHOTS = path.join(__dirname, 'screenshots');
fs.mkdirSync(SHOTS, { recursive: true });

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};

const shot = async (page, name) => {
  await page.screenshot({ path: path.join(SHOTS, name.endsWith('.png') ? name : `${name}.png`) });
};

const ADMIN_TABS = [
  'overview', 'quality', 'costs', 'feedback', 'searches', 'items',
  'growth', 'performance', 'providers', 'settings',
];

async function withPage(browser, viewport, fn) {
  const page = await browser.newPage();
  if (viewport) await page.setViewport(viewport);
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => pageErrors.push(e.message));
  try {
    await fn(page, { consoleErrors, pageErrors });
  } finally {
    await page.close().catch(() => {});
  }
  return { consoleErrors, pageErrors };
}

async function testAdmin(browser) {
  console.log('\n=== Admin panel ===');
  await withPage(browser, { width: 1280, height: 900 }, async (page, errs) => {
    const adminEntry = `${ADMIN_URL}/?api=${encodeURIComponent(API_URL + '/admin/api')}`;
    const resp = await page.goto(adminEntry, { waitUntil: 'networkidle2', timeout: 30000 });
    ok('admin responds 200', resp && resp.status() === 200, `status ${resp && resp.status()}`);
    await page.waitForSelector('#login-form', { timeout: 10000 });
    ok('admin shows login gate', await page.$eval('#login', (el) => !el.hidden));
    await shot(page, 'admin-01-login');

    await page.click('#token', { clickCount: 3 });
    await page.type('#token', 'wrong-token-definitely-invalid');
    await page.click('#login-form button[type="submit"]');
    await page.waitForFunction(() => {
      const err = document.querySelector('#login-error');
      return err && !err.hidden;
    }, { timeout: 8000 }).catch(() => {});
    ok('admin rejects invalid token (error shown)', await page.$eval('#login-error', (el) => !el.hidden));
    await shot(page, 'admin-02-bad-token');

    await page.click('#token', { clickCount: 3 });
    await page.keyboard.press('Backspace');
    await page.type('#token', ADMIN_TOKEN);
    await page.click('#login-form button[type="submit"]');
    await page.waitForFunction(() => {
      const app = document.querySelector('#app');
      return app && !app.hidden;
    }, { timeout: 10000 }).catch(() => {});
    ok('admin accepts valid token (app visible)', await page.$eval('#app', (el) => !el.hidden));
    await page.waitForSelector('#overview-cards .card, #status', { timeout: 10000 }).catch(() => {});
    await shot(page, 'admin-03-overview');

    for (const tab of ADMIN_TABS) {
      const btn = await page.$(`button.tab[data-tab="${tab}"]`);
      if (!btn) { ok(`admin tab button exists: ${tab}`, false); continue; }
      await btn.click();
      await page.waitForFunction((t) => {
        const panel = document.querySelector('#tab-' + t);
        return panel && !panel.hidden;
      }, { timeout: 8000 }, tab).catch(() => {});
      const panelOpen = await page.$eval(`#tab-${tab}`, (el) => !el.hidden).catch(() => false);
      ok(`admin tab opens: ${tab}`, panelOpen);
      await new Promise((r) => setTimeout(r, 350));
      await shot(page, `admin-tab-${tab}`);
    }

    await page.click('button.tab[data-tab="overview"]');
    await page.select('#range', '7');
    await new Promise((r) => setTimeout(r, 400));
    ok('admin range select works (7 days)', (await page.$eval('#range', (el) => el.value)) === '7');
    await shot(page, 'admin-04-range-7d');

    await page.click('#refresh');
    await new Promise((r) => setTimeout(r, 300));
    ok('admin refresh click (no throw)', true);

    await page.click('#logout');
    await page.waitForFunction(() => {
      const login = document.querySelector('#login');
      return login && !login.hidden;
    }, { timeout: 5000 }).catch(() => {});
    ok('admin logout returns to login', await page.$eval('#login', (el) => !el.hidden));
    await shot(page, 'admin-05-logout');

    const severe = errs.pageErrors.filter((e) => !/ResizeObserver/i.test(e));
    ok('admin no page errors', severe.length === 0, severe.slice(0, 2).join(' | '));
  });
}

async function testDocs(browser) {
  console.log('\n=== Docs site ===');
  await withPage(browser, { width: 1280, height: 900 }, async (page) => {
    const resp = await page.goto(DOCS_URL + '/', { waitUntil: 'networkidle2', timeout: 30000 });
    ok('docs home responds 200', resp && resp.status() === 200, `status ${resp && resp.status()}`);
    await page.waitForSelector('.sidebar, nav.nav, aside', { timeout: 10000 }).catch(() => {});
    ok('docs home shows brand text',
      await page.$eval('body', (b) => /Compre Barato/i.test(b.innerText)).catch(() => false));
    await shot(page, 'docs-01-home');

    for (const href of ['#visao-geral', '#arquitetura', '#fluxo', '#api', '#admin']) {
      const link = await page.$(`a[href="${href}"]`);
      if (!link) { ok(`docs link present: ${href}`, false); continue; }
      await link.click();
      await new Promise((r) => setTimeout(r, 200));
      const hash = await page.evaluate(() => location.hash);
      ok(`docs navigates to ${href}`, hash === href);
      await shot(page, `docs-nav-${href.replace('#', '')}`);
    }

    for (const p of ['seguranca-e-dados.html', 'lgpd-medicao-de-uso.html', 'seguranca-postura.html']) {
      const r = await page.goto(`${DOCS_URL}/${p}`, { waitUntil: 'networkidle2', timeout: 20000 });
      ok(`docs page ${p} responds 200`, r && r.status() === 200, `status ${r && r.status()}`);
      await shot(page, `docs-page-${p.replace('.html', '')}`);
    }
  });
}

async function testApiJourneys(browser, { allowMissingAdmin = false } = {}) {
  console.log('\n=== Public API (in-browser fetch) ===');
  await withPage(browser, { width: 390, height: 820, isMobile: true, hasTouch: true }, async (page) => {
    await page.goto(API_URL + '/health', { waitUntil: 'networkidle2', timeout: 20000 }).catch(() => {});
    await shot(page, 'api-01-health-document');

    const health = await page.evaluate(async (api) => {
      const r = await fetch(api + '/health');
      return { status: r.status, rid: r.headers.get('x-request-id'), body: await r.json().catch(() => null) };
    }, API_URL);
    ok('api health 200', health.status === 200 && health.body && health.body.status === 'ok');
    ok('api health has X-Request-ID', !!health.rid, health.rid || '(missing)');

    const suggestions = await page.evaluate(async (api) => {
      const r = await fetch(api + '/api/v1/suggestions');
      return { status: r.status, body: await r.json().catch(() => null) };
    }, API_URL);
    ok('api suggestions 200', suggestions.status === 200);
    const sugItems = suggestions.body?.items || [];
    ok('api suggestions non-empty', Array.isArray(sugItems) && sugItems.length > 0, `count=${sugItems.length}`);

    const search = await page.evaluate(async (api) => {
      const r = await fetch(api + '/api/v1/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: ['3 arroz', 'meia duzia de ovos', 'feijao', '1L leite'] }),
      });
      return { status: r.status, body: await r.json().catch(() => null) };
    }, API_URL);
    ok('api search 200', search.status === 200, `status ${search.status}`);
    const stores = search.body?.stores || [];
    ok('api search returns stores', stores.length > 0, `stores=${stores.length}`);
    if (stores[0]) {
      const arroz = (stores[0].items || []).find((i) => (i.query || '').toLowerCase().includes('arroz'));
      ok('api arroz requested_quantity=3', arroz && arroz.requested_quantity === 3,
        arroz ? `req=${arroz.requested_quantity}` : 'no arroz line');
      ok('api arroz line_total = price * qty',
        arroz && Math.abs(arroz.line_total - arroz.price * 3) < 0.011,
        arroz ? `price=${arroz.price} line=${arroz.line_total}` : '');
    }

    const shareId = search.body?.list_id || null;
    const deviceToken = Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('');

    const consent = await page.evaluate(async (api, token) => {
      const r = await fetch(api + '/api/v1/device/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Device-Token': token },
        // Must match the server's POLICY_VERSION (and frontend AppConfig.policyVersion);
        // the consent endpoint rejects a mismatched version (#344).
        body: JSON.stringify({ accepted: true, policy_version: '2026-06-06' }),
      });
      return { status: r.status, body: await r.json().catch(() => null) };
    }, API_URL, deviceToken);
    ok('api device consent 200', consent.status === 200, `status ${consent.status}`);
    ok('api device consented', consent.body && consent.body.consented === true);

    const me = await page.evaluate(async (api, token) => {
      const r = await fetch(api + '/api/v1/device/me', { headers: { 'X-Device-Token': token } });
      return { status: r.status, body: await r.json().catch(() => null) };
    }, API_URL, deviceToken);
    ok('api device me known', me.status === 200 && me.body && me.body.known === true);

    const fb = await page.evaluate(async (api) => {
      const r = await fetch(api + '/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'helpful', helpful: true, item: '', note: 'e2e headless' }),
      });
      return { status: r.status };
    }, API_URL);
    ok('api feedback accepted', fb.status === 200 || fb.status === 201, `status ${fb.status}`);

    if (shareId) {
      const saved = await page.evaluate(async (api, id) => {
        const r = await fetch(api + `/api/v1/lists/${id}`);
        return { status: r.status };
      }, API_URL, shareId);
      ok('api shared list resolves', saved.status === 200, `status ${saved.status}`);
    } else {
      const missing = await page.evaluate(async (api) => {
        const r = await fetch(api + '/api/v1/lists/00000000-0000-4000-8000-000000000000');
        return { status: r.status };
      }, API_URL);
      ok('api missing shared list 404', missing.status === 404, `status ${missing.status}`);
    }

    // LGPD erase — skip on live if LIVE_SKIP_DEVICE_DELETE=1 (optional safety)
    if (process.env.LIVE_SKIP_DEVICE_DELETE === '1') {
      ok('api device delete (skipped on live)', true, 'LIVE_SKIP_DEVICE_DELETE=1');
    } else {
      const del = await page.evaluate(async (api, token) => {
        const r = await fetch(api + '/api/v1/device/me', {
          method: 'DELETE', headers: { 'X-Device-Token': token },
        });
        return { status: r.status, body: await r.json().catch(() => null) };
      }, API_URL, deviceToken);
      ok('api device delete', del.status === 200 && del.body && del.body.deleted === true);
    }

    void allowMissingAdmin;
    await shot(page, 'api-02-journeys-done');
  });
}

async function testUserApp(browser) {
  if (!APP_URL) {
    console.log('\n=== User app (Flutter web) — SKIPPED (set APP_URL to enable) ===');
    ok('user app tested (or explicitly skipped)', true, 'APP_URL unset — skipped');
    return;
  }
  console.log('\n=== User app (Flutter web) ===');
  await withPage(browser, { width: 390, height: 820, isMobile: true, hasTouch: true }, async (page, errs) => {
    const resp = await page.goto(APP_URL + '/', { waitUntil: 'networkidle2', timeout: 45000 });
    ok('user app responds 200', resp && resp.status() === 200, `status ${resp && resp.status()}`);
    await page.waitForSelector('flutter-view, flt-glass-pane, canvas', { timeout: 30000 })
      .then(() => ok('user app flutter engine mounted', true))
      .catch(() => ok('user app flutter engine mounted', false, 'no flutter-view after 30s'));
    await new Promise((r) => setTimeout(r, 1200));
    await shot(page, 'app-01-home');
    const severe = errs.pageErrors.filter((e) => !/ResizeObserver| Favicon/i.test(e));
    ok('user app no page errors', severe.length === 0, severe.slice(0, 2).join(' | '));
  });
}

(async () => {
  console.log('Full headless suite');
  console.log(`  API_URL   = ${API_URL}`);
  console.log(`  ADMIN_URL = ${ADMIN_URL}`);
  console.log(`  DOCS_URL  = ${DOCS_URL}`);
  console.log(`  APP_URL   = ${APP_URL || '(none)'}`);

  let browser;
  try {
    browser = await puppeteer.launch(launchOpts());
  } catch (err) {
    ok('browser launched', false, String(err));
    process.exit(1);
  }

  try {
    await testAdmin(browser);
    await testDocs(browser);
    await testApiJourneys(browser);
    await testUserApp(browser);
  } catch (err) {
    ok('harness ran without throwing', false, String(err));
  } finally {
    await browser.close().catch(() => {});
  }

  const failed = checks.filter((c) => !c.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
  if (failed.length) {
    for (const f of failed) console.log(`  - ${f.name}${f.detail ? ': ' + f.detail : ''}`);
  }
  process.exit(failed.length ? 1 : 0);
})();
