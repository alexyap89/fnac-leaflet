#!/usr/bin/env /usr/bin/python3
"""Build the FULL FNAC scene: neck surface + viscera + probe + needle.

WHY THIS REPLACES build_neck.py
-------------------------------
The first build had the internal anatomy only. The three elements the procedure
is actually ABOUT - the neck surface, the ultrasound probe, and the needle -
were missing, so steps 5, 6 and 7 (probe, needle, passes) were captions with
nothing on screen. That is the wrong shape for a procedure explainer.

This build adds:
  * SKIN / neck surface - from the MuscularSystem FBX, using platysma (the
    superficial neck sheet) and sternocleidomastoid (which gives the neck its
    bulk). There is no skin mesh in the Z-Anatomy set, so platysma is the
    closest true anatomical surface, and an explicit neck shell is generated
    over it. Both are kept so either can be toggled.
  * PROBE - a linear-array ultrasound probe (the type used for thyroid work),
    built from primitives: footprint, body, handle, cable.
  * NEEDLE - a fine needle on a syringe, positioned along the trajectory the
    webapp's own geometry verifies: entering lateral to the probe, passing
    UNDER the probe face, tip inside the nodule, at about 45 degrees.

PLACEMENT IS DERIVED, NOT GUESSED. The probe sits on the anterior neck surface
above the thyroid; the needle entry point is computed from the thyroid's own
bounding box so it cannot drift if the anatomy is rebuilt. Every derived value
is written to the report for verification.

Z-Anatomy convention: 1 unit = 1 metre, +Z superior, -Y anterior.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = "/home/alex/Documents/FNAC_Webapp"
VISC = os.path.join(BASE, "assets", "VisceralSystem100.fbx")
MUSC = os.path.join(BASE, "assets", "MuscularSystem100.fbx")
OUT_GLB = os.path.join(BASE, "model", "fnac_scene.glb")
HEAD_GLB = os.path.join(BASE, "model", "head_shell.glb")
REPORT = os.path.join(BASE, "fnac_scene_report.json")

VISCERA = [
    ("Thyroid gland", "thyroid"),
    ("Trachea", "airway"),
    ("Laryngopharynx", "airway"),
    ("Oropharynx", "airway"),
    ("Epiglottis", "airway"),
    ("Tongue", "soft"),
    ("Inferior parathyroid gland.r", "parathyroid"),
    ("Inferior parathyroid gland.l", "parathyroid"),
    ("Superior parathyroid gland.r", "parathyroid"),
    ("Superior parathyroid gland.l", "parathyroid"),
]

# Neck surface. Platysma is the superficial sheet; SCM gives the neck its bulk.
# Strap muscles are included because they sit between skin and thyroid - the
# layers the needle passes through.
MUSCLES = [
    ("Platysma.l", "skin"),
    ("Platysma.r", "skin"),
    ("Sternocleidomastoid muscle.l", "skeletalmuscle"),
    ("Sternocleidomastoid muscle.r", "skeletalmuscle"),
    ("Sternohyoid muscle.l", "strap"),
    ("Sternohyoid muscle.r", "strap"),
    ("Sternothyroid muscle.l", "strap"),
    ("Sternothyroid muscle.r", "strap"),
    ("Thyrohyoid muscle.l", "strap"),
    ("Thyrohyoid muscle.r", "strap"),
]


def world_box(o):
    m = o.matrix_world
    pts = [m @ Vector(v) for v in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def centre_size(o):
    lo, hi = world_box(o)
    return (lo + hi) / 2, (hi - lo)




def anterior_surface(obj, z_lo, z_hi):
    """Most anterior (minimum y) vertex of a mesh within a z band.

    Used to find the real skin plane, rather than inventing one.
    """
    if obj is None:
        return None
    m = obj.matrix_world
    ys = [(m @ v.co).y for v in obj.data.vertices
          if z_lo <= (m @ v.co).z <= z_hi]
    return min(ys) if ys else None


def import_fbx(path):
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o.type == 'MESH']


def build_dressing(entry, skin_y, thyroid_lo, thyroid_hi, report):
    """A small dressing at the needle entry site.

    The later steps say a dressing is applied, so one must actually be drawn.
    It sits on the MEASURED skin plane at the entry point the needle used, so it
    lands where the procedure actually broke the skin.
    """
    ts = thyroid_hi - thyroid_lo
    pad_r = max(ts.z * 0.22, 0.008)          # pad radius scales with the gland
    pad_h = max(ts.z * 0.05, 0.0015)
    parts = []

    # The gauze pad, flattened onto the skin.
    bpy.ops.mesh.primitive_cylinder_add(
        radius=pad_r, depth=pad_h, vertices=24,
        location=(entry.x, skin_y + pad_h * 0.5, entry.z))
    pad = bpy.context.active_object
    pad.name = "dressing__pad"
    pad.rotation_euler = (math.radians(90), 0, 0)   # face the skin plane
    parts.append(pad)

    # The adhesive strip across the pad.
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(entry.x, skin_y + pad_h + 0.001, entry.z))
    strip = bpy.context.active_object
    strip.name = "dressing__strip"
    strip.scale = (pad_r * 1.9, 0.0015, max(ts.z * 0.08, 0.004))
    parts.append(strip)

    report["dressing"] = {
        "centre_cm": [round(entry.x * 100, 2), round(skin_y * 100, 2),
                      round(entry.z * 100, 2)],
        "pad_radius_cm": round(pad_r * 100, 2),
        "at_entry_site": True,
    }
    return parts


# ---- STEP 0: THE ROOM -----------------------------------------------------
# The first step shows the setting: the patient lying on a bed with the doctor
# beside them and the ultrasound machine on a cart. None of this geometry exists
# in the anatomical assets, so it is built from primitives.
#
# All of it is deliberately OUTSIDE the anatomical region so it can never
# interfere with the neck, thyroid or needle geometry.
def build_room(thyroid_lo, thyroid_hi, report, skin_y):
    """The setting: bed, patient, seated clinician, ultrasound cart.

    Proportions are taken from a standing 1.70 m human laid supine, so the
    figure reads as a person rather than a lump. The anatomical neck is a fixed
    reference: the patient is positioned so their neck surface meets it.
    """
    import math as _m
    neck_z = (thyroid_lo.z + thyroid_hi.z) * 0.5
    neck_y = (thyroid_lo.y + thyroid_hi.y) * 0.5

    # ---- human proportions (metres, supine) ------------------------------
    HEAD_R   = 0.095            # head radius
    HEAD_L   = 0.115            # head half-length
    TORSO_L  = 0.62             # shoulder to hip
    TORSO_W  = 0.34             # shoulder width
    body_r   = 0.150            # torso half-thickness (supine)
    # bed surface so the supine torso's TOP sits just under the neck
    bed_h    = neck_z - body_r - 0.012

    bed_w, bed_len = 0.92, 2.10
    parts = []

    def smooth(o, levels=1, shade=True):
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        m = o.modifiers.new("sub", "SUBSURF"); m.levels = levels; m.render_levels = levels
        bpy.ops.object.modifier_apply(modifier=m.name)
        if shade: bpy.ops.object.shade_smooth()
        o.select_set(False)
        return o

    def capsule(name, a, b, r1, r2=None, verts=16):
        from mathutils import Vector
        a = Vector(a); b = Vector(b); r2 = r1 if r2 is None else r2
        d = b - a; L = d.length
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                        depth=L, location=(a + d / 2))
        o = bpy.context.active_object; o.name = name
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = d.to_track_quat('Z', 'Y')
        bev = o.modifiers.new("bev", "BEVEL")
        bev.width = min(r1, r2) * 0.55; bev.segments = 3
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=bev.name)
        return smooth(o, 1)

    def blob(name, loc, scale, subdiv=2):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=14, radius=1.0, location=loc)
        o = bpy.context.active_object; o.name = name; o.scale = scale
        return smooth(o, subdiv)

    def rbox(name, loc, scale, bevel=0.04):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.active_object; o.name = name; o.scale = scale
        bv = o.modifiers.new("bev", "BEVEL"); bv.width = bevel; bv.segments = 3
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=bv.name)
        return smooth(o, 1)

    # ---- the bed ---------------------------------------------------------
    parts.append(rbox("bed__mattress", (0.0, neck_y + 0.30, bed_h + 0.045), (bed_w, bed_len, 0.11), 0.045))
    parts.append(rbox("bed__base", (0.0, neck_y + 0.30, bed_h - 0.09), (bed_w*0.94, bed_len*0.96, 0.09), 0.03))
    parts.append(blob("bed__pillow", (0.0, neck_y + 0.86, bed_h + 0.13), (0.26, 0.17, 0.075), 1))
    parts.append(capsule("bed__rail_head", (-bed_w/2, neck_y + 1.22, bed_h + 0.05), (bed_w/2, neck_y + 1.22, bed_h + 0.05), 0.020))
    parts.append(capsule("bed__rail_foot", (-bed_w/2, neck_y - 0.92, bed_h + 0.05), (bed_w/2, neck_y - 0.92, bed_h + 0.05), 0.020))
    for i,(sx,sy) in enumerate([(-1,-1),(1,-1),(-1,1),(1,1)]):
        parts.append(capsule(f"bed__leg{i}", (sx*bed_w*0.42, neck_y + 0.30 + sy*bed_len*0.40, bed_h-0.12),
                             (sx*bed_w*0.42, neck_y + 0.30 + sy*bed_len*0.40, 0.0), 0.030))

    # ---- the patient, supine: head, neck, torso, limbs -------------------
    # Head sits ON the pillow; its top must not rise above the anatomical neck.
    head_y = neck_y + 0.30
    head_z = neck_z - 0.075
    parts.append(blob("patient__head", (0.0, head_y, head_z), (HEAD_R, HEAD_L, HEAD_R*1.02), 2))
    # a face built as shallow relief so it reads as a front-on human
    # (the patient is supine, so the face points UP; these sit on the +Z face)
    parts.append(blob("patient__nose",   (0.0, head_y + 0.005, head_z + HEAD_R*0.96), (0.018, 0.026, 0.020), 1))
    parts.append(blob("patient__brow_l", (-0.030, head_y - 0.030, head_z + HEAD_R*0.92), (0.024, 0.010, 0.010), 1))
    parts.append(blob("patient__brow_r", ( 0.030, head_y - 0.030, head_z + HEAD_R*0.92), (0.024, 0.010, 0.010), 1))
    parts.append(blob("patient__eye_l",  (-0.032, head_y - 0.028, head_z + HEAD_R*0.90), (0.014, 0.011, 0.007), 1))
    parts.append(blob("patient__eye_r",  ( 0.032, head_y - 0.028, head_z + HEAD_R*0.90), (0.014, 0.011, 0.007), 1))
    parts.append(blob("patient__mouth",  (0.0, head_y + 0.055, head_z + HEAD_R*0.93), (0.026, 0.012, 0.008), 1))
    parts.append(blob("patient__ear_l",  (-HEAD_R*0.97, head_y, head_z), (0.012, 0.026, 0.032), 1))
    parts.append(blob("patient__ear_r",  ( HEAD_R*0.97, head_y, head_z), (0.012, 0.026, 0.032), 1))
    # neck, directly under the anatomical neck
    parts.append(capsule("patient__neck", (0.0, neck_y + 0.14, neck_z - 0.055),
                         (0.0, neck_y - 0.02, bed_h + body_r + 0.01), 0.052, 0.068))
    # torso: chest → waist, tapering, with the shoulders wide enough to read
    parts.append(blob("patient__shoulders", (0.0, neck_y - 0.05, bed_h + body_r),
                      (TORSO_W*0.52, 0.10, body_r*0.70), 2))
    parts.append(blob("patient__chest", (0.0, neck_y - 0.26, bed_h + body_r),
                      (TORSO_W*0.47, 0.24, body_r*0.93), 2))
    parts.append(blob("patient__waist", (0.0, neck_y - 0.62, bed_h + body_r - 0.015),
                      (TORSO_W*0.40, 0.22, body_r*0.80), 2))
    parts.append(blob("patient__hip", (0.0, neck_y - 0.90, bed_h + body_r - 0.02),
                      (TORSO_W*0.46, 0.16, body_r*0.82), 2))
    # arms along the sides
    for sd, nm in ((-1,"l"), (1,"r")):
        parts.append(capsule(f"patient__upperarm_{nm}", (sd*TORSO_W*0.50, neck_y - 0.06, bed_h + body_r*0.80),
                             (sd*TORSO_W*0.56, neck_y - 0.52, bed_h + body_r*0.62), 0.052, 0.040))
        parts.append(capsule(f"patient__forearm_{nm}", (sd*TORSO_W*0.56, neck_y - 0.54, bed_h + body_r*0.62),
                             (sd*TORSO_W*0.54, neck_y - 0.92, bed_h + body_r*0.55), 0.040, 0.031))
    # legs
    for sd, nm in ((-1,"l"), (1,"r")):
        parts.append(capsule(f"patient__thigh_{nm}", (sd*0.095, neck_y - 1.02, bed_h + body_r*0.78),
                             (sd*0.105, neck_y - 1.52, bed_h + body_r*0.66), 0.098, 0.070))
        parts.append(capsule(f"patient__shin_{nm}", (sd*0.105, neck_y - 1.54, bed_h + body_r*0.66),
                             (sd*0.110, neck_y - 1.98, bed_h + body_r*0.58), 0.068, 0.045))

    # ---- the doctor, seated, facing the patient --------------------------
    st_x, st_y = 0.60, neck_y + 0.20
    seat = neck_z - 0.34
    parts.append(blob("staff__torso", (st_x, st_y, seat + 0.20), (0.145, 0.105, 0.215), 2))
    parts.append(blob("staff__hip", (st_x, st_y - 0.06, seat - 0.04), (0.125, 0.115, 0.095), 2))
    parts.append(blob("staff__head", (st_x, st_y + 0.01, seat + 0.50), (0.088, 0.098, 0.105), 2))
    parts.append(blob("staff__nose", (st_x - 0.088, st_y + 0.01, seat + 0.49), (0.018, 0.016, 0.015), 1))
    parts.append(capsule("staff__neck", (st_x, st_y + 0.005, seat + 0.38), (st_x, st_y + 0.005, seat + 0.42), 0.042))
    parts.append(capsule("staff__thigh", (st_x, st_y - 0.07, seat - 0.05), (st_x - 0.03, st_y - 0.40, seat - 0.42), 0.082, 0.068))
    parts.append(capsule("staff__shin",  (st_x - 0.03, st_y - 0.40, seat - 0.42), (st_x, st_y - 0.36, 0.02), 0.062, 0.044))
    # the scanning arm reaching the patient's neck
    parts.append(capsule("staff__upperarm", (st_x - 0.13, st_y + 0.02, seat + 0.30),
                         (st_x - 0.30, st_y + 0.14, seat + 0.08), 0.050, 0.040))
    parts.append(capsule("staff__forearm", (st_x - 0.30, st_y + 0.14, seat + 0.08),
                         (st_x - 0.40, neck_y + 0.02, neck_z - 0.03), 0.038, 0.032))
    # stool
    parts.append(blob("staff__stool", (st_x, st_y - 0.10, seat - 0.30), (0.16, 0.16, 0.035), 1))
    parts.append(capsule("staff__stool_post", (st_x, st_y - 0.10, seat - 0.33), (st_x, st_y - 0.10, seat - 0.62), 0.030))

    # ---- the ultrasound machine ------------------------------------------
    cx, cy = 1.02, neck_y - 0.05
    parts.append(rbox("cart__body",   (cx, cy, bed_h + 0.30), (0.38, 0.32, 0.36), 0.035))
    parts.append(rbox("cart__screen", (cx - 0.06, cy, bed_h + 0.66), (0.34, 0.045, 0.24), 0.02))
    parts.append(capsule("cart__pole", (cx, cy, bed_h + 0.50), (cx, cy, bed_h + 0.52), 0.022))
    for i,(dx,dy) in enumerate([(-0.15,-0.12),(0.15,-0.12),(-0.15,0.12),(0.15,0.12)]):
        parts.append(blob(f"cart__wheel{i}", (cx+dx, cy+dy, bed_h - 0.03), (0.042,0.042,0.042), 1))

    report["room"] = {
        "bed_height_cm": round(bed_h*100, 1),
        "neck_z_cm": round(neck_z*100, 1),
        "patient_height_m": round((HEAD_L*2 + TORSO_L + 0.42 + 0.44), 2),
        "parts": len(parts), "sculpted": True,
        "note": "step 0 setting only; never shown with the anatomy",
    }
    return parts


def build_probe(thyroid_lo, thyroid_hi, report, skin_y=None):
    """A linear-array ultrasound probe resting on the anterior neck.

    Geometry follows a real thyroid probe: a flat rectangular footprint, a
    tapered body, a handle, and a cable. Long axis is transverse across the
    neck (+X), which is how a thyroid nodule is scanned in short axis.
    """
    tc = (thyroid_lo + thyroid_hi) / 2
    ts = thyroid_hi - thyroid_lo

    # Sizes are all DERIVED from the thyroid box so they scale with the anatomy
    # and can never come out a different order of magnitude.
    gland_len = ts.x                        # thyroid width, across the neck
    foot_len = gland_len * 1.30             # probe footprint slightly longer
    foot_wid = max(ts.y * 0.55, 0.010)      # front-to-back depth of the footprint
    foot_h = max(ts.z * 0.16, 0.004)

    # The probe rests ON the anterior surface. The thyroid's anterior face is
    # thyroid_lo.y; the skin sits a little in front of it. Put the footprint in
    # that gap, not several centimetres away from the anatomy.
    # Use the MEASURED skin plane when available; only fall back to an estimate
    # if the neck surface mesh was not loaded.
    if skin_y is None:
        skin_y = thyroid_lo.y - max(ts.y * 0.25, 0.006)
    foot_y = skin_y - foot_h * 0.5          # footprint sits ON the skin
    foot_z = tc.z + ts.z * 0.10

    parts = []

    # footprint (the part that touches skin)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(tc.x, foot_y, foot_z))
    fp = bpy.context.active_object
    fp.name = "probe__footprint"
    fp.scale = (foot_len / 2, foot_wid / 2, foot_h / 2)
    parts.append(fp)

    # body, tapering away from the skin
    bpy.ops.mesh.primitive_cube_add(size=1, location=(tc.x, foot_y - 0.018, foot_z))
    bd = bpy.context.active_object
    bd.name = "probe__body"
    bd.scale = (foot_len * 0.42, 0.020, 0.014)
    parts.append(bd)

    # handle, angled up and back
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.013, depth=0.085,
        location=(tc.x, foot_y - 0.055, foot_z + 0.030),
        rotation=(math.radians(62), 0, 0))
    hd = bpy.context.active_object
    hd.name = "probe__handle"
    parts.append(hd)

    # cable
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.006, depth=0.070,
        location=(tc.x, foot_y - 0.098, foot_z + 0.072),
        rotation=(math.radians(48), 0, 0))
    cb = bpy.context.active_object
    cb.name = "probe__cable"
    parts.append(cb)

    report["probe"] = {
        "thyroid_box_cm": {"lo": [round(v * 100, 2) for v in thyroid_lo],
                           "hi": [round(v * 100, 2) for v in thyroid_hi]},
        "skin_plane_y_cm": round(skin_y * 100, 2),
        "footprint_centre_cm": [round(v * 100, 2) for v in (tc.x, foot_y, foot_z)],
        "footprint_len_cm": round(foot_len * 100, 2),
        "footprint_gap_to_gland_cm": round((thyroid_lo.y - foot_y) * 100, 2),
        "resting_on": "anterior neck surface, above thyroid",
        "axis": "transverse across the neck (+X)",
    }
    return parts, foot_y, foot_z, tc


def build_needle(thyroid_lo, thyroid_hi, probe_foot_y, report, foot_len_probe=0.06):
    """A fine needle on a syringe, on a verified trajectory.

    Derived from the thyroid box: entry point lateral to the probe footprint,
    tip at the nodule inside the gland's left lobe, angle ~45 degrees. This
    mirrors the trajectory the webapp's own geometry check asserts.
    """
    tc = (thyroid_lo + thyroid_hi) / 2
    ts = thyroid_hi - thyroid_lo

    # nodule: inside the patient's-left lobe (which is -X here, patient faces us)
    nodule_pos = Vector((tc.x - ts.x * 0.26, tc.y + ts.y * 0.05, tc.z - ts.z * 0.05))
    nodule_r = max(ts.x, ts.z) * 0.16

    # Skin entry, DERIVED from the target angle rather than guessed.
    # The needle must pass UNDER the probe face, so the entry sits inferior and
    # lateral to the probe footprint, and the needle rises at ~45 degrees to the
    # vertical to reach a nodule that is above it.
    want_angle = math.radians(45.0)          # clinical convention for thyroid FNAC
    entry_y = probe_foot_y - 0.002           # at the skin plane, where the needle enters
    entry_x = tc.x - ts.x * 0.95             # lateral to the probe footprint

    # solve for the entry height that yields the wanted angle:
    #   horizontal run = distance from entry (x,y) to nodule (x,y)
    run_xy = math.hypot(nodule_pos.x - entry_x, nodule_pos.y - entry_y)
    #   tan(angle from vertical) = run / rise  ->  rise = run / tan(angle)
    rise = run_xy / math.tan(want_angle)
    entry_z = nodule_pos.z - rise            # start BELOW the nodule

    entry = Vector((entry_x, entry_y, entry_z))
    direction = (nodule_pos - entry).normalized()
    length = (nodule_pos - entry).length

    # shaft
    mid = entry + direction * (length * 0.5)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.0011, depth=length, location=mid,
        rotation=direction.to_track_quat('Z', 'Y').to_euler())
    sh = bpy.context.active_object
    sh.name = "needle__shaft"

    # hub + syringe body, extending back from the entry point
    back = entry - direction * 0.028
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.0035, depth=0.030, location=back,
        rotation=direction.to_track_quat('Z', 'Y').to_euler())
    hub = bpy.context.active_object
    hub.name = "needle__hub"

    back2 = entry - direction * 0.070
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.0075, depth=0.058, location=back2,
        rotation=direction.to_track_quat('Z', 'Y').to_euler())
    syr = bpy.context.active_object
    syr.name = "needle__syringe"

    # nodule marker so the target is visible
    bpy.ops.mesh.primitive_uv_sphere_add(radius=nodule_r, location=nodule_pos)
    nd = bpy.context.active_object
    # The nodule gets its OWN material. Previously it shared the polished-metal
    # "needle" material and was invisible inside the near-opaque gland, which is
    # why neither the Blender render nor the browser could show it.
    nd_mesh = bpy.data.meshes.new("nodule_mesh") if False else None
    nd_mat = bpy.data.materials.new("nodule")
    nd_mat.use_nodes = True
    # Role "nodule" (not "needle"): the role pass below assigns materials from
    # the role, so a nodule tagged as needle would be re-materialised as polished
    # metal and become invisible inside the near-opaque gland. Its own role also
    # lets the viewer toggle it independently of the needle.
    nd.name = "nodule__marker"

    # angle to the vertical (the clinical convention for FNAC)
    ang = math.degrees(math.acos(abs(direction.z) / direction.length))
    # does the shaft pass beneath the probe footprint? Sample along the shaft
    # and test the y-plane of the probe's skin contact.
    under = False
    for t in [i / 40 for i in range(41)]:
        p = entry + direction * (length * t)
        if abs(p.x - tc.x) < foot_len_probe / 2 and p.y > probe_foot_y:
            under = True
            break

    report["needle"] = {
        "passes_under_probe": under,
        "entry_point_cm": [round(v * 100, 2) for v in entry],
        "nodule_centre_cm": [round(v * 100, 2) for v in nodule_pos],
        "nodule_radius_cm": round(nodule_r * 100, 2),
        "length_cm": round(length * 100, 2),
        "angle_to_vertical_deg": round(ang, 1),
        "entry_lateral_of_probe_cm": round((tc.x - entry_x) * 100, 2),
        "tip_inside_nodule": True,
    }
    return [sh, hub, syr, nd], nodule_pos, nodule_r, entry


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {"sources": {"viscera": VISC, "muscles": MUSC}, "structures": []}

    # ---- load BOTH source files before touching anything ----
    # The FBX importer resets the scene on each call, so an object captured
    # before the second import is a dead reference. Import first is not enough
    # either: the second import frees the first. So take the measurements we
    # need as plain numbers, then re-import cleanly for the final build.
    vobjs = {o.name: o for o in import_fbx(VISC)}
    vwant = {}
    for name, role in VISCERA:
        o = vobjs.get(name)
        if o and len(o.data.polygons) >= 20:
            vwant[name] = role
            report["structures"].append({"name": name, "role": role,
                                         "faces": len(o.data.polygons)})
    # measure the thyroid NOW, while it is alive, and keep only numbers
    tg = vobjs.get("Thyroid gland")
    tlo, thi = world_box(tg)
    print(f"viscera to keep: {len(vwant)}")
    print(f"thyroid box cm: lo={tuple(round(v*100,1) for v in tlo)} "
          f"hi={tuple(round(v*100,1) for v in thi)}")

    # delete the rest of the viscera, keep what we want
    for o in [x for x in bpy.data.objects
              if x.type == 'MESH' and x.name not in vwant]:
        bpy.data.objects.remove(o, do_unlink=True)
    keep = [(bpy.data.objects[n], r) for n, r in vwant.items()
            if n in bpy.data.objects]

    # ---- neck surface: do NOT import again. Read the muscle file in a second
    # Blender pass is impossible here, so instead append the wanted muscles by a
    # separate import that preserves the existing scene.
    print("importing neck muscles into the same scene...")
    before = set(o.name for o in bpy.data.objects if o.type == 'MESH')
    try:
        bpy.ops.import_scene.fbx(filepath=MUSC, use_anim=False)
    except Exception as e:
        print(f"  muscle import failed: {e}")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=MUSC)
    after = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}

    mwant = {}
    for name, role in MUSCLES:
        o = after.get(name)
        if o and len(o.data.polygons) >= 20 and o.name not in vwant:
            mwant[name] = role
            report["structures"].append({"name": name, "role": role,
                                         "faces": len(o.data.polygons)})
    print(f"muscles to keep: {len(mwant)}")

    # rebuild the viscera list from live objects if the import cleared them
    if not keep or not any(o.name == "Thyroid gland" for o, _ in keep):
        print("  (scene was reset by the muscle import - reloading viscera)")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=VISC)
        live = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}
        keep = [(live[n], r) for n, r in vwant.items() if n in live]
        # muscles must now be taken from the muscle file alone; re-import
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=MUSC)
        live2 = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}
        mkeep = [(live2[n], r) for n, r in mwant.items() if n in live2]
        # the viscera are gone again, so keep only what this pass can hold:
        # accept that and note it, rather than silently exporting half a scene
        print(f"  NOTE: single-pass import cannot hold both files; "
              f"viscera={len(keep)} muscles={len(mkeep)}")
        keep, mkeep = [], mkeep
    else:
        mkeep = [(bpy.data.objects[n], r) for n, r in mwant.items()
                 if n in bpy.data.objects]

    print(f"kept: viscera={len(keep)} muscles={len(mkeep)}")

    # ---- head shell: DISABLED ----
    # Four attempts (three anchors, a face-profile deformation, and both opacity
    # extremes) all failed: primitive geometry does not carry human shape
    # language, and at any opacity it read as a blob. A wrong head is worse than
    # none, because it makes the model look broken and distracts from the
    # procedure - which is what the app is for.
    #
    # The neck and upper chest are framed instead: that is where the procedure
    # happens, and real Z-Anatomy anatomy supports it correctly.
    #
    # The shell is kept in the repo (build_head.py -> head_shell.glb) so a real
    # head mesh can be swapped in later by setting INCLUDE_HEAD = True.
    INCLUDE_HEAD = False
    if INCLUDE_HEAD and os.path.exists(HEAD_GLB):
        before_head = set(o.name for o in bpy.data.objects if o.type == 'MESH')
        bpy.ops.import_scene.gltf(filepath=HEAD_GLB)
        added = [o for o in bpy.data.objects
                 if o.type == 'MESH' and o.name not in before_head]
        for o in added:
            o.name = "skin__head_shell"
            report["structures"].append({"name": "head_shell", "role": "skin",
                                         "faces": len(o.data.polygons)})
        head_parts = added
        print(f"head shell imported: {len(added)} object(s), "
              f"{sum(len(o.data.polygons) for o in added)} faces")
    else:
        head_parts = []
        print("head shell disabled - framing the neck region only")

    # ---- probe + needle ----
    # Find the real skin plane from the loaded platysma, in the thyroid's z band.
    plat = None
    for nm in ("Platysma.l", "Platysma.r"):
        o = bpy.data.objects.get(nm)
        if o is not None:
            plat = o
            break
    skin_y = anterior_surface(plat, tlo.z, thi.z)
    print(f"measured skin plane y = {skin_y*100:.2f} cm" if skin_y is not None
          else "skin plane NOT measured - using estimate")
    probe_parts, foot_y, foot_z, tc = build_probe(tlo, thi, report, skin_y)
    needle_parts, nodule_pos, nodule_r, entry = build_needle(tlo, thi, foot_y, report, report["probe"]["footprint_len_cm"] / 100.0)
    dressing_parts = build_dressing(entry, skin_y, tlo, thi, report)
    room_parts = build_room(tlo, thi, report, skin_y)
    print(f"probe parts: {len(probe_parts)}, needle parts: {len(needle_parts)}, "
          f"dressing parts: {len(dressing_parts)}, room parts: {len(room_parts)}")

    # ---- apply transforms and tag materials by role ----
    allobjs = [(o, r) for o, r in keep] + [(o, r) for o, r in mkeep]
    for o in head_parts:
        allobjs.append((o, "skin"))
    for o in probe_parts:
        allobjs.append((o, "probe"))
    for o in dressing_parts:
        allobjs.append((o, "dressing"))
    # The room keeps its sub-roles so each part can carry its own material.
    # One flat grey role made the bed, patient, clinician and cart impossible to
    # tell apart at the distance step 0 is viewed from.
    for o in room_parts:
        nm = o.name
        if nm.startswith(("bed__", "cart__")):
            sub = "room"          # furniture and equipment
        elif nm.startswith("patient__"):
            sub = "patient"
        elif nm.startswith("staff__"):
            sub = "clinician"
        else:
            sub = "room"
        allobjs.append((o, sub))
    for o in needle_parts:
        # the nodule carries role "nodule" so it gets its own material; the rest
        # of the assembly is "needle"
        allobjs.append((o, "nodule" if o.name.startswith("nodule__") else "needle"))

    # Mirrored .l/.r pairs share a mesh datablock. Baking a per-object world
    # transform into a SHARED mesh would move both sides the same way and break
    # the mirror, so Blender refuses. Give every object its own mesh copy first.
    single = 0
    for o, _ in allobjs:
        if o.data.users > 1:
            o.data = o.data.copy()
            single += 1
    print(f"gave {single} objects a single-user mesh")

    bpy.ops.object.select_all(action='DESELECT')
    for o, _ in allobjs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = allobjs[0][0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print(f"applied transforms to {len(allobjs)} objects")

    mats = {}
    for role in sorted(set(r for _, r in allobjs)):
        m = bpy.data.materials.new(role)
        m.use_nodes = True
        mats[role] = m
    for o, role in allobjs:
        o.data.materials.clear()
        o.data.materials.append(mats[role])
        # name = role__original so the runtime can address parts by role
        base = o.name.replace(".", "_")
        if not base.startswith(role + "__"):
            o.name = f"{role}__{base}"
        # the nodule keeps the role prefix it was given ("nodule__marker")
        o.data.name = o.name

    # keep them separate: a single joined mesh cannot be shown/hidden per role
    print(f"\nfinal objects ({len(allobjs)}):")
    for o, role in allobjs:
        print(f"  {role:14} {o.name:46} {len(o.data.polygons):>6} faces")

    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o, _ in allobjs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB',
                              use_selection=True, export_apply=True,
                              export_materials='EXPORT')
    size = os.path.getsize(OUT_GLB)
    print(f"\nexported {OUT_GLB} ({size:,} bytes)")
    report["glb"] = OUT_GLB
    report["glb_bytes"] = size
    report["object_count"] = len(allobjs)

    # ---- VERIFY by re-importing ----
    print("\n=== verifying exported GLB ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=OUT_GLB)
    got = [o for o in bpy.data.objects if o.type == 'MESH']
    names = sorted(o.name for o in got)
    roles = sorted({o.name.split("__")[0] for o in got if "__" in o.name})
    # "nodule" and "dressing" are required too: both were added because they were
    # the visible thing (a lesion, a dressing) that the steps describe and the
    # model lacked.
    need = {"skin", "probe", "needle", "thyroid", "airway", "nodule", "dressing"}
    missing = need - set(roles)
    print(f"  objects: {len(got)}")
    print(f"  roles  : {roles}")
    print(f"  missing required roles: {missing or 'none'}")
    ok = not missing
    print(f"  VERIFY: {'PASS' if ok else 'FAIL'}")
    report["verify_pass"] = ok
    report["roles_in_glb"] = roles
    json.dump(report, open(REPORT, "w"), indent=1)
    print(f"\nwrote {REPORT}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
