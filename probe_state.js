// Probe the viewer's live state with Puppeteer. The Hermes browser daemon wedges
// after ~2 CDP calls on this page, so state probes go through Chrome directly.
//
// Prints, for every step: how many meshes each role has visible, the camera, and
// what applyStep decided. That distinguishes "want[] is wrong" from
// "refreshVisibility is not reached" from "the meshes are not in that role".
const puppeteer = require('/home/alex/node_modules/puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-gl=swiftshader',
           '--enable-unsafe-swiftshader', '--window-size=1600,1000'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000 });
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  await page.goto('http://127.0.0.1:8091/viewer.html?probe=' + Date.now(),
                  { waitUntil: 'networkidle2', timeout: 90000 });
  await page.waitForFunction(
    'window.__dbg && document.getElementById("loading") && document.getElementById("loading").hidden',
    { timeout: 90000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 2500));

  const roles = ['room', 'patient', 'clinician', 'skin', 'thyroid', 'airway', 'nodule', 'dressing', 'probe', 'needle', 'soft'];
  console.log('step  ' + roles.map(r => r.slice(0, 4).padStart(5)).join('') + '   dist    theta  phi    note');
  for (let i = 0; i < 11; i++) {
    await page.evaluate(idx => {
      const r = document.querySelectorAll('.step');
      if (r[idx]) r[idx].click();
    }, i);
    await new Promise(r => setTimeout(r, 1600));
    const s = await page.evaluate(rs => {
      const d = window.__dbg;
      const vis = {};
      rs.forEach(r => {
        const l = (d.structures[r] || []);
        vis[r] = l.length ? (l.filter(m => m.visible).length + '/' + l.length) : '-';
      });
      // is the first room mesh reachable from root, or parented to the scene?
      const rm = (d.structures.room || [])[0];
      let chain = [];
      let p = rm;
      while (p) { chain.push(p.name || p.type); p = p.parent; }
      return { vis, sph: { t: +d.sph.theta.toFixed(2), p: +d.sph.phi.toFixed(2), d: +d.sph.dist.toFixed(4) },
               chain: chain.slice(0, 3).join('<'), };
    }, roles);
    console.log('  ' + String(i).padStart(2) + '  ' +
      roles.map(r => String(s.vis[r]).padStart(5)).join('') +
      '   ' + String(s.sph.d).padStart(7) + '  ' + String(s.sph.t).padStart(4) +
      '  ' + String(s.sph.p).padStart(4) + '   ' + s.chain);
  }
  console.log(errs.length ? '\nERRORS: ' + errs.slice(0, 5).join(' | ') : '\nno page errors');
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
