/** Shared Chrome resolution for Puppeteer scripts. */
const fs = require('fs');

function resolveChrome() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) return process.env.PUPPETEER_EXECUTABLE_PATH;
  try {
    const bundled = require('puppeteer').executablePath();
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

module.exports = { resolveChrome, launchOpts };
