// Capture every step of the FNAC viewer with Puppeteer.
//
// The Hermes browser daemon wedges after ~2 CDP calls on this heavy page, which
// is why per-step loops kept dying halfway. Driving Chrome directly from Node
// gives one process, one page, all steps - and it can read live state
// (sph.dist, box sizes) alongside each screenshot, so the images and the
// numbers in the report come from the same instant.
//
// Usage:  node capture_steps.js [outDir]
const puppeteer = require('/home/alex/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');

const URL = 'http://127.0.0.1:8091/viewer.html?cap=' + Date.now();
const OUT = process.argv[2] || '/home/alex/Documents/FNAC_Webapp/shots';

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-gl=swiftshader',
           '--enable-unsafe-swiftshader', '--window-size=1600,1000'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 1 });
  const errs = [];
  page.on('pageerror', e => errs.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 160)); });

  await page.goto(URL, { waitUntil: 'networkidle2', timeout: 90000 });
  // wait for the model to finish loading: __dbg appears once setupInstruments ran
  await page.waitForFunction('window.__dbg && document.getElementById("loading") && document.getElementById("loading").hidden',
                             { timeout: 90000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 3000));

  const rows = [];
  for (let i = 0; i < 11; i++) {
    await page.evaluate((idx) => {
      const r = document.querySelectorAll('.step');
      if (r[idx]) r[idx].click();
    }, i);
    await new Promise(r => setTimeout(r, 2000));

    const state = await page.evaluate(() => {
      const d = window.__dbg;
      if (!d) return { err: 'no __dbg' };
      const s = d.sph;
      const V = d.camera.position.constructor;
      let boxCm = null;
      try {
        const b = d.focusBox('all');
        const sz = b.getSize(new V());
        boxCm = [+(sz.x).toFixed(3), +(sz.y).toFixed(3), +(sz.z).toFixed(3)];
      } catch (e) {}
      return { theta: +s.theta.toFixed(3), phi: +s.phi.toFixed(3), dist: +s.dist.toFixed(4),
               allBox: boxCm,
               diagShown: (() => { const e = document.getElementById('roomfig');
                                   return e ? !e.hidden : null; })(),
               photoShown: (() => { const e = document.getElementById('roomphoto');
                                    return e ? !e.hidden : null; })(),
               canvasHidden: (() => { const c = document.querySelector('canvas');
                                      return c ? c.style.visibility === 'hidden' : null; })() };
    });
    const file = path.join(OUT, 'step' + String(i).padStart(2, '0') + '.png');
    await page.screenshot({ path: file });
    rows.push(Object.assign({ step: i, file, bytes: fs.statSync(file).size }, state));
    console.log('  step' + String(i).padStart(2, '0') +
                '  dist=' + (state.dist ?? '?') +
                '  theta=' + (state.theta ?? '?') + '  phi=' + (state.phi ?? '?') +
                '  photo=' + (state.photoShown ? 'Y' : '-') +
                '  diag=' + (state.diagShown ? 'Y' : '-') +
                '  canvasHidden=' + (state.canvasHidden ? 'Y' : '-') +
                '  ' + fs.statSync(file).size + 'B');
  }

  fs.writeFileSync(path.join(OUT, 'capture_report.json'),
                   JSON.stringify({ url: URL, rows, errors: errs.slice(0, 20) }, null, 1));
  if (errs.length) {
    console.log('\nPAGE ERRORS (' + errs.length + '):');
    errs.slice(0, 8).forEach(e => console.log('  ' + e));
  } else {
    console.log('\nno page errors');
  }
  console.log('report -> ' + path.join(OUT, 'capture_report.json'));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
