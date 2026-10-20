#!/usr/bin/env python3
"""Open the shipped GLB in Blender and save it as an editable .blend.

Loads the SAME file the viewer renders, so anything edited here is exactly what
the app shows - there is no parallel copy to drift out of sync.

Materials are mapped to a viewport-friendly display colour so the roles are
distinguishable while editing, and the objects are grouped into collections by
role so a whole role can be selected or hidden in one click.
"""
import bpy, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(HERE, "model", "fnac_scene.glb")
OUT = os.path.join(HERE, "fnac_scene_editable.blend")

# viewport colours per role: Base Color alone reads as near-black in the default
# viewport shading, which made every role look the same while editing.
ROLE_COLOUR = {
    "skin":          (0.85, 0.70, 0.62, 1.0),
    "skeletalmuscle":(0.78, 0.32, 0.30, 1.0),
    "strap":         (0.72, 0.40, 0.36, 1.0),
    "thyroid":       (0.85, 0.30, 0.32, 1.0),
    "parathyroid":   (0.90, 0.75, 0.35, 1.0),
    "airway":        (0.72, 0.82, 0.90, 1.0),
    "soft":          (0.80, 0.62, 0.55, 1.0),
    "probe":         (0.55, 0.60, 0.68, 1.0),
    "needle":        (0.80, 0.85, 0.90, 1.0),
    "nodule":        (0.45, 0.10, 0.08, 1.0),
    "dressing":      (0.94, 0.92, 0.88, 1.0),
    "room":          (0.72, 0.76, 0.79, 1.0),
    "patient":       (0.85, 0.76, 0.68, 1.0),
    "clinician":     (0.29, 0.42, 0.54, 1.0),
}

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)

    n = 0
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            continue
        role = o.name.split("__", 1)[0] if "__" in o.name else "other"
        # a collection per role: hide or select a whole role in one click
        coll = bpy.data.collections.get(role)
        if coll is None:
            coll = bpy.data.collections.new(role)
            bpy.context.scene.collection.children.link(coll)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)

        m = o.data.materials[0] if o.data.materials else None
        if m and role in ROLE_COLOUR:
            m.diffuse_color = ROLE_COLOUR[role]      # viewport colour
            m.roughness = 0.8
        n += 1

    print(f"imported {n} meshes across {len(bpy.data.collections)} collections")
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("saved", OUT, os.path.getsize(OUT), "bytes")

if __name__ == "__main__":
    main()
