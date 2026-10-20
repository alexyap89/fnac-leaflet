// Measure the SCREEN-SPACE extent of the visible anatomy, per step.
//
// fillY (the bounding box's span as a fraction of frame height) overstates how
// big a subject looks when the subject is tall and thin - the airway alone can
// span most of the frame while occupying very little of it. This projects the
// eight corners of each visible mesh into screen space and reports the box and
// its area, which is directly comparable to the judge's "frame %" reading.
const puppeteer = require('/home/alex/node_modules/puppeteer');

const ROLES = ['skin', 'skeletalmuscle', 'strap', 'thyroid', 'parathyroid',
               'airway', 'soft', 'probe', 'needle', 'dressing'];

(async () => {
  const b = await puppeteer.launch({
    headless: 'new',
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-gl=angle',
           '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
           '--disable-gpu-sandbox'],
    protocolTimeout: 600000,
  });
  const p = await b.newPage();
  await p.setViewport({ width: 1600, height: 1000 });
  await p.goto('http://127.0.0.1:8091/viewer.html?ar=' + Date.now(),
               { waitUntil: 'networkidle2', timeout: 90000 });
  await p.waitForFunction(
    'window.__dbg && document.getElementById("loading").hidden', { timeout: 90000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 6000));

  console.log('step  screenBox        area    meshes   dist');
  for (let i = 0; i < 11; i++) {
    await p.evaluate(idx => document.querySelectorAll('.step')[idx].click(), i);
    await new Promise(r => setTimeout(r, 2200));
    const s = await p.evaluate(roles => {
      const d = window.__dbg;
      const V = d.camera.position.constructor;
      const Box = d.focusBox('thyroid').constructor;
      const cv = document.querySelector('canvas');
      const w = cv.clientWidth, h = cv.clientHeight;
      let minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9, n = 0;
      roles.forEach(r => {
        (d.structures[r] || []).forEach(m => {
          if (!m.visible) return;
          const bb = new Box().setFromObject(m);
          if (bb.isEmpty()) return;
          const corners = [
            [bb.min.x, bb.min.y, bb.min.z], [bb.max.x, bb.min.y, bb.min.z],
            [bb.min.x, bb.max.y, bb.min.z], [bb.max.x, bb.max.y, bb.min.z],
            [bb.min.x, bb.min.y, bb.max.z], [bb.max.x, bb.min.y, bb.max.z],
            [bb.min.x, bb.max.y, bb.max.z], [bb.max.x, bb.max.y, bb.max.z],
          ];
          corners.forEach(c => {
            const v = new V(c[0], c[1], c[2]).project(d.camera);
            const sx = (v.x * 0.5 + 0.5) * w, sy = (-v.y * 0.5 + 0.5) * h;
            if (sx < minx) minx = sx; if (sy < miny) miny = sy;
            if (sx > maxx) maxx = sx; if (sy > maxy) maxy = sy;
          });
          n++;
        });
      });
      const bw = Math.max(0, maxx - minx), bh = Math.max(0, maxy - miny);
      return { n, bw: Math.round(bw / w * 100), bh: Math.round(bh / h * 100),
               area: Math.round((bw * bh) / (w * h) * 100),
               dist: +d.sph.dist.toFixed(3) };
    }, ROLES);
    console.log('  ' + String(i).padStart(2) + '   ' +
      (s.bw + '% x ' + s.bh + '%').padEnd(12) + '  ' +
      String(s.area + '%').padStart(5) + '   ' +
      String(s.n).padStart(5) + '   ' + String(s.dist).padStart(6));
  }
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
