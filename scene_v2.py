#!/usr/bin/env /usr/bin/python3
"""FNAC webapp — 3D scene model (improved).

Round 2 addresses the critique of round 1:
  * the scene was abstract blobs; no recognisable neck/thyroid anatomy
  * no trachea, strap muscles, carotid/jugular, no skin surface
  * the ultrasound probe was an unrecognisable box
  * the needle had no bevel / hub / syringe, entry point ambiguous
  * no labels, scale or orientation

Design decisions:
  * Build the neck as a proper cross-sectional volume: skin surface, strap
    muscles, trachea (with rings), thyroid lobes + isthmus, carotid and jugular
    on each side, and the nodule within the right lobe.
  * Head tipped back = the whole neck root rotates, as in the real position.
  * The ultrasound probe is a realistic linear-array transducer: footprint,
    body, handle, cable.
  * The needle is a proper bevel-tipped 25G needle on a syringe hub, entering
    at the marked skin point at a shallow angle, tip visible in the nodule.
  * Floating 3D labels follow the key structures so a patient knows what they
    are looking at (implemented as DOM overlays projected from 3D positions).

This module returns the scene graph; index.html owns rendering.
"""
import os

SCENE_JS = r"""
/* ==========================================================================
   FNAC scene — anatomically-informed geometry
   Coordinates: +X = patient's left, +Y = up (cranial), +Z = anterior.
   The neck is modelled as a cross-sectional volume around the trachea.
   ========================================================================== */

const C = {
  skin:      [0.93,0.78,0.68],
  fat:       [0.96,0.86,0.72],
  muscle:    [0.68,0.30,0.30],
  muscle2:   [0.58,0.24,0.26],
  trachea:   [0.86,0.88,0.92],
  cart:      [0.94,0.95,0.97],
  thyroid:   [0.85,0.34,0.40],
  thyroid2:  [0.78,0.28,0.34],
  nodule:    [0.42,0.16,0.24],
  artery:    [0.80,0.16,0.20],
  vein:      [0.22,0.30,0.62],
  nerve:     [0.95,0.88,0.35],
  steel:     [0.90,0.93,0.98],
  hub:       [0.30,0.62,0.85],
  transducer:[0.16,0.19,0.26],
  cable:     [0.10,0.11,0.15],
  gel:       [0.55,0.80,0.95],
  marker:    [0.20,0.88,0.78],
  dressing:  [0.96,0.94,0.90],
  beam:      [0.40,0.75,1.00]
};

function buildScene(addMesh, geo){
  const S = {parts:{}, groups:{}};

  /* ---------------------------------------------------- neck root transform */
  S.groups.neck = [];       // everything that tilts with neck extension
  const push = (name, mesh) => { S.parts[name] = mesh;
                                 S.groups.neck.push(mesh); return mesh; };

  /* ---------------------------------------------------------- skin & fat --- */
  // Anterior neck skin surface — a broad flattened shell so the probe sits on it
  push('skin', addMesh(
    geo.ellipsoid(1.30, 2.10, 1.05, C.skin, 48, 30),
    C.skin, {alpha:0.13}));
  push('fat', addMesh(
    geo.ellipsoid(1.08, 1.95, 0.88, C.fat, 44, 28),
    C.fat, {alpha:0.10}));

  /* ------------------------------------------------- strap muscles (pair) - */
  for (const sx of [1,-1]) {
    push('scm'+sx, addMesh(
      geo.capsule(0.22, 1.55, C.muscle, 28, 14),
      C.muscle, {model: geo.mul(geo.T(sx*0.78, 0.18, 0.30), geo.RZ(sx*0.13))}));
    push('strapA'+sx, addMesh(
      geo.capsule(0.15, 1.30, C.muscle2, 24, 12),
      C.muscle2, {model: geo.mul(geo.T(sx*0.34, 0.05, 0.34), geo.RZ(sx*0.05))}));
  }

  /* -------------------------------------------------------------- trachea -- */
  push('trachea', addMesh(
    geo.cylinder(0.30, 0.30, 2.75, C.trachea, 34), C.trachea,
    {model: geo.T(0, -0.05, -0.32)}));
  // cartilage rings — this is what makes it read as a trachea, not a tube
  for (let i=0; i<8; i++){
    push('ring'+i, addMesh(
      geo.torus(0.315, 0.045, C.cart, 32, 10), C.cart,
      {model: geo.T(0, -1.20 + i*0.33, -0.32)}));
  }

  /* --------------------------------------------------------------- thyroid -- */
  // Right lobe (patient's right = -X in our frame is screen-left; we place the
  // nodule in the right lobe and mirror for the left)
  const lobeR = geo.ellipsoid(0.30, 0.62, 0.30, C.thyroid, 40, 26);
  push('lobeR', addMesh(lobeR, C.thyroid,
    {model: geo.mul(geo.T( 0.44, 0.02, 0.10), geo.RZ(-0.06))}));
  push('lobeL', addMesh(lobeR, C.thyroid,
    {model: geo.mul(geo.T(-0.44, 0.02, 0.10), geo.RZ( 0.06))}));
  // isthmus bridging the lobes across the midline
  push('isthmus', addMesh(
    geo.ellipsoid(0.26, 0.20, 0.24, C.thyroid2, 32, 20), C.thyroid2,
    {model: geo.T(0, -0.08, 0.20)}));

  /* ---------------------------------------------------------------- nodule -- */
  S.parts.nodule = addMesh(
    geo.ellipsoid(0.145, 0.185, 0.145, C.nodule, 32, 22), C.nodule,
    {model: geo.T(0.47, 0.06, 0.20), emis:0.06});
  push('nodule', S.parts.nodule);
  // a faint halo so the nodule is findable in the lobe
  push('noduleHalo', addMesh(
    geo.ellipsoid(0.20, 0.24, 0.20, C.nodule, 24, 16), C.nodule,
    {model: geo.T(0.47, 0.06, 0.20), alpha:0.18}));

  /* --------------------------------------------------- vessels (bilateral) - */
  for (const sx of [1,-1]) {
    push('carotid'+sx, addMesh(
      geo.cylinder(0.115, 0.115, 2.4, C.artery, 26), C.artery,
      {model: geo.T(sx*0.86, 0.05, -0.30)}));
    push('jugular'+sx, addMesh(
      geo.cylinder(0.095, 0.095, 2.4, C.vein, 26), C.vein,
      {model: geo.T(sx*0.66, 0.05, -0.55)}));
  }

  /* -------------------------------------------------------------- skin mark - */
  S.parts.marker = addMesh(
    geo.disc(0.075, C.marker, 28), C.marker,
    {model: geo.T(0.47, 1.02, 0.42), emis:0.30});
  push('marker', S.parts.marker);

  /* ------------------------------------------------------------------ probe -- */
  // Linear-array transducer: footprint, body, handle, cable
  S.parts.probe = addMesh(
    geo.box(0.62, 0.10, 1.05, C.transducer), C.transducer);           // footprint
  push('probe', S.parts.probe);
  S.parts.probeBody = addMesh(
    geo.box(0.72, 0.26, 1.15, [0.20,0.24,0.32]), [0.20,0.24,0.32]);
  push('probeBody', S.parts.probeBody);
  S.parts.probeHandle = addMesh(
    geo.capsule(0.16, 0.55, [0.17,0.20,0.27], 24, 12), [0.17,0.20,0.27]);
  push('probeHandle', S.parts.probeHandle);
  S.parts.probeCable = addMesh(
    geo.capsule(0.062, 1.9, C.cable, 18, 10), C.cable);
  push('probeCable', S.parts.probeCable);
  S.parts.gel = addMesh(
    geo.ellipsoid(0.34, 0.035, 0.55, C.gel, 28, 16), C.gel, {alpha:0.45});

  /* ----------------------------------------------------------------- needle - */
  S.parts.needle = addMesh(
    geo.needle(0.014, 0.010, 1.55, C.steel, 20), C.steel, {emis:0.22});
  push('needle', S.parts.needle);
  S.parts.hub = addMesh(
    geo.cylinder(0.055, 0.048, 0.34, C.hub, 22), C.hub);
  push('hub', S.parts.hub);
  S.parts.syringe = addMesh(
    geo.cylinder(0.075, 0.075, 0.50, [0.92,0.94,0.98], 24), [0.92,0.94,0.98],
    {alpha:0.55});
  push('syringe', S.parts.syringe);

  /* --------------------------------------------------------------- dressing - */
  S.parts.dressing = addMesh(
    geo.box(0.30, 0.022, 0.30, C.dressing), C.dressing);
  push('dressing', S.parts.dressing);

  /* ---------------------------------------------------- ultrasound beam cone - */
  // A translucent cone from the probe footprint to the nodule: shows what the
  // screen image is actually imaging.
  S.parts.beam = addMesh(
    geo.cone(0.52, 1.55, C.beam, 30), C.beam, {alpha:0.13});
  push('beam', S.parts.beam);

  return S;
}
"""


def main():
    out = "/home/alex/Documents/FNAC_Webapp/scene.js"
    with open(out, "w") as fh:
        fh.write(SCENE_JS)
    print("wrote", out, len(SCENE_JS), "bytes")


if __name__ == "__main__":
    main()
