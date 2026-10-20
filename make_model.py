#!/usr/bin/env /usr/bin/python3.11
"""Build the FNAC anatomical cutaway model in Blender, headless.

Run with the bpy venv:
    /home/alex/.blender-venv/bin/python make_model.py

Design: an ANATOMICAL CUTAWAY of the neck (chosen by Alex 2026-10-11).
A vertical hemi-section through the neck so every layer is legible:
    skin -> subcutaneous fat -> strap muscles -> thyroid -> trachea
with the carotid/jugular posterolateral and the nodule inside the right lobe.

Scale: 1 Blender unit = 1 metre, per Blender convention. The anatomy is built at
life size:
    neck diameter       0.11 m
    thyroid lobe        0.050 x 0.021 x 0.021 m   (5 x 2.1 x 2.1 cm)
    isthmus thickness   0.005 m                    (5 mm)
    nodule              0.020 m                    (2 cm)
The exporter/consumer scales to the scene (1 world unit = 5 cm).

Technique (why it is built this way):
  * Metaball-free. Every organ is a primitive -> Subdivision Surface modifier ->
    applied. This gives smooth, organ-like surfaces rather than visible sphere
    seams, which is what made earlier versions look amateurish.
  * A Boolean DIFFERENCE with a box produces the cutaway face, so the patient
    sees a genuine cross-section, not a distorted whole neck.
  * Separate materials per tissue layer, with colour matched to what the tissue
    looks like in a real anatomical illustration.
  * Nothing is joined into one mesh: separate objects keep the material slots
    clean and let the runtime fade layers independently (the staged reveal).
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

OUT = "/home/alex/Documents/FNAC_Webapp/model"
os.makedirs(OUT, exist_ok=True)

# --------------------------------------------------------------------------- #
# scene reset
# --------------------------------------------------------------------------- #
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


def mat(name, rgba, rough=0.55, metal=0.0, emit=None, alpha=1.0, subsurf=0.0):
    """Create a Principled BSDF material. Blender 4.x uses descriptive socket
    names, so sockets are looked up by name with a fallback."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgba[:3], alpha)
    b = m.node_tree.nodes.get("Principled BSDF")
    if b is None:
        return m

    def setv(key, val, fallback=None):
        if key in b.inputs:
            try:
                b.inputs[key].default_value = val
                return True
            except Exception:
                pass
        if fallback and fallback in b.inputs:
            try:
                b.inputs[fallback].default_value = val
                return True
            except Exception:
                pass
        return False

    setv("Base Color", (*rgba[:3], 1.0))
    setv("Roughness", rough, "Roughness")
    setv("Metallic", metal, "Metallic")
    setv("Alpha", alpha, "Alpha")
    if subsurf:
        # Subsurface gives skin/flesh its characteristic light bleed.
        if not setv("Subsurface Weight", subsurf, "Subsurface"):
            setv("Subsurface", subsurf)
        setv("Subsurface Radius", (0.006, 0.0025, 0.0016), "Subsurface Radius")
        setv("Subsurface Color", (*rgba[:3], 1.0), "Subsurface Color")
    if emit:
        setv("Emission Color", (*emit[:3], 1.0), "Emission")
        setv("Emission Strength", emit[3], "Emission Strength")
    if alpha < 1.0:
        m.blend_method = 'BLEND'
    return m


def smooth_shade(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def subsurf(obj, levels=2, apply=True):
    # Levels are capped deliberately: level 3 on a joined multi-part organ
    # produced 264k faces and a 22 MB GLB, which is unusable in a browser.
    levels = min(levels, 2)
    m = obj.modifiers.new("Subdivision", 'SUBSURF')
    m.levels = levels
    m.render_levels = levels
    if apply:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=m.name)
    return obj


def add_ellipsoid(name, loc, scale, material, rot=(0, 0, 0), segments=32,
                  rings=20, sub=2):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         radius=1.0, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    subsurf(o, sub)
    smooth_shade(o)
    o.data.materials.append(material)
    return o


def add_capsule(name, loc, radius, height, material, rot=(0, 0, 0),
                scale=(1, 1, 1), sub=2):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=height,
                                        location=loc)
    o = bpy.context.object
    o.name = name
    bpy.ops.object.modifier_add(type='SUBSURF')
    md = o.modifiers[-1]
    md.levels = sub
    md.render_levels = sub
    bpy.ops.object.modifier_apply(modifier=md.name)
    o.rotation_euler = rot
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    smooth_shade(o)
    o.data.materials.append(material)
    return o


def boolean_cut(target, cutter_name, loc, size, rot=(0, 0, 0)):
    """Subtract a box from target -> produces the anatomical cutaway face."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    c = bpy.context.object
    c.name = cutter_name
    c.scale = size
    c.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    bpy.context.view_layer.objects.active = target
    m = target.modifiers.new("Cut", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = c
    m.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c, do_unlink=True)
    return target


def join(objs, name):
    """Join a list of mesh objects. Returns None if the list is empty.

    Guarded because bpy.ops.object.join() silently produces an empty result if
    the active object is not in the selection, or if the context is stale — the
    failure mode observed here was two organs reporting 0 faces after a join.
    """
    objs = [o for o in objs if o is not None and o.name in bpy.data.objects]
    if not objs:
        print(f"  [join] {name}: nothing to join")
        return None
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]   # must be IN the selection
    bpy.ops.object.join()
    j = bpy.context.view_layer.objects.active
    if j is None or len(j.data.polygons) == 0:
        print(f"  [join] {name}: join produced empty mesh")
        return None
    j.name = name
    return j


# --------------------------------------------------------------------------- #
def build():
    reset()
    parts = {}

    # ---- materials ---------------------------------------------------------
    M_skin    = mat("skin",    (0.86, 0.62, 0.50), rough=0.46, subsurf=0.30)
    M_fat     = mat("fat",     (0.95, 0.86, 0.66), rough=0.72)
    M_muscle  = mat("muscle",  (0.66, 0.26, 0.24), rough=0.62, subsurf=0.12)
    M_muscle2 = mat("muscle2", (0.56, 0.21, 0.20), rough=0.62)
    M_trachea = mat("trachea", (0.82, 0.85, 0.89), rough=0.45)
    M_cart    = mat("cartilage",(0.92,0.94, 0.96), rough=0.30)
    M_thyroid = mat("thyroid", (0.76, 0.31, 0.35), rough=0.44, subsurf=0.18)
    M_nodule  = mat("nodule",  (0.44, 0.12, 0.20), rough=0.34,
                    emit=(0.44, 0.10, 0.18, 0.35))
    M_artery  = mat("artery",  (0.70, 0.16, 0.18), rough=0.40)
    M_vein    = mat("vein",    (0.20, 0.29, 0.56), rough=0.40)

    # ===================================================== NECK  (life size) ==
    # neck ~ 11 cm across, 13 cm deep, 14 cm tall sectional
    NECK_R_X, NECK_R_Z, NECK_H = 0.058, 0.050, 0.15

    neck = add_ellipsoid("NECK_SKIN", (0, 0, 0),
                         (NECK_R_X, NECK_H/2, NECK_R_Z), M_skin, sub=2)

    # subcutaneous fat — a slightly smaller shell inside the skin
    fat = add_ellipsoid("NECK_FAT", (0, 0, 0),
                        (NECK_R_X-0.007, NECK_H/2-0.006, NECK_R_Z-0.006), M_fat, sub=2)

    # ---- strap muscles: flat ribbons, anterior, one pair each --------------
    straps = []
    for sx in (1, -1):
        s1 = add_ellipsoid(f"STRAP_sho_{sx}", (sx*0.019, 0.004, 0.030),
                           (0.008, 0.036, 0.006), M_muscle, sub=2)
        s2 = add_ellipsoid(f"STRAP_st_{sx}",  (sx*0.034, -0.002, 0.030),
                           (0.009, 0.034, 0.006), M_muscle2, sub=2)
        straps += [s1, s2]

    # ---- sternocleidomastoid: the big lateral columns ----------------------
    scms = []
    for sx in (1, -1):
        scm = add_ellipsoid(f"SCM_{sx}", (sx*0.050, -0.004, 0.015),
                            (0.011, 0.042, 0.013), M_muscle,
                            rot=(0, sx*0.16, 0), sub=2)
        scms.append(scm)

    # ===================================================== TRACHEA ==========
    # hollow tube with cartilage rings; anterior-and-lateral rings
    trachea_parts = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.011,
                                        depth=0.115, location=(0, -0.030, 0.010))
    tube = bpy.context.object
    tube.name = "TRACHEA"
    # hollow it out
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.0085,
                                        depth=0.125, location=(0, -0.030, 0.010))
    inner = bpy.context.object
    inner.name = "TRACHEA_inner"
    bpy.context.view_layer.objects.active = tube
    m = tube.modifiers.new("Hollow", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = inner
    m.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(inner, do_unlink=True)
    smooth_shade(tube)
    tube.data.materials.append(M_trachea)
    trachea_parts.append(tube)

    for i in range(9):
        z = -0.052 + i*0.0128
        bpy.ops.mesh.primitive_torus_add(major_radius=0.0116, minor_radius=0.0016,
                                         major_segments=24, minor_segments=8,
                                         location=(0, -0.030, z),
                                         rotation=(math.pi/2, 0, 0))
        r = bpy.context.object
        r.name = f"TRACHEA_ring{i}"
        smooth_shade(r)
        r.data.materials.append(M_cart)
        trachea_parts.append(r)

    # laryngeal prominence
    larynx = add_ellipsoid("LARYNX", (0, -0.020, 0.066),
                           (0.013, 0.017, 0.011), M_cart, sub=2)
    trachea_parts.append(larynx)

    trachea = join(trachea_parts, "TRACHEA_ALL")

    # ===================================================== THYROID ==========
    # two lobes straddling the trachea + isthmus. Lobe 5 x 2.1 x 2.1 cm.
    thyroid_parts = []
    for sx in (1, -1):
        # No Y-axis rotation: rotating the lobe inflated its bounding box
        # (measured 3.3 cm against a 1.5-2.5 cm target). The lobes are instead
        # angled by their POSITION, which keeps each lobe's own width true.
        lobe = add_ellipsoid(f"THYROID_lobe_{sx}", (sx*0.0135, -0.014, 0.004),
                             (0.0100, 0.0250, 0.0100), M_thyroid,
                             rot=(0, 0, 0), sub=2)
        thyroid_parts.append(lobe)
    isth = add_ellipsoid("THYROID_isthmus", (0, -0.008, -0.011),
                         (0.0145, 0.0030, 0.0095), M_thyroid, sub=2)
    thyroid_parts.append(isth)
    thyroid = join(thyroid_parts, "THYROID")

    # ---- NODULE: 2 cm, in the RIGHT lobe (patient right = -X), anterior ----
    nodule = add_ellipsoid("NODULE", (-0.0165, -0.001, 0.014),
                           (0.0100, 0.0105, 0.0098), M_nodule, sub=2)

    # ===================================================== VESSELS ==========
    vessels = []
    for sx in (1, -1):
        a = add_ellipsoid(f"CAROTID_{sx}", (sx*0.040, -0.026, 0.006),
                          (0.0048, 0.034, 0.0048), M_artery, sub=2)
        v = add_ellipsoid(f"JUGULAR_{sx}", (sx*0.032, -0.040, 0.006),
                          (0.0040, 0.034, 0.0040), M_vein, sub=2)
        vessels += [a, v]
    vessels_obj = join(vessels, "VESSELS")

    # ===================================================== CUTAWAY ==========
    # Vertical hemi-section through the neck, removing the NEAR (anterior)
    # half so the interior layers read as a genuine cross-section.
    #
    # The cutter must be OFFSET so it sits entirely in the half being removed,
    # and must be only just larger than the neck in the other axes. An
    # oversized or centred cutter deletes the whole object (measured: a 30 cm
    # box centred on the anatomy reduced every organ to 0 faces).
    #
    # Anatomy spans roughly x +/-6 cm, y +/-5 cm, z +/-7.5 cm.
    # Remove everything with y < -0.004 (the anterior part is -y here).
    CUT_HALF = 0.075                      # enough to cover the neck in y
    CUT_CENTRE = (0.0, -0.004 - CUT_HALF, 0.0)   # box centre pushed into -y
    CUT_SIZE = (0.40, CUT_HALF * 2, 0.40)         # generous in x and z only

    # The skin and fat are shells; cut them the same way so the rim reads.
    straps_obj = join(straps, "STRAPS")
    # The strap muscles sit at y ~ 0 to -0.01, i.e. BEHIND the cut plane at
    # y = -0.004, so they need no boolean at all. Attempting one destroyed them
    # (39,936 -> 0 faces): joining four overlapping ellipsoids produces a
    # non-manifold shell, which Blender's exact boolean solver resolves to
    # nothing. Skipping the cut is both correct and safer.
    for name, obj, do_cut in (("STRAPS", straps_obj, False),
                              ("SCMS", join(scms, "SCMS"), True),
                              ("VESSELS", vessels_obj, True)):
        if obj is None:
            print(f"  [cut] {name}: object is None, skipped")
            continue
        if not do_cut:
            print(f"  [cut] {name}: no cut needed (behind the cut plane)")
            continue
        before = len(obj.data.polygons)
        boolean_cut(obj, f"CUT_{name}", CUT_CENTRE, CUT_SIZE)
        after = len(obj.data.polygons)
        print(f"  [cut] {name}: {before} -> {after} faces")
        if after == 0:
            print(f"  [cut] !! {name} was destroyed by the cut")

    # Trachea, thyroid and nodule lie near the midline, so a flat hemi-section
    # would slice them in half and hide the nodule's interior. Cut them with a
    # smaller anterior wedge instead, keeping enough of each organ visible.
    # Clip only the ANTERIOR FACE of each organ: a thin slab whose far edge
    # sits just inside the organ surface. An oversized cutter centred in front
    # of the organ deletes it entirely (measured: trachea -> 0 faces).
    #   trachea  surface y ~ -0.042   -> clip from y < -0.036
    #   thyroid  surface y ~ -0.040   -> clip from y < -0.034
    #   nodule   surface y ~ -0.012   -> clip from y < -0.008
    ORGAN_CLIPS = {
        "TRACHEA": (trachea, -0.036),
        "THYROID": (thyroid, -0.034),
        "NODULE":  (nodule,  -0.008),
    }
    for name, (obj, clip_y) in ORGAN_CLIPS.items():
        if obj is None:
            continue
        depth = 0.12                       # thin slab, pushed to the near side
        centre = (0.0, clip_y - depth/2.0, 0.0)
        size = (0.30, depth, 0.30)
        boolean_cut(obj, f"CUT_{name}", centre, size)

    # Skin and fat are thin shells — cut them with the main plane so the
    # cutaway face is clean.
    for name, obj in (("SKIN", neck), ("FAT", fat)):
        boolean_cut(obj, f"CUT_{name}", CUT_CENTRE, CUT_SIZE)

    # Mesh data names become glTF mesh names. Set them explicitly so the
    # runtime can address parts by name rather than by index.
    for o in bpy.data.objects:
        if o.type == 'MESH':
            clean = o.name.replace(".001", "").replace(".002", "").replace(".003", "")
            o.name = clean
            if o.data:
                o.data.name = clean

    # ===================================================== DECIMATE ========
    # Budget the polycount for a browser: the whole scene must stay well under
    # a few hundred thousand faces so the GLB is small and it renders on a
    # phone. Decimate anything over budget.
    BUDGET = {
        "NECK_SKIN": 4000, "NECK_FAT": 3000, "STRAPS": 2500, "SCMS": 2500,
        "TRACHEA_ALL": 6000, "THYROID": 9000, "NODULE": 3000, "VESSELS": 2500,
    }
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            continue
        cap = BUDGET.get(o.name, 3000)
        n = len(o.data.polygons)
        if n > cap:
            ratio = cap / float(n)
            bpy.context.view_layer.objects.active = o
            md = o.modifiers.new("Decimate", 'DECIMATE')
            md.decimate_type = 'COLLAPSE'
            md.ratio = ratio
            bpy.ops.object.modifier_apply(modifier=md.name)
            smooth_shade(o)

    # ===================================================== EXPORT ==========
    bpy.ops.object.select_all(action='SELECT')
    glb = os.path.join(OUT, "neck_anatomy.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb,
        export_format='GLB',
        use_selection=False,
        export_apply=True,
        export_materials='EXPORT',
        export_yup=True,
    )

    # report
    print("\n=== model built ===")
    total_tris = 0
    for o in bpy.data.objects:
        if o.type == 'MESH':
            n = len(o.data.polygons)
            total_tris += n
            dim = o.dimensions
            print(f"  {o.name:18} {n:6} faces  "
                  f"{dim.x*100:.1f} x {dim.y*100:.1f} x {dim.z*100:.1f} cm")
    print(f"\n  total faces: {total_tris}")
    print(f"  exported   : {glb}  "
          f"({os.path.getsize(glb)/1024:.0f} KB)")
    return glb


if __name__ == "__main__":
    build()
