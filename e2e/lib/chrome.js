/** Shared Chrome resolution for Puppeteer scripts (host or pre-baked CI image). */
const fs = require('fs');
const Module = require('module');

// Prefer image-baked node_modules when the checkout has none (CI container).
if (!process.env.NODE_PATH && fs.existsSync('/opt/ci/e2e/node_modules')) {
  process.env.NODE_PATH = '/opt/ci/e2e/node_modules';
  Module._initPaths();
}

function resolvePuppeteer() {
  try {
    return require('puppeteer');
  } catch (e1) {
    try {
      return require('/opt/ci/e2e/node_modules/puppeteer');
    } catch (e2) {
      throw e1;
    }
  }
}

function resolveChrome() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) return process.env.PUPPETEER_EXECUTABLE_PATH;
  try {
    const bundled = resolvePuppeteer().executablePath();
    if (bundled && fs.existsSync(bundled)) return bundled;
  } catch (_) { /* not installed */ }
  for (const p of ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser']) {
    if (fs.existsSync(p)) return p;
  }
  return undefined;
}

function launchOpts(viewport) {
  return {
    headless: 'new',
    executablePath: resolveChrome(),
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--window-size=1280,900',
      '--lang=pt-BR',
    ],
    defaultViewport: viewport || { width: 1280, height: 900 },
  };
}

module.exports = { resolveChrome, launchOpts, resolvePuppeteer };
