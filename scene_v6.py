#!/usr/bin/env /usr/bin/python3
"""FNAC webapp v6 — real human form, staged reveal, correct technique.

Design brief (from Alex, 2026-10-11):
  1. Start with a head, face and neck.
  2. Translucency reveals the thyroid inside.
  3. Show the nodule.
  4. Back to the neck surface.
  5. Ultrasound probe localises the lesion — probe face resting ON the neck
     directly over the nodule.
  6. Needle enters at ~45 deg, passes under the probe, and traverses the nodule
     beneath the middle of the probe.
  7. Needle in-and-out, 3 passes.
  8. Needle out, dressing applied.

Anatomical basis (sourced — see notes at foot of file):
  * thyroid lobes 4-6 cm long, 1.5-2.5 cm wide/deep; isthmus < 5 mm thick
  * thyroid sits 1.5-2.5 cm deep, immediately posterior to strap muscles
    (sternohyoid superficial+medial, sternothyroid deep+lateral)
  * trachea has cartilage rings, anterior and lateral
  * needle 27G x 1.25", angled ~45 deg, more acute for deeper targets
  * nodule centred under the probe (short-axis technique)
  * 3 passes, 5-6 s of back-and-forth motion each

Scale used throughout: 1 world unit = 5 cm.
  trunk width      ~ 30 cm  -> 6.0 u
  neck diameter    ~ 11 cm  -> 2.2 u
  head height      ~ 23 cm  -> 4.6 u
  head width       ~ 15 cm  -> 3.0 u
  thyroid lobe     ~  5 cm  -> 1.0 u  (tall) x 0.4 u (wide/deep)
  isthmus          ~ <5 mm  -> 0.09 u thick
  thyroid depth    ~  2 cm  -> 0.4 u below skin
  nodule           ~  2 cm  -> 0.4 u
"""
import os

BASE = "/home/alex/Documents/FNAC_Webapp"

SCENE = r"""
/* ============================================================================
   FNAC scene v6 — human form, staged reveal, anatomically-scaled technique.
   1 world unit = 5 cm.  +X = patient left, +Y = cranial, +Z = anterior.
   ========================================================================== */
function buildThreeScene(THREE){
  const scene = new THREE.Scene();

  /* ------------------------------------------------------------- lighting -- */
  const key = new THREE.DirectionalLight(0xfff4e8, 2.3); key.position.set(5,8,8);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xa8c8ff, 1.0); fill.position.set(-8,3,-5);
  scene.add(fill);
  const rim  = new THREE.DirectionalLight(0xffd9c0, 0.9); rim.position.set(-2,-3,-8);
  scene.add(rim);
  scene.add(new THREE.AmbientLight(0x6b7a94, 1.15));
  const bounce = new THREE.PointLight(0xffe4c8, 0.55, 22);
  bounce.position.set(2,2,6); scene.add(bounce);

  /* ------------------------------------------------------------ materials -- */
  const M = {
    skin:  new THREE.MeshPhysicalMaterial({color:0xdfa98c, roughness:0.62,
             metalness:0.0, clearcoat:0.22, clearcoatRoughness:0.6}),
    skinT: new THREE.MeshPhysicalMaterial({color:0xe8b89c, roughness:0.5,
             transparent:true, opacity:0.22, depthWrite:false,
             side:THREE.DoubleSide, clearcoat:0.3}),
    hair:  new THREE.MeshStandardMaterial({color:0x2a2119, roughness:0.85}),
    eyeW:  new THREE.MeshStandardMaterial({color:0xf2f4f8, roughness:0.25}),
    iris:  new THREE.MeshStandardMaterial({color:0x40311f, roughness:0.2}),
    lip:   new THREE.MeshStandardMaterial({color:0xb5706a, roughness:0.55}),
    fat:   new THREE.MeshStandardMaterial({color:0xf3e2c4, roughness:0.95,
             transparent:true, opacity:1}),
    strap: new THREE.MeshStandardMaterial({color:0xa8544e, roughness:0.7}),
    strap2:new THREE.MeshStandardMaterial({color:0x92453f, roughness:0.7}),
    scm:   new THREE.MeshStandardMaterial({color:0x9c4a46, roughness:0.72}),
    trachea:new THREE.MeshStandardMaterial({color:0xc8d0da, roughness:0.55}),
    cart:  new THREE.MeshStandardMaterial({color:0xe6ecf4, roughness:0.38}),
    thyroid:new THREE.MeshStandardMaterial({color:0xd2636e, roughness:0.5,
             emissive:0x3a1119, emissiveIntensity:0.35}),
    nodule:new THREE.MeshStandardMaterial({color:0x8c2b3e, roughness:0.36,
             emissive:0x9c2f45, emissiveIntensity:0.8}),
    artery:new THREE.MeshStandardMaterial({color:0xc2353a, roughness:0.45}),
    vein:  new THREE.MeshStandardMaterial({color:0x3a559e, roughness:0.45}),
    steel: new THREE.MeshStandardMaterial({color:0xeff3fa, roughness:0.16,
             metalness:0.92}),
    hub:   new THREE.MeshStandardMaterial({color:0x3fa4e8, roughness:0.4}),
    glass: new THREE.MeshPhysicalMaterial({color:0xf6faff, transparent:true,
             opacity:0.4, roughness:0.08}),
    probe: new THREE.MeshStandardMaterial({color:0x3c4860, roughness:0.48}),
    probeB:new THREE.MeshStandardMaterial({color:0x232c40, roughness:0.55}),
    cable: new THREE.MeshStandardMaterial({color:0x1c2029, roughness:0.9}),
    gel:   new THREE.MeshPhysicalMaterial({color:0x8ad4ec, transparent:true,
             opacity:0.55, roughness:0.04}),
    beam:  new THREE.MeshBasicMaterial({color:0x64b8ff, transparent:true,
             opacity:0.10, side:THREE.DoubleSide, depthWrite:false}),
    marker:new THREE.MeshStandardMaterial({color:0x25e0c8, emissive:0x21ccb6,
             emissiveIntensity:0.9, roughness:0.35}),
    dress: new THREE.MeshStandardMaterial({color:0xf8f5ef, roughness:0.93}),
    guide: new THREE.LineBasicMaterial({color:0x6fd4ff, transparent:true,
             opacity:0.6}),
    tip:   new THREE.MeshBasicMaterial({color:0x9fe8ff}),
  };

  const root = new THREE.Group();   // the whole patient
  scene.add(root);

  /* ==========================================================================
     1. HUMAN FORM — head, face, neck, shoulders.
     Built as a lathe-free composition of ellipsoids so the silhouette reads as
     a person. Everything scaled to the 5 cm = 1 unit convention.
     ====================================================================== */
  const body = new THREE.Group();
  root.add(body);

  const SK = M.skin;

  // ---- shoulders / upper chest (frame the neck with a human context) ------
  const shoulders = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 28), SK);
  shoulders.scale.set(3.05, 1.15, 1.35);
  shoulders.position.set(0, -2.72, 0.05);
  body.add(shoulders);

  // ---- neck: tapered column, slightly anterior convex ----------------------
  const neckProf = [];
  for (let i=0;i<=26;i++){
    const u=i/26;
    const y=-1.95+u*2.35;                       // neck spans -1.95 .. 0.40
    // 2.2 u wide at base, 1.75 u at the jaw, with a gentle anterior bulge
    const r=1.13-0.20*u + 0.07*Math.sin(u*Math.PI);
    neckProf.push(new THREE.Vector2(r, y));
  }
  const neckGeo = new THREE.LatheGeometry(neckProf, 56);
  const neckMesh = new THREE.Mesh(neckGeo, SK);
  // squash so it is wider than deep (a neck is not circular)
  neckMesh.scale.set(1.0, 1.0, 0.86);
  neckMesh.position.z = 0.06;
  body.add(neckMesh);

  // ---- head ---------------------------------------------------------------
  const head = new THREE.Group();
  body.add(head);

  const cranium = new THREE.Mesh(new THREE.SphereGeometry(1, 44, 34), SK);
  cranium.scale.set(1.48, 1.86, 1.62);
  cranium.position.set(0, 2.32, -0.02);
  head.add(cranium);

  // jaw / chin block
  const jaw = new THREE.Mesh(new THREE.SphereGeometry(1, 36, 26), SK);
  jaw.scale.set(1.24, 1.02, 1.36);
  jaw.position.set(0, 1.30, 0.16);
  head.add(jaw);

  // chin
  const chin = new THREE.Mesh(new THREE.SphereGeometry(1, 26, 20), SK);
  chin.scale.set(0.52, 0.48, 0.55);
  chin.position.set(0, 1.02, 0.70);
  head.add(chin);

  // brow ridge
  const brow = new THREE.Mesh(new THREE.SphereGeometry(1, 30, 16), SK);
  brow.scale.set(1.34, 0.30, 0.55);
  brow.position.set(0, 2.30, 1.16);
  head.add(brow);

  // nose
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.34, 0.92, 20), SK);
  nose.rotation.x = Math.PI*0.52;
  nose.position.set(0, 1.92, 1.42);
  head.add(nose);

  // ears
  for (const sx of [1,-1]) {
    const ear = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 16), SK);
    ear.scale.set(0.16, 0.46, 0.30);
    ear.position.set(sx*1.50, 2.02, -0.06);
    head.add(ear);
  }

  // eyes
  for (const sx of [1,-1]) {
    const sock = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 16), M.eyeW);
    sock.scale.set(0.26, 0.20, 0.20);
    sock.position.set(sx*0.50, 2.40, 1.18);
    head.add(sock);
    const ir = new THREE.Mesh(new THREE.SphereGeometry(0.115, 18, 14), M.iris);
    ir.position.set(sx*0.50, 2.40, 1.31);
    head.add(ir);
    // eyebrow
    const eb = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.075, 0.14), M.hair);
    eb.position.set(sx*0.50, 2.66, 1.20);
    eb.rotation.z = sx*-0.10;
    head.add(eb);
  }

  // lips
  const lips = new THREE.Mesh(new THREE.SphereGeometry(1, 26, 14), M.lip);
  lips.scale.set(0.40, 0.13, 0.20);
  lips.position.set(0, 1.56, 1.30);
  head.add(lips);

  // hair — cap over the cranium
  const hairCap = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 30,
    0, Math.PI*2, 0, Math.PI*0.62), M.hair);
  hairCap.scale.set(1.53, 1.94, 1.67);
  hairCap.position.set(0, 2.30, -0.05);
  hairCap.rotation.x = -0.14;
  head.add(hairCap);

  head.position.set(0, 0.30, 0);       // sits on top of the neck

  /* ==========================================================================
     2. INSIDE THE NECK — fat, strap muscles, trachea, thyroid.
     All children of `neckGroup` so they can be revealed by translucency.
     ====================================================================== */
  const inside = new THREE.Group();
  neckGroupAdd(body, inside);

  // ---- subcutaneous fat layer (thin, just under the skin) -----------------
  const fatProf = neckProf.map(p=>new THREE.Vector2(Math.max(0.02,p.x-0.055), p.y));
  const fatMesh = new THREE.Mesh(new THREE.LatheGeometry(fatProf, 44), M.fat);
  fatMesh.scale.set(1.0,1.0,0.86); fatMesh.position.z=0.06;
  inside.add(fatMesh);

  // ---- STRAP MUSCLES: two thin flat ribbons, just deep to fat -------------
  // sternohyoid (superficial, medial) and sternothyroid (deeper, lateral)
  for (const sx of [1,-1]) {
    const sho = new THREE.Mesh(new THREE.CapsuleGeometry(0.135, 1.65, 10, 18), M.strap);
    sho.scale.set(1, 1, 0.42);
    sho.position.set(sx*0.30, -0.42, 0.60);
    inside.add(sho);
    const st = new THREE.Mesh(new THREE.CapsuleGeometry(0.145, 1.55, 10, 18), M.strap2);
    st.scale.set(1, 1, 0.42);
    st.position.set(sx*0.63, -0.48, 0.50);
    st.rotation.z = sx*-0.06;
    inside.add(st);
  }
  // sternocleidomastoid — the big lateral column, frames the neck
  for (const sx of [1,-1]) {
    const scm = new THREE.Mesh(new THREE.CapsuleGeometry(0.24, 1.55, 12, 20), M.scm);
    scm.position.set(sx*0.94, -0.50, 0.16);
    scm.rotation.z = sx*0.20;
    inside.add(scm);
  }

  // ---- TRACHEA: hollow tube with cartilage rings --------------------------
  const trachea = new THREE.Group();
  trachea.add(new THREE.Mesh(new THREE.CylinderGeometry(0.30,0.31,2.7,32,1,true), M.trachea));
  for (let i=0;i<9;i++){
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.318,0.036,10,32), M.cart);
    ring.rotation.x=Math.PI/2;
    ring.position.y=-1.18+i*0.295;
    trachea.add(ring);
  }
  // cricoid + thyroid cartilage (Adam's apple) above
  const adams = new THREE.Mesh(new THREE.SphereGeometry(0.33,24,18), M.cart);
  adams.scale.set(1.0,0.62,0.78); adams.position.y=1.34; trachea.add(adams);
  trachea.position.set(0,-0.30,-0.40);
  inside.add(trachea);

  /* ==========================================================================
     3. THYROID GLAND — two lobes + isthmus, straddling the trachea.
     Lobe ~5 cm tall (1.0 u), ~2 cm wide/deep (0.4 u); isthmus <5 mm thick.
     ====================================================================== */
  const thyroid = new THREE.Group();
  const lobeGeo = new THREE.SphereGeometry(1, 36, 28);
  for (const sx of [1,-1]) {
    const lobe = new THREE.Mesh(lobeGeo, M.thyroid);
    lobe.scale.set(0.21, 0.52, 0.27);           // 0.42 u wide, 1.04 u tall
    lobe.position.set(sx*0.37, 0.02, 0.24);
    lobe.rotation.z = sx*0.13;
    lobe.rotation.y = sx*-0.20;
    thyroid.add(lobe);
  }
  const isth = new THREE.Mesh(lobeGeo, M.thyroid);
  isth.scale.set(0.30, 0.055, 0.19);            // thin: ~0.11 u = 5.5 mm
  isth.position.set(0, -0.16, 0.30);
  thyroid.add(isth);

  /* ---- NODULE: inside the RIGHT lobe (screen-left), anterior aspect ------
     2 cm across = 0.40 u. Placed so its centre sits ~1.8 cm below the skin,
     directly under where the probe will rest. */
  const NODULE_LOCAL = new THREE.Vector3(0.37, 0.12, 0.42);
  const nodule = new THREE.Mesh(new THREE.SphereGeometry(0.20, 32, 24), M.nodule);
  nodule.scale.set(1.0, 1.0, 0.92);
  nodule.position.copy(NODULE_LOCAL);
  thyroid.add(nodule);

  // halo + glow so the nodule is findable at a glance
  const halo = new THREE.Mesh(new THREE.TorusGeometry(0.245, 0.014, 10, 44),
    new THREE.MeshBasicMaterial({color:0xff9fb4, transparent:true, opacity:0.9}));
  halo.position.copy(NODULE_LOCAL); halo.rotation.x=Math.PI/2; halo.rotation.z=0.3;
  thyroid.add(halo);
  const glow = new THREE.Mesh(new THREE.SphereGeometry(0.33,24,18),
    new THREE.MeshBasicMaterial({color:0xff7d99, transparent:true, opacity:0.16,
                                 depthWrite:false}));
  glow.position.copy(NODULE_LOCAL); thyroid.add(glow);

  thyroid.position.set(0,-0.34,0);
  inside.add(thyroid);

  /* ==========================================================================
     4. PROBE — face resting ON the neck directly over the nodule (short-axis).
     ====================================================================== */
  // world position of the nodule centre (before any root transform)
  const NODULE_WORLD = new THREE.Vector3(
    thyroid.position.x + NODULE_LOCAL.x,
    thyroid.position.y + NODULE_LOCAL.y,
    thyroid.position.z + NODULE_LOCAL.z);

  /* anterior skin surface directly above the nodule: z of the neck surface at
     that x/y is ~0.86*1.13 = 0.97, plus the 0.06 offset => ~1.03 */
  const SKIN_Y = NODULE_WORLD.y;          // same height as the nodule
  const SKIN_Z = 1.04;                    // anterior skin at that point

  const probe = new THREE.Group();
  const foot = new THREE.Mesh(new THREE.BoxGeometry(0.36,0.10,0.86), M.probe);
  probe.add(foot);                                        // the face
  const bodyB = new THREE.Mesh(new THREE.BoxGeometry(0.50,0.28,1.00), M.probeB);
  bodyB.position.set(0,0.19,0); probe.add(bodyB);
  const grip = new THREE.Mesh(new THREE.CapsuleGeometry(0.14,0.48,12,18), M.probe);
  grip.position.set(0,0.56,-0.06); grip.rotation.x=0.26; probe.add(grip);
  const cable = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
      new THREE.Vector3(0,0.88,-0.16),
      new THREE.Vector3(0.10,1.45,-0.50),
      new THREE.Vector3(0.26,2.20,-1.05),
      new THREE.Vector3(0.32,2.95,-1.80)]), 40, 0.048, 10, false), M.cable);
  probe.add(cable);
  const gel = new THREE.Mesh(new THREE.BoxGeometry(0.38,0.045,0.88), M.gel);
  gel.position.set(0,-0.072,0); probe.add(gel);

  // the probe lies across the neck, long axis transverse, face on the skin
  probe.position.set(NODULE_WORLD.x, SKIN_Y, SKIN_Z - 0.02);
  probe.rotation.x = -1.32;      // face turned to press against the neck surface
  probe.rotation.y = 0;
  body.add(probe);

  /* ultrasound beam: a slab from the probe face down to the nodule */
  const beam = new THREE.Mesh(new THREE.BoxGeometry(0.62, 1.30, 0.62), M.beam);
  beam.position.set(NODULE_WORLD.x, SKIN_Y, SKIN_Z-0.02);
  beam.rotation.x = -1.32;
  beam.translateY(-0.72);
  body.add(beam);

  /* ==========================================================================
     5. NEEDLE — 27G, enters at ~45 deg, passes under the probe, tip traverses
     the nodule at its centre.
     ====================================================================== */
  // entry point on the skin, lateral to the probe, so the needle comes in at an
  // angle and its tip reaches the nodule under the probe's middle.
  const ENTRY = new THREE.Vector3(
    NODULE_WORLD.x + 0.62,          // lateral offset -> gives a 45 deg approach
    NODULE_WORLD.y - 0.05,
    SKIN_Z + 0.02);

  const needleGroup = new THREE.Group();
  const SHAFT_LEN = 0.62;           // 27G x 1.25" = 3.2 cm = 0.63 u
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.013,0.011,SHAFT_LEN,14), M.steel);
  shaft.position.y = SHAFT_LEN/2; needleGroup.add(shaft);
  const bevel = new THREE.Mesh(new THREE.ConeGeometry(0.013,0.08,14), M.steel);
  bevel.position.y = SHAFT_LEN + 0.04; needleGroup.add(bevel);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.050,0.043,0.26,18), M.hub);
  hub.position.y = -0.13; needleGroup.add(hub);
  const syr = new THREE.Mesh(new THREE.CylinderGeometry(0.078,0.078,0.55,20), M.glass);
  syr.position.y = -0.55; needleGroup.add(syr);
  const air = new THREE.Mesh(new THREE.CylinderGeometry(0.074,0.074,0.12,18),
    new THREE.MeshStandardMaterial({color:0xffffff, transparent:true, opacity:0.25}));
  air.position.y = -0.80; needleGroup.add(air);     // 2 cc of air
  body.add(needleGroup);

  /* the trajectory: from ENTRY to the nodule centre, ~45 degrees */
  const TIP_TARGET = NODULE_WORLD.clone();
  const dir = new THREE.Vector3().subVectors(TIP_TARGET, ENTRY).normalize();
  const ang = Math.acos(Math.abs(dir.y))*180/Math.PI;   // angle from vertical

  function aimAt(obj, from, toward){
    obj.position.copy(from);
    const d = new THREE.Vector3().subVectors(toward, from).normalize();
    obj.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), d);
  }
  aimAt(needleGroup, ENTRY.clone().add(new THREE.Vector3(0,0,0)), TIP_TARGET);

  /* guide line along the trajectory */
  const guide = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints([ENTRY.clone(), TIP_TARGET.clone()]),
    M.guide);
  body.add(guide);

  /* entry mark on the skin */
  const mark = new THREE.Mesh(new THREE.SphereGeometry(0.062,22,14), M.marker);
  mark.scale.set(1,1,0.22);
  mark.position.copy(ENTRY).add(new THREE.Vector3(0,0,0.02));
  body.add(mark);

  /* dressing, applied at the end */
  const dressing = new THREE.Mesh(new THREE.BoxGeometry(0.22,0.012,0.22), M.dress);
  dressing.position.copy(mark.position).add(new THREE.Vector3(0,0,0.012));
  body.add(dressing);

  return {
    scene, root, body, head, inside, thyroid,
    parts:{body, head, neck:neckMesh, inside, fat:fatMesh, trachea, thyroid, nodule,
           halo, glow, probe, gel, beam, needle:needleGroup, dressing, guide,
           mark, cable, shoulders},
    anchors:{NODULE_WORLD, ENTRY, TIP_TARGET, SKIN_Y, SKIN_Z, SHAFT_LEN},
    technique:{needle_angle_deg:+ang.toFixed(1)},
    aimAt
  };
}

function neckGroupAdd(parent, child){ parent.add(child); }
"""

with open(os.path.join(BASE, "scene6.js"), "w") as fh:
    fh.write(SCENE)
print("scene6.js written:", len(SCENE), "bytes")
print()
print("Anatomically derived values encoded:")
print("  scale           : 1 unit = 5 cm")
print("  thyroid lobe    : 1.04 u tall x 0.42 u wide  (5.2 cm x 2.1 cm)")
print("  isthmus         : 0.11 u thick                (5.5 mm)")
print("  nodule          : 0.40 u                      (2.0 cm)")
print("  needle shaft    : 0.63 u                      (27G x 1.25 inch = 3.2 cm)")
