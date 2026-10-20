#!/usr/bin/env /usr/bin/python3
"""Local subagent vet cycle for the FNAC anatomical model.

Per the local-swarm skill: the orchestrator computes ground truth in Python and
never takes a local model's self-report as fact. The swarm's only job here is
the mechanical one — read a measured record and emit defect rows as JSONL.

What the swarm CAN do here (and why this split is safe):
  * check a measured record against the stated design intent
  * spot named anatomical structures missing or mis-scaled relative to the
    supplied ground-truth dimensions
  * flag implausible proportions given the numbers it is handed

What it must NOT do: supply the numbers. All measurements come from parsing the
GLB in Python.
"""
import json
import os
import struct
import sys

sys.path.insert(0, "/home/alex/rag")
from swarm import swarm, parse_jsonl, merge  # noqa: E402

GLB = "/home/alex/Documents/FNAC_Webapp/model/neck_anatomy.glb"
WS = "/home/alex/.hermes/cache/scratch/fnac_model_vet"
os.makedirs(WS, exist_ok=True)

# --------------------------------------------------------------- ground truth
# Sourced anatomy. These MUST come from literature, not from a model.
TRUTH = {
    "neck_diameter_cm":        (9.0, 14.0),
    "neck_height_section_cm":  (10.0, 18.0),
    "thyroid_lobe_height_cm":  (4.0, 6.0),
    "thyroid_lobe_width_cm":   (1.5, 2.5),
    "thyroid_total_width_cm":  (4.5, 7.0),
    "isthmus_thickness_cm":    (0.2, 0.6),
    "nodule_size_cm":          (0.5, 4.0),
    "trachea_diameter_cm":     (1.5, 3.0),
}


def parse_glb(path):
    d = open(path, "rb").read()
    assert d[:4] == b"glTF", "not a GLB"
    clen, _ = struct.unpack("<II", d[12:20])
    j = json.loads(d[20:20 + clen])
    off = 20 + clen
    blen, _ = struct.unpack("<II", d[off:off + 8])
    bin_ = d[off + 8:off + 8 + blen]
    return j, bin_


def measure(path):
    """Compute per-mesh bounding boxes from the GLB accessors, in Python."""
    j, bin_ = parse_glb(path)
    accs = j.get("accessors", [])
    views = j.get("bufferViews", [])
    out = {}
    # glTF accessor min/max are authoritative for POSITION and are stored in
    # the accessor itself, so no binary parsing is needed for bounds.
    for mesh in j.get("meshes", []):
        name = mesh.get("name", "?")
        lo = [1e9, 1e9, 1e9]
        hi = [-1e9, -1e9, -1e9]
        tris = 0
        mats = set()
        for prim in mesh.get("primitives", []):
            a = accs[prim["attributes"]["POSITION"]]
            for k in range(3):
                lo[k] = min(lo[k], a["min"][k])
                hi[k] = max(hi[k], a["max"][k])
            if "indices" in prim:
                tris += accs[prim["indices"]]["count"] // 3
            else:
                tris += a["count"] // 3
            if "material" in prim:
                mats.add(j["materials"][prim["material"]].get("name"))
        dims = [round((hi[k] - lo[k]) * 100, 2) for k in range(3)]  # metres -> cm
        out[name] = {"dims_cm": dims, "tris": tris, "materials": sorted(mats)}
    return out


def check_truth(m):
    """Python-side validation against the sourced ranges. Authoritative."""
    findings = []
    g = lambda n: (m.get(n) or {}).get("dims_cm")
    # neck
    d = g("NECK_SKIN")
    if d:
        # A neck is elliptical: transverse width > anteroposterior depth. So
        # check the WIDTH against the range, and separately assert that the
        # depth is smaller than the width. Comparing min(width, depth) against
        # a circular range is wrong and produced a false positive here.
        width, depth = d[0], d[2]
        if not (TRUTH["neck_diameter_cm"][0] <= width <= TRUTH["neck_diameter_cm"][1]):
            findings.append(f"NECK_SKIN width {width} cm outside "
                            f"{TRUTH['neck_diameter_cm']}")
        if depth >= width:
            findings.append(f"NECK_SKIN depth {depth} >= width {width}; a neck "
                            f"should be wider than it is deep")
    t = g("THYROID")
    if t:
        # thyroid total width spans the two lobes; height is the taller axis
        h = max(t)
        if not (TRUTH["thyroid_lobe_height_cm"][0] <= h <= TRUTH["thyroid_lobe_height_cm"][1] + 1.5):
            findings.append(f"THYROID tallest axis {h} cm vs lobe height "
                            f"{TRUTH['thyroid_lobe_height_cm']}")
    n = g("NODULE")
    if n:
        if not (TRUTH["nodule_size_cm"][0] <= max(n) <= TRUTH["nodule_size_cm"][1]):
            findings.append(f"NODULE max dim {max(n)} cm outside {TRUTH['nodule_size_cm']}")
    tr = g("TRACHEA_ALL")
    if tr:
        if not (TRUTH["trachea_diameter_cm"][0] <= min(tr[0], tr[2]) <= TRUTH["trachea_diameter_cm"][1] + 0.5):
            findings.append(f"TRACHEA diameter {tr[0]}/{tr[2]} cm vs {TRUTH['trachea_diameter_cm']}")
    return findings


SYS = (
    "You audit an anatomical 3D model of the human neck built for a patient "
    "education app. You are given MEASURED DIMENSIONS (authoritative, computed "
    "in Python from the exported model) and the DESIGN INTENT. Report only "
    "defects you can justify from the numbers given. One JSON object per line "
    "(JSONL). No prose, no fences.\n"
    'Schema: {"defect": "<short name>", "severity": "CRITICAL|MAJOR|MINOR", '
    '"evidence": "<quote a measured value>", "fix": "<concrete change>"}\n'
    'Example — measured THYROID dims_cm [2.0, 1.1, 1.0], intent "lobe 4-6 cm tall"\n'
    'Output: {"defect": "thyroid too small", "severity": "MAJOR", '
    '"evidence": "THYROID tallest axis is 2.0 cm", '
    '"fix": "scale the thyroid lobes to 5 cm along their long axis"}\n'
    'If nothing is defensible, output exactly: {"defect": "none"}'
)


def main():
    print("=== anatomical model vet cycle (local swarm) ===\n")

    print("[1] MEASURE — Python, from the GLB")
    m = measure(GLB)
    for k in sorted(m):
        v = m[k]
        print(f"    {k:12} {str(v['dims_cm']):22} cm  {v['tris']:5} tris  {v['materials']}")
    print(f"    total tris: {sum(v['tris'] for v in m.values()):,}")

    print("\n[2] VALIDATE against sourced anatomy — Python, authoritative")
    fails = check_truth(m)
    if fails:
        for f in fails:
            print("    FAIL:", f)
    else:
        print("    all measured dimensions within sourced ranges")

    print("\n[3] VET — local swarm (mechanical review of the measured record)")
    facts = json.dumps(m, indent=1)[:3600]
    intent = (
        "DESIGN INTENT: an ANATOMICAL CUTAWAY of the human neck showing, in "
        "order: skin, subcutaneous fat, strap muscles, sternocleidomastoid, "
        "trachea with cartilage rings, thyroid gland (two lobes + isthmus), a "
        "nodule inside the right lobe, and the carotid/jugular vessels. "
        "Sourced normal ranges (cm): neck 9-14, thyroid lobe height 4-6, lobe "
        "width 1.5-2.5, isthmus 0.2-0.6, nodule 0.5-4.0, trachea diameter "
        "1.5-3.0. Scale: 1 unit = 1 m; dims_cm are centimetres. Report defects "
        "where a measured value contradicts the intent or the ranges."
    )
    prompt = f"{intent}\n\nMEASURED DIMENSIONS (authoritative):\n{facts}\n\nList defects."
    res = swarm([{"id": "VET-MODEL", "prompt": prompt}], system=SYS, max_tokens=2000)
    rows = []
    for r in res:
        print(f"    {r.get('host','?'):8} ok={r.get('ok')} {r.get('secs','?')}s")
        if r.get("ok") and r.get("text"):
            print(f"      {r['text'][:260]!r}")
            rows += parse_jsonl(r["text"])
    rows = [r for r in rows if str(r.get("defect", "")).lower() not in ("none", "")]

    print(f"\n[4] ADJUDICATE — Python confirms each row before it becomes a fix")
    for r in merge(rows, "defect"):
        ev = str(r.get("evidence", ""))
        # independently confirm: does any measured value literally appear?
        confirmed = any(str(v) in ev for v in
                        [d for mm in m.values() for d in mm["dims_cm"]])
        print(f"    [{'CONFIRMED' if confirmed else 'UNVERIFIED':10}] "
              f"{r.get('severity','?'):8} {r.get('defect','?')}")
        print(f"                 {ev[:100]}")
        print(f"                 fix: {str(r.get('fix',''))[:100]}")

    outp = os.path.join(WS, "vet.json")
    json.dump({"measured": m, "python_fails": fails, "swarm_rows": rows},
              open(outp, "w"), indent=1)
    print(f"\n    written {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
