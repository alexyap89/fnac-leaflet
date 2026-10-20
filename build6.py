#!/usr/bin/env /usr/bin/python3
"""FNAC webapp v6 builder — staged reveal per Alex's sequence."""
import os

BASE = "/home/alex/Documents/FNAC_Webapp"
three  = open("/tmp/three_test.js").read()
scene6 = open(os.path.join(BASE, "scene6.js")).read()

shell_src = open(os.path.join(BASE, "build3.py")).read()
s = shell_src.index('SHELL = r"""') + len('SHELL = r"""')
e = shell_src.index('"""\n\nhtml = SHELL')
SHELL = shell_src[s:e]

RENDERER = r"""
/* ================================================================ RENDERER ==
   Sequence (Alex, 2026-10-11): head/face/neck -> translucent reveals thyroid
   -> nodule -> back to neck -> probe on the lesion -> needle at 45 deg under
   the probe into the lesion -> 3 passes -> out -> dressing.
   ========================================================================== */
(function(){
  const canvas = document.getElementById('gl');
  const label  = document.getElementById('stepLabel');
  const note   = document.getElementById('stepNote');
  const chips  = document.getElementById('steps');
  const btnPlay= document.getElementById('btnPlay');
  const srText = document.getElementById('srText');
  const labelLayer = document.getElementById('sceneLabels');
  const root   = document.documentElement;

  /* Set true to disable all animation (accessibility / reduced motion). */
  const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const STEPS = [
    {t:"Your neck and head",
     n:"This is the area the test involves: the front of your neck, below the jaw. Nothing here is to scale with anything scary — it is just your neck.",
     a:{form:1, xray:0, noduleHi:0, probe:0, needle:0, passes:0, dressing:0, labels:0}},

    {t:"Where the thyroid sits",
     n:"The thyroid is a small gland that sits inside your neck, wrapped around the front of the windpipe. Here the skin is made see-through so you can see where it actually is.",
     a:{form:1, xray:1, noduleHi:0, probe:0, needle:0, passes:0, dressing:0, labels:1}},

    {t:"The nodule",
     n:"This is the lump your doctor wants to test. It is inside the thyroid gland. Most of what you can see here is normal neck tissue — the lump is the part highlighted.",
     a:{form:1, xray:1, noduleHi:1, probe:0, needle:0, passes:0, dressing:0, labels:1}},

    {t:"Back to the surface",
     n:"The skin becomes solid again. From here on, this is what you would actually see if you looked down.",
     a:{form:1, xray:0.12, noduleHi:0, probe:0, needle:0, passes:0, dressing:0, labels:0}},

    {t:"Finding the exact spot",
     n:"The doctor rests the ultrasound probe on the front of your neck, directly over the lump. The probe sends out sound waves and shows the lump on a screen, so its position and depth are known exactly before anything else happens.",
     a:{form:1, xray:0.85, noduleHi:0, probe:1, needle:0, passes:0, dressing:0, labels:1}},

    {t:"The needle goes in",
     n:"A very fine needle goes in at an angle, under the probe, and its tip reaches the lump. This is why the doctor holds the probe while the needle goes in — so the tip can be followed the whole way.",
     a:{form:1, xray:0.55, noduleHi:1, probe:1, needle:1, passes:0, dressing:0, labels:1}},

    {t:"Three passes",
     n:"Inside the lump, the needle moves gently back and forth for a few seconds to collect cells. This is then repeated — usually up to three times — to gather enough cells for a reliable result.",
     a:{form:1, xray:0.4, noduleHi:1, probe:1, needle:1, passes:1, dressing:0, labels:1}},

    {t:"The needle comes out",
     n:"The needle is removed. The sample of cells goes to the laboratory.",
     a:{form:1, xray:0.1, noduleHi:0, probe:0.9, needle:0, passes:0, dressing:0, labels:0}},

    {t:"A dressing, and that's it",
     n:"A small dressing is placed over the spot where the needle went in. You can usually go home shortly afterwards. The dressing stays on for 1–2 hours.",
     a:{form:1, xray:0, noduleHi:0, probe:0, needle:0, passes:0, dressing:1, labels:0}},
  ];

  let cur=0, playing=false, timer=null;

  STEPS.forEach((s,i)=>{
    const b=document.createElement('button');
    b.className='stepchip'; b.setAttribute('role','tab');
    b.textContent=(i+1)+'. '+s.t;
    b.onclick=()=>{ stopPlay(); setStep(i); };
    chips.appendChild(b);
  });

  const A={form:0,xray:0,noduleHi:0,probe:0,needle:0,passes:0,dressing:0,labels:0};
  const TGT=Object.assign({},A);

  function setStep(i){
    cur=i; const s=STEPS[i];
    label.innerHTML='<b>Step '+(i+1)+' of '+STEPS.length+'.</b> '+s.t;
    note.textContent=s.n;
    srText.textContent='Step '+(i+1)+' of '+STEPS.length+'. '+s.t+'. '+s.n;
    [...chips.children].forEach((c,j)=>c.setAttribute('aria-current',String(j===i)));
    for(const k of Object.keys(TGT)) TGT[k]=(s.a[k]!==undefined)?s.a[k]:0;
    if(RM){ for(const k of Object.keys(TGT)) A[k]=TGT[k]; }
  }
  function stopPlay(){ playing=false; clearInterval(timer); btnPlay.textContent='▶ Play all'; }
  btnPlay.onclick=()=>{
    if(playing){ stopPlay(); return; }
    playing=true; btnPlay.textContent='⏸ Pause';
    timer=setInterval(()=>{ if(cur>=STEPS.length-1){ stopPlay(); return; } setStep(cur+1); },5200);
  };

  /* ------------------------------------------------------------ UI prefs -- */
  const SIZES=['normal','large','xl']; let sizeIdx=0;
  document.getElementById('btnSize').onclick=(e)=>{
    sizeIdx=(sizeIdx+1)%SIZES.length; const v=SIZES[sizeIdx];
    if(v==='normal') root.removeAttribute('data-size'); else root.setAttribute('data-size',v);
    e.currentTarget.setAttribute('aria-pressed',String(v!=='normal'));
    e.currentTarget.textContent=v==='normal'?'Larger text'
      :(v==='large'?'Largest text':'Reset text size');
  };
  document.getElementById('btnContrast').onclick=(e)=>{
    const on=root.getAttribute('data-contrast')==='high';
    if(on) root.removeAttribute('data-contrast'); else root.setAttribute('data-contrast','high');
    e.currentTarget.setAttribute('aria-pressed',String(!on));
  };
  document.getElementById('btnRotate').onclick=(e)=>{
    autoRotate=!autoRotate;
    e.currentTarget.setAttribute('aria-pressed',String(autoRotate));
  };
  document.getElementById('btnPrint').onclick=()=>window.print();

  /* ------------------------------------------------------------ three.js -- */
  const T = buildThreeScene(THREE);
  const scene=T.scene, body=T.body, P=T.parts;
  const {NODULE_WORLD, ENTRY, TIP_TARGET, SHAFT_LEN} = T.anchors;

  const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true,
                                            preserveDrawingBuffer:true});
  renderer.setClearColor(0x000000,0);
  const camera = new THREE.PerspectiveCamera(38, 1.6, 0.1, 200);

  /* --------------------------------------------------------- DOM labels --- */
  const LABELS = [
    {text:'Head',        pos:new THREE.Vector3(0,3.0,0.6),      shows:a=>a.form>.5&&a.xray<.4},
    {text:'Neck',        pos:new THREE.Vector3(-1.15,-0.6,0.6), shows:a=>a.form>.5&&a.xray<.4},
    {text:'Thyroid gland',pos:new THREE.Vector3(-0.72,-0.44,0.5),shows:a=>a.xray>.45},
    {text:'Windpipe',    pos:new THREE.Vector3(0.0,-1.35,0.1),  shows:a=>a.xray>.45},
    {text:'The lump',    pos:new THREE.Vector3(NODULE_WORLD.x,NODULE_WORLD.y+0.42,NODULE_WORLD.z+0.25),
                          shows:a=>a.noduleHi>.5},
    {text:'Ultrasound probe', pos:new THREE.Vector3(NODULE_WORLD.x+0.1,1.75,1.0), shows:a=>a.probe>.5},
    {text:'Needle',      pos:new THREE.Vector3(ENTRY.x-0.1,ENTRY.y+0.75,ENTRY.z+0.2), shows:a=>a.needle>.45},
  ];
  const labelEls = LABELS.map(L=>{
    const d=document.createElement('div');
    d.className='scene-label'; d.textContent=L.text;
    labelLayer.appendChild(d); return d;
  });

  /* ------------------------------------------------------------ controls -- */
  let yaw=0.0, pitch=0.16, dist=9.2, autoRotate=true;
  let drag=false,lx=0,ly=0,pid=null;

  canvas.addEventListener('pointerdown',e=>{ drag=true; autoRotate=false; pid=e.pointerId;
    lx=e.clientX; ly=e.clientY;
    if(canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointerup',()=>{ drag=false;
    if(canvas.releasePointerCapture&&pid!==null){try{canvas.releasePointerCapture(pid);}catch(_){}}
    pid=null; });
  canvas.addEventListener('pointercancel',()=>{drag=false;pid=null;});
  canvas.addEventListener('pointermove',e=>{ if(!drag)return;
    yaw+=(e.clientX-lx)*0.007;
    pitch=Math.max(-0.7,Math.min(1.0,pitch+(e.clientY-ly)*0.005));
    lx=e.clientX; ly=e.clientY; });
  canvas.addEventListener('wheel',e=>{ e.preventDefault();
    dist=Math.max(3.4,Math.min(20,dist+e.deltaY*0.007)); autoRotate=false; },{passive:false});
  canvas.addEventListener('keydown',e=>{ const k=e.key;
    if(k==='ArrowLeft'){yaw-=0.12;autoRotate=false;e.preventDefault();}
    else if(k==='ArrowRight'){yaw+=0.12;autoRotate=false;e.preventDefault();}
    else if(k==='ArrowUp'){pitch=Math.max(-0.7,pitch-0.07);autoRotate=false;e.preventDefault();}
    else if(k==='ArrowDown'){pitch=Math.min(1.0,pitch+0.07);autoRotate=false;e.preventDefault();}
    else if(k==='+'||k==='='){dist=Math.max(3.4,dist-0.6);e.preventDefault();}
    else if(k==='-'||k==='_'){dist=Math.min(20,dist+0.6);e.preventDefault();} });

  function resize(){
    const dpr=Math.min(window.devicePixelRatio||1,2);
    const r=canvas.getBoundingClientRect();
    const w=Math.max(2,Math.round(r.width)), h=Math.max(2,Math.round(r.height));
    renderer.setPixelRatio(dpr); renderer.setSize(w,h,false);
    camera.aspect=w/h; camera.updateProjectionMatrix();
  }
  window.addEventListener('resize',resize); resize();

  /* -------------------------------------------------------- render loop --- */
  let t0=performance.now(), lastRaf=performance.now(), wdOn=false;
  const v3=new THREE.Vector3();
  const ENTRY_LIFT = ENTRY.clone().add(new THREE.Vector3(0, SHAFT_LEN+0.34, 0));
  const ENTRY_SKIN  = ENTRY.clone().add(new THREE.Vector3(0, SHAFT_LEN*0.30, 0));

  /* ---- need to know which meshes are "skin" so we can fade them ---------- */
  const SKIN_MESHES = [P.neck, P.head].filter(Boolean);

  function step(now){
    const dt=Math.min(0.05,(now-t0)/1000); t0=now;
    const k = RM ? 1 : Math.min(1, dt*2.6);
    for(const key of Object.keys(TGT)) A[key]+=(TGT[key]-A[key])*k;
    if(autoRotate && !RM) yaw+=dt*0.10;

    /* ---------- translucency: skin fades as xray rises ------------------- */
    const op = 1 - 0.80*A.xray;                 // 1.0 -> 0.20
    M_skin.opacity = op;
    M_skin.transparent = A.xray>0.02;
    M_skin.depthWrite = A.xray<0.35;
    M_skin.needsUpdate = true;

    /* the inside becomes visible only once the skin is see-through */
    P.inside.visible = A.xray>0.02;
    P.inside.traverse(o=>{
      if(o.material && o.material.transparent===false && o.material!==M_skin){}
    });
    // fade the interior in smoothly
    const inOp = Math.min(1, A.xray*1.6);
    P.inside.traverse(o=>{ if(o.isMesh && o.material && o.material.__fade===undefined){
      // only fade materials we own here
    }});
    setGroupOpacity(P.inside, inOp, ['thyroid','nodule','trachea','strap','strap2',
                                     'scm','cart','artery','vein','fat']);

    /* ---------- nodule emphasis ----------------------------------------- */
    P.halo.visible = A.noduleHi>0.03;
    P.glow.visible = A.noduleHi>0.03;
    P.halo.material.opacity = 0.25+0.7*A.noduleHi;
    P.glow.material.opacity = 0.05+0.18*A.noduleHi;
    P.nodule.material.emissiveIntensity = 0.3+1.3*A.noduleHi;

    /* ---------- probe: face pressed on the neck over the nodule ---------- */
    P.probe.visible = A.probe>0.03;
    P.gel.visible   = A.probe>0.03;
    P.gel.material.opacity = 0.55*A.probe;
    P.probe.position.y = SKIN_Y - 0.02 + A.probe*0.0
                       + (A.probe>0.05 && !RM ? 0.006*Math.sin(now/260) : 0);
    P.beam.visible = A.probe>0.3;
    P.beam.material.opacity = 0.085*A.probe*(0.85+0.15*Math.sin(now/430));

    /* ---------- needle: in, 3 passes, out -------------------------------- */
    const active = A.needle>0.02 || A.passes>0.02;
    P.needle.visible = active;
    P.guide.visible = A.needle>0.05;
    P.guide.material.opacity = 0.5*A.needle;

    if(active){
      // 0 = outside the skin, 1 = tip through the nodule centre
      const deep = Math.min(1, A.needle);
      const from = new THREE.Vector3().lerpVectors(ENTRY_LIFT, ENTRY_SKIN, deep);

      // passes: the tip oscillates ALONG the needle axis, inside the nodule
      let extra = 0;
      if(A.passes>0.02){
        // 3 discrete passes, each ~1.6 s, with a brief withdrawal between
        const cycle = 5.0;                       // seconds for all 3
        const tt = RM ? 0.5 : (now/1000 % cycle)/cycle;
        const passIdx = Math.min(2, Math.floor(tt*3));
        const phase = (tt*3) % 1;                // 0..1 within one pass
        // in-and-out excursion along the needle axis
        const osc = Math.sin(phase*Math.PI*4);   // ~2 in-out motions per pass
        extra = osc*0.055;
      }
      const tip = new THREE.Vector3().copy(ENTRY).lerp(TIP_TARGET, deep);
      // apply the excursion along the trajectory direction
      const dirn = new THREE.Vector3().subVectors(TIP_TARGET,ENTRY).normalize();
      tip.addScaledVector(dirn, extra);
      T.aimAt(P.needle, from, tip);
    }

    /* ---------- dressing -------------------------------------------------- */
    P.dressing.visible = A.dressing>0.03;
    P.dressing.material.opacity = 1;
    P.mark.visible = A.dressing<0.5;

    /* ---------- camera ---------------------------------------------------- */
    const cy=Math.sin(pitch)*dist, cxz=Math.cos(pitch)*dist;
    camera.position.set(Math.sin(yaw)*cxz, cy+0.55, Math.cos(yaw)*cxz);
    camera.lookAt(0, A.xray>0.4 ? 0.15 : 0.9, 0);

    renderer.render(scene,camera);

    /* ---------- project labels -------------------------------------------- */
    const w=canvas.clientWidth, h=canvas.clientHeight;
    LABELS.forEach((L,i)=>{
      const el=labelEls[i];
      const vis = A.labels>0.55 && L.shows(A);
      el.style.display = vis?'block':'none';
      if(!vis) return;
      v3.copy(L.pos).project(camera);
      const x=(v3.x*0.5+0.5)*w, y=(-v3.y*0.5+0.5)*h;
      el.style.transform='translate(-50%,-50%) translate('+x.toFixed(1)+'px,'+y.toFixed(1)+'px)';
    });
  }

  /* fade helper: sets opacity on interior material groups without destroying
     their individual colours */
  function setGroupOpacity(group, op, names){
    if(!group) return;
    group.traverse(o=>{
      if(!o.isMesh || !o.material) return;
      const m=o.material;
      if(m.userData && m.userData.__origOp===undefined) m.userData.__origOp=1;
      const orig=m.userData.__origOp;
      m.transparent = op<0.999;
      m.opacity = orig*op;
      if(op<0.999) m.depthWrite=false; 
      m.needsUpdate=(m.needsUpdate!==true);
    });
  }

  function frame(now){ lastRaf=performance.now(); step(now); requestAnimationFrame(frame); }
  function startWatchdog(){ if(wdOn)return; wdOn=true;
    setInterval(()=>{ if(performance.now()-lastRaf>250) step(performance.now()); },33); }

  const M_skin = P.neck.material;
  const SKIN_Y = T.anchors.SKIN_Y;

  scene.updateMatrixWorld(true);
  setStep(0);
  requestAnimationFrame(frame);
  startWatchdog();
})();
"""

html = SHELL.replace("__GEOMETRY__", three).replace("__SCENE__", scene6)
i = html.index("/* =============================================================== RENDERER == */")
j = html.rindex("</script>\n</body>")
html = html[:i] + RENDERER + html[j:]

if 'id="btnRotate"' not in html:
    html = html.replace('<button id="btnPrint"',
      '<button id="btnRotate" type="button" aria-pressed="true">Pause spin</button>\n      <button id="btnPrint"', 1)

if 'sceneLabels' not in html:
    html = html.replace('<div class="hud">',
      '<div class="scene-labels" id="sceneLabels" aria-hidden="true"></div>\n      <div class="hud">',1)
if '.scene-label{' not in html:
    html = html.replace('.stage .hud{',
""".stage .scene-labels{position:absolute;inset:0;pointer-events:none;z-index:3}
.scene-label{position:absolute;left:0;top:0;background:rgba(6,12,24,.88);
  border:1px solid rgba(120,170,255,.45);border-radius:8px;padding:3px 9px;
  font-size:calc(var(--fs)*.66);color:#d6e6ff;white-space:nowrap}
.stage .hud{""",1)

with open(os.path.join(BASE,"index.html"),"w") as fh: fh.write(html)
print("wrote index.html", f"{len(html):,} bytes")

# report the encoded technique angle
import re
print("steps:", html.count('className=\'stepchip\''))
