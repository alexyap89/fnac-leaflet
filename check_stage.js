// Smoke-test the STAGED upload copy (served from /tmp/fnac_upload on :8093).
// Catches missing runtime files before anything is uploaded: a viewer that 404s
// on three.min.js or a GLB would look fine in the local build and break in Drive.
const puppeteer = require('/home/alex/node_modules/puppeteer');

(async () => {
  const b = await puppeteer.launch({
    headless: 'new',
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-gl=angle',
           '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
           '--disable-gpu-sandbox'],
    protocolTimeout: 300000,
  });
  const p = await b.newPage();
  const fails = [];
  p.on('requestfailed', r => fails.push('FAILED ' + r.url().split('/').pop()));
  p.on('response', r => {
    if (r.status() >= 400) fails.push(r.status() + ' ' + r.url().split('/').pop());
  });
  await p.setViewport({ width: 1600, height: 1000 });
  await p.goto('http://127.0.0.1:8093/viewer.html?chk=1',
               { waitUntil: 'networkidle2', timeout: 60000 });
  await p.waitForFunction(
    'window.__dbg && document.getElementById("loading").hidden',
    { timeout: 60000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 4000));

  const st = await p.evaluate(() => {
    const d = window.__dbg;
    return {
      loaded: !!d,
      steps: document.querySelectorAll('.step').length,
      canvas: !!document.querySelector('canvas'),
      dist: d ? +d.sph.dist.toFixed(3) : null,
    };
  });

  console.log('staged copy loads :', st.loaded);
  console.log('steps present     :', st.steps);
  console.log('canvas present    :', st.canvas);
  console.log('camera distance   :', st.dist);
  console.log('failed requests   :', fails.length ? fails.join(', ') : 'none');
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
