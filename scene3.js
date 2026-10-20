
/* ============================================================================
   FNAC 3D scene (three.js)

   Design intent: a patient must be able to answer "where in my neck?", "what
   goes in?", and "what does the doctor see?" from this scene alone. Every
   visible structure exists to answer one of those questions.
   ========================================================================== */
function buildThreeScene(THREE){
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x0a111f, 12, 26);

  /* ------------------------------------------------------------- lighting -- */
  const key = new THREE.DirectionalLight(0xffffff, 2.1);
  key.position.set(4, 7, 6);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x88bbff, 0.85);
  fill.position.set(-6, 2, -4);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xffffff, 0.75);
  rim.position.set(0, -3, -7);
  scene.add(rim);
  scene.add(new THREE.AmbientLight(0x404a5e, 1.15));
  const under = new THREE.PointLight(0xffd9b0, 0.55, 14);
  under.position.set(0, -2.2, 2.4);
  scene.add(under);

  /* ------------------------------------------------------------- materials - */
  const M = {
    skin:   new THREE.MeshPhysicalMaterial({color:0xe8bda6, transparent:true,
              opacity:0.16, roughness:0.75, metalness:0.0, side:THREE.DoubleSide}),
    fat:    new THREE.MeshStandardMaterial({color:0xf0dcc0, transparent:true,
              opacity:0.13, roughness:0.95}),
    muscle: new THREE.MeshStandardMaterial({color:0x9e4444, roughness:0.72}),
    muscle2:new THREE.MeshStandardMaterial({color:0x8a3a3c, roughness:0.72}),
    trachea:new THREE.MeshStandardMaterial({color:0xd8dde4, roughness:0.45}),
    cart:   new THREE.MeshStandardMaterial({color:0xeef1f5, roughness:0.35}),
    thyroid:new THREE.MeshStandardMaterial({color:0xc4485a, roughness:0.55}),
    thyroid2:new THREE.MeshStandardMaterial({color:0xb03e50, roughness:0.55}),
    nodule: new THREE.MeshStandardMaterial({color:0x5e1f30, roughness:0.42,
              emissive:0x3a0f1c, emissiveIntensity:0.5}),
    artery: new THREE.MeshStandardMaterial({color:0xc22b31, roughness:0.5}),
    vein:   new THREE.MeshStandardMaterial({color:0x2f4a8c, roughness:0.5}),
    steel:  new THREE.MeshStandardMaterial({color:0xdfe6f0, roughness:0.22,
              metalness:0.85}),
    hub:    new THREE.MeshStandardMaterial({color:0x2f8fd0, roughness:0.4}),
    glassy: new THREE.MeshPhysicalMaterial({color:0xf2f6ff, transparent:true,
              opacity:0.42, roughness:0.15, metalness:0.05}),
    probe:  new THREE.MeshStandardMaterial({color:0x2b3346, roughness:0.55}),
    probeB: new THREE.MeshStandardMaterial({color:0x1c2233, roughness:0.6}),
    cable:  new THREE.MeshStandardMaterial({color:0x15181f, roughness:0.85}),
    gel:    new THREE.MeshPhysicalMaterial({color:0x74c4e8, transparent:true,
              opacity:0.55, roughness:0.05, transmission:0.6}),
    beam:   new THREE.MeshBasicMaterial({color:0x59a8ff, transparent:true,
              opacity:0.10, side:THREE.DoubleSide, depthWrite:false}),
    marker: new THREE.MeshStandardMaterial({color:0x1fd6c0,
              emissive:0x18b8a6, emissiveIntensity:0.8, roughness:0.4}),
    dressing:new THREE.MeshStandardMaterial({color:0xf5f2ec, roughness:0.9}),
  };

  /* =================================================================== NECK */
  // The neck is a group so the whole thing can tilt (head tipped back).
  const neck = new THREE.Group();
  scene.add(neck);

  // --- outer skin: an open shell so you can see inside ---
  const skinGeo = new THREE.CylinderGeometry(1.55, 1.75, 4.2, 48, 1, true,
                                             -Math.PI*0.62, Math.PI*1.24);
  const skin = new THREE.Mesh(skinGeo, M.skin);
  skin.position.set(0, 0.1, 0);
  neck.add(skin);

  // --- fat layer just under the skin ---
  const fat = new THREE.Mesh(
    new THREE.CylinderGeometry(1.36, 1.55, 4.0, 40, 1, true,
                               -Math.PI*0.60, Math.PI*1.20), M.fat);
  fat.position.set(0, 0.1, 0);
  neck.add(fat);

  // --- sternocleidomastoid (the big oblique neck muscle), both sides ---
  for (const sx of [1,-1]) {
    const scm = new THREE.Mesh(new THREE.CapsuleGeometry(0.26, 2.3, 12, 20), M.muscle);
    scm.position.set(sx*1.02, 0.35, 0.28);
    scm.rotation.z = sx*0.20;
    scm.rotation.x = 0.06;
    neck.add(scm);
  }
  // --- strap muscles: the thin layer in front of the thyroid ---
  for (const sx of [1,-1]) {
    const strap = new THREE.Mesh(new THREE.CapsuleGeometry(0.115, 2.0, 10, 16), M.muscle2);
    strap.position.set(sx*0.30, 0.10, 0.52);
    neck.add(strap);
  }

  // --- trachea: ringed cartilage. The landmark patients recognise. ---
  const trachea = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.30, 0.31, 3.0, 32), M.trachea);
  trachea.add(trunk);
  for (let i = 0; i < 9; i++){
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.315, 0.038, 10, 32), M.cart);
    ring.rotation.x = Math.PI/2;
    ring.position.y = -1.30 + i*0.325;
    trachea.add(ring);
  }
  trachea.position.set(0, -0.15, -0.42);
  neck.add(trachea);

  // --- thyroid: two lobes + isthmus = the butterfly shape ---
  const thyroid = new THREE.Group();
  const lobeGeo = new THREE.SphereGeometry(0.5, 32, 24);
  for (const sx of [1,-1]) {
    const lobe = new THREE.Mesh(lobeGeo, M.thyroid);
    lobe.scale.set(0.62, 1.28, 0.66);      // tall, flattened lobe
    lobe.position.set(sx*0.46, 0.02, 0.16);
    lobe.rotation.z = sx*0.10;
    thyroid.add(lobe);
  }
  const isthmus = new THREE.Mesh(new THREE.SphereGeometry(0.30, 26, 18), M.thyroid2);
  isthmus.scale.set(1.15, 0.52, 0.72);
  isthmus.position.set(0, -0.16, 0.30);
  thyroid.add(isthmus);

  // --- the nodule: sits INSIDE the right lobe, clearly a mass ---
  const nodule = new THREE.Mesh(new THREE.SphereGeometry(0.20, 28, 20), M.nodule);
  nodule.scale.set(1.0, 1.22, 1.0);
  nodule.position.set(0.50, 0.14, 0.30);
  thyroid.add(nodule);
  // a subtle halo ring so the nodule is findable at any angle
  const halo = new THREE.Mesh(new THREE.TorusGeometry(0.235, 0.018, 10, 40),
    new THREE.MeshBasicMaterial({color:0xff8fa8, transparent:true, opacity:0.75}));
  halo.position.copy(nodule.position);
  halo.rotation.x = Math.PI/2.2;
  thyroid.add(halo);
  neck.add(thyroid);

  // --- carotid artery and internal jugular vein: what ultrasound avoids ---
  for (const sx of [1,-1]) {
    const car = new THREE.Mesh(new THREE.CylinderGeometry(0.115, 0.12, 2.8, 20), M.artery);
    car.position.set(sx*0.90, 0.05, -0.34);
    neck.add(car);
    const ijv = new THREE.Mesh(new THREE.CylinderGeometry(0.095, 0.10, 2.8, 20), M.vein);
    ijv.position.set(sx*0.70, 0.05, -0.62);
    neck.add(ijv);
  }

  // --- the marked entry point on the skin ---
  const marker = new THREE.Mesh(new THREE.SphereGeometry(0.072, 22, 14), M.marker);
  marker.scale.set(1, 0.22, 1);
  marker.position.set(0.50, 1.14, 0.72);
  neck.add(marker);

  /* ================================================================== PROBE */
  const probe = new THREE.Group();
  // footprint (the face that touches the skin)
  const foot = new THREE.Mesh(new THREE.BoxGeometry(0.50, 0.10, 0.90), M.probe);
  probe.add(foot);
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.30, 1.02), M.probeB);
  body.position.set(0, 0.20, 0);
  probe.add(body);
  const grip = new THREE.Mesh(new THREE.CapsuleGeometry(0.15, 0.55, 12, 18), M.probe);
  grip.position.set(0, 0.62, -0.10);
  grip.rotation.x = 0.30;
  probe.add(grip);
  // cable leaving the top — makes it obviously an ultrasound probe
  const cable = new THREE.Mesh(new THREE.CatmullRomCurve3
    ? new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
        new THREE.Vector3(0,0.95,-0.20), new THREE.Vector3(0.15,1.5,-0.55),
        new THREE.Vector3(0.35,2.2,-1.1), new THREE.Vector3(0.4,2.9,-1.9)]),
        32, 0.055, 10, false)
    : new THREE.CylinderGeometry(0.055,0.055,1.6,12), M.cable);
  probe.add(cable);
  // gel layer between probe and skin
  const gel = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.045, 0.92), M.gel);
  gel.position.set(0, -0.075, 0);
  probe.add(gel);
  neck.add(probe);

  /* ============================================================ ULTRASOUND BEAM */
  // A cone from the footprint down to the nodule: shows what the screen images.
  const beamGeo = new THREE.ConeGeometry(0.62, 1.45, 28, 1, true);
  const beam = new THREE.Mesh(beamGeo, M.beam);
  beam.position.set(0.50, 0.42, 0.34);
  beam.rotation.x = 0.10;
  neck.add(beam);

  /* ================================================================= NEEDLE */
  const needle = new THREE.Group();
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.013, 1.30, 14), M.steel);
  shaft.position.y = 0.30;
  needle.add(shaft);
  const bevel = new THREE.Mesh(new THREE.ConeGeometry(0.015, 0.09, 14), M.steel);
  bevel.position.y = 0.995;
  needle.add(bevel);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.048, 0.30, 18), M.hub);
  hub.position.y = -0.48;
  needle.add(hub);
  const syringe = new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.085, 0.46, 20), M.glassy);
  syringe.position.y = -0.88;
  needle.add(syringe);
  neck.add(needle);

  /* =============================================================== DRESSING */
  const dressing = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.016, 0.26), M.dressing);
  dressing.position.set(0.50, 1.13, 0.72);
  neck.add(dressing);

  return {scene, neck, parts:{
    skin, fat, trachea, thyroid, nodule, halo, marker, probe, gel, beam,
    needle, hub, syringe, dressing, cable
  }};
}
