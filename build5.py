#!/usr/bin/env /usr/bin/python3
"""FNAC webapp v5 builder."""
import os

BASE = "/home/alex/Documents/FNAC_Webapp"
three = open("/tmp/three_test.js").read()
scene5 = open(os.path.join(BASE, "scene5.js")).read()

shell_src = open(os.path.join(BASE, "build3.py")).read()
s = shell_src.index('SHELL = r"""') + len('SHELL = r"""')
e = shell_src.index('"""\n\nhtml = SHELL')
SHELL = shell_src[s:e]

RENDERER = r"""
/* ================================================================ RENDERER == */
(function(){
  const canvas = document.getElementById('gl');
  const label  = document.getElementById('stepLabel');
  const note   = document.getElementById('stepNote');
  const chips  = document.getElementById('steps');
  const btnPlay= document.getElementById('btnPlay');
  const srText = document.getElementById('srText');
  const labels = document.getElementById('sceneLabels');

  const STEPS = [
    {t:"Getting into position",
     n:"You lie on your back with your head tipped gently back, so your neck is extended. Sometimes a pillow goes under your shoulders. This brings the thyroid closer to the surface and makes it easier to reach.",
     a:{tilt:1, probeOn:0.15, needleOut:1, markerIn:0, needleIn:0, passes:0, dressing:0, beam:0, labels:1}},
    {t:"Ultrasound first",
     n:"The doctor scans your neck to find the thyroid gland and the exact nodule. Blood vessels along the needle path are checked so they can be avoided.",
     a:{tilt:1, probeOn:1, needleOut:1, markerIn:0, needleIn:0, passes:0, dressing:0, beam:0.6, labels:1}},
    {t:"Marking the entry point",
     n:"The skin where the needle will go in may be marked with a pen, so it enters at the planned spot.",
     a:{tilt:1, probeOn:0.85, needleOut:1, markerIn:1, needleIn:0, passes:0, dressing:0, beam:0.85, labels:1}},
    {t:"Local anaesthetic, if needed",
     n:"You may be given a local anaesthetic injection to numb the injection site. Many people do not need one — your doctor will decide with you.",
     a:{tilt:1, probeOn:1, needleOut:1, markerIn:1, needleIn:0, passes:0, dressing:0, beam:0.55, labels:1}},
    {t:"The needle goes in",
     n:"A very fine needle — finer than the one used for a blood test — passes through the skin and into the nodule, guided live by the ultrasound image on the screen.",
     a:{tilt:1, probeOn:1, needleOut:0, markerIn:1, needleIn:1, passes:0, dressing:0, beam:0.9, labels:1}},
    {t:"Several passes",
     n:"The needle moves gently back and forth inside the nodule for a few seconds to collect cells. The needle may be inserted more than once — this is called making several passes — to gather enough cells for a reliable result.",
     a:{tilt:1, probeOn:1, needleOut:0, markerIn:1, needleIn:1, passes:1, dressing:0, beam:0.9, labels:1}},
    {t:"The sample goes to the laboratory",
     n:"The cells collected are sent to the laboratory, where a pathologist examines them under a microscope. A dressing is placed over the puncture site.",
     a:{tilt:1, probeOn:0.5, needleOut:1, markerIn:1, needleIn:0, passes:0, dressing:1, beam:0.25, labels:1}}
  ];

  let cur=0, playing=false, timer=null;

  STEPS.forEach((s,i)=>{
    const b=document.createElement('button');
    b.className='stepchip'; b.setAttribute('role','tab');
    b.textContent=(i+1)+'. '+s.t;
    b.onclick=()=>{ stopPlay(); setStep(i); };
    chips.appendChild(b);
  });

  const A={tilt:0,probeOn:0,needleOut:1,markerIn:0,needleIn:0,passes:0,
           dressing:0,beam:0,labels:0};
  const TGT=Object.assign({},A);

  function setStep(i){
    cur=i; const s=STEPS[i];
    label.innerHTML='<b>Step '+(i+1)+' of '+STEPS.length+'.</b> '+s.t;
    note.textContent=s.n;
    srText.textContent='Step '+(i+1)+' of '+STEPS.length+'. '+s.t+'. '+s.n;
    [...chips.children].forEach((c,j)=>c.setAttribute('aria-current',String(j===i)));
    for(const k of Object.keys(TGT)) TGT[k]=(s.a[k]!==undefined)?s.a[k]:0;
  }
  function stopPlay(){ playing=false; clearInterval(timer); btnPlay.textContent='▶ Play'; }
  btnPlay.onclick=()=>{
    if(playing){ stopPlay(); return; }
    playing=true; btnPlay.textContent='⏸ Pause';
    timer=setInterval(()=>{ if(cur>=STEPS.length-1){ stopPlay(); return; } setStep(cur+1); },4800);
  };

  /* ------------------------------------------------------------- UI prefs */
  const html=document.documentElement;
  const SIZES=['normal','large','xl']; let sizeIdx=0;
  document.getElementById('btnSize').onclick=(e)=>{
    sizeIdx=(sizeIdx+1)%SIZES.length; const v=SIZES[sizeIdx];
    if(v==='normal') html.removeAttribute('data-size'); else html.setAttribute('data-size',v);
    e.currentTarget.setAttribute('aria-pressed',String(v!=='normal'));
    e.currentTarget.textContent=v==='normal'?'Larger text'
      :(v==='large'?'Largest text':'Reset text size');
  };
  document.getElementById('btnContrast').onclick=(e)=>{
    const on=html.getAttribute('data-contrast')==='high';
    if(on) html.removeAttribute('data-contrast'); else html.setAttribute('data-contrast','high');
    e.currentTarget.setAttribute('aria-pressed',String(!on));
  };
  document.getElementById('btnPrint').onclick=()=>window.print();

  /* ------------------------------------------------------------- three.js */
  const T = buildThreeScene(THREE);
  const scene=T.scene, neck=T.neck, P=T.parts;
  const {ENTRY, TARGET} = T.anchors;

  const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true,
                                            preserveDrawingBuffer:true});
  renderer.setClearColor(0x000000,0);
  const camera = new THREE.PerspectiveCamera(42, 1.6, 0.1, 100);

  /* ------------------------------------------------ in-scene DOM labels ---
     Projected from 3D world positions each frame, so a patient can name what
     they are looking at. */
  const LABELS = [
    {text:'Thyroid gland', pos:new THREE.Vector3(-0.46,-0.40,0.30), show:a=>1},
    {text:'Nodule',        pos:new THREE.Vector3(0.44, 0.30, 0.60), show:a=>a.beam>0.25||a.needleIn>0.3},
    {text:'Trachea',       pos:new THREE.Vector3(0.0, -0.95, 0.10), show:a=>1},
    {text:'Ultrasound probe', pos:new THREE.Vector3(0.44, 1.62, 1.10), show:a=>a.probeOn>0.3},
    {text:'Needle',        pos:new THREE.Vector3(0.44, 1.55, 1.30), show:a=>a.needleIn>0.05||a.markerIn>0.5},
  ];
  const labelEls = LABELS.map(L=>{
    const d=document.createElement('div');
    d.className='scene-label'; d.textContent=L.text;
    labels.appendChild(d);
    return d;
  });

  /* -------------------------------------------------------------- controls */
  let yaw=-0.58, pitch=0.24, dist=6.0, autoRotate=true;
  let drag=false,lx=0,ly=0,pid=null;
  canvas.addEventListener('pointerdown',e=>{ drag=true; autoRotate=false; pid=e.pointerId;
    lx=e.clientX; ly=e.clientY;
    if(canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointerup',()=>{ drag=false;
    if(canvas.releasePointerCapture&&pid!==null){ try{canvas.releasePointerCapture(pid);}catch(_){}}
    pid=null; });
  canvas.addEventListener('pointercancel',()=>{ drag=false; pid=null; });
  canvas.addEventListener('pointermove',e=>{ if(!drag)return;
    yaw+=(e.clientX-lx)*0.008;
    pitch=Math.max(-0.6,Math.min(1.15,pitch+(e.clientY-ly)*0.006));
    lx=e.clientX; ly=e.clientY; });
  canvas.addEventListener('wheel',e=>{ e.preventDefault();
    dist=Math.max(3.0,Math.min(12,dist+e.deltaY*0.004)); autoRotate=false; },{passive:false});
  canvas.addEventListener('keydown',e=>{ const k=e.key;
    if(k==='ArrowLeft'){yaw-=0.12;autoRotate=false;e.preventDefault();}
    else if(k==='ArrowRight'){yaw+=0.12;autoRotate=false;e.preventDefault();}
    else if(k==='ArrowUp'){pitch=Math.max(-0.6,pitch-0.08);autoRotate=false;e.preventDefault();}
    else if(k==='ArrowDown'){pitch=Math.min(1.15,pitch+0.08);autoRotate=false;e.preventDefault();}
    else if(k==='+'||k==='='){dist=Math.max(3.0,dist-0.5);e.preventDefault();}
    else if(k==='-'||k==='_'){dist=Math.min(12,dist+0.5);e.preventDefault();} });

  function resize(){
    const dpr=Math.min(window.devicePixelRatio||1,2);
    const r=canvas.getBoundingClientRect();
    const w=Math.max(2,Math.round(r.width)), h=Math.max(2,Math.round(r.height));
    renderer.setPixelRatio(dpr); renderer.setSize(w,h,false);
    camera.aspect=w/h; camera.updateProjectionMatrix();
  }
  window.addEventListener('resize',resize); resize();

  /* ----------------------------------------------------------- render loop */
  let t0=performance.now(), lastRaf=performance.now(), watchdogOn=false;
  const v3=new THREE.Vector3();

  function step(now){
    const dt=Math.min(0.05,(now-t0)/1000); t0=now;
    for(const k of Object.keys(TGT)) A[k]+=(TGT[k]-A[k])*Math.min(1,dt*3.0);
    if(autoRotate) yaw+=dt*0.12;

    neck.rotation.x = -A.tilt*0.22;

    const cy=Math.sin(pitch)*dist, cxz=Math.cos(pitch)*dist;
    camera.position.set(Math.sin(yaw)*cxz, cy+0.35, Math.cos(yaw)*cxz);
    camera.lookAt(0,0.02,0);

    /* probe rests on the skin */
    P.probe.visible = A.probeOn>0.03;
    P.gel.visible = P.probe.visible;
    P.gel.material.opacity = 0.5*A.probeOn;
    P.probe.position.y = 1.14 - A.probeOn*0.02
                       + (A.probeOn>0.05 ? 0.006*Math.sin(now/250) : 0);

    /* beam */
    P.beam.visible = A.beam>0.03;
    P.beam.material.opacity = 0.085*A.beam*(0.85+0.15*Math.sin(now/420));

    /* needle: aim from a point above ENTRY toward TARGET */
    const exc = A.passes ? Math.sin(now/210)*0.024 : 0;
    const from = new THREE.Vector3(ENTRY.x+exc, ENTRY.y+1.05-A.needleIn*0.55,
                                   ENTRY.z+0.28-A.needleIn*0.16);
    // tip follows the entry->target line as needleIn goes 0->1
    const tip = new THREE.Vector3().lerpVectors(
      new THREE.Vector3(ENTRY.x+exc, ENTRY.y+0.62, ENTRY.z+0.10), TARGET, A.needleIn);
    T.aimAt(P.needle, from, tip);
    const nv = A.needleOut<0.97 || A.needleIn>0.02;
    P.needle.visible=nv;
    P.guide.visible = A.markerIn>0.3 || A.needleIn>0.02;
    P.guide.material.opacity = (A.markerIn>0.3?0.35:0) + 0.45*A.needleIn;

    /* marker, nodule highlight, dressing */
    P.marker.visible = A.markerIn>0.02;
    P.marker.material.emissiveIntensity = 0.4+0.9*A.markerIn;
    P.halo.visible = A.beam>0.25 || A.needleIn>0.05;
    P.halo.material.opacity = 0.35+0.5*A.beam;
    P.glow.visible = P.halo.visible;
    P.glow.material.opacity = 0.08+0.16*A.beam;
    P.dressing.visible = A.dressing>0.02;

    renderer.render(scene,camera);

    /* ---- project labels to screen ---- */
    const w=canvas.clientWidth, h=canvas.clientHeight;
    LABELS.forEach((L,i)=>{
      const el=labelEls[i];
      const vis = A.labels>0.5 && L.show(A);
      el.style.display = vis ? 'block' : 'none';
      if(!vis) return;
      v3.copy(L.pos).applyMatrix4(neck.matrixWorld).project(camera);
      const x=(v3.x*0.5+0.5)*w, y=(-v3.y*0.5+0.5)*h;
      el.style.transform='translate(-50%,-50%) translate('+x.toFixed(1)+'px,'+y.toFixed(1)+'px)';
    });
  }

  function frame(now){ lastRaf=performance.now(); step(now); requestAnimationFrame(frame); }
  function startWatchdog(){ if(watchdogOn) return; watchdogOn=true;
    setInterval(function(){ if(performance.now()-lastRaf>250) step(performance.now()); },33); }

  neck.updateMatrixWorld(true);
  setStep(0);
  requestAnimationFrame(frame);
  startWatchdog();
})();
"""

html = SHELL.replace("__GEOMETRY__", three).replace("__SCENE__", scene5)
i = html.index("/* =============================================================== RENDERER == */")
j = html.rindex("</script>\n</body>")
html = html[:i] + RENDERER + html[j:]

# add the label overlay container + styles
html = html.replace('<div class="hud">',
  '<div class="scene-labels" id="sceneLabels" aria-hidden="true"></div>\n      <div class="hud">', 1)
html = html.replace('.stage .hud{',
""".stage .scene-labels{position:absolute;inset:0;pointer-events:none}
.scene-label{position:absolute;left:0;top:0;background:rgba(6,12,24,.86);
  border:1px solid rgba(120,170,255,.42);border-radius:8px;padding:3px 9px;
  font-size:calc(var(--fs)*.66);color:#cfe2ff;white-space:nowrap;
  letter-spacing:.3px}
.stage .hud{""", 1)

with open(os.path.join(BASE, "index.html"), "w") as fh:
    fh.write(html)
print("wrote index.html", f"{len(html):,} bytes")
