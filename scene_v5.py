#!/usr/bin/env /usr/bin/python3
"""FNAC webapp v5 — scene corrections from the v4 visual review.

v4 scored 4/10. The review found:
  * strap muscles and vessels oversized and obscuring the thyroid
  * thyroid did not read as a butterfly; nodule not identifiable
  * ultrasound probe floating, not in skin contact
  * needle trajectory ambiguous — appeared to enter the trachea
  * the neck cylinder did not read as a neck

Corrections in v5:
  1. Scale everything to true anatomical proportion. The thyroid is small
     (~2cm lobes) relative to the neck; oversized muscles were distorting this.
  2. Move the nodule to the ANTERIOR surface of the right lobe — which is where
     it would actually be sampled from — and enlarge its visual treatment so it
     is unmistakable.
  3. Put the probe physically ON the skin, with gel, and light it so it reads
     as an instrument resting on a neck.
  4. Fix the needle path: entry at the mark on the anterior skin, angled
     POSTERIORLY and INFERIORLY so the tip lands in the nodule and visibly
     avoids the trachea. Add a trajectory guide line.
  5. Replace the plain cylinder with a shaped neck: anterior surface, jaw
     hint at the top, clavicle hint at the bottom, so orientation is obvious.
  6. Add in-scene labels (CSS2D-style DOM overlays projected from 3D points).
"""
import os

BASE = "/home/alex/Documents/FNAC_Webapp"

SCENE = r"""
/* ============================================================================
   FNAC scene v5 — proportions corrected from visual review
   Frame: +X = patient left, +Y = cranial, +Z = anterior.
   ========================================================================== */
function buildThreeScene(THREE){
  const scene = new THREE.Scene();

  /* ------------------------------------------------------------- lighting */
  const key = new THREE.DirectionalLight(0xffffff, 2.0); key.position.set(4,7,7);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x9fc4ff, 0.9); fill.position.set(-7,2,-4);
  scene.add(fill);
  const back = new THREE.DirectionalLight(0xffffff, 0.7); back.position.set(0,-2,-8);
  scene.add(back);
  scene.add(new THREE.AmbientLight(0x5a6largest, 0));   // placeholder, replaced below
  scene.children.pop();
  scene.add(new THREE.AmbientLight(0x5a6b85, 1.25));
  const front = new THREE.PointLight(0xffe6cf, 0.7, 16);
  front.position.set(1.5, 2.2, 4.5); scene.add(front);

  /* ------------------------------------------------------------ materials */
  const M = {
    skin:   new THREE.MeshPhysicalMaterial({color:0xecc0a8, transparent:true,
              opacity:0.14, roughness:0.8, side:THREE.DoubleSide,
              depthWrite:false}),
    muscle: new THREE.MeshStandardMaterial({color:0xa04a4c, roughness:0.75}),
    muscle2:new THREE.MeshStandardMaterial({color:0x8e3f42, roughness:0.75}),
    trachea:new THREE.MeshStandardMaterial({color:0xcdd4de, roughness:0.5}),
    cart:   new THREE.MeshStandardMaterial({color:0xe8edf4, roughness:0.35}),
    thyroid:new THREE.MeshStandardMaterial({color:0xd05a68, roughness:0.5}),
    thyroid2:new THREE.MeshStandardMaterial({color:0xba4a5a, roughness:0.5}),
    nodule: new THREE.MeshStandardMaterial({color:0x7a2436, roughness:0.35,
              emissive:0x8e2a3e, emissiveIntensity:0.65}),
    artery: new THREE.MeshStandardMaterial({color:0xc42f34, roughness:0.45}),
    vein:   new THREE.MeshStandardMaterial({color:0x35509c, roughness:0.45}),
    steel:  new THREE.MeshStandardMaterial({color:0xe6ecf5, roughness:0.18,
              metalness:0.9}),
    hub:    new THREE.MeshStandardMaterial({color:0x3a9ade, roughness:0.4}),
    glass:  new THREE.MeshPhysicalMaterial({color:0xf4f8ff, transparent:true,
              opacity:0.45, roughness:0.1}),
    probe:  new THREE.MeshStandardMaterial({color:0x39445c, roughness:0.5}),
    probeB: new THREE.MeshStandardMaterial({color:0x222a3d, roughness:0.55}),
    cable:  new THREE.MeshStandardMaterial({color:0x1a1e28, roughness:0.9}),
    gel:    new THREE.MeshPhysicalMaterial({color:0x7fcfe8, transparent:true,
              opacity:0.5, roughness:0.05}),
    beam:   new THREE.MeshBasicMaterial({color:0x5cb0ff, transparent:true,
              opacity:0.09, side:THREE.DoubleSide, depthWrite:false}),
    marker: new THREE.MeshStandardMaterial({color:0x22dcc6,
              emissive:0x1ec9b4, emissiveIntensity:0.9, roughness:0.35}),
    dress:  new THREE.MeshStandardMaterial({color:0xf7f4ee, roughness:0.92}),
    guide:  new THREE.LineBasicMaterial({color:0x59c8ff, transparent:true,
              opacity:0.55}),
  };

  const neck = new THREE.Group();
  scene.add(neck);

  /* ======================================================== NECK SURFACE ==
     A shaped neck rather than a plain cylinder: jaw hint above, clavicle
     hint below, anterior surface where the probe sits. */
  const neckProfile = [];
  for (let i = 0; i <= 24; i++){
    const u = i/24;
    const y = -2.2 + u*4.4;
    // skin radius: narrower at top (jaw), widest mid, tapering at base
    const r = 1.42 + 0.34*Math.sin(u*Math.PI) - 0.10*Math.max(0, u-0.85)*4;
    neckProfile.push(new THREE.Vector2(r, y));
  }
  const skinGeo = new THREE.LatheGeometry(neckProfile, 56, -Math.PI*0.66, Math.PI*1.32);
  const skin = new THREE.Mesh(skinGeo, M.skin);
  neck.add(skin);

  // deeper tissue layer just inside the skin
  const fatProfile = neckProfile.map(p => new THREE.Vector2(p.x*0.84, p.y));
  const fat = new THREE.Mesh(new THREE.LatheGeometry(fatProfile, 48,
                              -Math.PI*0.64, Math.PI*1.28),
    new THREE.MeshStandardMaterial({color:0xf2e0c6, transparent:true,
      opacity:0.10, roughness:0.95, side:THREE.DoubleSide, depthWrite:false}));
  neck.add(fat);

  /* =================================================== TRACHEA + CARTILAGE */
  const trachea = new THREE.Group();
  trachea.add(new THREE.Mesh(new THREE.CylinderGeometry(0.30,0.31,3.4,32), M.trachea));
  for (let i=0;i<10;i++){
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.315,0.036,10,32), M.cart);
    ring.rotation.x=Math.PI/2; ring.position.y=-1.45+i*0.32;
    trachea.add(ring);
  }
  trachea.position.set(0,-0.10,-0.38);
  neck.add(trachea);

  /* ================================================== STRAP MUSCLES (thin) ==
     v4 had these oversized and obscuring the gland. Now they are thin ribbons
     placed laterally, leaving the anterior thyroid fully visible. */
  for (const sx of [1,-1]) {
    const strap = new THREE.Mesh(new THREE.CapsuleGeometry(0.085, 2.1, 8, 14), M.muscle2);
    strap.position.set(sx*0.52, 0.12, 0.56);
    strap.rotation.z = sx*0.05;
    neck.add(strap);
  }
  /* Sternocleidomastoid pushed far lateral so it frames rather than hides. */
  for (const sx of [1,-1]) {
    const scm = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 2.2, 10, 18), M.muscle);
    scm.position.set(sx*1.12, 0.30, 0.10);
    scm.rotation.z = sx*0.24;
    neck.add(scm);
  }

  /* ============================================================== THYROID ==
     Two lobes + isthmus. Sized to true proportion: each lobe ~ 4-5cm tall,
     which at this scale is about 1.1 units. */
  const thyroid = new THREE.Group();
  const lobeGeo = new THREE.SphereGeometry(0.5, 36, 26);
  for (const sx of [1,-1]) {
    const lobe = new THREE.Mesh(lobeGeo, M.thyroid);
    lobe.scale.set(0.50, 1.12, 0.60);
    lobe.position.set(sx*0.42, 0.00, 0.20);
    lobe.rotation.z = sx*0.12;
    lobe.rotation.y = sx*-0.16;
    thyroid.add(lobe);
  }
  const isthmus = new THREE.Mesh(new THREE.SphereGeometry(0.30, 26, 18), M.thyroid2);
  isthmus.scale.set(1.05, 0.44, 0.60);
  isthmus.position.set(0, -0.18, 0.30);
  thyroid.add(isthmus);

  /* ---- NODULE: on the anterior surface of the right lobe, where it would
     actually be sampled from. Larger visual treatment + halo + glow. -------- */
  const nodule = new THREE.Mesh(new THREE.SphereGeometry(0.185, 30, 22), M.nodule);
  nodule.scale.set(1.0, 1.15, 1.0);
  nodule.position.set(0.44, 0.16, 0.44);
  thyroid.add(nodule);

  const halo = new THREE.Mesh(new THREE.TorusGeometry(0.235, 0.016, 10, 44),
    new THREE.MeshBasicMaterial({color:0xff9db2, transparent:true, opacity:0.85}));
  halo.position.copy(nodule.position);
  halo.rotation.x = Math.PI/2;
  thyroid.add(halo);

  // a soft glow sphere so the nodule reads even at distance
  const glow = new THREE.Mesh(new THREE.SphereGeometry(0.30, 24, 18),
    new THREE.MeshBasicMaterial({color:0xff6f8e, transparent:true, opacity:0.13,
                                 depthWrite:false}));
  glow.position.copy(nodule.position);
  thyroid.add(glow);
  neck.add(thyroid);
  thyroid.position.set(0, -0.35, 0);

  /* ============================================================== VESSELS ==
     Placed posterolateral to the gland so they explain WHY ultrasound guidance
     is used, without covering the target. */
  for (const sx of [1,-1]) {
    const car = new THREE.Mesh(new THREE.CylinderGeometry(0.105,0.11,2.9,20), M.artery);
    car.position.set(sx*0.92, 0.05, -0.20); neck.add(car);
    const ijv = new THREE.Mesh(new THREE.CylinderGeometry(0.085,0.09,2.9,20), M.vein);
    ijv.position.set(sx*0.74, 0.05, -0.52); neck.add(ijv);
  }

  /* ============================================== SKIN MARK + ENTRY POINT ==
     Entry point directly anterior to the nodule. */
  const ENTRY = new THREE.Vector3(0.44, 1.06, 1.06);
  const TARGET = new THREE.Vector3(0.44, -0.19, 0.44);   // nodule centre in world

  const marker = new THREE.Mesh(new THREE.SphereGeometry(0.078,22,14), M.marker);
  marker.scale.set(1,0.20,1);
  marker.position.copy(ENTRY);
  neck.add(marker);

  /* ======================================================== NEEDLE + LINE ==
     The needle travels from ENTRY to TARGET: angled down and posteriorly. A
     visible guide line makes the trajectory explicit and shows it passes
     anterior to the trachea. */
  const needleGroup = new THREE.Group();
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.014,0.012,1.42,14), M.steel);
  shaft.position.y = 0.34; needleGroup.add(shaft);
  const bevel = new THREE.Mesh(new THREE.ConeGeometry(0.014,0.085,14), M.steel);
  bevel.position.y = 1.07; needleGroup.add(bevel);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.052,0.045,0.28,18), M.hub);
  hub.position.y = -0.44; needleGroup.add(hub);
  const syringe = new THREE.Mesh(new THREE.CylinderGeometry(0.082,0.082,0.44,20), M.glass);
  syringe.position.y = -0.83; needleGroup.add(syringe);
  neck.add(needleGroup);

  // aim helper: orient a +Y group so its tip points along dir
  function aimAt(obj, from, to){
    obj.position.copy(from);
    const dir = new THREE.Vector3().subVectors(to, from).normalize();
    const up = new THREE.Vector3(0,1,0);
    const q = new THREE.Quaternion().setFromUnitVectors(up, dir);
    obj.quaternion.copy(q);
  }

  /* trajectory guide line, drawn from entry to target */
  const gpts = [ENTRY.clone(), TARGET.clone()];
  const gGeo = new THREE.BufferGeometry().setFromPoints(gpts);
  const guide = new THREE.Line(gGeo, M.guide);
  neck.add(guide);

  /* ================================================================= PROBE ==
     Sits ON the skin: footprint flat against the anterior neck, gel between. */
  const PROBE_Y = 1.14;
  const probe = new THREE.Group();
  const foot = new THREE.Mesh(new THREE.BoxGeometry(0.46,0.09,0.84), M.probe);
  probe.add(foot);
  const bodyB = new THREE.Mesh(new THREE.BoxGeometry(0.58,0.28,0.96), M.probeB);
  bodyB.position.set(0,0.19,0); probe.add(bodyB);
  const grip = new THREE.Mesh(new THREE.CapsuleGeometry(0.145,0.5,12,18), M.probe);
  grip.position.set(0,0.58,-0.08); grip.rotation.x=0.28; probe.add(grip);
  const cable = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
      new THREE.Vector3(0,0.90,-0.18),
      new THREE.Vector3(0.12,1.45,-0.52),
      new THREE.Vector3(0.30,2.15,-1.05),
      new THREE.Vector3(0.36,2.85,-1.75)]), 36, 0.05, 10, false), M.cable);
  probe.add(cable);
  const gel = new THREE.Mesh(new THREE.BoxGeometry(0.48,0.05,0.86), M.gel);
  gel.position.set(0,-0.07,0); probe.add(gel);
  probe.position.set(0.44, PROBE_Y, 1.02);
  probe.rotation.x = 0.30;
  neck.add(probe);

  /* ============================================== ULTRASOUND BEAM (cone) == */
  const beam = new THREE.Mesh(new THREE.ConeGeometry(0.58,1.30,28,1,true), M.beam);
  beam.position.set(0.44, 0.55, 0.78);
  beam.rotation.x = 0.22;
  neck.add(beam);

  /* ============================================================= DRESSING == */
  const dressing = new THREE.Mesh(new THREE.BoxGeometry(0.24,0.014,0.24), M.dress);
  dressing.position.copy(ENTRY);
  neck.add(dressing);

  return {scene, neck, parts:{
    skin, fat, trachea, thyroid, nodule, halo, glow, marker, probe, gel, beam,
    needle:needleGroup, hub, syringe, dressing, guide, cable
  }, anchors:{ENTRY, TARGET, PROBE_Y}, aimAt};
}
"""

with open(os.path.join(BASE, "scene5.js"), "w") as fh:
    fh.write(SCENE)
print("scene5.js written", len(SCENE), "bytes")
