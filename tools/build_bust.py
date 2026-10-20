import bpy
import bmesh
import json
import math
import os
from mathutils import Vector

# === 1. Reset to empty scene ===
bpy.ops.wm.read_factory_settings(use_empty=True)

# === 2. Import GLB ===
import_path = "/Users/alexyap/My Drive/20_Projects/Radiology/01-Active/FNAC Webapp/model/fnac_scene_web.glb"
bpy.ops.import_scene.gltf(filepath=import_path)

# === 3. Loft table (z, a, b, cy) ===
# The neck may not go below a=0.063: the reported skin entry point sits 6.1 cm
# from the neck axis and has to stay on the surface. So the head-to-neck
# contrast that makes a silhouette read as human is bought by widening the
# cranium instead, and the shoulder shelf reaches full width by z=1.305 so it
# reads as shoulders rather than as a vase foot.
table = [
    (1.256, 0.178, 0.098,  0.005),
    (1.265, 0.180, 0.100,  0.005),
    (1.280, 0.182, 0.102,  0.004),
    (1.295, 0.182, 0.102,  0.003),
    (1.305, 0.180, 0.100,  0.002),
    (1.315, 0.172, 0.096,  0.002),
    (1.325, 0.158, 0.088,  0.003),
    (1.335, 0.130, 0.080,  0.004),
    (1.345, 0.092, 0.068,  0.006),
    (1.355, 0.070, 0.060,  0.007),
    (1.365, 0.064, 0.057,  0.008),
    (1.380, 0.063, 0.056,  0.009),
    (1.400, 0.063, 0.056,  0.009),
    (1.420, 0.063, 0.057,  0.009),
    (1.440, 0.061, 0.055,  0.009),
    (1.460, 0.058, 0.054,  0.010),
    (1.475, 0.054, 0.053,  0.011),
    (1.487, 0.056, 0.055,  0.013),
    (1.497, 0.063, 0.073,  0.020),
    (1.510, 0.074, 0.082,  0.010),
    (1.524, 0.082, 0.088, -0.002),
    (1.545, 0.085, 0.095, -0.007),
    (1.570, 0.087, 0.097, -0.008),
    (1.595, 0.086, 0.096, -0.006),
    (1.620, 0.081, 0.090, -0.004),
    (1.645, 0.071, 0.079, -0.004),
    (1.665, 0.054, 0.062, -0.004),
    (1.678, 0.029, 0.035, -0.004),
    (1.688, 0.009, 0.012, -0.004),
]

# Angular and vertical sampling. The face needs the finer of the two: a nose is
# only about 12 degrees wide, so at N=128 it spanned roughly four vertices and
# read as a lump rather than a nose. 256 samples is 1.4 degrees apart, which
# gives the raised-cosine falloff enough room to be smooth.
N = 256
dz = 0.003
# === 4. Feature definitions (z1, z2, t0_deg, amplitude, angular_half_width_deg) ===
features = [
    (1.355, 1.475,  40.0,  0.009, 22.0),
    (1.355, 1.475, 140.0,  0.009, 22.0),
    (1.410, 1.450,  90.0,  0.006, 16.0),
    (1.478, 1.492,  90.0, -0.003, 20.0),
    (1.295, 1.340,  90.0, -0.009, 18.0),
    (1.312, 1.338,  60.0,  0.007, 26.0),
    (1.312, 1.338, 120.0,  0.007, 26.0),
    (1.295, 1.352, 270.0,  0.012, 34.0),
    # A jaw line and a chin. These are proportions of a head, not facial
    # decoration: without them the head reads as a ball on a stick.
    (1.500, 1.524,  62.0,  0.006, 38.0),
    (1.500, 1.524, 118.0,  0.006, 38.0),
    (1.488, 1.508,  90.0,  0.005, 26.0),
]

# The face is data, not hand-tuning. _lab/face_spec_v2.json was authored by the
# local model (mtplx) against this exact builder's convention (theta 90 = front,
# 0/180 = sides, 270 = back; amplitude is peak radial displacement with a
# raised-cosine falloff). Each feature entry is [z1, z2, theta, amp_m,
# half_width_deg, "what it is"], so the label is dropped and the rest maps 1:1
# onto the tuples above. v2 also carries eyeball/iris/brow geometry and the hair
# rim, all of which the old spec had no place for. Keeping it in JSON means the
# face can be re-specified without touching this script.
LAB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lab")
FACE_SPEC = os.path.join(LAB, "face_spec_v2.json")
if not os.path.exists(FACE_SPEC):
    FACE_SPEC = os.path.join(LAB, "face_spec.json")
FACE_FEATURES = []
HAIR_SPEC = None
EYES, BROWS, SHAPES = [], [], []
if os.path.exists(FACE_SPEC):
    with open(FACE_SPEC) as fh:
        _spec = json.load(fh)
    FACE_FEATURES = [tuple(row[:5]) for row in _spec.get("face_features", [])]
    HAIR_SPEC = _spec.get("hair")
    EYES = _spec.get("eyes", []) or []
    BROWS = _spec.get("brows", []) or []
    SHAPES = _spec.get("surface_shapes", []) or []
    # table_edits are [z, a, b, cy]: replace the row at that z, or append it and
    # re-sort if there is none. (The original unpacked five names from a
    # four-element row, so any spec carrying edits would have crashed.)
    for _dz in _spec.get("table_delete", []):
        before = len(table)
        table[:] = [r for r in table if abs(r[0] - _dz) > 1e-6]
        print(f"  table delete at z {_dz:.3f}: removed {before - len(table)} row(s)")
    for _row in _spec.get("table_edits", []):
        _z, _a, _b, _c = _row[:4]
        for idx, (tz, _ta, _tb, _tcy) in enumerate(table):
            if abs(tz - _z) < 1e-6:
                table[idx] = (_z, _a, _b, _c)
                break
        else:
            table.append((_z, _a, _b, _c))
            table.sort(key=lambda r: r[0])
        print(f"  table edit at z {_z:.3f}: a {_a:.3f} b {_b:.3f} cy {_c:.3f}")
    print('EFFECTIVE TABLE:')
    for _r in table: print('   [%.4f, %.4f, %.4f, %.4f],' % _r)
    features += FACE_FEATURES
    print(f"face spec {os.path.basename(FACE_SPEC)}: {len(FACE_FEATURES)} features, "
          f"{len(_spec.get('table_edits', []))} table edits, {len(EYES)} eyes, "
          f"{len(BROWS)} brows, hair {bool(HAIR_SPEC)}")
else:
    print("WARNING: no face spec, building the plain head")


# The table is only now final: the spec above may have replaced or deleted rows,
# so the interpolation has to be built from it HERE, not before. Building it
# earlier silently discarded every table_edit and table_delete.
z_lo = table[0][0]
z_hi = table[-1][0]
n_rows = int(round((z_hi - z_lo) / dz)) + 1

# Monotone cubic (PCHIP) interpolation to uniform rows, NOT Catmull-Rom.
# Catmull-Rom is not monotone-preserving: where the table's row spacing changes - the
# crown rows are 10 mm apart while the neck rows are up to 55 mm - it overshoots its
# own control points, and that overshoot rippled the surface in and out every few
# millimetres. On a head that reads as a series of rims or a flange, and it survived
# subdivision untouched (verified: identical ripples at 30k and 186k triangles).
# PCHIP cannot overshoot by construction.
def _pchip_tangents(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0] = d[0]
    m[-1] = d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0.0:
            m[i] = 0.0
        else:
            w1 = 2.0 * h[i] + h[i - 1]
            w2 = h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    return m


def _hermite(x0, y0, m0, x1, y1, m1, x):
    h = x1 - x0
    if h <= 0:
        return y0
    tt = (x - x0) / h
    t2 = tt * tt
    t3 = t2 * tt
    return ((2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + tt) * h * m0
            + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * h * m1)


_xs = [r[0] for r in table]
_TA = _pchip_tangents(_xs, [r[1] for r in table])
_TB = _pchip_tangents(_xs, [r[2] for r in table])
_TC = _pchip_tangents(_xs, [r[3] for r in table])


def _eval(idx, tan, z):
    if z <= _xs[0]:
        return table[0][idx]
    if z >= _xs[-1]:
        return table[-1][idx]
    lo = len(_xs) - 2
    for j in range(len(_xs) - 1):
        if _xs[j] <= z <= _xs[j + 1]:
            lo = j
            break
    return _hermite(_xs[lo], table[lo][idx], tan[lo],
                    _xs[lo + 1], table[lo + 1][idx], tan[lo + 1], z)


interp_table = []
for i in range(n_rows):
    z = max(z_lo, min(z_hi, z_lo + i * dz))
    interp_table.append((z, _eval(1, _TA, z), _eval(2, _TB, z), _eval(3, _TC, z)))

fp_z1, fp_z2 = 1.545, 1.630   # start ABOVE the nose: it was flattening the nose away
fp_t0, fp_hw = 90.0, 55.0
fp_amt = 0.02


def _raised_cos(x, hw):
    if abs(x) > hw:
        return 0.0
    c = math.cos(math.pi * x / (2.0 * hw))
    return c * c


def _ang_dist(t1, t2):
    d = t1 - t2
    while d > 180.0:
        d -= 360.0
    while d < -180.0:
        d += 360.0
    return d


def _displace(x, y, z, cy):
    dx, dy = x, y - cy
    r = math.sqrt(dx * dx + dy * dy)
    if r < 1e-10:
        return x, y
    t_deg = math.degrees(math.atan2(dy, dx))
    if t_deg < 0.0:
        t_deg += 360.0

    # Radial bumps
    disp = 0.0
    for (z1, z2, t0, amp, hw) in features:
        if z < z1 - 1e-9 or z > z2 + 1e-9:
            continue
        zm = (z1 + z2) * 0.5
        zh = (z2 - z1) * 0.5
        if zh < 1e-9:
            continue
        zf = _raised_cos(z - zm, zh)
        af = _raised_cos(_ang_dist(t_deg, t0), hw)
        disp += amp * zf * af

    if abs(disp) > 1e-12:
        nr = r + disp
        if nr < 0.0:
            nr = 0.0
        s = nr / r
        x = x * s
        y = cy + (y - cy) * s
        dx, dy = x, y - cy
        r = math.sqrt(dx * dx + dy * dy)
        if r < 1e-10:
            return x, y
        t_deg = math.degrees(math.atan2(dy, x))
        if t_deg < 0.0:
            t_deg += 360.0

    # Face plane (flatten front)
    if fp_z1 <= z <= fp_z2:
        zm = (fp_z1 + fp_z2) * 0.5
        zh = (fp_z2 - fp_z1) * 0.5
        zf = _raised_cos(z - zm, zh)
        af = _raised_cos(_ang_dist(t_deg, fp_t0), fp_hw)
        scale = 1.0 - fp_amt * zf * af
        dy = y - cy
        if dy > 0.0:
            y = cy + dy * scale

    return x, y


# === 5. Build bmesh ===
bm = bmesh.new()
rows = []
for (z, a, b, cy) in interp_table:
    row = []
    for i in range(N):
        t = 2.0 * math.pi * i / N
        x = a * math.cos(t)
        y = cy + b * math.sin(t)
        x, y = _displace(x, y, z, cy)
        row.append(bm.verts.new((x, y, z)))
    rows.append(row)

# Feather the cheeks and temples. Twenty-odd radial features on a loft leave visible
# ridges where their falloffs meet, and the user's read of that was "weird contours
# on the face".
#
# STOP AT THE HAIRLINE. Extending this over the crown was a mistake with a clear
# signature: a Laplacian pass pulls a CONVERGING surface inward, and the crown
# converges 15 mm per row, so smoothing it shrank the skull unevenly and produced
# exactly the stepped lid and flange the user could see. Measured: 42 mm of radius
# where the table specifies 68. The window now stops at 1.660; the crown's shape is
# entirely the table's business, which is what the explicit dome rows are for.
_face_lo, _face_hi = 1.488, 1.660
for _it in range(3):
    for _ri in range(1, len(rows) - 1):
        z = rows[_ri][0].co.z
        if not (_face_lo <= z <= _face_hi):
            continue
        for _ci in range(N):
            v = rows[_ri][_ci]
            dx, dy = v.co.x, v.co.y - interp_table[_ri][3]
            t_deg = math.degrees(math.atan2(dy, dx)) % 360.0
            off = abs(((t_deg - 90.0 + 180.0) % 360.0) - 180.0)
            if (off < 14.0 and 1.515 <= z <= 1.615) or off > 82.0:
                continue                     # keep the nose sharp, skip the back
                continue
            acc = Vector((0.0, 0.0, 0.0))
            for (dr, dc) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                acc += rows[_ri + dr][(_ci + dc) % N].co
            acc /= 4.0
            v.co = v.co.lerp(acc, 0.45)

# Side quads
for ri in range(len(rows) - 1):
    for i in range(N):
        j = (i + 1) % N
        bm.faces.new((rows[ri][i], rows[ri][j], rows[ri + 1][j], rows[ri + 1][i]))

# Bottom cap (flat fan)
bz, _, _, bcy = interp_table[0]
bc = bm.verts.new((0.0, bcy, bz))
for i in range(N):
    j = (i + 1) % N
    bm.faces.new((bc, rows[0][i], rows[0][j]))

# Top cap. The loft previously stopped at the crown ring and was left open
# there; an open ring reads as a hard crest once the surface is shaded, and it
# is exactly the kind of hole that shows through a translucent skin.
tz_, _, _, tcy_ = interp_table[-1]
tc = bm.verts.new((0.0, tcy_, tz_ + 0.0004))
for i in range(N):
    j = (i + 1) % N
    bm.faces.new((tc, rows[-1][i], rows[-1][j]))

# Mirror front-to-back. This loft authors anterior as Blender +y, but Blender's
# glTF exporter maps Blender +y to glTF -z, while the viscera put anterior at +z
# (thyroid z -0.0045..+0.0370, trachea -0.0213..+0.0177, tongue +0.0219..+0.0782).
# Without this the face points backwards relative to the gland and windpipe.
# Mirroring the finished mesh flips every cross-section and every radial feature
# in one provable step, rather than flipping axis signs feature by feature.
# Mirroring inverts the winding, so the faces must be reversed to keep the
# surface facing outward.
for _v in bm.verts:
    _v.co.y = -_v.co.y
bmesh.ops.reverse_faces(bm, faces=bm.faces)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# Convert to mesh and create object
mesh_data = bpy.data.meshes.new("patient__bust_mesh")
bm.to_mesh(mesh_data)
bm.free()

bust_obj = bpy.data.objects.new("patient__bust", mesh_data)
bpy.context.scene.collection.objects.link(bust_obj)

# Select and activate
bpy.ops.object.select_all(action='DESELECT')
bust_obj.select_set(True)
bpy.context.view_layer.objects.active = bust_obj

# Clear custom split normals (edit mode required)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
try:
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
except Exception:
    pass
bpy.ops.object.mode_set(mode='OBJECT')

# NO Subdivision Surface. The loft is already dense - dz is 3 mm, so about 150 rows
# by 256 samples - and Catmull-Clark pulls the surface INSIDE the control cage
# wherever curvature is high. At the crown, where the radius drops 15 mm per row,
# it shrank unevenly (measured: 27.8 mm on the mesh where the table says 60.8) and
# that is what rendered as a stepped lid with a flange. Shading smooth is enough
# for a surface this dense; the density is bought back by decimating less.

# Shade smooth AFTER the subdivision is applied, otherwise the faces the
# modifier creates keep flat normals and the surface shows banding.
bpy.ops.object.shade_smooth()

# Decimate: the bust is inlined into the page as base64, so its size is page
# weight. Subdivision alone gave 113k triangles (a 3.3 MB GLB, 4.4 MB inlined);
# collapsing to a quarter keeps the silhouette smooth at ~28k while roughly
# halving nothing else that matters.
dec = bust_obj.modifiers.new(name="Dec", type='DECIMATE')
dec.decimate_type = 'COLLAPSE'
dec.ratio = float(os.environ.get("BUST_DECIMATE", "0.50"))
bpy.context.view_layer.objects.active = bust_obj
bpy.ops.object.modifier_apply(modifier=dec.name)

# Material
mat = bpy.data.materials.new(name="patient")
mat.use_nodes = True
mesh_data.materials.clear()
mesh_data.materials.append(mat)

# === 5b. Hair cap ==========================================================
# A second surface over the same head profile, offset outward by the spec's
# thickness so it always sits ON the skull rather than inside it, with a rim
# that sweeps from the nape up to the hairline. The grid is parametrised by
# (theta, u) rather than by fixed z rows: for each angle the rim is at
# zlow(theta) and the cap runs from there to the crown, so the lower edge can
# follow the hairline without any row ever crossing another.
if HAIR_SPEC and HAIR_SPEC.get("front_lower_z") is not None:
    _th = float(HAIR_SPEC.get("thickness_m", 0.005))
    _zf = float(HAIR_SPEC["front_lower_z"])
    _zb = float(HAIR_SPEC["back_lower_z"])
    _zs = float(HAIR_SPEC.get("side_lower_z", (_zf + _zb) * 0.5))
    # The cap follows the SKULL's own cross-sections offset by the thickness,
    # rather than the spec's own rows: those converge to a near-point at the
    # crown and produced a cone. Riding the skull profile gives a dome that
    # cannot intersect the head, because it is the head plus a constant.
    #
    # The apex must sit ABOVE the skull's own top. Deriving it from the table's
    # last row (1.688) left the skull's 4 mm top cap bare, which is why the hair
    # read as a cap perched on a bald crown. The spec gives an explicit apex.
    _zt = float(HAIR_SPEC.get("apex_z", interp_table[-1][0] + _th))

    def _bust_at(z):
        i = int(round((z - interp_table[0][0]) / dz))
        i = max(0, min(len(interp_table) - 1, i))
        return interp_table[i][1], interp_table[i][2], interp_table[i][3]

    def _rim(t):
        # THREE waypoints, not two. A single sinusoid between front and back put
        # the temples at the midpoint of the two, which is what made the rim read
        # as a swim cap. This is continuous and hits F at the front, B at the
        # back and S at both sides, so the hair can come down over the ears.
        #
        # Plus a fixed scallop: a three-point blend is still too regular to read as
        # hair - the edge is machined. 5 mm over five lobes breaks the arc the way a
        # real hairline does, without putting corrugation on the cap itself
        # (corrugating the surface is what the shoulder band taught us not to do:
        # collapse decimation turns fast ripples into terraces). 2.5 mm over six
        # lobes was tried first and was invisible at any real viewing distance.
        s = math.sin(t)
        scallop = 0.0050 * math.sin(5.0 * t + 0.7)
        return (_zs + (_zf - _zs) * max(0.0, s)
                + (_zb - _zs) * max(0.0, -s)) + scallop

    # Build the hair from the ACTUAL skull surface. A radial lookup over bins
    # was tried first and ballooned the cap: taking a max over neighbouring z
    # bins over-reads the radius wherever the profile changes quickly, and the
    # misfit gets multiplied outward. Ray-casting the built mesh is exact, needs
    # no margins, and naturally closes over the crown instead of leaving a spout
    # wherever the profile is clamped.
    def _skull_radius(origin, direction):
        """(radius, hit). Above the skull's apex the ray misses, and the caller
        must then CLOSE the cap rather than fall back to the table's clamped
        radius - that fallback is what left a 12 mm disc standing on the crown."""
        try:
            ok, loc, _nor, _idx = bust_obj.ray_cast(origin, direction)
        except Exception:
            ok = False
        if not ok:
            return 0.0, False
        return math.hypot(loc.x - origin.x, loc.y - origin.y), True

    # The table's last row (z=1.7075) becomes a flat top-cap vertex at z+0.0004,
    # so the skull's TRUE top is here -- not 4 mm above it. A closure line placed
    # above the real top left z in [1.7079, 1.7115] ray-missed: that band fell
    # back to a constant r_tab (~8.6 mm), i.e. a flat cylindrical plateau with no
    # curvature to close it, which is what stood up as the spout/nub on the crown.
    # Placing the closure exactly at the skull's top means the cap closes as one
    # smooth dome with no flat wall, so the radius falls monotonically to the pole.
    # The skull's REAL apex, measured from the built mesh - not the table's last row.
    # The table stops at z 1.701 with a 13 mm ring and the skull's own cap domes on
    # from there to about 1.7075. Taking the table's last row as "the top" made the
    # hair start closing while the skull was still 33 mm wide, so it had to fall to a
    # point over the remaining 14 mm: a 68-degree cone standing on the crown, which is
    # the bun or topknot on the head. Following the skull up to where it actually ends
    # means the closure starts from a few millimetres and is invisible.
    _z_top_skull = max(_v.co.z for _v in mesh_data.vertices)
    CLOSE = 0.028                                   # how far the crown closes over
    _R_AT_APEX = 0.0
    def _measure_apex_r():
        a_, b_, cy_ = _bust_at(_z_top_skull - 0.004)
        rr, ok_ = _skull_radius(Vector((0.0, -cy_, _z_top_skull - 0.004)),
                                Vector((1.0, 0.0, 0.0)))
        return (rr + _th) if ok_ else (math.hypot(a_, b_) + _th)
    _R_AT_APEX = _measure_apex_r()
    print(f"  hair closes from radius {_R_AT_APEX*1000:.1f} mm at the skull apex")

    # NU is the number of rows from the rim to the crown. It was 22, spread over the
    # cap's whole height, which left only about ONE row inside the last 13 mm - so the
    # closure from the skull's ~33 mm crown to the cap's top ring happened in a single
    # band and rendered as a ledge with a topknot on it. The hair is not decimated, so
    # rows here are cheap: enough of them for the crown to close smoothly.
    NH, NU = 128, 64
    hbm = bmesh.new()
    hrows = []
    for iu in range(NU + 1):
        u = iu / float(NU)
        row = []
        for i in range(NH):
            t = 2.0 * math.pi * i / NH
            zlow = _rim(t)
            z = zlow + (_zt - zlow) * u
            a, b, cy = _bust_at(z)
            r_tab = math.hypot((a + _th) * math.cos(t), (b + _th) * math.sin(t))
            # The hair is being built in the PRE-mirror frame, but bust_obj's
            # mesh is POST-mirror (y negated). Casting with unmirrored origins
            # and directions therefore sampled the FRONT of the head whenever it
            # meant to measure the back, and the cap ballooned wherever the two
            # silhouettes differ. Mirror the ray into the mesh's own frame; the
            # radial distance is unchanged by the mirror.
            org = Vector((0.0, -cy, z))
            d = Vector((math.cos(t), -math.sin(t), 0.0)).normalized()
            r_hit, hit = _skull_radius(org, d)
            # Close the crown as an ellipsoid centred on the skull's apex. Where
            # the skull is present the cap may never sit below skull + thickness;
            # above the apex there is nothing to cover, so it simply closes. The
            # old fallback to the table's clamped radius is what left a 12 mm disc
            # standing on the crown as a tuft.
            # BELOW the skull's apex the cap is simply skull + thickness, and may
            # never sink inside the skull. ABOVE it there is nothing to cover, so
            # the cap closes as an ellipsoid. Clamping the ellipsoid on both sides
            # of the apex was the previous mistake: outside the band the factor
            # collapsed to zero and the hair vanished to a small cap.
            if z <= _z_top_skull:
                r = ((r_hit + _th) if hit else r_tab)
            else:
                # Close over the height the cap actually has above the skull (~13.6 mm),
                # not over a fixed 28 mm. With a fixed span the radius only fell to
                # ~29 mm by the cap's top row, so the closing fan flattened a 29 mm
                # ring into a lid with a pinched centre - the nub that every reviewer
                # picked out on top of the head. Forcing the radius all the way to zero
                # is worse: the whole top row collapses into one point and the last
                # band becomes slivers that shade as a jagged crest. So close over the
                # real span but STOP ON A SMALL RING (~13 mm) and let the apex fan
                # close that, which is exactly how the skull's own crown cap is built
                # and it shades smoothly.
                _span = max(1e-6, _zt - _z_top_skull)
                _f = min(1.0, (z - _z_top_skull) / _span)
                _apex_r = (_R_AT_APEX if _R_AT_APEX > 0 else r_tab)
                r = _apex_r * math.sqrt(max(0.0, 1.0 - _f * _f))
            row.append(hbm.verts.new((r * math.cos(t), cy + r * math.sin(t), z)))
        hrows.append(row)
    for ri in range(len(hrows) - 1):
        for i in range(NH):
            j = (i + 1) % NH
            hbm.faces.new((hrows[ri][i], hrows[ri][j], hrows[ri + 1][j], hrows[ri + 1][i]))
    _ca, _cb, _ccy = _bust_at(_zt)
    # Put the apex vertex ABOVE the cap's last ring, not level with it. Level, the
    # closing fan is a flat 13 mm disc whose faces alternate light and dark under
    # shading and read as a zipper or a crest on the crown - which is the "spike on
    # the head" every reviewer picked out. The skull's own crown cap is smooth for
    # exactly this reason: its apex sits about 6 mm above its last ring, so the fan
    # is a shallow dome rather than a flat plate.
    hc = hbm.verts.new((0.0, _ccy, _zt))
    for i in range(NH):
        j = (i + 1) % NH
        hbm.faces.new((hc, hrows[-1][i], hrows[-1][j]))
    # same front-to-back mirror as the bust, so the two stay registered
    for _v in hbm.verts:
        _v.co.y = -_v.co.y
    bmesh.ops.reverse_faces(hbm, faces=hbm.faces)
    bmesh.ops.recalc_face_normals(hbm, faces=hbm.faces)

    hair_mesh = bpy.data.meshes.new("hair__cap_mesh")
    hbm.to_mesh(hair_mesh)
    hbm.free()
    hair_obj = bpy.data.objects.new("hair__cap", hair_mesh)
    bpy.context.scene.collection.objects.link(hair_obj)
    _hm = bpy.data.materials.new(name="hair")
    _hm.use_nodes = True
    hair_mesh.materials.append(_hm)
    print(f"Hair: {sum(len(p.vertices) - 2 for p in hair_mesh.polygons)} triangles, "
          f"z [{min(v.co.z for v in hair_mesh.vertices):.3f}, "
          f"{max(v.co.z for v in hair_mesh.vertices):.3f}]")

# === 5c. Eyes, irises and eyebrows ========================================
# Separate objects, because a radial bump on the loft cannot make an eye. What
# makes a face read as a face is eyes and eyebrows, and both need discrete
# geometry rather than a displacement of the skin.
#
# Everything here is built in the POST-MIRROR frame, i.e. the same frame as the
# finished bust mesh, where anterior is -y. The spec's numbers are written in the
# pre-mirror frame with anterior +y, so y is negated on the way in. Getting this
# the wrong way round would put the eyes in the back of the head.
def _blob(name, centre, half, rot_ant_deg=0.0, segs=26, rings=18):
    """A squashed sphere: half-extents (x, y, z) in metres, rotated about the
    anterior axis so a brow can tilt its outer end up."""
    b = bmesh.new()
    try:
        bmesh.ops.create_uvsphere(b, u_segments=segs, v_segments=rings, radius=1.0)
    except TypeError:                       # older signatures used `diameter`
        bmesh.ops.create_uvsphere(b, u_segments=segs, v_segments=rings, diameter=1.0)
    ca, sa = math.cos(math.radians(rot_ant_deg)), math.sin(math.radians(rot_ant_deg))
    for v in b.verts:
        x = v.co.x * half[0]
        y = v.co.y * half[1]
        z = v.co.z * half[2]
        xr = x * ca - z * sa                # rotate in the x-z plane
        zr = x * sa + z * ca
        v.co = Vector((xr + centre[0], y + centre[1], zr + centre[2]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    me = bpy.data.meshes.new(name + "_mesh")
    b.to_mesh(me)
    b.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mt = bpy.data.materials.new(name + "_mat")
    mt.use_nodes = True
    me.materials.append(mt)
    return ob


def _skin_anterior(x_target, z_target, tol=0.006):
    """The bust's front surface at an (x, z), in the post-mirror frame where
    anterior is -y, so the surface is the MINIMUM y there.

    The window is deliberately tight (6 mm). At 14 mm it also spanned the brow
    ridge and the nose bridge, so a shape placed "against the surface actually
    built" was measured against a point 5-6 mm in FRONT of its own location - which
    is what had the iris disc floating clear of the eyeball instead of lying on it,
    and it misplaces the lips and nostrils by the same amount. If the decimated
    mesh leaves the window empty, widen once rather than return None and drop the
    shape somewhere arbitrary."""
    ys = [v.co.y for v in mesh_data.vertices
          if abs(v.co.x - x_target) < tol and abs(v.co.z - z_target) < tol]
    if not ys:
        ys = [v.co.y for v in mesh_data.vertices
              if abs(v.co.x - x_target) < 0.014 and abs(v.co.z - z_target) < 0.014]
    return min(ys) if ys else None


def _skin_sym(x_target, z_target):
    """The mean of the surface at +x and -x, i.e. the value BOTH sides of a mirrored
    pair should be placed against.

    The mesh is decimated, and decimation is not left-right symmetric: sampling one
    side alone put the two eyes, the two brows and the two irises at different
    depths, so the face came out lopsided - the mouth sat off the midline and the
    two eyes did not match. Averaging makes every mirrored pair land identically,
    which is what the geometry's own symmetry says it should be."""
    a = _skin_anterior(x_target, z_target)
    if not x_target:
        return a
    b = _skin_anterior(-x_target, z_target)
    if a is None:
        return b
    if b is None:
        return a
    return 0.5 * (a + b)


for _e in EYES:
    _cx, _cy, _cz = _e["centre"]
    _R = float(_e["ball_radius_m"])
    _side = _e.get("side", "x")
    _blob(f"eye__ball_{_side}", (_cx, -_cy, _cz), (_R, _R, _R))
    # The iris sits just proud of the sclera so the two cannot z-fight, and is
    # flattened against the ball so it reads as a disc rather than a bump.
    # Only build the iris disc when the spec actually asks for an iris
    # (iris_radius_m > 0). Here the irises are authored separately in
    # surface_shapes as iris__l/iris__r, so a disc here would duplicate them.
    _ir = float(_e.get("iris_radius_m", 0.0))
    if _ir > 0:
        _fwd = float(_e.get("iris_forward_m", _R * 0.96))
        _blob(f"iris__disc_{_side}", (_cx, -(_cy + _fwd + 0.0004), _cz),
              (_ir, _R * 0.20, _ir))
        print(f"eye {_side}: ball at y {-_cy:.3f}, iris at y {-(_cy + _fwd + 0.0004):.3f}")
    else:
        print(f"eye {_side}: sclera ball at y {-_cy:.3f} (no iris disc)")

for _sh in SHAPES:
    _nm = _sh["name"]; _sx = float(_sh.get("x", 0.0)); _sz = float(_sh["z"])
    _hx, _hy, _hz = [float(v) for v in _sh["half"]]
    _pr = float(_sh.get("prot", 0.002))
    # Sample the surface on the SAME side as the shape, through the symmetric
    # sampler: the decimated mesh is not left-right symmetric, so one-sided sampling
    # put mirrored pairs (the two irises) at different depths and lopsided the face.
    _S = _skin_sym(_sx, _sz)
    _y = ((_S - _pr + _hy) if _S is not None else -0.085)
    _blob(_nm, (_sx, _y, _sz), (_hx, _hy, _hz), segs=30, rings=20)
    print(f"shape {_nm}: surface y {_S if _S is None else round(_S,4)}, centre y {_y:.4f}, "
          f"protrudes {(0 if _S is None else (_S - (_y - _hy)) * 1000):.1f} mm")

for _b in BROWS:
    _cx, _cy, _cz = _b["centre"]
    _hl = float(_b["half_length_m"])
    _th = float(_b["thickness_m"])
    _tl = float(_b.get("tilt_deg", 0.0))
    _side = _b.get("side", "x")
    # Place the brow against the surface the features ACTUALLY produced, not the
    # spec's pre-ridge figure. The spec's own +5 mm supraorbital ridge pushes the
    # skin out further than the brow's 90 mm front extent, so taking the spec's
    # centre at face value buries the eyebrow inside the head.
    _S = _skin_sym(_cx, _cz)
    _y = (_S + 0.0005) if _S is not None else -_cy
    _blob(f"brow__{_side}", (_cx, _y, _cz), (_hl, 0.0020, _th * 0.5),
          rot_ant_deg=(_tl if _side != "r" else -_tl))
    print(f"brow {_side}: surface y {_S:.4f}, brow centre y {_y:.4f}, "
          f"front-most {(_y - 0.0035):.4f} "
          f"({((_S - (_y - 0.0020)) * 1000 if _S is not None else 0):.1f} mm proud)")

# === 6. Diagnostics ===
tri_count = sum(len(p.vertices) - 2 for p in mesh_data.polygons)
print(f"Triangle count: {tri_count}")

# Bounding box in cm
xs, ys, zs = [], [], []
for v in mesh_data.vertices:
    xs.append(v.co.x)
    ys.append(v.co.y)
    zs.append(v.co.z)
print(f"Bust bbox (cm): x [{min(xs)*100:.2f}, {max(xs)*100:.2f}]  "
      f"y [{min(ys)*100:.2f}, {max(ys)*100:.2f}]  "
      f"z [{min(zs)*100:.2f}, {max(zs)*100:.2f}]")

# Entry point distance. NOTE the y sign: the entry point is anterior, and after
# the mirror above anterior is Blender -y (the exporter turns it back into glTF
# +z), so the probe point is (-0.0462, -0.049, 1.4216) here.
ep = Vector((-0.0462, -0.049, 1.4216))
min_d = float('inf')
for v in mesh_data.vertices:
    d = (v.co - ep).length
    if d < min_d:
        min_d = d
print(f"Entry point distance: {min_d * 1000.0:.3f} mm")

# Orientation check: at the jaw the chin must reach further anterior than the
# skull reaches posterior. Anterior is Blender -y after the mirror.
band = [v.co for v in mesh_data.vertices if 1.478 <= v.co.z <= 1.512]
if band:
    _ant = max(-p.y for p in band)
    _post = max(p.y for p in band)
    print(f"Jaw band (Blender y): anterior reach {_ant*1000:.1f} mm, "
          f"posterior reach {_post*1000:.1f} mm -> "
          f"chin points {'FORWARD (correct)' if _ant > _post else 'BACKWARD (still mirrored)'}")

# Object list
obj_names = [o.name for o in bpy.data.objects]
print(f"Objects in scene: {obj_names}")

# === 7. Export ===
# Drop the department's own body meshes before exporting. They are the supine
# anatomy the authored bust was built to replace: the page already hides all three
# by name (`src/app_scene.js`, "the authored bust takes their place"), and nothing
# else - not the viewer page, not the build - refers to them. They were 21,696
# triangles, 22% of everything the file carried, for geometry that could never be
# drawn. Removing them here rather than in the page keeps the page's hide list as a
# no-op and takes the bytes out of the download as well as the draw call.
for _dead in ("patient__head", "patient__neck", "patient__shoulders"):
    _o = bpy.data.objects.get(_dead)
    if _o is not None:
        _t = len(_o.data.polygons) if _o.type == 'MESH' else 0
        bpy.data.objects.remove(_o, do_unlink=True)
        print(f"removed superseded mesh {_dead} ({_t} faces)")

export_path = "/Users/alexyap/My Drive/20_Projects/Radiology/01-Active/FNAC Webapp/model/fnac_scene_v10.glb"
bpy.ops.export_scene.gltf(filepath=export_path, export_format='GLB')
print(f"Exported to: {export_path}")
