#!/usr/bin/env /usr/bin/python3
"""Local subagent build/debug cycle for the FNAC 3D webapp.

Cycle shape (per local-swarm skill rules):
    BUILD  -> RENDER -> VET (local swarm, spread across nodes) -> FIX -> repeat

Why the split is this way:
  * Local models are throughput devices over supplied text, not oracles. They
    cannot do geometry maths reliably and must never be the source of truth for
    a numeric claim. So all measurement (angles, positions, pixel stats) is
    computed HERE, in Python, and handed to the swarm as facts to check against
    stated intent.
  * The swarm's job is the *mechanical* one: read a structured observation
    record and emit JSONL defect rows. One row per defect. No prose.
  * Every row is re-validated in Python before it is allowed to become a fix.

Nodes are spread, never fanned out to one host (the local-swarm hard rule).
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/home/alex/rag")
from swarm import swarm, parse_jsonl, merge  # noqa: E402

BASE = "/home/alex/Documents/FNAC_Webapp"
PAGE = f"file://{BASE}/index.html"
WS = "/home/alex/.hermes/cache/scratch/fnac_cycle"
os.makedirs(WS, exist_ok=True)


# --------------------------------------------------------------------------- #
# 1. MEASURE — deterministic ground truth, computed here, never by a model.
# --------------------------------------------------------------------------- #
PROBE_JS = r"""
(() => {
  const out = {ok:true};
  try {
    const c = document.getElementById('gl');
    const gl = c.getContext('webgl') || c.getContext('webgl2');
    const w = c.width, h = c.height;
    const px = new Uint8Array(w*h*4);
    gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,px);
    let lit=0, sum=0;
    for (let i=0;i<px.length;i+=4){
      const v = px[i]+px[i+1]+px[i+2];
      if (v>15) lit++;
      sum += v;
    }
    out.canvas = {w:w, h:h, lit_pct:+(100*lit/(w*h)).toFixed(2),
                  mean:+(sum/(w*h)).toFixed(2)};
    out.labels = Array.from(document.querySelectorAll('.scene-label'))
      .filter(e=>e.style.display!=='none').map(e=>e.textContent);
    out.steps = document.querySelectorAll('.stepchip').length;
    out.step_label = (document.getElementById('stepLabel')||{}).innerText || '';
    out.errs = window.__errs || [];
    // geometry ground truth
    if (typeof buildThreeScene === 'function' && typeof THREE !== 'undefined') {
      const t = buildThreeScene(THREE);
      const A = t.anchors;
      const d = new THREE.Vector3().subVectors(A.TIP_TARGET, A.ENTRY);
      const n = d.clone().normalize();
      out.geom = {
        entry: A.ENTRY.toArray().map(v=>+v.toFixed(3)),
        tip:   A.TIP_TARGET.toArray().map(v=>+v.toFixed(3)),
        track_len: +d.length().toFixed(3),
        angle_from_vertical_deg: +(Math.acos(Math.abs(n.y))*180/Math.PI).toFixed(1),
        angle_from_horizontal_deg: +(Math.asin(Math.abs(n.y))*180/Math.PI).toFixed(1),
        part_count: Object.keys(t.parts).length,
        has: {
          head: !!t.parts.head, neck: !!t.parts.neck, thyroid: !!t.parts.thyroid,
          nodule: !!t.parts.nodule, probe: !!t.parts.probe, needle: !!t.parts.needle,
          trachea: !!t.parts.trachea, dressing: !!t.parts.dressing
        }
      };
    } else { out.geom = null; }
  } catch(e) { out.ok=false; out.fatal = e.message; }
  return JSON.stringify(out);
})()
"""


def render_probe(step_index=None):
    """Drive a headless browser, measure the frame. Returns a dict."""
    # written as a standalone script the browser harness runs
    script = f'''
import json, time, sys
sys.path.insert(0, "/home/alex/.hermes/cache/scratch")
new_tab("{PAGE}")
wait_for_load()
time.sleep(2.5)
{"js(\"document.querySelectorAll('.stepchip')[%d].click()\"); time.sleep(2.0)" % step_index if step_index is not None else ""}
print(js("""{PROBE_JS.replace('"""', '')}"""))
'''
    sp = os.path.join(WS, "probe.py")
    open(sp, "w").write(script)
    r = subprocess.run(["python3", sp], capture_output=True, text=True, timeout=300)
    raw = r.stdout.strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"ok": False, "raw": raw[:2000], "stderr": r.stderr[-1000:]}


# --------------------------------------------------------------------------- #
# 2. VET — local swarm checks the measured record against stated intent.
# --------------------------------------------------------------------------- #
SYS_VET = (
    "You audit a 3D medical animation for a patient-education app. You are given "
    "MEASURED FACTS and the DESIGN INTENT. Report only defects you can justify "
    "from the facts given. One JSON object per line (JSONL). No prose, no fences.\n"
    'Schema: {"defect": "<short name>", "severity": "CRITICAL|MAJOR|MINOR", '
    '"evidence": "<quote the measured value>", "fix": "<what to change>"}\n'
    'Example — facts: {"angle_from_horizontal_deg": 89}, intent: "needle at 45 deg"\n'
    'Output: {"defect": "needle angle wrong", "severity": "MAJOR", '
    '"evidence": "angle_from_horizontal_deg is 89, intent is 45",'
    ' "fix": "make the ENTRY point sit at skin height and descend to the nodule"}\n'
    "If there are no defensible defects, output exactly: {\"defect\": \"none\"}"
)

INTENT = """
DESIGN INTENT (from the requester, verbatim):
  1. Start with a head, face and neck.
  2. Translucency reveals the thyroid inside.
  3. Show the nodule.
  4. Back to the neck surface.
  5. Ultrasound probe localises the lesion — the probe FACE must REST ON the
     neck, directly over the lesion.
  6. Needle enters at ~45 degrees, goes UNDER the probe, and traverses the
     lesion beneath the MIDDLE of the probe.
  7. Needle moves in and out, 3 passes.
  8. Needle out; dressing applied.

ANATOMICAL GROUND TRUTH (sourced; treat as correct):
  * thyroid lobes 4-6 cm long, 1.5-2.5 cm wide/deep; isthmus under 5 mm thick
  * thyroid sits 1.5-2.5 cm deep, just behind the strap muscles
  * needle 27G x 1.25 inch; nodule centred under the probe (short-axis)
  * 3 passes, 5-6 seconds of back-and-forth per pass
  * scale: 1 world unit = 5 cm
"""


def vet(observed, tag):
    """Send the measured record to the swarm; return validated defect rows."""
    facts = json.dumps(observed, indent=1)[:3800]
    prompt = (f"{INTENT}\n\nMEASURED FACTS (authoritative, from Python):\n{facts}"
              f"\n\nList the defects.")
    res = swarm([{"id": f"VET-{tag}", "prompt": prompt}],
                system=SYS_VET, max_tokens=2000)
    rows = []
    for r in res:
        if r.get("ok") and r.get("text"):
            rows += parse_jsonl(r["text"])
    # drop the explicit "none" sentinel
    rows = [r for r in rows if str(r.get("defect", "")).lower() not in ("none", "")]
    return rows, res


# --------------------------------------------------------------------------- #
# 3. VALIDATE — a defect only becomes a fix if Python can confirm it.
# --------------------------------------------------------------------------- #
def validate(rows, observed):
    """Independent check: does the measured data actually support the claim?"""
    g = observed.get("geom") or {}
    canvas = observed.get("canvas") or {}
    out = []
    for r in rows:
        d = str(r.get("defect", "")).lower()
        ev = str(r.get("evidence", ""))
        confirmed, why = None, ""
        if "angle" in d or "45" in ev:
            a = g.get("angle_from_horizontal_deg")
            confirmed = (a is not None and abs(a - 45) > 8)
            why = f"measured {a} vs intent 45"
        elif "blank" in d or "render" in d or "empty" in d or "not draw" in d:
            confirmed = (canvas.get("lit_pct", 0) < 3)
            why = f"lit_pct={canvas.get('lit_pct')}"
        elif "label" in d:
            confirmed = len(observed.get("labels") or []) == 0 and observed.get("steps", 0) > 0
            why = f"{len(observed.get('labels') or [])} labels visible"
        elif "probe" in d:
            confirmed = not g.get("has", {}).get("probe")
            why = "probe presence in measured facts"
        else:
            confirmed = None   # can't independently confirm -> goes to human list
            why = "not independently verifiable from measurements"
        out.append({**r, "confirmed": confirmed, "why": why})
    return out


# --------------------------------------------------------------------------- #
def main():
    tag = time.strftime("%H%M%S")
    print(f"=== FNAC build/debug cycle  [{tag}] ===\n")

    print("[1] MEASURE — deterministic, in Python")
    obs = render_probe()
    print("    " + json.dumps(obs)[:600])
    if not obs.get("ok"):
        print("    RENDER FAILED — fatal:", obs.get("fatal"))
        return 1

    print(f"\n[2] VET — local swarm")
    rows, res = vet(obs, tag)
    for r in res:
        print(f"    {r.get('host','?'):8} ok={r.get('ok')} "
              f"{r.get('secs','?')}s  {str(r.get('text',''))[:90]!r}")

    print(f"\n[3] VALIDATE — defects must be independently confirmable")
    for r in validate(rows, obs):
        mark = {True: "CONFIRMED", False: "REFUTED", None: "UNVERIFIED"}[r["confirmed"]]
        print(f"    [{mark:10}] {r.get('severity','?'):8} {r.get('defect','?')}")
        print(f"                 evidence: {str(r.get('evidence',''))[:110]}")
        print(f"                 check   : {r['why']}")

    out = os.path.join(WS, f"cycle_{tag}.json")
    json.dump({"observed": obs, "raw_rows": rows,
               "validated": validate(rows, obs)}, open(out, "w"), indent=1)
    print(f"\n    written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
