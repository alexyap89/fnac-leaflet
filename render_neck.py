#!/usr/bin/env /usr/bin/python3
"""Render the neck assembly in the style of Alex's reference video.

The reference is an interactive anatomy viewer: neutral studio background, soft
key/fill/rim lighting, glossy cartilage, an organic gland, and the thyroid
clearly visible as a distinct reddish-brown bilobed mass.

Key trick here: the thyroid must be VISIBLE, not buried inside the airway
geometry. We tag materials by role so each structure gets its own look, and we
render one view with the airway semi-transparent so the gland reads through it.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = "/home/alex/Documents/FNAC_Webapp"
GLB = os.path.join(BASE, "model", "fnac_scene.glb")
OUTDIR = os.path.join(BASE, "_png")

# role -> (base colour, roughness, subsurface, alpha)
LOOK = {
    "thyroid":     ((0.62, 0.20, 0.17), 0.42, 0.35, 1.0),   # reddish-brown gland
    "airway":      ((0.90, 0.88, 0.85), 0.55, 0.05, 0.22),   # pale, semi-clear
    "parathyroid": ((0.92, 0.78, 0.20), 0.40, 0.10, 1.0),    # yellow-tan
    "soft":        ((0.80, 0.45, 0.42), 0.50, 0.30, 1.0),    # muscle/tongue
}


def setup_world():
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.90, 0.91, 0.92, 1)
    bg.inputs[1].default_value = 0.9


def add_lamp(name, loc, energy, size):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.size = size
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).normalized() \
        .to_track_quat('-Z', 'Y').to_euler()
    return o


def make_material(role):
    rgb, rough, sss, alpha = LOOK[role]
    m = bpy.data.materials.new(f"M_{role}")
    m.use_nodes = True
    m.blend_method = 'BLEND' if alpha < 1.0 else 'OPAQUE'
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alpha
    for key in ("Subsurface Weight", "Subsurface"):
        if key in b.inputs:
            b.inputs[key].default_value = sss
            break
    return m


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    objs = [o for o in bpy.data.objects if o.type == 'MESH']
    print(f"imported {len(objs)} mesh(es) from {os.path.basename(GLB)}")

    # centre the whole assembly on the origin so the camera framing is stable
    pts = []
    for o in objs:
        m = o.matrix_world
        pts += [m @ Vector(v) for v in o.bound_box]
    ctr = Vector((
        (max(p.x for p in pts) + min(p.x for p in pts)) / 2,
        (max(p.y for p in pts) + min(p.y for p in pts)) / 2,
        (max(p.z for p in pts) + min(p.z for p in pts)) / 2,
    ))
    span = max(max(p.x for p in pts) - min(p.x for p in pts),
               max(p.y for p in pts) - min(p.y for p in pts),
               max(p.z for p in pts) - min(p.z for p in pts))
    for o in objs:
        o.location -= ctr
    print(f"assembly span: {span*100:.1f} cm; centred at origin")

    setup_world()
    # scale lights to the model so the rig works at any model size
    s = span
    add_lamp("key", (0.55 * s, -0.75 * s, 0.60 * s), 220 * s * s, 0.35 * s)
    add_lamp("fill", (-0.70 * s, -0.45 * s, 0.10 * s), 80 * s * s, 0.5 * s)
    add_lamp("rim", (0.05 * s, 0.80 * s, 0.45 * s), 150 * s * s, 0.3 * s)

    # Assign the role materials. The GLB carries material slots named by role,
    # so use those names directly rather than guessing by position.
    seen_roles = set()
    for o in objs:
        for m in o.data.materials:
            if m:
                seen_roles.add(m.name)
    print(f"material names in the GLB: {sorted(seen_roles)}")

    # Match roles EXACTLY, not by substring: "thyroid" is a substring of
    # "parathyroid", so a naive `in` test painted the parathyroids as thyroid.
    role_of = {}
    for m in bpy.data.materials:
        base = m.name.strip()
        if base in LOOK:
            role_of[base] = base
        else:
            for role in sorted(LOOK, key=len, reverse=True):
                if role.lower() == base.lower():
                    role_of[base] = role
                    break
    print(f"role mapping: {role_of}")

    for m in list(bpy.data.materials):
        role = role_of.get(m.name)
        if role:
            rgb, rough, sss, alpha = LOOK[role]
            m.blend_method = 'BLEND' if alpha < 1 else 'OPAQUE'
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Base Color"].default_value = (*rgb, 1)
                b.inputs["Roughness"].default_value = rough
                b.inputs["Alpha"].default_value = alpha
                for key in ("Subsurface Weight", "Subsurface"):
                    if key in b.inputs:
                        b.inputs[key].default_value = sss
                        break

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 85
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 780
    sc.render.resolution_y = 900
    sc.render.image_settings.file_format = 'PNG'

    os.makedirs(OUTDIR, exist_ok=True)
    d = 2.05 * span
    views = {
        "front":         (0.0, -d, 0.02 * span),
        "three_quarter": (0.62 * d, -0.78 * d, 0.22 * span),
        "lateral":       (0.98 * d, -0.08 * d, 0.05 * span),
        "posterior":     (0.10 * d, 0.95 * d, 0.30 * span),
    }
    # one extra pass with only the thyroid visible — this is the money shot and
    # it also proves the gland's geometry is right on its own.
    # With separate nodes this is a straightforward name test. Previously the
    # mesh was joined, so the filter could not exclude anything and the
    # "thyroid only" render still contained the trachea and larynx.
    thyroid_parts = [o for o in objs if o.name.startswith("thyroid__")]
    if thyroid_parts:
        saved = {}
        for o in objs:
            if o not in thyroid_parts:
                saved[o] = o.hide_render
                o.hide_render = True
        cam.location = (0.55 * d, -0.80 * d, 0.16 * span)
        cam.rotation_euler = (Vector((0, 0, 0)) - Vector(cam.location)).normalized() \
            .to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(OUTDIR, "anatz_thyroid_only.png")
        bpy.ops.render.render(write_still=True)
        print("  rendered thyroid_only")
        for o, v in saved.items():
            o.hide_render = v

    for name, loc in views.items():
        cam.location = loc
        cam.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).normalized() \
            .to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(OUTDIR, f"anatz_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"  rendered {name}")

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
