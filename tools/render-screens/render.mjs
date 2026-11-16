#!/usr/bin/env node
/**
 * Render OrroFi prototype screens for the marketing site.
 * Usage: npm run render   (from tools/render-screens)
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const OUT_DIR = join(ROOT, 'assets/screens');
const CONFIG_PATH = join(__dirname, 'frames.json');

const HIDE_CHROME_CSS = `
  .top, .mapbtn { display: none !important; }
  html, body { overflow: hidden !important; background: #13254A !important; }
  .stage { position: fixed !important; inset: 0 !important; top: 0 !important; display: flex !important;
    align-items: center !important; justify-content: center !important; margin: 0 !important; }
  .pw { width: 430px !important; height: 932px !important; margin: 0 !important; }
  #phone.phone {
    position: relative !important; left: 0 !important; top: 0 !important;
    width: 430px !important; height: 932px !important;
    transform: none !important; transform-origin: unset !important;
    box-shadow: none !important; border-radius: 0 !important;
  }
  .toast { display: none !important; }
`;

const cfg = JSON.parse(readFileSync(CONFIG_PATH, 'utf8'));

function mergeFlags(frameFlags = {}) {
  return { ...cfg.defaultFlags, ...frameFlags };
}

function buildIndexMd(results, skipped) {
  const ok = results.filter((r) => r.status === 'ok');
  const lines = [
    '# Кадры OrroFi (prototipo público)',
    '',
    'Автоматически снято с https://muratpod.github.io/orrofi-proto/ — idioma **es**, tema **Oscuro · HUD**, viewport 430×932 @2x.',
    '',
    '| Archivo | ID pantalla | Función | Título (ES) | Descripción (RU) |',
    '| --- | --- | --- | --- | --- |',
  ];
  for (const r of ok) {
    const f = cfg.frames.find((x) => x.file === r.file);
    lines.push(
      `| \`${r.file}\` | \`${f.screenId}\` | ${f.function} | ${f.titleEs} | ${f.descRu} |`,
    );
  }
  lines.push('', '## No incluidos en assets', '');
  for (const s of skipped) {
    lines.push(`- **${s.screenId}** (${s.function}): ${s.reason}`);
  }
  const failed = results.filter((r) => r.status !== 'ok');
  if (failed.length) {
    lines.push('', '## Fallos de render', '');
    for (const r of failed) {
      lines.push(`- **${r.file}** (\`${r.screenId}\`): ${r.reason}`);
    }
  }
  return lines.join('\n') + '\n';
}

async function sanitizePlaceholders(page, rules) {
  await page.evaluate((rules) => {
    const phone = document.getElementById('phone');
    if (!phone || !rules) return;

    phone.querySelectorAll(rules.legalBlockSelector || '.b-dp').forEach((el) => {
      const p = document.createElement('p');
      p.className = 'sec2';
      p.textContent = rules.legalBlockText;
      el.replaceChildren(p);
    });

    const exact = rules.exactReplacements || {};
    const fallback = rules.defaultBracketReplacement || 'Ver condiciones';
    const bracketRe = /\[[^\]]+\]/g;

    function replaceBrackets(text) {
      let out = text;
      const keys = Object.keys(exact).sort((a, b) => b.length - a.length);
      for (const key of keys) {
        out = out.split(key).join(exact[key]);
      }
      out = out.replace(bracketRe, (m) => exact[m] || fallback);
      out = out.replace(/(?:Ver condiciones)(?:\s*·\s*Ver condiciones)+/g, 'Consulta los detalles en la app.');
      out = out.replace(/\s*·\s*·\s*/g, ' · ');
      out = out.replace(/\s{2,}/g, ' ');
      return out.trim();
    }

    const walker = document.createTreeWalker(phone, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      if (bracketRe.test(node.textContent)) {
        node.textContent = replaceBrackets(node.textContent);
      }
    }

    let rounds = 0;
    while (rounds < 3 && /\[[^\]]+\]/.test(phone.innerText)) {
      for (const node of nodes) {
        if (bracketRe.test(node.textContent)) {
          node.textContent = replaceBrackets(node.textContent);
        }
      }
      rounds++;
    }
  }, rules);
}

async function applyState(page, flags, theme, lang) {
  await page.evaluate(
    ({ flags, theme, lang }) => {
      const KEY = 'orrofi-proto';
      const st = { theme, lang, flags: { ...window.OrroData.flags, ...flags } };
      localStorage.setItem(KEY, JSON.stringify(st));
      if (window.OrroProto) {
        Object.assign(window.OrroProto.state, st);
        Object.assign(window.OrroProto.state.flags, st.flags);
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.lang = lang;
      }
    },
    { flags, theme: 'dark', lang: 'es' },
  );
}

async function renderOne(page, frame) {
  const flags = mergeFlags(frame.flags);
  await page.goto(cfg.prototypeUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.OrroProto && window.OrroData, { timeout: 30000 });
  await applyState(page, flags, 'dark', 'es');

  await page.evaluate((id) => {
    window.OrroProto.go(id, true);
  }, frame.screenId);

  await page.waitForSelector(`[data-screen="${frame.screenId}"]`, { timeout: 15000 }).catch(() => {});

  if (frame.preActions) {
    for (const act of frame.preActions) {
      if (act.click) await page.click(act.click);
    }
  }

  if (frame.sanitizePlaceholders) {
    await sanitizePlaceholders(page, cfg.placeholderSanitize);
  }

  const waitMs = frame.waitMs ?? 350;
  if (waitMs > 0) await page.waitForTimeout(waitMs);

  await page.evaluate(() => {
    const st = document.querySelector('.stage');
    if (st) {
      st.style.cssText =
        'position:fixed!important;inset:0!important;top:0!important;display:flex!important;align-items:center!important;justify-content:center!important;overflow:hidden!important;';
    }
    const pw = document.getElementById('pw');
    const ph = document.getElementById('phone');
    if (pw) {
      pw.style.cssText = 'width:430px!important;height:932px!important;margin:0!important;position:relative!important;';
    }
    if (ph) {
      ph.style.cssText =
        'position:relative!important;left:0!important;top:0!important;width:430px!important;height:932px!important;transform:none!important;transform-origin:top center!important;box-shadow:none!important;border-radius:0!important;';
    }
  });

  const phone = page.locator('#phone');
  await phone.waitFor({ state: 'visible', timeout: 10000 });

  const text = await page.evaluate(() => {
    const sheet = document.querySelector('.sheet[role="dialog"]');
    if (sheet && !sheet.hidden) return sheet.innerText;
    const lock = document.querySelector('.lockwrap');
    if (lock) return lock.innerText;
    const active = document.querySelector('.sc:not([aria-hidden="true"]) .in');
  const sc = active || document.querySelector('.sc:not([aria-hidden="true"])') || document.querySelector('#phone .sc');
    return (sc && sc.innerText) || document.getElementById('phone').innerText;
  });
  if (frame.sanitizePlaceholders && /\[[^\]]+\]/.test(text)) {
    return { status: 'blocked', reason: 'Quedan marcadores [...] tras sanitizar' };
  }
  for (const pat of cfg.forbiddenPatterns) {
    const re = new RegExp(pat, 'i');
    if (re.test(text)) {
      return { status: 'blocked', reason: `Texto prohibido: /${pat}/` };
    }
  }
  if (!text.trim()) {
    return { status: 'empty', reason: 'Pantalla en blanco' };
  }
  if (!/OrroFi|Código|Mi |Servicios|Fibra|Factura|Tickets|Wi|red|SMS|gestor|Perfil|Instalación|Borrar|Restablecer|Familia|Móvil|Radio|Entrar|Avisos|Solicitud|Cliente|Introduce|Descargar|Privacidad|Face ID|Cerrar|Contratar|Tarifa|Línea|Nombre|Teléfono|política/i.test(text)) {
    return { status: 'suspicious', reason: 'No se detectó texto UI esperado en español' };
  }

  const outPath = join(OUT_DIR, frame.file);
  await phone.screenshot({ path: outPath, type: 'png', animations: 'disabled' });

  const { execSync } = await import('node:child_process');
  let dims = '';
  try {
    dims = execSync(`file "${outPath}"`, { encoding: 'utf8' });
  } catch {
    /* ignore */
  }
  if (dims && !dims.includes('860 x 1864')) {
    return {
      status: 'size',
      reason: `PNG no es 860×1864: ${dims.trim()}`,
      file: frame.file,
    };
  }

  return { status: 'ok', file: frame.file, screenId: frame.screenId };
}

async function optimizePngs(files) {
  try {
    const { execSync } = await import('node:child_process');
    if (execSync('which oxipng', { encoding: 'utf8' }).trim()) {
      for (const f of files) {
        execSync(`oxipng -o2 -q "${join(OUT_DIR, f)}"`, { stdio: 'ignore' });
      }
      return 'oxipng';
    }
  } catch {
    /* optional */
  }
  return null;
}

async function main() {
  const checkOnly = process.argv.includes('--check-only');
  mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: cfg.viewport,
    deviceScaleFactor: cfg.deviceScaleFactor,
    locale: 'es-ES',
  });
  await context.addInitScript(() => {
    const style = document.createElement('style');
    style.textContent = HIDE_CHROME_CSS;
    document.documentElement.appendChild(style);
  });
  const page = await context.newPage();
  await page.addStyleTag({ content: HIDE_CHROME_CSS });

  const results = [];
  for (const frame of cfg.frames) {
    if (checkOnly) continue;
    process.stdout.write(`Rendering ${frame.screenId} -> ${frame.file} ... `);
    try {
      const r = await renderOne(page, frame);
      results.push({ ...r, file: frame.file, screenId: frame.screenId });
      console.log(r.status);
    } catch (err) {
      console.log('error');
      results.push({ status: 'error', file: frame.file, screenId: frame.screenId, reason: err.message });
    }
  }

  await browser.close();

  const skipped = [...cfg.skipped];
  for (const r of results) {
    if (r.status !== 'ok') {
      skipped.push({ screenId: r.screenId, function: cfg.frames.find((f) => f.file === r.file)?.function ?? '?', reason: r.reason });
    }
  }

  const indexPath = join(OUT_DIR, 'index.md');
  writeFileSync(indexPath, buildIndexMd(results, skipped));

  const okFiles = results.filter((r) => r.status === 'ok').map((r) => r.file);
  const opt = await optimizePngs(okFiles);
  if (opt) console.log(`Optimized PNGs with ${opt}`);

  const reportPath = join(__dirname, 'last-run.json');
  writeFileSync(reportPath, JSON.stringify({ results, skipped, at: new Date().toISOString() }, null, 2));

  const failed = results.filter((r) => r.status !== 'ok');
  if (failed.length) {
    console.error(`${failed.length} frame(s) failed or blocked`);
    process.exitCode = 1;
  } else {
    console.log(`OK: ${okFiles.length} PNGs in ${OUT_DIR}`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});