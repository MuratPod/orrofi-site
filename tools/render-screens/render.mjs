#!/usr/bin/env node
/**
 * Render OrroFi prototype screens for the marketing site.
 * Screenshots #phone only (prototype chrome stays outside the crop).
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const OUT_DIR = join(ROOT, 'assets/screens');
const CONFIG_PATH = join(__dirname, 'frames.json');
const DRAWN_DIR = join(__dirname, 'drawn');

const cfg = JSON.parse(readFileSync(CONFIG_PATH, 'utf8'));
const ICON_URL =
  cfg.appIconUrl ||
  'https://muratpod.github.io/orrofi-preview/icons/ios/AppIcon-60.png';

/** Entry / redirect-only ids — use concrete screens instead (see frames.json). */
const REDIRECT_GUARD_IDS = new Set([
  'net-entry',
  'del-entry',
  'rst-entry',
  'net-00',
  'del-16a',
  'rst-sms',
]);

function mergeFlags(frameFlags = {}) {
  return { ...cfg.defaultFlags, ...frameFlags };
}

function buildIndexMd(results, skipped) {
  const ok = results.filter((r) => r.status === 'ok');
  const lines = [
    '# Кадры OrroFi (prototipo público)',
    '',
    'Автоматически снято с https://muratpod.github.io/orrofi-proto/ — idioma **es**, tema **Oscuro · HUD**, recorte `#phone` 430×932 @2x.',
    '',
    '| Archivo | ID pantalla | Función | Título (ES) | Descripción (RU) |',
    '| --- | --- | --- | --- | --- |',
  ];
  for (const r of ok) {
    const f = cfg.frames.find((x) => x.file === r.file);
    if (!f) continue;
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

async function layoutPhone(page) {
  await page.evaluate(() => {
    const ph = document.getElementById('phone');
    const pw = document.getElementById('pw');
    if (pw) {
      pw.style.width = '430px';
      pw.style.height = '932px';
      pw.style.margin = '0';
    }
    if (ph) {
      ph.style.transform = 'translateX(-50%) scale(1)';
      ph.style.position = 'relative';
      ph.style.left = '50%';
      ph.style.top = '0';
      ph.style.width = '430px';
      ph.style.height = '932px';
      ph.style.boxShadow = 'none';
      ph.style.borderRadius = '0';
    }
  });
}

async function applyState(page, flags) {
  await page.evaluate(
    ({ flags }) => {
      const KEY = 'orrofi-proto';
      const O = window.OrroProto;
      const st = {
        theme: 'dark',
        lang: 'es',
        flags: { ...window.OrroData.flags, ...flags },
      };
      localStorage.setItem(KEY, JSON.stringify(st));
      sessionStorage.removeItem('orrofi-proto-sess');
      if (O) {
        Object.assign(O.state, st);
        Object.assign(O.state.flags, st.flags);
        document.documentElement.setAttribute('data-theme', 'dark');
        document.documentElement.lang = 'es';
      }
    },
    { flags },
  );
}

async function protoGo(page, screenId, { blockNestedGo = false } = {}) {
  await page.evaluate(
    ({ screenId, blockNestedGo }) => {
      const O = window.OrroProto;
      if (!O?.listing) {
        O.go(screenId, true);
        return;
      }
      const screens = O.listing().screens;
      const def = screens[screenId];
      if (!blockNestedGo || !def?.render) {
        O.go(screenId, true);
        return;
      }
      const orig = def.render;
      def.render = function (ctx) {
        const child = { ...ctx, go() {} };
        return orig.call(this, child);
      };
      try {
        O.go(screenId, true);
      } finally {
        def.render = orig;
      }
    },
    { screenId, blockNestedGo: blockNestedGo || REDIRECT_GUARD_IDS.has(screenId) },
  );
}

async function runPreSetup(page, setup) {
  if (setup === 'rst-reset-faceid') {
    await protoGo(page, 'rst-17b');
    await page.waitForSelector('[data-screen="rst-17b"]', { timeout: 10000 });
    await page.locator('label.chk.c-opt input[type="radio"]').first().click({ force: true });
    await page.evaluate(() => {
      const radio = document.querySelector('label.chk.c-opt input[type="radio"]');
      if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event('change', { bubbles: true }));
        radio.dispatchEvent(new Event('input', { bubbles: true }));
      }
      document.querySelectorAll('.gate-btn, button[data-go="rst-17c"]').forEach((btn) => {
        btn.removeAttribute('disabled');
        btn.setAttribute('aria-disabled', 'false');
        btn.classList.remove('d');
      });
    });
    await page.waitForTimeout(100);
    await protoGo(page, 'rst-sh-bio-c');
    await page.waitForTimeout(200);
    return;
  }
  if (setup === 'net-8-wifi') {
    await protoGo(page, 'net-8');
    await page.waitForTimeout(150);
    const bio = page
      .locator('.sheet [data-b="bio-ok"], .sheet .btn')
      .filter({ hasText: 'Confirmar' });
    if (await bio.count()) {
      await bio.first().click();
      await page.waitForTimeout(200);
    }
    await protoGo(page, 'net-8');
    return;
  }
}

async function sanitizePlaceholders(page, mode) {
  const rules = cfg.placeholderSanitize;
  await page.evaluate(({ rules, mode }) => {
    const phone = document.getElementById('phone');
    if (!phone || !rules) return;

    phone.querySelectorAll(rules.legalBlockSelector || '.b-dp').forEach((el) => {
      const p = document.createElement('p');
      p.className = 'sec2';
      p.textContent = rules.legalBlockText;
      el.replaceChildren(p);
    });

    if (mode === 'orderMovil') {
      phone.querySelectorAll('.cd .sec2').forEach((p) => {
        if (/Responsable|\[DIRECCIÓN\]|\[EMAIL\]|\[TELÉFONO\]|Reclamaciones:/i.test(p.textContent)) {
          p.style.display = 'none';
        }
      });
      const orderMap = rules.orderMovilReplacements || {};
      const walker = document.createTreeWalker(phone, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      for (const node of nodes) {
        let t = node.textContent;
        Object.keys(orderMap)
          .sort((a, b) => b.length - a.length)
          .forEach((k) => {
            t = t.split(k).join(orderMap[k]);
          });
        t = t.replace(/\[[^\]]+\]/g, (m) => orderMap[m] || '');
        node.textContent = t;
      }
      return;
    }

    const exact = rules.exactReplacements || {};
    const fallback = rules.defaultBracketReplacement || 'Ver condiciones';
    const bracketRe = /\[[^\]]+\]/g;

    function replaceBrackets(text) {
      let out = text;
      Object.keys(exact)
        .sort((a, b) => b.length - a.length)
        .forEach((key) => {
          out = out.split(key).join(exact[key]);
        });
      out = out.replace(bracketRe, (m) => exact[m] || fallback);
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
  }, { rules, mode });
}

async function prepareMarketingShot(page, frame) {
  await page.evaluate(
    ({ frame, iconUrl }) => {
      const phone = document.getElementById('phone');
      if (!phone) return;

      phone.querySelectorAll('.c-demos').forEach((e) => e.remove());

      phone.querySelectorAll('.cap').forEach((cap) => {
        if (cap.textContent.trim() === 'DEMO') {
          const chips = cap.nextElementSibling;
          if (chips && chips.classList.contains('chips')) chips.remove();
          cap.remove();
        }
      });

      phone.querySelectorAll('.chips').forEach((chips) => {
        if (/DEMO/i.test(chips.textContent)) chips.remove();
      });

      phone.querySelectorAll('button.chip, .chip').forEach((chip) => {
        if (/DEMO/i.test(chip.textContent)) chip.remove();
      });

      const reProv = /Provisional · lema sin decidir/i;
      phone.querySelectorAll('.pill, .cap, p, span, h1, h2, h3').forEach((el) => {
        if (reProv.test(el.textContent) && el.textContent.trim().length < 80) el.remove();
      });
      phone.querySelectorAll('div').forEach((el) => {
        if (el.closest('.sheet') || el.querySelector('.sheet, .sc, .lockwrap')) return;
        const t = el.textContent.trim();
        if (t === 'Provisional · lema sin decidir' || (reProv.test(t) && t.length < 60)) el.remove();
      });

      phone.querySelectorAll('.dis').forEach((d) => {
        if (/\[RESPONSABLE\]|\[EMAIL PRIVACIDAD\]|Responsable:\s*\[/i.test(d.textContent)) {
          d.textContent = 'Consulta nuestra política de privacidad en la app.';
        }
      });

      if (frame.screenId === 'sh-export' || frame.hideResponsable) {
        phone.querySelectorAll('.dis, .sec2, p, .foot, .legal').forEach((el) => {
          if (/Responsable:|responsable del tratamiento/i.test(el.textContent)) {
            el.style.display = 'none';
          }
        });
      }

      phone.querySelectorAll('.pushc .pi').forEach((pi) => {
        pi.textContent = '';
        pi.style.display = 'grid';
        pi.style.placeItems = 'center';
        pi.style.background = `center/cover no-repeat url(${iconUrl})`;
        pi.style.color = 'transparent';
        pi.style.fontSize = '0';
        pi.style.lineHeight = '0';
        pi.style.overflow = 'hidden';
      });

      if (frame.hideTabs) {
        phone.querySelectorAll('.tabs').forEach((t) => (t.style.display = 'none'));
      }

      const sc = phone.querySelector('.sc:not([aria-hidden="true"])');
      if (sc) {
        if (typeof frame.scrollY === 'number') sc.scrollTop = frame.scrollY;
        else if (frame.screenId === 'order-movil') sc.scrollTop = 0;
      }
    },
    { frame, iconUrl: ICON_URL },
  );

  await page.evaluate(async (iconUrl) => {
    const imgs = [...document.querySelectorAll('#phone .pushc .pi')];
    await Promise.all(
      imgs.map(
        () =>
          new Promise((resolve) => {
            const img = new Image();
            img.onload = () => resolve();
            img.onerror = () => resolve();
            img.src = iconUrl;
          }),
      ),
    );
  }, ICON_URL);
}

function collectVisibleText(page) {
  return page.evaluate(() => {
    const phone = document.getElementById('phone');
    if (!phone) return '';
    const sheet = phone.querySelector('.sheet:not([hidden])');
    if (sheet && sheet.getAttribute('aria-hidden') !== 'true') {
      const t = sheet.innerText?.trim();
      if (t) return t;
    }
    const lock = phone.querySelector('.lockwrap');
    if (lock && lock.offsetParent !== null) return lock.innerText;
    const sc = phone.querySelector('.sc:not([aria-hidden="true"])');
    return (sc && sc.innerText) || phone.innerText || '';
  });
}

async function bootPrototype(page) {
  await page.goto(cfg.prototypeUrl, { waitUntil: 'networkidle' });
  await page.waitForFunction(
    () => window.OrroProto && window.OrroProto.listing && window.OrroData,
    { timeout: 30000 },
  );
  await layoutPhone(page);
}

async function renderProtoFrame(page, frame) {
  const flags = mergeFlags(frame.flags);
  await applyState(page, flags);
  await layoutPhone(page);

  for (const act of frame.preActions || []) {
    if (act.setup) await runPreSetup(page, act.setup);
  }

  const skipFinalGo = (frame.preActions || []).some(
    (a) =>
      (a.setup === 'rst-reset-faceid' && frame.screenId === 'rst-sh-bio-c') ||
      (a.setup === 'net-8-wifi' && frame.screenId === 'net-8'),
  );
  if (!skipFinalGo) await protoGo(page, frame.screenId);

  await page
    .waitForSelector(`#phone [data-screen="${frame.screenId}"], #phone .sheet:not([hidden])`, {
      timeout: 12000,
    })
    .catch(() => {});

  if (frame.sanitizePlaceholders) {
    const mode = frame.sanitizePlaceholders === true ? 'default' : frame.sanitizePlaceholders;
    await sanitizePlaceholders(page, mode);
  }

  const waitMs = frame.waitMs ?? 350;
  if (waitMs > 0) await page.waitForTimeout(waitMs);

  await prepareMarketingShot(page, frame);

  const text = await collectVisibleText(page);

  const badUi = [/Oscuro/i, /Claro · Tech/i, /\bMapa\b/, /DEMO/, /\[[^\]]+\]/, /Provisional · lema/i];
  for (const re of badUi) {
    if (re.test(text)) {
      return { status: 'blocked', reason: `UI marketing: ${re}` };
    }
  }
  for (const pat of cfg.forbiddenPatterns) {
    if (new RegExp(pat, 'i').test(text)) {
      return { status: 'blocked', reason: `Texto prohibido: /${pat}/` };
    }
  }
  if (!text.trim()) return { status: 'empty', reason: 'Pantalla en blanco' };

  const phone = page.locator('#phone');
  const outPath = join(OUT_DIR, frame.file);
  await phone.screenshot({ path: outPath, type: 'png', animations: 'disabled' });
  return { status: 'ok', file: frame.file, screenId: frame.screenId };
}

async function renderDrawnFrame(page, frame) {
  const htmlPath = join(DRAWN_DIR, frame.drawnHtml);
  const url = pathToFileURL(htmlPath).href;
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(200);
  const phone = page.locator('#phone');
  const outPath = join(OUT_DIR, frame.file);
  await phone.screenshot({ path: outPath, type: 'png', animations: 'disabled' });
  return { status: 'ok', file: frame.file, screenId: frame.screenId || 'drawn' };
}

async function renderOne(page, frame, protoReady) {
  if (frame.drawnHtml) return renderDrawnFrame(page, frame);
  if (!protoReady) {
    await bootPrototype(page);
    protoReady = true;
  }
  return renderProtoFrame(page, frame);
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: cfg.viewport,
    deviceScaleFactor: cfg.deviceScaleFactor,
    locale: 'es-ES',
  });
  await context.addInitScript(() => {
    localStorage.setItem('orrofi-proto', JSON.stringify({ theme: 'dark', lang: 'es' }));
    sessionStorage.removeItem('orrofi-proto-sess');
  });
  const page = await context.newPage();
  let protoReady = false;

  const results = [];
  for (const frame of cfg.frames) {
    process.stdout.write(`Rendering ${frame.screenId || frame.drawnHtml} -> ${frame.file} ... `);
    try {
      if (frame.drawnHtml) {
        const r = await renderDrawnFrame(page, frame);
        results.push({ ...r, file: frame.file, screenId: frame.screenId });
        console.log(r.status);
      } else {
        if (!protoReady) {
          await bootPrototype(page);
          protoReady = true;
        }
        const r = await renderProtoFrame(page, frame);
        results.push({ ...r, file: frame.file, screenId: frame.screenId });
        console.log(r.status);
      }
    } catch (err) {
      console.log('error', err.message);
      results.push({
        status: 'error',
        file: frame.file,
        screenId: frame.screenId,
        reason: err.message,
      });
    }
  }

  await browser.close();
  const skipped = [...(cfg.skipped || [])];
  writeFileSync(join(OUT_DIR, 'index.md'), buildIndexMd(results, skipped));
  writeFileSync(
    join(__dirname, 'last-run.json'),
    JSON.stringify({ results, at: new Date().toISOString() }, null, 2),
  );

  const failed = results.filter((r) => r.status !== 'ok');
  if (failed.length) {
    console.error(`${failed.length} frame(s) failed`);
    process.exitCode = 1;
  } else {
    console.log(`OK: ${results.length} PNGs`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});