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

/**
 * Chrome flags for Flutter web (CanvasKit) under headless Puppeteer.
 *
 * Do NOT pass bare `--disable-gpu`: that leaves flt-glass-pane empty (no canvas /
 * first-frame) so captures are splash-only white. Prefer software GL (SwiftShader)
 * so CI and GPU-busy hosts still paint. Override with CHROME_GL=host|swiftshader|off.
 */
function flutterChromeArgs() {
  const gl = (process.env.CHROME_GL || 'swiftshader').toLowerCase();
  const base = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--window-size=1280,900',
    '--lang=pt-BR',
  ];
  if (gl === 'off' || gl === 'disable' || gl === 'disable-gpu') {
    // Explicit opt-out only (broken for CanvasKit product UI).
    return [...base, '--disable-gpu'];
  }
  if (gl === 'host' || gl === 'desktop') {
    return [
      ...base,
      '--enable-webgl',
      '--ignore-gpu-blocklist',
      '--enable-gpu-rasterization',
    ];
  }
  // Default: ANGLE + SwiftShader — works headless without host GPU.
  return [
    ...base,
    '--enable-webgl',
    '--ignore-gpu-blocklist',
    '--use-gl=angle',
    '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader',
  ];
}

function launchOpts(viewport) {
  return {
    headless: 'new',
    executablePath: resolveChrome(),
    protocolTimeout: Number(process.env.PUPPETEER_PROTOCOL_TIMEOUT_MS || 120000),
    args: flutterChromeArgs(),
    defaultViewport: viewport || { width: 1280, height: 900 },
  };
}

module.exports = { resolveChrome, launchOpts, resolvePuppeteer };
