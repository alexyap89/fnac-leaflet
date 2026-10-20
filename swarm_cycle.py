#!/usr/bin/env /usr/bin/python3
"""Local subagent BUILD/DEBUG swarm for the FNAC 2D SVG animation.

Division of labour — per the local-swarm skill, and deliberately shaped so the
fleet is never the source of truth:

  ORCHESTRATOR (this script, Python)          FLEET (local models)
  ---------------------------------------     ------------------------------
  computes all geometry numerically           reviews structured records
  validates every change measurably           proposes concrete fixes as JSONL
  renders / rasterises / counts pixels        spots inconsistencies in text
  adjudicates: a suggestion only lands         reports defects as rows
      if a Python check confirms it

The fleet CANNOT do arithmetic or geometry reliably, and must never be trusted
for a numeric claim (measured repeatedly). So every number it sees is computed
here first, and every fix it proposes is re-verified here before being applied.

Hosts are SPREAD, never fanned out to one node (the fleet serialises).
"""
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, "/home/alex/rag")
from swarm import swarm, parse_jsonl, merge  # noqa: E402

BASE = "/home/alex/Documents/FNAC_Webapp"
WS = "/home/alex/.hermes/cache/scratch/svg_swarm"
os.makedirs(WS, exist_ok=True)
SVG = os.path.join(BASE, "anim.svg")


# =========================================================================== #
# Python-side ground truth. The fleet never supplies any of this.
# =========================================================================== #
def svg_facts(path):
    """Parse the SVG and compute deterministic facts about it."""
    if not os.path.exists(path):
        return {"exists": False}
    s = open(path).read()
    f = {"exists": True, "bytes": len(s)}
    f["paths"] = len(re.findall(r"<path\b", s))
    f["circles"] = len(re.findall(r"<circle\b", s))
    f["ellipses"] = len(re.findall(r"<ellipse\b", s))
    f["rects"] = len(re.findall(r"<rect\b", s))
    f["texts"] = len(re.findall(r"<text\b", s))
    f["groups"] = len(re.findall(r"<g\b", s))
    f["ids"] = re.findall(r'\bid="([^"]+)"', s)
    f["viewBox"] = (re.search(r'viewBox="([^"]+)"', s) or [None, None])[1]
    f["has_script"] = "<script" in s
    f["external_refs"] = re.findall(r'(?:href|src)="(?!#)([^"]+)"', s)
    # geometry: the nodule and the needle tip must coincide at the target step
    f["animate_elems"] = len(re.findall(r"<animate\b|<animateTransform\b", s))
    return f


def svg_geometry(path):
    """Extract the coordinates of the key elements, in Python, from the source.

    These are the values the animation must satisfy. Kept as literals in the
    generator so this function can verify the RENDERED file, not the intent.
    """
    s = open(path).read() if os.path.exists(path) else ""
    g = {}
    for key in ("nodule-centre", "probe-face", "needle-tip", "skin-entry", "target"):
        m = re.search(rf'id="{key}"[^>]*data-x="([-\d.]+)"[^>]*data-y="([-\d.]+)"', s)
        if not m:
            m = re.search(rf'data-x="([-\d.]+)"[^>]*data-y="([-\d.]+)"[^>]*id="{key}"', s)
        if m:
            g[key] = (float(m.group(1)), float(m.group(2)))
    return g


def check_invariants(facts, geom):
    """The checks that must hold. Python decides pass/fail, never the fleet."""
    fails = []
    if not facts.get("exists"):
        return ["SVG does not exist"]
    if facts.get("external_refs"):
        fails.append(f"external references present (must be self-contained): "
                     f"{facts['external_refs'][:4]}")
    if facts.get("has_script"):
        fails.append("inline <script> present (animation must be SMIL/CSS only "
                     "so it works with scripting disabled)")
    if not facts.get("viewBox"):
        fails.append("no viewBox (will not scale)")
    # Strict XML parse. Browsers are lenient about undeclared namespace
    # prefixes, but a strict consumer rejects the file outright — measured: an
    # undeclared xlink: prefix made the whole SVG unparseable.
    try:
        import xml.etree.ElementTree as ET
        ET.parse(path)
    except Exception as e:
        fails.append(f"not well-formed XML: {e}")
    for need in ("nodule-centre", "probe-face", "needle-tip"):
        if need not in geom:
            fails.append(f"geometry anchor missing: {need}")
    if "needle-tip" in geom and "nodule-centre" in geom:
        nx, ny = geom["needle-tip"]
        cx, cy = geom["nodule-centre"]
        d = ((nx - cx) ** 2 + (ny - cy) ** 2) ** 0.5
        if d > 2.0:
            fails.append(f"needle tip is {d:.1f} units from the nodule centre "
                         f"at the target step (must coincide)")

    # --- trajectory checks -------------------------------------------------
    # INTENT: the needle enters BESIDE the probe, crosses UNDER the probe face,
    # and the probe face rests on the skin ABOVE the nodule.
    if all(k in geom for k in ("skin-entry", "probe-face", "nodule-centre")):
        ex, ey = geom["skin-entry"]
        px, py = geom["probe-face"]
        cx, cy = geom["nodule-centre"]
        # 1. the probe face must sit above (smaller y) and near the nodule in x
        if abs(px - cx) > 40:
            fails.append(f"probe face x={px} is {abs(px-cx):.0f} units from the "
                         f"nodule x={cx}; the probe must rest over the lesion")
        if py >= cy:
            fails.append(f"probe face y={py} is not above the nodule y={cy}; "
                         f"the probe must rest on the skin")
        # 2. the entry point must be lateral to the probe (to the left, since
        #    the patient faces left) so the needle crosses underneath it
        if ex >= px:
            fails.append(f"skin entry x={ex} is not lateral to the probe face "
                         f"x={px}; the needle must enter beside the probe")
        # 3. the trajectory angle must be roughly 45 degrees
        import math
        ang = math.degrees(math.atan2(abs(cy - ey), abs(cx - ex)))
        if not (30 <= ang <= 60):
            fails.append(f"needle trajectory is {ang:.0f} degrees from horizontal "
                         f"at the skin; intent is about 45")
    else:
        for need in ("skin-entry", "probe-face", "nodule-centre"):
            if need not in geom:
                fails.append(f"trajectory anchor missing: {need}")
    return fails


# =========================================================================== #
# Prompt builders. The fleet gets FACTS, never questions about itself.
# =========================================================================== #
SYS_SVG = (
    "You review a 2D SVG medical animation for a patient-education app about "
    "thyroid fine needle aspiration (FNAC). You are given MEASURED FACTS about "
    "the file and the DESIGN INTENT. Report only defects you can justify from "
    "the facts given. One JSON object per line (JSONL). No prose, no fences.\n"
    'Schema: {"defect": "<short name>", "severity": "CRITICAL|MAJOR|MINOR", '
    '"evidence": "<quote a measured value>", "fix": "<concrete change>"}\n'
    'Example — facts: {"texts": 0}, intent: "every structure is labelled"\n'
    'Output: {"defect": "no labels", "severity": "MAJOR", '
    '"evidence": "texts is 0", "fix": "add <text> labels for each structure"}\n'
    'If nothing is defensible, output exactly: {"defect": "none"}'
)

INTENT = """
DESIGN INTENT — a patient-education animation of ultrasound-guided thyroid FNAC.
Style reference: a flat vector medical illustration (black outlines, muted
clinical palette, profile cutaway view of the head and neck with the thyroid
visible behind transparent skin).

REQUIRED VISUAL ELEMENTS:
  * profile head + neck, neck extended, eyes closed
  * a transparent cutaway so the thyroid gland is visible in situ
  * thyroid: two lobes, brownish-red
  * nodule: a distinct darker mass INSIDE the thyroid
  * ultrasound probe: angled on the anterior neck, face touching the skin
  * blue ultrasound wave arcs radiating from the probe face
  * needle + syringe: entering BESIDE the probe, at roughly 45 degrees,
    crossing UNDER the probe, tip reaching the nodule
  * dressing at the end
  * labels naming: ultrasound probe, needle, nodule, thyroid

REQUIRED STEPS (in order): position -> thyroid revealed -> nodule shown ->
surface -> probe localises -> needle in -> 3 passes -> needle out -> dressing.

ACCESSIBILITY: must work with scripting disabled; must not rely on colour alone;
must carry a text alternative.
"""


def fleet_review(section, facts, tag):
    f = json.dumps(facts, indent=1)[:3600]
    prompt = (f"{section}\n\nMEASURED FACTS (authoritative, computed in Python):\n"
              f"{f}\n\nList the defects.")
    res = swarm([{"id": f"SVG-{tag}", "prompt": prompt}], system=SYS_SVG,
                max_tokens=2000)
    rows, notes = [], []
    for r in res:
        notes.append({"host": r.get("host"), "ok": r.get("ok"),
                      "secs": r.get("secs"), "chars": len(r.get("text") or "")})
        if r.get("ok") and r.get("text"):
            rows += parse_jsonl(r["text"])
    rows = [r for r in rows if str(r.get("defect", "")).lower() not in ("none", "")]
    return rows, notes


def adjudicate(rows, facts, geom):
    """A row only survives if Python can independently confirm its claim."""
    out = []
    for r in rows:
        d = str(r.get("defect", "")).lower()
        ev = str(r.get("evidence", ""))
        ok, why = None, ""
        if "label" in d or "text" in d:
            n = facts.get("texts", 0)
            ok = n < 4
            why = f"texts={n}, need >=4 labels"
        elif "external" in d or "self-contain" in d:
            ok = bool(facts.get("external_refs"))
            why = f"external_refs={facts.get('external_refs')}"
        elif "script" in d:
            ok = bool(facts.get("has_script"))
            why = f"has_script={facts.get('has_script')}"
        elif "viewbox" in d or "scal" in d:
            ok = not facts.get("viewBox")
            why = f"viewBox={facts.get('viewBox')}"
        elif "needle" in d and ("nodule" in d or "target" in d):
            if "needle-tip" in geom and "nodule-centre" in geom:
                nx, ny = geom["needle-tip"]; cx, cy = geom["nodule-centre"]
                dist = ((nx - cx) ** 2 + (ny - cy) ** 2) ** 0.5
                ok = dist > 2.0
                why = f"tip-to-nodule distance {dist:.1f}"
            else:
                ok, why = None, "anchor missing, cannot confirm"
        else:
            ok, why = None, "not independently verifiable from the parsed facts"
        out.append({**r, "confirmed": ok, "why": why})
    return out


def build():
    """Run the generator, then report the fresh facts."""
    r = subprocess.run(["/usr/bin/python3", os.path.join(BASE, "build_anim.py")],
                       capture_output=True, text=True, timeout=300)
    return {"rc": r.returncode, "out": r.stdout[-1500:], "err": r.stderr[-800:]}


def main():
    tag = time.strftime("%H%M%S")
    print(f"=== FNAC SVG local build/debug cycle [{tag}] ===\n")

    print("[0] BUILD — orchestrator runs the generator")
    b = build()
    print(f"    rc={b['rc']}")
    for line in (b["out"] or "").splitlines()[-8:]:
        print("    " + line)

    print("\n[1] MEASURE — Python parses the produced SVG")
    facts = svg_facts(SVG)
    geom = svg_geometry(SVG)
    print("    " + json.dumps(facts)[:400])
    print("    geometry: " + json.dumps(geom))

    print("\n[2] PYTHON INVARIANTS — authoritative pass/fail")
    fails = check_invariants(facts, geom)
    print("    " + ("all invariants hold" if not fails else ""))
    for f in fails:
        print("    FAIL:", f)

    print("\n[3] FLEET REVIEW — mechanical defect proposals (spread across nodes)")
    rows, notes = fleet_review(INTENT, {**facts, "geometry": geom}, tag)
    for n in notes:
        print(f"    host={n['host']:8} ok={n['ok']} {n['secs']}s {n['chars']} chars")
    for r in rows[:8]:
        print(f"      - [{r.get('severity','?')}] {str(r.get('defect'))[:70]}")

    print("\n[4] ADJUDICATE — Python confirms each row before it can become a fix")
    for r in adjudicate(rows, facts, geom):
        mark = {True: "CONFIRMED", False: "REFUTED", None: "UNVERIFIED"}[r["confirmed"]]
        print(f"    [{mark:10}] {r.get('severity','?'):8} {str(r.get('defect'))[:60]}")
        print(f"                 {r['why']}")

    out = os.path.join(WS, f"cycle_{tag}.json")
    json.dump({"build": b, "facts": facts, "geom": geom, "invariant_fails": fails,
               "fleet_rows": rows, "adjudicated": adjudicate(rows, facts, geom)},
              open(out, "w"), indent=1)
    print(f"\n    written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
