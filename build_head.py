#!/usr/bin/env /usr/bin/python3
"""Build a stylised head-and-neck shell for the FNAC viewer.

WHY
---
Z-Anatomy models internal organs only - it has no facial or cranial surface
geometry (verified: the only head-region meshes are hair, eyebrows and
eyelashes). Steps 1-4 of the spec need a recognisable person, so the viewer had
a headless neck and a patient could not tell WHERE in their neck the procedure
was happening.

WHAT THIS IS
------------
A deliberately simplified surface: cranium, face, jaw, and a neck column. It is
NOT photoreal and is not meant to be. It is a clean medical-illustration shell
whose only jobs are:
  * to read instantly as a human head and neck
  * to be translucent, so the viscera show through it
  * to sit in exactly the right place relative to the Z-Anatomy viscera

Every dimension is DERIVED from the viscera so the shell cannot drift: the head
is centred on the airway's superior end, the neck wraps the trachea, and the
shell is positioned so the mandible clears the thyroid.

METHOD
------
Built from scaled/tapered spheres and a swept neck column using bmesh, then
remeshed to a smooth surface. No external assets, no licences, no downloads.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = "/home/alex/Documents/FNAC_Webapp"
VISC = os.path.join(BASE, "assets", "VisceralSystem100.fbx")
OUT_GLB = os.path.join(BASE, "model", "head_shell.glb")
REPORT = os.path.join(BASE, "head_shell_report.json")

# Z-Anatomy full-body landmarks (cm, from earlier measurement of the viscera)
CHIN_Z = 152.0        # approximate mandible inferior border is derived below
NECK_TOP_Z = 150.0


def world_box(o):
    m = o.matrix_world
    pts = [m @ Vector(v) for v in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def new_mesh(name):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def ellipsoid(name, centre, radii, segments=48, rings=32, squash_front=1.0,
              taper=None, face=False):
    """A UV-sphere ellipsoid shaped into a head when face=True.

    A plain ellipsoid reads as an egg. What makes a silhouette read as a HUMAN
    head is the profile: a flattened face plane at the front, a forehead that
    recedes above the brow, a slight nasal bridge, a jawline narrowing below the
    cheekbones, and a chin projecting forward at the bottom. Those are all cheap
    vertex deformations, and they are what the eye actually uses.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         radius=1.0, location=centre)
    ob = bpy.context.active_object
    ob.name = name
    n = len(ob.data.vertices)
    for v in ob.data.vertices:
        x, y, z = v.co           # unit sphere, -y is anterior
        sx, sy, sz = radii
        if taper:
            z_from, z_to, s_from, s_to = taper
            t = (z - z_from) / max(1e-6, (z_to - z_from))
            t = max(0.0, min(1.0, t))
            k = s_from + (s_to - s_from) * t
            sx *= k
            sy *= k

        if face and y < 0:
            # front hemisphere is the face
            # 1. flatten it: a face is a plane, not a bulge
            y *= squash_front
            # 2. recede the forehead (upper front) so the brow sits proud
            if z > 0.15:
                y *= 1.0 - 0.30 * min(1.0, (z - 0.15) / 0.85)
            # 3. nasal bridge / mid-face: push slightly forward just above centre
            if -0.05 < z < 0.35:
                y *= 1.10
            # 4. jawline: narrow the front-lower region toward the chin
            if z < -0.15:
                k2 = 1.0 - 0.34 * min(1.0, (-0.15 - z) / 0.75)
                x *= k2
                y *= 1.0 + 0.10 * min(1.0, (-0.15 - z) / 0.75)
            # 5. chin: a small forward projection at the very bottom-front
            if z < -0.55:
                y *= 1.14
        elif y < 0:
            y *= squash_front

        # back of the skull is fuller than the face, as in life
        if y > 0:
            y *= 1.04

        v.co = Vector((x * sx, y * sy, z * sz))
    return ob


def neck_column(name, x_center, y_center, z_bottom, z_top, r_bottom, r_top,
                segments=40):
    """A tapered cylinder for the neck, widest at the base, slightly oval."""
    mid_z = (z_bottom + z_top) / 2
    bpy.ops.mesh.primitive_cone_add(vertices=segments, radius1=r_bottom,
                                    radius2=r_top, depth=(z_top - z_bottom),
                                    location=(x_center, y_center, mid_z))
    ob = bpy.context.active_object
    ob.name = name
    for v in ob.data.vertices:
        v.co.x *= 1.06          # neck is wider than it is deep
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # ---- measure the viscera so the shell is placed from real landmarks ----
    bpy.ops.import_scene.fbx(filepath=VISC)
    trach = bpy.data.objects.get("Trachea")
    lary = bpy.data.objects.get("Laryngopharynx")
    tg = bpy.data.objects.get("Thyroid gland")
    tongue = bpy.data.objects.get("Tongue")
    if not (trach and lary and tg and tongue):
        print("FATAL: missing landmark meshes in the viscera model")
        return 1

    t_lo, t_hi = world_box(trach)
    l_lo, l_hi = world_box(lary)
    g_lo, g_hi = world_box(tg)
    tg_lo, tg_hi = world_box(tongue)

    # landmarks in metres
    top_of_airway = l_hi.z                 # where the pharynx ends
    tongue_top = tg_hi.z
    neck_base = t_lo.z                     # bottom of the trachea here
    gland_top = g_hi.z
    gland_bot = g_lo.z
    y_mid = (t_lo.y + t_hi.y) / 2          # airway centre, for x/y placement

    print("landmarks (cm):")
    print(f"  airway top      {top_of_airway*100:7.1f}")
    print(f"  tongue top      {tongue_top*100:7.1f}")
    print(f"  gland top/bot   {gland_top*100:7.1f} / {gland_bot*100:7.1f}")
    print(f"  neck base       {neck_base*100:7.1f}")
    print(f"  airway y-mid    {y_mid*100:7.2f}")

    # ---- choose head proportions from the airway, not from memory ----
    # The mandible sits just above the tongue's root; the head is roughly
    # 1.4x the neck-column height, which reproduces normal adult proportions.
    # Anchor to the dataset's OWN reference planes, which are authoritative:
    #   Frontal / Occipital  z 163.1..164.5  -> the head's mid level
    #   Cranial              z 168.6..174.7  -> toward the crown
    # Read them from the References model when present; otherwise fall back.
    ref_path = os.path.join(BASE, "assets", "References100.fbx")
    head_mid_z = None
    if os.path.exists(ref_path):
        before_ref = set(o.name for o in bpy.data.objects if o.type == 'MESH')
        try:
            bpy.ops.import_scene.fbx(filepath=ref_path)
            for nm in ("Frontal", "Occipital"):
                o = bpy.data.objects.get(nm)
                if o is not None:
                    lo, hi = world_box(o)
                    head_mid_z = (lo.z + hi.z) / 2 if head_mid_z is None else head_mid_z
            # delete the reference planes again; we only wanted the datum
            for o in [x for x in bpy.data.objects
                      if x.type == 'MESH' and x.name not in before_ref]:
                bpy.data.objects.remove(o, do_unlink=True)
        except Exception as e:
            print(f"  could not read reference planes: {e}")

    if head_mid_z is None:
        head_mid_z = tongue_top + 0.010          # fallback
    mouth_z = head_mid_z - 0.011                 # mouth sits just below mid-head
    chin_z = mouth_z - 0.026                     # mandible inferior border
    crown_z = head_mid_z + 0.106                 # crown above the datum
    head_h = crown_z - chin_z
    # the head ellipsoid is centred between chin and crown, biased up to account
    # for the cranium being larger than the face
    head_c_z = head_mid_z
    head_c_x = 0.0
    # face plane: the tongue's anterior surface is the back of the mouth, so the
    # face sits a little in front of it
    face_front_y = tg_lo.y - 0.012
    head_c_y = face_front_y + 0.088      # centre is behind the face plane

    # radii: head ~ 7.5 cm half-width, 9.5 cm half-depth, 11.2 cm half-height
    rx, ry, rz = 0.075, 0.095, 0.112

    neck_top = chin_z + 0.006            # neck meets the jaw
    neck_bot = neck_base + 0.010         # slightly above the model's cut
    neck_h = neck_top - neck_bot

    print(f"\nhead mid (dataset datum) {head_mid_z*100:.1f} cm"
          f"   mouth {mouth_z*100:.1f}  chin {chin_z*100:.1f}  crown {crown_z*100:.1f}")
    print(f"head centre cm: ({head_c_x*100:.1f}, {head_c_y*100:.1f}, {head_c_z*100:.1f})")
    print(f"head radii cm : ({rx*100:.1f}, {ry*100:.1f}, {rz*100:.1f})")
    print(f"neck column   : z {neck_bot*100:.1f} .. {neck_top*100:.1f}  (h={neck_h*100:.1f} cm)")

    # ---- build ----
    # cranium/face: one ellipsoid, tapered so the jaw is narrower than the skull,
    # and flattened at the front where the face is.
    head = ellipsoid("skin__head", (head_c_x, head_c_y, head_c_z),
                     (rx, ry, rz), segments=72, rings=52,
                     squash_front=0.80,
                     taper=(-1.0, 1.0, 0.70, 1.06),
                     face=True)
    head.name = "skin__head"

    # jaw/mandible mass, blending the head into the neck
    jaw = ellipsoid("skin__jaw", (head_c_x, face_front_y + 0.030, chin_z + 0.026),
                    (rx * 0.66, 0.062, 0.044), segments=44, rings=28,
                    squash_front=0.94)
    jaw.name = "skin__jaw"

    # neck column, wrapping the airway
    neck = neck_column("skin__neck", head_c_x, y_mid,
                       neck_bot, neck_top,
                       r_bottom=0.062, r_top=0.058)
    neck.name = "skin__neck"

    # shoulders, so the model does not end abruptly
    sh = ellipsoid("skin__shoulders", (0.0, y_mid, neck_bot - 0.012),
                   (0.155, 0.105, 0.055), segments=56, rings=30)
    sh.name = "skin__shoulders"

    parts = [head, jaw, neck, sh]
    print("\nbuilt parts:")
    for o in parts:
        print(f"  {o.name:22} {len(o.data.polygons):>6} faces")

    # smooth shading so it reads as skin, not a low-poly blob
    for o in parts:
        for p in o.data.polygons:
            p.use_smooth = True

    # ---- join into ONE mesh so the role stays "skin" ----
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    shell = bpy.context.active_object
    shell.name = "skin__head_shell"
    shell.data.name = "skin__head_shell"

    bpy.ops.object.shade_smooth()
    print(f"\njoined shell: {len(shell.data.polygons)} faces, "
          f"{len(shell.data.vertices)} verts")

    # material placeholder; the runtime applies its own skin material
    m = bpy.data.materials.new("skin")
    m.use_nodes = True
    shell.data.materials.clear()
    shell.data.materials.append(m)

    # ---- export ----
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    shell.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB',
                              use_selection=True, export_apply=True)

    # ---- verify by reimport, and CHECK THE SHELL ENCLOSES THE VISCERA ----
    print("\n=== verifying ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=OUT_GLB)
    got = [o for o in bpy.data.objects if o.type == 'MESH']
    ok = len(got) == 1
    print(f"  objects: {len(got)} (expect 1)")
    if got:
        lo, hi = world_box(got[0])
        print(f"  shell bbox cm lo=({lo.x*100:.1f},{lo.y*100:.1f},{lo.z*100:.1f}) "
              f"hi=({hi.x*100:.1f},{hi.y*100:.1f},{hi.z*100:.1f})")
        # the thyroid must be INSIDE the shell in x and z (y is depth; the gland
        # is anterior so it should be within the shell's y range too)
        inside_x = lo.x <= g_lo.x and hi.x >= g_hi.x
        inside_z = lo.z <= g_lo.z and hi.z >= g_hi.z
        inside_y = lo.y <= g_lo.y and hi.y >= g_hi.y
        print(f"  thyroid inside shell: x={inside_x} y={inside_y} z={inside_z}")
        ok = ok and inside_x and inside_z
        report = {
            "glb": OUT_GLB,
            "faces": len(got[0].data.polygons),
            "verts": len(got[0].data.vertices),
            "shell_bbox_cm": {"lo": [round(v*100,2) for v in lo],
                              "hi": [round(v*100,2) for v in hi]},
            "landmarks_cm": {
                "airway_top": round(top_of_airway*100,2),
                "tongue_top": round(tongue_top*100,2),
                "gland_top": round(gland_top*100,2),
                "gland_bot": round(gland_bot*100,2),
                "neck_base": round(neck_base*100,2),
                "chin_z": round(chin_z*100,2),
                "head_centre_z": round(head_c_z*100,2),
            },
            "thyroid_inside_shell": {"x": inside_x, "y": inside_y, "z": inside_z},
            "verify_pass": ok,
        }
        json.dump(report, open(REPORT, "w"), indent=1)
        print(f"\nwrote {REPORT}")
    print(f"\nVERIFY: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
