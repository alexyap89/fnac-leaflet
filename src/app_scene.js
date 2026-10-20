function buildThreeScene(THREE, root){
  const scene=new THREE.Scene();
  scene.add(new THREE.AmbientLight(0x8899bb,0.75));
  const key=new THREE.DirectionalLight(0xfff2e4,1.15); key.position.set(0.5,1.2,0.9);
  scene.add(key);
  const fill=new THREE.DirectionalLight(0x9fc0ff,0.55); fill.position.set(-0.8,0.4,-0.6);
  scene.add(fill);
  /* Under-fill. With a real head on the neck the jaw overhangs the throat, and
     the key light alone leaves that whole region as a black crease that reads
     as a seam in the model. A weak warm light from below-front lifts it. */
  const under=new THREE.DirectionalLight(0xffd8bf,0.42); under.position.set(0.1,-0.9,0.7);
  scene.add(under);

  root.updateMatrixWorld(true);
  const byRole={};
  root.traverse(o=>{ if(!o.isMesh) return;
    (byRole[o.userData.role]=byRole[o.userData.role]||[]).push(o); });

  const G={};
  for(const r in byRole){
    const g=new THREE.Group(); g.name=r; G[r]=g;
    byRole[r].forEach(o=>{
      const isNeedle=(r==='needle'), isProbe=(r==='probe');
      o.material=new THREE.MeshStandardMaterial({
        color:ROLE_COL[r]!==undefined?ROLE_COL[r]:0x999999,
        roughness:isNeedle?0.25:(isProbe?0.45:0.6),
        metalness:isNeedle?0.55:(isProbe?0.30:0.0), side:THREE.DoubleSide,
        emissive:r==='nodule'?0xff7a2a:0x000000, emissiveIntensity:0});
      g.add(o);
    });
  }
  const shell=new THREE.Group(); scene.add(shell);
  for(const r in G) shell.add(G[r]);
  /* the GLB still carries the department's own body meshes, but they are laid
     out supine with the head detached from the neck, so they stay hidden; the
     authored bust takes their place. The neck muscles stay hidden too: they
     overrun the new skin and their shape is already carried by the bust. */
  ['strap','skeletalmuscle'].forEach(r=>{ if(G[r]) G[r].visible=false; });
  ['patient__head','patient__neck','patient__shoulders'].forEach(nm=>{
    const o=shell.getObjectByName(nm); if(o) o.visible=false;
  });

  const inside=new THREE.Group();
  ['thyroid','nodule','airway','parathyroid','soft']
    .forEach(r=>{ if(G[r]) inside.add(G[r]); });
  ['Oropharynx','Tongue'].forEach(nm=>{
    const o=inside.getObjectByName('airway__'+nm)||inside.getObjectByName('soft__'+nm);
    if(o) o.visible=false;
  });
  shell.add(inside);

  /* ---- teaching scale for the two structures the page is about ------------
     The thyroid and the nodule are life size, which on a neck 12 cm wide is
     small enough to be hard to read at phone scale. The user's requirement is
     that both be identifiable at first glance, so they are scaled up modestly
     about their own centres; every position stays exactly where the anatomy puts
     it, and the needle is still anchored to the nodule centroid afterwards. */
  (function(){
    const grow=(grp, k)=>{ if(!grp) return;
      const c=new THREE.Box3().setFromObject(grp).getCenter(new THREE.Vector3());
      const pv=new THREE.Group(); pv.position.copy(c);
      [...grp.children].forEach(o=>{ o.position.sub(c); pv.add(o); });
      pv.scale.setScalar(k); grp.add(pv); };
    grow(G.thyroid, 1.26);
    grow(G.nodule, 1.30);
    /* The trachea is the other structure the text names, and it had never been
       scaled. Scale the trachea MESH about its own centre rather than the whole
       airway group: the group also holds the oropharynx, laryngopharynx and
       epiglottis, and growing all of that about the group centre would push the
       upper airway up through the jaw. This takes the trachea from 27 mm to 31 mm
       radially - the "slightly bigger" that was asked for - and it stays well
       inside the neck, because the neck is ~118 mm wide and the trachea sits on
       its axis. */
    (function(){
      const m=G.airway && G.airway.getObjectByName('airway__Trachea');
      if(!m || !m.geometry) return;
      const pa=m.geometry.getAttribute('position'); if(!pa) return;
      const c=new THREE.Box3().setFromBufferAttribute(pa).getCenter(new THREE.Vector3()), k=1.15;
      for(let i=0;i<pa.count;i++)
        pa.setXYZ(i, c.x+(pa.getX(i)-c.x)*k, c.y+(pa.getY(i)-c.y)*k, c.z+(pa.getZ(i)-c.z)*k);
      pa.needsUpdate=true;
    })();
  })();

  /* ---- skin envelope, fitted to the viscera ------------------------------ */
  /* The skin is the pale near-white of the reference build, not a tan. The model is now the
     neck/shoulders/chest surface only - no head, no face - so the skin IS the picture, and the
     viscera have to read through it against white rather than against tan. */
  const SKIN_MAT=()=>new THREE.MeshPhysicalMaterial({color:0xf2ece3,roughness:0.62,
    clearcoat:0.2,clearcoatRoughness:0.6,side:THREE.DoubleSide,transparent:false});
  function buildBody(contents){
    const box=new THREE.Box3(), v=new THREE.Vector3();
    contents.forEach(o=>{ const pa=o.geometry.getAttribute('position'); if(!pa) return;
      for(let i=0;i<pa.count;i+=2){
        v.fromBufferAttribute(pa,i).applyMatrix4(o.matrixWorld); box.expandByPoint(v); } });
    const zc=(box.min.z+box.max.z)/2, ylo=box.min.y, yhi=box.max.y;
    const NB=40, dy=(yhi-ylo)/(NB-1), r=new Array(NB).fill(0);
    contents.forEach(o=>{ const pa=o.geometry.getAttribute('position'); if(!pa) return;
      for(let i=0;i<pa.count;i++){
        v.fromBufferAttribute(pa,i).applyMatrix4(o.matrixWorld);
        let b=Math.round((v.y-ylo)/dy); if(b<0)b=0; if(b>NB-1)b=NB-1;
        const d=Math.hypot(v.x, v.z-zc); if(d>r[b]) r[b]=d; } });
    for(let i=0;i<NB;i++) if(r[i]===0) r[i]=i?r[i-1]:(r.find(x=>x>0)||0.04);
    const sm=r.slice();
    for(let pass=0;pass<3;pass++) for(let i=0;i<NB;i++){
      const a=sm[Math.max(0,i-2)], b=sm[Math.min(NB-1,i+2)];
      sm[i]=(sm[i]*2+a+b)/4;
    }
    const margin=0.014, rB=sm[0]+margin, rT=sm[NB-1]+margin;
    const yB=ylo-0.085, yT=yhi+0.055;
    const pts=[[rB*1.06,yB],[rB*1.02,yB+0.034],[rB*1.00,ylo]];
    for(let i=1;i<NB-1;i++) pts.push([sm[i]+margin, ylo+i*dy]);
    pts.push([rT,yhi],[rT*0.94,yhi+0.026],[rT*0.74,yT]);
    const g=new THREE.Group(); g.name='body';
    g.userData.zc=zc; g.userData.pts=pts;
    const neck=new THREE.Mesh(new THREE.LatheGeometry(
      pts.map(p=>new THREE.Vector2(p[0],p[1])),64),SKIN_MAT());
    neck.scale.set(1.10,1,0.94);
    neck.position.set(0,0,zc);
    g.add(neck);
    return g;
  }
  shell.updateMatrixWorld(true);
  const contents=[]; inside.traverse(o=>{ if(o.isMesh) contents.push(o); });
  /* ---- body ------------------------------------------------------------
     The authored bust from the GLB is the skin: a lofted head, neck and
     shoulders fitted so the reported needle entry point lies on its surface.
     If a build ever ships without it, the old fitted envelope is the fallback
     so the page still renders something. */
  const BUST=shell.getObjectByName('patient__bust');
  function bustBody(bust){
    const g=new THREE.Group(); g.name='body';
    bust.material=SKIN_MAT();
    bust.material.side=THREE.FrontSide;   // a closed shell can be single sided
    g.add(bust);
    g.userData.zc=0;
    return g;
  }
  const body=BUST?bustBody(BUST):buildBody(contents);
  /* The facial detail - eyeballs, irises, eyebrows, lips and the mouth line - is
     separate geometry so it can carry its own colour. It has to fade WITH the
     skin: left opaque it would float as a solid mouth and eyes over a ghost of a
     face at the see-through steps. The nostril marks are gone: two dark ovals at
     that scale only ever read as dots. */
  ['eye','iris','brow','lip','mouth'].forEach(r=>{
    if(G[r] && G[r].parent!==body) body.add(G[r]);
  });
  /* The HAIR is deliberately NOT in that group. It was, on the reasoning that an
     opaque cap over a see-through head reads as a floating wig - and it does. But
     fading it instead only traded one fault for another: at 53% a near-black cap
     over a translucent head reads as a dark ghost, which the user reported from
     more than one angle. Hair is dense geometry, not a veil, so it goes on `shell`
     (same anchor, `body` carries no transform, so this is transform-neutral) and
     app_app.js holds it near-opaque at every step. The real fix for "floating wig"
     is the hair's SHAPE (hair.py), not its opacity. */
  if(G.hair && G.hair.parent!==shell) shell.add(G.hair);
  /* ---- dressing: dock it onto the real skin ------------------------------
     The exported dressing is authored inside the body. The old code pushed it
     radially outward from a body of revolution, which against a real bust left
     it floating in space beside the neck. Instead: find the nearest point on
     the skin surface, take the outward normal there, then rotate the pad so its
     thin axis follows that normal, offset it clear of the surface, and scale it
     so it reads as a dressing at phone size. */
  const skinMeshes=[]; body.traverse(o=>{ if(o.isMesh) skinMeshes.push(o); });
  const _np=new THREE.Vector3(), _nn=new THREE.Vector3();
  function nearestSkin(p, outPoint, outNormal){
    let bestD=Infinity;
    skinMeshes.forEach(o=>{
      const pa=o.geometry.getAttribute('position'); if(!pa) return;
      const na=o.geometry.getAttribute('normal');
      for(let i=0;i<pa.count;i++){
        _np.fromBufferAttribute(pa,i);
        const d=_np.distanceToSquared(p);
        if(d<bestD){ bestD=d; outPoint.copy(_np);
          if(na){ outNormal.fromBufferAttribute(na,i).normalize(); } else { outNormal.set(0,0,1); } }
      } });
    return bestD;
  }
  const dressP=new THREE.Box3().setFromObject(G.dressing).getCenter(new THREE.Vector3());
  const dockP=new THREE.Vector3(), dockN=new THREE.Vector3();
  nearestSkin(dressP, dockP, dockN);
  const outwardToSkin=new THREE.Vector3().subVectors(dockP, dressP);
  if(outwardToSkin.lengthSq()>0 && dockN.dot(outwardToSkin)<0) dockN.negate();
  if(dockN.lengthSq()<0.5) dockN.copy(outwardToSkin).normalize();
  const DRESS_LIFT=0.006, DRESS_SCALE=2.0;
  const dq=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1), dockN);
  const _dp=new THREE.Vector3();
  [...G.dressing.children].forEach(o=>{
    _dp.subVectors(o.position, dressP).multiplyScalar(DRESS_SCALE).applyQuaternion(dq);
    o.position.copy(dressP).add(_dp).addScaledVector(dockN, DRESS_LIFT);
    o.quaternion.premultiply(dq);
    o.scale.multiplyScalar(DRESS_SCALE);
  });
  shell.add(body);
  shell.updateMatrixWorld(true);

  /* ---- nodule pivot: the lesion is scaled on highlight ------------------- */
  const nodC=new THREE.Box3().setFromObject(G.nodule).getCenter(new THREE.Vector3());
  const nodulePivot=new THREE.Group(); nodulePivot.position.copy(nodC);
  [...G.nodule.children].forEach(o=>{ o.position.sub(nodC); nodulePivot.add(o); });
  G.nodule.add(nodulePivot);

  /* ---- anchor the whole scene on the nodule ------------------------------ */
  /* Reported skin entry, restored with the model: this is the value the pre-graft build used, because
     the entry has to lie on THIS bust. It was re-derived for the grafted head, and the graft has now
     been reverted - the earlier model was judged better and the head/neck is its own. If the bust ever
     changes again, re-derive it by casting the needle's axis from the nodule out to the skin.
     Original note (grafted head):
     The sculpt's neck is not the loft's, and the shoulder junction moved from
     1.365 to 1.420 to shorten the visible neck, so the entry was recomputed both
     times by casting the needle's own axis from the nodule out to the skin:
     now (-0.0495, 1.4169, 0.0524), which is 77.2 mm of travel from the nodule.
     Direction is unchanged (entry lateral-inferior-anterior of the nodule,
     needling past the trachea), only the point moved. */
  const ENTRY_G=new THREE.Vector3(-0.0462,1.4216,0.049);
  const AXIS=new THREE.Vector3().subVectors(nodC,ENTRY_G).normalize();
  const shaft=G.needle.getObjectByName('needle__shaft')||G.needle.children[0];
  const sv=new THREE.Vector3(), tip=new THREE.Vector3(); let best=-1e9;
  if(shaft && shaft.geometry){
    shaft.updateMatrix();
    const pa=shaft.geometry.getAttribute('position');
    for(let i=0;i<pa.count;i++){
      sv.fromBufferAttribute(pa,i).applyMatrix4(shaft.matrix);
      const t=sv.dot(AXIS); if(t>best){ best=t; tip.copy(sv); }
    }
  }
  /* ---- orient the needle along the insertion axis -------------------------
     The authored needle points in its own arbitrary direction, so translating it
     until the tip reached the nodule left the SHAFT hanging in mid-air beside the
     neck. Rotate the assembly about its tip until its own long axis lies along
     the insertion axis (skin entry -> nodule), then translate the tip onto the
     nodule. Rotating about the tip first keeps the tip where it belongs. */
  const hub=G.needle.getObjectByName('needle__syringe')||G.needle.children[0];
  const hv=new THREE.Vector3(), _m=new THREE.Matrix4();
  hub.updateMatrix();
  const hp=hub.geometry.getAttribute('position');
  const hubC=new THREE.Vector3();
  for(let i=0;i<hp.count;i++){ hv.fromBufferAttribute(hp,i).applyMatrix4(hub.matrix); hubC.add(hv); }
  hubC.divideScalar(hp.count);
  const ownAxis=new THREE.Vector3().subVectors(tip,hubC).normalize();
  if(ownAxis.lengthSq()>0.5 && AXIS.lengthSq()>0.5){
    const q=new THREE.Quaternion().setFromUnitVectors(ownAxis,AXIS);
    const _tp=new THREE.Vector3(), _dp=new THREE.Vector3();
    [...G.needle.children].forEach(o=>{
      _dp.subVectors(o.position,tip).applyQuaternion(q);
      o.position.copy(tip).add(_dp);
      o.quaternion.premultiply(q);
    });
  }
  const aim=new THREE.Vector3().subVectors(nodC,tip);
  [...G.needle.children].forEach(o=>{ o.position.add(aim); });
  const NEEDLE_HOME=G.needle.position.clone();

  /* ---- make sure the needle actually clears the skin ----------------------
     The tip is in the nodule; the shaft has to reach from there back out through
     the skin, or the needle appears to begin inside the neck. Stretch the shaft
     AWAY from the tip (never move the tip) until its far end clears the skin. */
  (function(){
    const sh=G.needle.getObjectByName('needle__shaft');
    if(!sh||!sh.geometry) return;
    const _sp=new THREE.Vector3(), _sn=new THREE.Vector3(), _q=new THREE.Vector3();
    // how far is the skin from the nodule, measured along the needle axis?
    let skinDist=1e9;
    for(let t=-0.01;t<=0.11;t+=0.002){
      _q.copy(nodC).addScaledVector(AXIS,t);
      const d=nearestSkin(_q.clone(), _sp, _sn);
      if(d<skinDist) skinDist=d;
    }
    skinDist=Math.sqrt(skinDist);
    sh.updateMatrix();
    const pa=sh.geometry.getAttribute('position');
    const _v=new THREE.Vector3(); let lo=1e9, hi=-1e9;
    for(let i=0;i<pa.count;i++){ _v.fromBufferAttribute(pa,i).applyMatrix4(sh.matrix);
      const t=_v.dot(AXIS); if(t<lo)lo=t; if(t>hi)hi=t; }
    const have=hi-lo, need=skinDist+0.025;    // 2.5 cm of needle left outside the skin
    if(need>have){
      const stretch=need-have;
      for(let i=0;i<pa.count;i++){
        _v.fromBufferAttribute(pa,i).applyMatrix4(sh.matrix);
        const f=(_v.dot(AXIS)-lo)/Math.max(1e-6,have);   // 1 at the tip, 0 at the hub end
        const push=(1-f)*stretch;
        pa.setXYZ(i, pa.getX(i)-AXIS.x*push, pa.getY(i)-AXIS.y*push, pa.getZ(i)-AXIS.z*push);
      }
      pa.needsUpdate=true;
      console.log('[needle] stretched '+stretch.toFixed(3)+' m so the hub clears the skin');
    }
  })();

  /* ---- rest the ultrasound probe on the neck -----------------------------
     The probe is authored pointing anteriorly from about the jaw, so it hung in
     the air over the face. A transducer is held with its face flat on the skin,
     over the target, with the body pointing away from the neck. Find the skin in
     front of the nodule, then rotate the probe so its contact face lies in that
     surface and translate it until the face is ON the skin with a hair of contact. */
  (function(){
    const face=G.probe.getObjectByName('probe__footprint');
    const body=G.probe.getObjectByName('probe__body')||G.probe.children[0];
    if(!body) return;
    /* Seek the skin just in front of the nodule. The +6 mm vertical offset put the
       contact point near the jaw on the grafted neck, where the surface bulges
       outward sooner; dropping it to -4 mm and pulling the anterior offset in to
       26 mm puts the contact over the lump itself, which is where the probe has to
       be for the picture to be true. */
    const anchor=nodC.clone().add(new THREE.Vector3(-0.004, -0.004, 0.026));
    const sp=new THREE.Vector3(), sn=new THREE.Vector3();
    nearestSkin(anchor, sp, sn);
    if(sn.lengthSq()<0.25) return;
    const faceC=new THREE.Box3().setFromObject(face||body).getCenter(new THREE.Vector3());
    const bodyC=new THREE.Box3().setFromObject(body).getCenter(new THREE.Vector3());
    const own=new THREE.Vector3().subVectors(faceC,bodyC).normalize();   // body -> contact face
    if(own.lengthSq()<0.25) return;
    const q=new THREE.Quaternion().setFromUnitVectors(own, sn.clone().negate());
    const _dp=new THREE.Vector3();
    [...G.probe.children].forEach(o=>{
      _dp.subVectors(o.position,faceC).applyQuaternion(q);
      o.position.copy(faceC).add(_dp);
      o.quaternion.premultiply(q);
    });
    const fc2=new THREE.Box3().setFromObject(face||body).getCenter(new THREE.Vector3());
    const move=new THREE.Vector3().subVectors(sp,fc2).addScaledVector(sn,0.0015);
    [...G.probe.children].forEach(o=>{ o.position.add(move); });
    console.log('[probe] contact face onto the skin at '
      +sp.toArray().map(v=>v.toFixed(3)).join(','));
  })();

  shell.position.copy(nodC).negate();
  shell.updateMatrixWorld(true);

  const ENTRY=ENTRY_G.clone().sub(nodC);
  const NODULE_WORLD=new THREE.Vector3(0,0,0);
  const SKIN=[]; body.traverse(o=>{ if(o.isMesh){ o.material.side=THREE.FrontSide;
    SKIN.push(o.material); } });

  return {
    scene, root, body, inside, thyroid:G.thyroid,
    parts:{body, inside, skin:SKIN, G, thyroid:G.thyroid, nodule:G.nodule,
           nodulePivot, needle:G.needle, probe:G.probe, dressing:G.dressing,
           skinMesh:body.children[0]},
    anchors:{NODULE_WORLD, ENTRY, TIP:NODULE_WORLD.clone(), AXIS, NEEDLE_HOME}
  };
}

/* neckGroupAdd(parent, child){ parent.add(child); } stood here, a no-op with no call
   sites. Removed: it only ever invited someone to think it did something. */



/* ================================================================ RENDERER ==
   Sequence (Alex, 2026-10-11): head/face/neck -> translucent reveals thyroid
   -> nodule -> back to neck -> probe on the lesion -> needle at 45 deg under
   the probe into the lesion -> 3 passes -> out -> dressing.
   ========================================================================== */
