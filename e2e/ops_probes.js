/**
 * Lightweight ops/contract probes (#278) — no Puppeteer required.
 *
 * Checks public API health, client-config contract, and well-known security.txt
 * on the configured host (local mock backend or production).
 *
 * Env:
 *   API_URL   default http://127.0.0.1:8000
 *   APP_URL   default same as API_URL (well-known served from app/nginx host in prod)
 *   OPS_EXPECT_MOCKS  if "true", require use_mock_sefaz/llm true (local e2e)
 *   OPS_FORBID_MOCKS  if "true", require mocks false (strict live prod — optional)
 *   OPS_REQUIRE_CLIENT_CONFIG  default "true"; set "false" until PR #271 (or equivalent) is deployed
 *   OPS_REQUIRE_SECURITY_TXT   default "false" locally (often only on app nginx); "true" on live
 */

const API_URL = (process.env.API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const APP_URL = (process.env.APP_URL || API_URL).replace(/\/$/, '');
const EXPECT_MOCKS = process.env.OPS_EXPECT_MOCKS === 'true';
const FORBID_MOCKS = process.env.OPS_FORBID_MOCKS === 'true';
const REQUIRE_CLIENT_CONFIG = process.env.OPS_REQUIRE_CLIENT_CONFIG !== 'false';
const REQUIRE_SECURITY_TXT = process.env.OPS_REQUIRE_SECURITY_TXT === 'true';

const checks = [];
const ok = (name, pass, detail = '') => {
  checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
};

async function getJson(url) {
  const r = await fetch(url, { redirect: 'follow' });
  const text = await r.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch (_) {
    /* not json */
  }
  return { status: r.status, headers: r.headers, body, text };
}

async function getText(url) {
  const r = await fetch(url, { redirect: 'follow' });
  return { status: r.status, text: await r.text() };
}

(async () => {
  console.log('Ops probes');
  console.log(`  API_URL = ${API_URL}`);
  console.log(`  APP_URL = ${APP_URL}`);

  try {
    const health = await getJson(`${API_URL}/health`);
    ok('health status 200', health.status === 200, `status ${health.status}`);
    ok('health body ok', health.body && health.body.status === 'ok', JSON.stringify(health.body));
    if (health.body) {
      if (EXPECT_MOCKS) {
        ok(
          'health mocks on (local)',
          health.body.use_mock_sefaz === true && health.body.use_mock_llm === true,
          `sefaz=${health.body.use_mock_sefaz} llm=${health.body.use_mock_llm}`,
        );
      }
      if (FORBID_MOCKS) {
        ok(
          'health mocks off (prod)',
          health.body.use_mock_sefaz === false && health.body.use_mock_llm === false,
          `sefaz=${health.body.use_mock_sefaz} llm=${health.body.use_mock_llm}`,
        );
      }
    }

    const cc = await getJson(`${API_URL}/api/v1/client-config`);
    if (REQUIRE_CLIENT_CONFIG) {
      ok('client-config 200', cc.status === 200, `status ${cc.status}`);
      if (cc.body) {
        ok('client-config policy_version', typeof cc.body.policy_version === 'string' && cc.body.policy_version.length > 0);
        ok('client-config force_update boolean', typeof cc.body.force_update === 'boolean');
        ok('client-config update_message', typeof cc.body.update_message === 'string');
      } else {
        ok('client-config json body', false, 'missing or non-json (deploy client-config route first — see PR #271)');
      }
    } else {
      ok('client-config skipped (OPS_REQUIRE_CLIENT_CONFIG=false)', true, `status ${cc.status}`);
    }

    const sec = await getText(`${APP_URL}/.well-known/security.txt`);
    if (REQUIRE_SECURITY_TXT) {
      ok('security.txt 200', sec.status === 200, `status ${sec.status}`);
      ok(
        'security.txt Contact',
        /Contact:\s*\S+/i.test(sec.text || ''),
        (sec.text || '').slice(0, 120),
      );
    } else if (sec.status === 200 && /Contact:/i.test(sec.text || '')) {
      ok('security.txt present (optional local)', true);
    } else {
      ok(
        'security.txt optional (set OPS_REQUIRE_SECURITY_TXT=true on live app host)',
        true,
        `status ${sec.status}`,
      );
    }
  } catch (err) {
    ok('ops probes ran without exception', false, String(err));
  }

  const failed = checks.filter((c) => !c.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} passed`);
  process.exit(failed.length ? 1 : 0);
})();
