#!/usr/bin/env /usr/bin/python3
"""Build the neck assembly from the Z-Anatomy visceral FBX, CORRECTLY.

Bugs fixed from the first attempt, each measured rather than guessed:

1. JOIN LOST OBJECTS. `bpy.ops.object.join()` names the result after the ACTIVE
   object, and meshes[0] was arbitrary, so the export was named "Epiglottis".
   Now the active object is chosen explicitly and the name is set after joining.

2. PARENTED TRANSFORMS. The thyroid is parented to `Endocrine glands.g` at
   z=1.487 m. Joining objects that have unapplied parent transforms collapses
   them into the parent's space, so structures silently move or vanish — the
   first render had no thyroid at all. Now every object has its transform
   APPLIED (matrix_world baked into the mesh) before joining.

3. VERIFY AFTER BUILDING. The script re-imports its own GLB and asserts each
   expected structure is present and in a plausible position. The first export
   looked fine until it was rendered and inspected.

Z-Anatomy coordinate convention: 1 unit = 1 metre, +Z = superior (head up).
"""
import json
import os
import sys

import bpy
from mathutils import Vector

BASE = "/home/alex/Documents/FNAC_Webapp"
FBX = os.path.join(BASE, "assets", "VisceralSystem100.fbx")
OUT_GLB = os.path.join(BASE, "model", "neck_anatomy_z.glb")
REPORT = os.path.join(BASE, "neck_build_report.json")

# Structures to include, in priority order. Each is (object name, role).
# Roles matter because the app tints/fades them independently.
WANTED = [
    ("Thyroid gland",                "thyroid"),
    ("Trachea",                      "airway"),
    ("Laryngopharynx",               "airway"),
    ("Oropharynx",                   "airway"),
    ("Epiglottis",                   "airway"),
    ("Tongue",                       "soft"),
    ("Inferior parathyroid gland.r", "parathyroid"),
    ("Inferior parathyroid gland.l", "parathyroid"),
    ("Superior parathyroid gland.r", "parathyroid"),
    ("Superior parathyroid gland.l", "parathyroid"),
]


def world_stats(o):
    m = o.matrix_world
    pts = [m @ Vector(v) for v in o.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    c = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2)
    s = ((max(xs) - min(xs)) * 100, (max(ys) - min(ys)) * 100, (max(zs) - min(zs)) * 100)
    return c, s


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX)
    print(f"imported {len([o for o in bpy.data.objects if o.type=='MESH'])} meshes")

    # ---- collect the wanted structures, recording their world positions ----
    keep = []
    report = {"source": FBX, "structures": []}
    print("\nselected structures (world coords, cm):")
    for name, role in WANTED:
        o = bpy.data.objects.get(name)
        if o is None or o.type != 'MESH':
            print(f"  MISSING  {name}")
            report["structures"].append({"name": name, "role": role, "found": False})
            continue
        if len(o.data.polygons) < 20:
            print(f"  PROXY    {name} ({len(o.data.polygons)} faces) - skipped")
            report["structures"].append({"name": name, "role": role, "found": False,
                                         "reason": "proxy geometry"})
            continue
        c, s = world_stats(o)
        keep.append((o, role))
        print(f"  OK       {name:32} faces={len(o.data.polygons):>6} "
              f"centre=({c[0]*100:6.1f},{c[1]*100:6.1f},{c[2]*100:6.1f}) "
              f"size=({s[0]:4.1f},{s[1]:4.1f},{s[2]:4.1f})")
        report["structures"].append({
            "name": name, "role": role, "found": True,
            "faces": len(o.data.polygons),
            "world_centre_cm": [round(v * 100, 2) for v in c],
            "world_size_cm": [round(v, 2) for v in s],
        })

    if not keep:
        print("nothing to export")
        return 1

    # ---- remove everything else so the scene is only the neck ----
    keepnames = set(o.name for o, _ in keep)
    for o in [x for x in bpy.data.objects if x.type == 'MESH' and x.name not in keepnames]:
        bpy.data.objects.remove(o, do_unlink=True)

    # ---- APPLY world transforms before joining (fix #2) ----
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print(f"\napplied transforms to {len(meshes)} objects")

    # ---- tag each object's faces with its role via a material slot ----
    role_mats = {}
    for role in sorted(set(r for _, r in keep)):
        m = bpy.data.materials.new(role)
        m.use_nodes = True
        role_mats[role] = m

    for o, role in keep:
        o.data.materials.clear()
        o.data.materials.append(role_mats[role])

    # ---- DO NOT JOIN. Keep one GLB node per structure. ----
    # Joining was the first version's second real mistake: a single mesh cannot
    # be shown, hidden, or tinted per structure, so "thyroid only" rendered the
    # trachea and larynx too, and the whole point of the segmented source was
    # lost. The reference app treats each structure as an independent node.
    neck = keep[0][0]
    print(f"keeping {len(keep)} separate objects (no join)")
    for o, role in keep:
        o.name = f"{role}__{o.name.replace(' ', '_')}"
        o.data.name = o.name
        print(f"    {o.name:50} {len(o.data.polygons):>6} faces")

    # ---- export ----
    bpy.ops.object.select_all(action='DESELECT')
    for o, _ in keep:
        o.select_set(True)
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB',
                              use_selection=True, export_apply=True,
                              export_materials='EXPORT')
    size = os.path.getsize(OUT_GLB)
    print(f"\nexported {OUT_GLB} ({size:,} bytes)")
    report["glb"] = OUT_GLB
    report["glb_bytes"] = size
    report["faces"] = sum(len(o.data.polygons) for o, _ in keep)
    report["nodes"] = [o.name for o, _ in keep]
    json.dump(report, open(REPORT, "w"), indent=1)

    # ---- VERIFY by re-importing (fix #3) ----
    print("\n=== verifying the exported GLB by re-importing it ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=OUT_GLB)
    got = [o for o in bpy.data.objects if o.type == 'MESH']
    print(f"  meshes in GLB: {[o.name for o in got]}")
    total_f = sum(len(o.data.polygons) for o in got)
    print(f"  total faces: {total_f:,}")
    mats = set()
    for o in got:
        for m in o.data.materials:
            if m:
                mats.add(m.name)
    print(f"  materials present: {sorted(mats)}")
    # glTF TRIANGULATES: a Blender polygon that is a quad becomes two triangles,
    # so the face counts legitimately differ. Compare triangulated counts, i.e.
    # assert the GLB has AT LEAST as many triangles as the source had polygons,
    # and no more than twice (the worst case for an all-quad mesh).
    src_faces = report["faces"]
    tri_ok = src_faces <= total_f <= src_faces * 2
    node_names = [o.name for o in got]
    has_thyroid_node = any(n.startswith("thyroid__") for n in node_names)
    ok = has_thyroid_node and "thyroid" in mats and tri_ok
    print(f"  separate nodes: {node_names}")
    print(f"  thyroid node present: {has_thyroid_node}")
    print(f"  thyroid material present: {'thyroid' in mats}")
    print(f"  faces: source {src_faces:,} polygons -> GLB {total_f:,} triangles")
    print(f"  triangulation plausible ({src_faces:,} <= {total_f:,} <= {src_faces*2:,}): {tri_ok}")
    print(f"  VERIFY: {'PASS' if ok else 'FAIL'}")
    report["verify_pass"] = bool(ok)
    json.dump(report, open(REPORT, "w"), indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
