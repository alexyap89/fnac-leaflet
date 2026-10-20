#!/usr/bin/env /usr/bin/python3
"""FNAC webapp v4 builder — three.js scene, inlined for full offline use."""
import os

BASE = "/home/alex/Documents/FNAC_Webapp"
three = open("/tmp/three_test.js").read()
scene3 = open(os.path.join(BASE, "scene3.js")).read()

# ---- reuse the v3 shell, swapping the renderer + scene ----------------------
shell = open(os.path.join(BASE, "build3.py")).read()
start = shell.index('SHELL = r"""') + len('SHELL = r"""')
end = shell.index('"""\n\nhtml = SHELL')
SHELL = shell[start:end]

RENDERER = r"""
/* ================================================================ RENDERER == */
(function(){
  const canvas = document.getElementById('gl');
  const label  = document.getElementById('stepLabel');
  const note   = document.getElementById('stepNote');
  const chips  = document.getElementById('steps');
  const btnPlay= document.getElementById('btnPlay');
  const srText = document.getElementById('srText');

  const STEPS = [
    {t:"Getting into position",
     n:"You lie on your back with your head tipped gently back, so your neck is extended. Sometimes a pillow goes under your shoulders. This brings the thyroid closer to the surface and makes it easier to reach.",
     a:{tilt:1, probeOn:0.15, needleOut:1, markerIn:0, anaes:0, needleIn:0, passes:0, dressing:0, beam:0}},
    {t:"Ultrasound first",
     n:"The doctor scans your neck to find the thyroid gland and the exact nodule. Blood vessels along the needle path are checked so they can be avoided.",
     a:{tilt:1, probeOn:1, needleOut:1, markerIn:0, anaes:0, needleIn:0, passes:0, dressing:0, beam:0.55}},
    {t:"Marking the entry point",
     n:"The skin where the needle will go in may be marked with a pen, so it enters at the planned spot.",
     a:{tilt:1, probeOn:0.85, needleOut:1, markerIn:1, anaes:0, needleIn:0, passes:0, dressing:0, beam:0.75}},
    {t:"Local anaesthetic, if needed",
     n:"You may be given a local anaesthetic injection to numb the injection site. Many people do not need one — your doctor will decide with you.",
     a:{tilt:1, probeOn:1, needleOut:1, markerIn:1, anaes:1, needleIn:0, passes:0, dressing:0, beam:0.5}},
    {t:"The needle goes in",
     n:"A very fine needle — finer than the one used for a blood test — passes through the skin and into the nodule, guided live by the ultrasound image on the screen.",
     a:{tilt:1, probeOn:1, needleOut:0, markerIn:1, anaes:1, needleIn:1, passes:0, dressing:0, beam:0.9}},
    {t:"Several passes",
     n:"The needle moves gently back and forth inside the nodule for a few seconds to collect cells. The needle may be inserted more than once — this is called making several passes — to gather enough cells for a reliable result.",
     a:{tilt:1, probeOn:1, needleOut:0, markerIn:1, anaes:1, needleIn:1, passes:1, dressing:0, beam:0.9}},
    {t:"The sample goes to the laboratory",
     n:"The cells collected are sent to the laboratory, where a pathologist examines them under a microscope. A dressing is placed over the puncture site.",
     a:{tilt:1, probeOn:0.5, needleOut:1, markerIn:1, anaes:0, needleIn:0, passes:0, dressing:1, beam:0.25}}
  ];

  let cur = 0, playing = false, timer = null;

  STEPS.forEach((s,i)=>{
    const b = document.createElement('button');
    b.className='stepchip'; b.setAttribute('role','tab');
    b.textContent=(i+1)+'. '+s.t;
    b.onclick=()=>{ stopPlay(); setStep(i); };
    chips.appendChild(b);
  });

  const A = {tilt:0, probeOn:0, needleOut:1, markerIn:0, anaes:0, needleIn:0,
             passes:0, dressing:0, beam:0};
  const TGT = Object.assign({}, A);

  function setStep(i){
    cur=i; const s=STEPS[i];
    label.innerHTML='<b>Step '+(i+1)+' of '+STEPS.length+'.</b> '+s.t;
    note.textContent=s.n;
    srText.textContent='Step '+(i+1)+' of '+STEPS.length+'. '+s.t+'. '+s.n;
    [...chips.children].forEach((c,j)=>c.setAttribute('aria-current', String(j===i)));
    for (const k of Object.keys(TGT)) TGT[k] = (s.a[k]!==undefined)? s.a[k] : 0;
  }
  function stopPlay(){ playing=false; clearInterval(timer); btnPlay.textContent='▶ Play'; }
  btnPlay.onclick=()=>{
    if (playing){ stopPlay(); return; }
    playing=true; btnPlay.textContent='⏸ Pause';
    timer=setInterval(()=>{ if(cur>=STEPS.length-1){ stopPlay(); return; } setStep(cur+1); }, 4800);
  };

  /* ------------------------------------------------------------ UI prefs -- */
  const html=document.documentElement;
  const SIZES=['normal','large','xl']; let sizeIdx=0;
  document.getElementById('btnSize').onclick=(e)=>{
    sizeIdx=(sizeIdx+1)%SIZES.length; const v=SIZES[sizeIdx];
    if(v==='normal') html.removeAttribute('data-size'); else html.setAttribute('data-size',v);
    e.currentTarget.setAttribute('aria-pressed',String(v!=='normal'));
    e.currentTarget.textContent = v==='normal'?'Larger text'
      :(v==='large'?'Largest text':'Reset text size');
  };
  document.getElementById('btnContrast').onclick=(e)=>{
    const on=html.getAttribute('data-contrast')==='high';
    if(on) html.removeAttribute('data-contrast'); else html.setAttribute('data-contrast','high');
    e.currentTarget.setAttribute('aria-pressed',String(!on));
  };
  document.getElementById('btnPrint').onclick=()=>window.print();

  /* ------------------------------------------------------------- three.js - */
  const T = buildThreeScene(THREE);
  const scene = T.scene, neck = T.neck, P = T.parts;

  const renderer = new THREE.WebGLRenderer({canvas:canvas, antialias:true,
                                            alpha:true, preserveDrawingBuffer:true});
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace !== undefined
    ? THREE.SRGBColorSpace : renderer.outputColorSpace;

  const camera = new THREE.PerspectiveCamera(42, 1.6, 0.1, 100);

  /* -------------------------------------------------------------- controls */
  let yaw=-0.62, pitch=0.26, dist=6.2, autoRotate=true;
  let drag=false, lx=0, ly=0, pid=null;

  canvas.addEventListener('pointerdown', e=>{
    drag=true; autoRotate=false; pid=e.pointerId; lx=e.clientX; ly=e.clientY;
    if(canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointerup', ()=>{
    drag=false;
    if(canvas.releasePointerCapture && pid!==null){
      try{ canvas.releasePointerCapture(pid); }catch(_){}
    }
    pid=null;
  });
  canvas.addEventListener('pointercancel', ()=>{ drag=false; pid=null; });
  canvas.addEventListener('pointermove', e=>{
    if(!drag) return;
    yaw += (e.clientX-lx)*0.008;
    pitch = Math.max(-0.6, Math.min(1.15, pitch + (e.clientY-ly)*0.006));
    lx=e.clientX; ly=e.clientY;
  });
  canvas.addEventListener('wheel', e=>{
    e.preventDefault();
    dist = Math.max(3.0, Math.min(12, dist + e.deltaY*0.004));
    autoRotate=false;
  }, {passive:false});
  canvas.addEventListener('keydown', e=>{
    const k=e.key;
    if(k==='ArrowLeft'){ yaw-=0.12; autoRotate=false; e.preventDefault(); }
    else if(k==='ArrowRight'){ yaw+=0.12; autoRotate=false; e.preventDefault(); }
    else if(k==='ArrowUp'){ pitch=Math.max(-0.6,pitch-0.08); autoRotate=false; e.preventDefault(); }
    else if(k==='ArrowDown'){ pitch=Math.min(1.15,pitch+0.08); autoRotate=false; e.preventDefault(); }
    else if(k==='+'||k==='='){ dist=Math.max(3.0,dist-0.5); e.preventDefault(); }
    else if(k==='-'||k==='_'){ dist=Math.min(12,dist+0.5); e.preventDefault(); }
  });

  function resize(){
    const dpr=Math.min(window.devicePixelRatio||1, 2);
    const r=canvas.getBoundingClientRect();
    const w=Math.max(2, Math.round(r.width)), h=Math.max(2, Math.round(r.height));
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    camera.aspect = w/h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  /* ------------------------------------------------------------- render loop */
  let t0=performance.now(), lastRaf=performance.now(), watchdogOn=false;

  function step(now){
    const dt=Math.min(0.05,(now-t0)/1000); t0=now;
    for(const k of Object.keys(TGT)) A[k]+=(TGT[k]-A[k])*Math.min(1, dt*3.0);
    if(autoRotate) yaw+=dt*0.13;

    /* neck extension: tilt the anatomy back */
    neck.rotation.x = -A.tilt*0.24;

    /* camera */
    const cy=Math.sin(pitch)*dist, cxz=Math.cos(pitch)*dist;
    camera.position.set(Math.sin(yaw)*cxz, cy+0.35, Math.cos(yaw)*cxz);
    camera.lookAt(0, 0.05, 0);

    /* probe sits on the anterior skin over the nodule */
    const py = 1.30 - A.probeOn*0.13 + (A.probeOn>0.05 ? 0.008*Math.sin(now/240):0);
    P.probe.position.set(0.50, py, 0.86);
    P.probe.rotation.set(0.62, 0, 0);
    P.probe.visible = A.probeOn>0.03;
    P.gel.visible = P.probe.visible;
    P.gel.material.opacity = 0.55*A.probeOn;

    /* beam from the footprint down to the nodule */
    P.beam.visible = A.beam>0.03;
    P.beam.material.opacity = 0.09*A.beam*(0.85+0.15*Math.sin(now/420));

    /* needle enters at the mark and angles down into the nodule */
    const exc = A.passes ? Math.sin(now/210)*0.026 : 0;
    const ny = 1.14 - A.needleIn*0.86;
    P.needle.position.set(0.50 + exc, ny, 0.72 - A.needleIn*0.30);
    P.needle.rotation.set(0.30 + A.needleIn*0.26, 0, 0);
    const nv = A.needleOut<0.97 || A.needleIn>0.02;
    P.needle.visible=nv; P.hub.visible=nv; P.syringe.visible=nv;

    /* marker + nodule highlight */
    P.marker.visible = A.markerIn>0.02;
    P.marker.material.emissiveIntensity = 0.4+0.8*A.markerIn;
    P.halo.visible = A.markerIn>0.02 || A.beam>0.3;
    P.halo.material.opacity = 0.35+0.45*A.beam;

    /* dressing appears at the end */
    P.dressing.visible = A.dressing>0.02;
    P.dressing.position.set(0.50, 1.13, 0.72);

    renderer.render(scene, camera);
  }

  function frame(now){ lastRaf=performance.now(); step(now); requestAnimationFrame(frame); }

  /* rAF is throttled to zero when the page is not compositing (kiosk tablets,
     background tabs, low-power modes). A watchdog keeps the animation moving. */
  function startWatchdog(){
    if(watchdogOn) return;
    watchdogOn=true;
    setInterval(function(){
      if(performance.now()-lastRaf>250) step(performance.now());
    }, 33);
  }

  setStep(0);
  requestAnimationFrame(frame);
  startWatchdog();
})();
"""

html = (SHELL.replace("__GEOMETRY__", "")
              .replace("__SCENE__", "const THREE_INLINE = 1;\n" + scene3))
# inject three.js + the renderer, and drop the old inline geometry/scene blocks
html = html.replace("<script>\nconst THREE_INLINE = 1;",
                    "<script>\n/* three.js r150+ (MIT) — inlined so the app works fully offline */\n"
                    + three + "\n" + scene3.replace(scene3, "") + RENDERER + "\n</scr" + "ipt>\n<script>")

# simpler and safer: rebuild the script block from scratch
html = (SHELL.replace("__GEOMETRY__", three)
              .replace("__SCENE__", scene3))
# now swap the old renderer (everything after the scene) for the new one
i = html.index("/* =============================================================== RENDERER == */")
j = html.rindex("</script>\n</body>")
html = html[:i] + RENDERER + html[j:]

path = os.path.join(BASE, "index.html")
with open(path, "w") as fh:
    fh.write(html)
print("wrote", path, f"{len(html):,} bytes")
