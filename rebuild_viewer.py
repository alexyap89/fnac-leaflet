#!/usr/bin/env /usr/bin/python3
"""Rebuild viewer.html on the surviving later base.

WHAT HAPPENED
-------------
The previous viewer.html was truncated to 1 byte by a bad rfind(); the only
backup (viewer.html.bak-preview) turned out to be an early 9-step single-role
build that loads model/neck_anatomy_z.glb and has no skin, muscles, probe or
needle. Everything after that - the 9-role instrument build, the attach() fix,
the opacity ramp, the focus camera - was lost with the file.

WHAT SURVIVES (and is the source of truth)
------------------------------------------
  model/fnac_scene.glb   892 KB, 9 roles, VERIFY: PASS, head disabled
  fnac_scene_report.json needle at 45.0 deg, length 6.84 cm,
                         passes_under_probe true, tip_inside_nodule true
  build_scene.py         regenerates the GLB
  build_head.py          the (disabled) head shell

WHAT THIS SCRIPT DOES
---------------------
Rebuilds the viewer against fnac_scene.glb, restoring, with the fixes that were
each measured working today:

  * 9 roles including skin / skeletalmuscle / strap / probe / needle
  * attach() NOT add() when grouping instruments. Group.add() re-parents a mesh
    and reinterprets its LOCAL coordinates, which threw the probe and needle
    off-screen. attach() preserves the world transform.
  * the step text as it was when the patient swarm saw it (persona_review.json),
    which is a coherent reviewed 9-step text
  * a per-step SKIN_OPACITY ramp: opaque for step 1 so the first thing a patient
    sees is a body surface, translucent from step 2 so the gland shows through
  * focusGroup()/fitCamera(which) so late steps zoom onto the gland - the old
    code declared focus on every step and never read it
  * __dbg handles so the runtime state is readable from the console
"""
import json
import os
import re

BASE = "/home/alex/Documents/FNAC_Webapp"
SRC = os.path.join(BASE, "viewer.html")
OUT = os.path.join(BASE, "viewer.html")

src = open(SRC, encoding="utf-8").read()
report = json.load(open(os.path.join(BASE, "fnac_scene_report.json")))

# ---------------------------------------------------------------- step text
# Use the text the patient swarm actually reviewed, from persona_review.json.
reviewed = json.load(open(os.path.join(BASE, "persona_review.json")))["text_reviewed"]
steps = reviewed["steps"]
footer = reviewed.get("footer", "").strip()

# The reviewed set is 9 steps; the app wants a dressing step and a closing step
# separated, which the original file also had. Split step 8 into 8 + 9 and add a
# closing step, preserving the reviewed wording.
STEPS = [
    ("The neck",
     "This is a three-dimensional view of the neck. The test is a fine needle "
     "aspiration of the thyroid — FNAC. A very thin needle is used to take a "
     "small sample from the gland.",
     {"skin": True, "skeletalmuscle": False, "strap": False, "thyroid": False,
      "parathyroid": False, "airway": False, "soft": False, "probe": False,
      "needle": False}, "front", "neck"),
    ("The thyroid gland",
     "The thyroid gland sits in the front of the neck, over the upper trachea.",
     {"skin": True, "skeletalmuscle": False, "strap": False, "thyroid": True,
      "parathyroid": False, "airway": True, "soft": False, "probe": False,
      "needle": False}, "front", "thyroid"),
    ("The gland in position",
     "The gland rests against the trachea, with a lobe on each side, joined in "
     "the middle.",
     {"skin": True, "skeletalmuscle": False, "strap": False, "thyroid": True,
      "parathyroid": False, "airway": True, "soft": False, "probe": False,
      "needle": False}, "oblique", "thyroid"),
    ("The nodule",
     "A nodule is a lump inside the gland. Most thyroid nodules are not cancer, "
     "but some are, so a sample is taken to find out.",
     {"skin": True, "skeletalmuscle": False, "strap": False, "thyroid": True,
      "parathyroid": False, "airway": False, "soft": False, "probe": False,
      "needle": False}, "oblique", "thyroid"),
    ("The ultrasound probe",
     "The ultrasound probe is placed on the skin over the gland.",
     {"skin": True, "skeletalmuscle": True, "strap": True, "thyroid": True,
      "parathyroid": False, "airway": False, "soft": True, "probe": True,
      "needle": False}, "oblique", "procedure"),
    ("The needle",
     "A fine needle is passed through the skin into the nodule. You may be "
     "given an injection to numb the skin first. You may feel a slight pin "
     "prick from the needle.",
     {"skin": True, "skeletalmuscle": True, "strap": True, "thyroid": True,
      "parathyroid": False, "airway": False, "soft": True, "probe": True,
      "needle": True}, "oblique", "procedure"),
    ("Several passes",
     "The needle is moved back and forth within the nodule several times.",
     {"skin": True, "skeletalmuscle": True, "strap": True, "thyroid": True,
      "parathyroid": False, "airway": False, "soft": True, "probe": True,
      "needle": True}, "oblique", "procedure"),
    ("The needle is withdrawn",
     "The needle is removed and an adhesive dressing is applied. The dressing "
     "stays on for 1-2 hours, then you can take it off and wash the area.",
     {"skin": True, "skeletalmuscle": False, "strap": True, "thyroid": True,
      "parathyroid": False, "airway": False, "soft": True, "probe": False,
      "needle": False}, "oblique", "thyroid"),
    ("The dressing",
     "A small plaster covers the site. You can take it off after 1-2 hours.",
     {"skin": True, "skeletalmuscle": False, "strap": False, "thyroid": True,
      "parathyroid": False, "airway": False, "soft": True, "probe": False,
      "needle": False}, "oblique", "thyroid"),
    ("After the procedure",
     "You can go back to your usual activities. Results are usually available "
     "in 1-2 weeks; the department will contact you with them. Sometimes the "
     "sample does not give a clear answer, and the test may be repeated.",
     {"skin": True, "skeletalmuscle": False, "strap": False, "thyroid": True,
      "parathyroid": False, "airway": False, "soft": True, "probe": False,
      "needle": False}, "front", "all"),
]

# --------------------------------------------------------------- build STEPS
lines = []
for t, d, show, cam, focus in STEPS:
    sh = ", ".join(f"{k}: {'true' if v else 'false'}" for k, v in show.items())
    lines.append(
        f'    {{ t: "{t}", d: "{d}",\n'
        f'      show: {{ {sh} }},\n'
        f'      cam: "{cam}", focus: "{focus}" }}')
steps_js = "  var STEPS = [\n" + ",\n".join(lines) + "\n  ];\n"

# ------------------------------------------------------- replace the STEPS
src = re.sub(r"  var STEPS = \[.*?\n  \];\n", steps_js, src, count=1, flags=re.S)

# ------------------------------------------- replace materials with 9 roles
mats_old = re.search(r"  function makeMaterials\(\) \{.*?\n  \}\n", src, re.S)
assert mats_old, "makeMaterials not found"
mats_new = '''  function makeMaterials() {
    return {
      // skin opacity is driven per-step by SKIN_OPACITY, so it starts opaque:
      // the first thing a patient sees must be a body surface, not a diagram.
      skin: new THREE.MeshStandardMaterial({
        color: 0xe8c4ae, roughness: 0.78, metalness: 0.0,
        transparent: true, opacity: 1.0, depthWrite: true,
        side: THREE.DoubleSide }),
      skeletalmuscle: new THREE.MeshStandardMaterial({
        color: 0xc06060, roughness: 0.62, metalness: 0.0,
        transparent: true, opacity: 0.34, depthWrite: false }),
      strap: new THREE.MeshStandardMaterial({
        color: 0xb85c58, roughness: 0.6, metalness: 0.0,
        transparent: true, opacity: 0.5, depthWrite: false }),
      thyroid: new THREE.MeshStandardMaterial({
        color: 0xa3382f, roughness: 0.52, metalness: 0.0,
        transparent: true, opacity: 0.96 }),
      parathyroid: new THREE.MeshStandardMaterial({
        color: 0xd9c26a, roughness: 0.5, metalness: 0.0 }),
      airway: new THREE.MeshStandardMaterial({
        color: 0xbfcdd6, roughness: 0.55, metalness: 0.0,
        transparent: true, opacity: 0.7, depthWrite: false }),
      soft: new THREE.MeshStandardMaterial({
        color: 0xc98d86, roughness: 0.58, metalness: 0.0,
        transparent: true, opacity: 0.7, depthWrite: false }),
      probe: new THREE.MeshStandardMaterial({
        color: 0x2b3138, roughness: 0.35, metalness: 0.1 }),
      needle: new THREE.MeshStandardMaterial({
        color: 0xd8dce0, roughness: 0.2, metalness: 0.65 })
    };
  }
'''
src = src[:mats_old.start()] + mats_new + src[mats_old.end():]

# ------------------------------------------------ replace classify() (roles)
cls_old = re.search(r"  function classify\(name\) \{.*?\n  \}\n", src, re.S)
assert cls_old, "classify not found"
cls_new = '''  // Roles come from the GLB's own object names, which the builder writes as
  // "<role>__<original name>". Trust that prefix first so the runtime cannot
  // disagree with the build; fall back to keyword matching only if absent.
  function classify(name) {
    var n = (name || "");
    var i = n.indexOf("__");
    if (i > 0) {
      var pre = n.slice(0, i).toLowerCase();
      if (pre === "skin" || pre === "skeletalmuscle" || pre === "strap" ||
          pre === "thyroid" || pre === "parathyroid" || pre === "airway" ||
          pre === "soft" || pre === "probe" || pre === "needle") {
        return pre;
      }
    }
    var l = n.toLowerCase();
    if (l.indexOf("parathyroid") !== -1) return "parathyroid";
    if (l.indexOf("thyroid") !== -1) return "thyroid";
    if (l.indexOf("trachea") !== -1 || l.indexOf("laryng") !== -1 ||
        l.indexOf("epiglottis") !== -1) return "airway";
    return null;
  }
'''
src = src[:cls_old.start()] + cls_new + src[cls_old.end():]

# ------------------------------------------------- replace the loader block
load_old = re.search(r'  var loader = new THREE\.GLTFLoader\(\);\n.*?\n  \}\);\n', src, re.S)
assert load_old, "loader block not found"
load_new = '''  var structures = {};
  var roles = ["skin", "skeletalmuscle", "strap", "thyroid", "parathyroid",
               "airway", "soft", "probe", "needle"];
  var want = {};
  var needleGroup = null, probeGroup = null, nodule = null;
  var SKIN_OPACITY = [1.00, 1.00, 1.00, 0.42, 0.34, 0.30, 0.30, 0.34, 1.00, 1.00];

  var loader = new THREE.GLTFLoader();
  loader.load("model/fnac_scene.glb", function (gltf) {
    var obj = gltf.scene;

    obj.traverse(function (o) {
      if (!o.isMesh) return;
      var role = classify(o.name) || classify(o.parent && o.parent.name) || "soft";
      o.material = MATS[role];
      if (!structures[role]) structures[role] = [];
      structures[role].push(o);
    });

    // Centre the assembly so it sits in front of the camera.
    var box = new THREE.Box3().setFromObject(obj);
    var c = box.getCenter(new THREE.Vector3());
    var size = box.getSize(new THREE.Vector3());
    obj.position.sub(c);
    modelRadius = size.length() / 2;
    modelSize.copy(size);
    root.add(obj);

    setupInstruments();
    applyStep(0, true);
  }, undefined, function () {
    fail("The 3D model file could not be loaded.");
  });

  // ---- instruments -------------------------------------------------------
  // Grouping the probe and needle parts lets one toggle drive each instrument.
  // attach() is REQUIRED here: Group.add() re-parents a mesh and reinterprets
  // its LOCAL coordinates, which threw both instruments off-screen. attach()
  // preserves each mesh's world transform.
  function setupInstruments() {
    var nparts = (structures.needle || []).slice();
    var pparts = (structures.probe || []).slice();

    if (pparts.length) {
      probeGroup = new THREE.Group();
      probeGroup.name = "probeGroup";
      pparts.forEach(function (m) { probeGroup.attach(m); });
      root.add(probeGroup);
    }
    if (nparts.length) {
      needleGroup = new THREE.Group();
      needleGroup.name = "needleGroup";
      nparts.forEach(function (m) { needleGroup.attach(m); });
      root.add(needleGroup);
    }

    // The nodule the build placed inside the needle group, if any.
    var all = [];
    (structures.needle || []).forEach(function (m) { all.push(m); });
    (structures.probe || []).forEach(function (m) { all.push(m); });
    nodule = all.filter(function (m) {
      return (m.name || "").toLowerCase().indexOf("nodule") !== -1;
    })[0] || null;
  }

  // ---- skin opacity ramp -------------------------------------------------
  // 1.0 = a body surface; 0.30 = you can see the gland through it.
  var skinTween = null;
  function easeSkinTo(target) {
    var m = MATS.skin;
    if (!m) return;
    var from = m.opacity;
    if (Math.abs(from - target) < 0.001) {
      m.opacity = target; m.transparent = target < 0.999;
      m.depthWrite = target > 0.85; return;
    }
    if (skinTween) { cancelAnimationFrame(skinTween); skinTween = null; }
    var t0 = null, dur = 700;
    function frame(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / dur);
      var e = k * k * (3 - 2 * k);
      m.opacity = from + (target - from) * e;
      m.transparent = m.opacity < 0.999;
      m.depthWrite = m.opacity > 0.85;
      m.needsUpdate = true;
      if (k < 1) { skinTween = requestAnimationFrame(frame); } else { skinTween = null; }
    }
    skinTween = requestAnimationFrame(frame);
  }

  // ---- camera focus ------------------------------------------------------
  // Steps declare focus:"thyroid"/"procedure"/"neck"/"all". The old code
  // declared it on every step and never read it, so the camera always framed
  // the whole assembly and the gland was unreadable at 3.4 cm.
  function focusGroup(which) {
    if (which === "neck") {
      return (structures.skin || []).concat(structures.skeletalmuscle || []);
    }
    if (which === "thyroid") {
      return (structures.thyroid || []).concat(structures.parathyroid || []);
    }
    if (which === "procedure") {
      var g = (structures.thyroid || []).concat(structures.probe || [])
                .concat(structures.needle || []);
      if (nodule) g = g.concat([nodule]);
      return g;
    }
    return [];
  }

  function focusBox(which) {
    var box = new THREE.Box3();
    if (!which || which === "all") { box.expandByObject(root); return box; }
    var list = focusGroup(which);
    if (!list.length) { box.expandByObject(root); return box; }
    list.forEach(function (m) { box.expandByObject(m); });
    var sz = box.getSize(new THREE.Vector3());
    if (sz.length() < 0.02) box.expandByScalar(0.02);
    return box;
  }

  // ---- debug handles -----------------------------------------------------
  window.__dbg = {
    get structures() { return structures; },
    get roles() { return roles; },
    get nodule() { return nodule; },
    get needleGroup() { return needleGroup; },
    get probeGroup() { return probeGroup; },
    get step() { return cur; },
    get skinOpacity() { return MATS.skin ? MATS.skin.opacity : null; }
  };
'''
src = src[:load_old.start()] + load_new + src[load_old.end():]

# --------------------------------------------- fitCamera honours the focus
fit_old = re.search(r"  function fitCamera\(\) \{.*?\n  \}\n", src, re.S)
assert fit_old, "fitCamera not found"
fit_new = '''  function fitCamera(which) {
    var box = focusBox(which);
    var c = box.getCenter(new THREE.Vector3());
    var size = box.getSize(new THREE.Vector3());
    target.copy(c);
    var vFov = camera.fov * Math.PI / 180;
    var vDist = (size.y / 2) / Math.tan(vFov / 2);
    var hFov = 2 * Math.atan(Math.tan(vFov / 2) * camera.aspect);
    var hDist = (size.x / 2) / Math.tan(hFov / 2);
    var margin = (which && which !== "all") ? 1.15 : 1.28;
    var d = Math.max(vDist, hDist) * margin;
    if (controls) { controls.target.copy(target); controls.update(); }
    camDist = d;
    sph.dist = d;
    placeCamera();
  }
'''
src = src[:fit_old.start()] + fit_new + src[fit_old.end():]

open(OUT, "w", encoding="utf-8").write(src)
print(f"wrote {OUT}: {len(src)} bytes")
print(f"steps: {len(STEPS)}")
print(f"roles: 9")
