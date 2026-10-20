#!/usr/bin/env python3
"""Judge every step of the FNAC viewer: vision review + text adjudication.

Two stages, because the hardware dictates it:

  STAGE 1 (vision)  MTPLX on the MBP is the ONLY vision-capable model on the
                    tailnet. Both llama.cpp nodes are text-only, so a local
                    vision "swarm" is not possible - one reviewer sees the
                    pixels. It scores each step's screenshot against a fixed
                    rubric and returns strict JSON.

  STAGE 2 (judge)   The text-only fleet reads stage 1's FINDINGS ONLY (never
                    the image) and adjudicates: which are real defects, which
                    are the model hallucinating, and what the single highest-
                    value fix is. Two independent nodes, then agreement is
                    measured rather than assumed.

Neither stage may add clinical content. This tool judges PRESENTATION only.

Usage:
    python3 judge_swarm.py shots/            # a directory of step screenshots
"""
import base64, json, os, subprocess, sys, urllib.request, urllib.error

MBP = "alexyap@100.110.244.103"
VISION_URL = "http://127.0.0.1:8000/v1/chat/completions"   # bound to localhost
VISION_MODEL = "mtplx-qwen38-27b-optimized-speed-fp16"

X13 = "http://100.81.219.125:8080/v1/chat/completions"
X13_MODEL = "gemma-4-26b-a4b-mtp"
ORNITH = "http://100.93.142.121:11435/v1/chat/completions"
ORNITH_MODEL = os.environ.get("ORNITH_MODEL", "Ornith-1.5-35B-A3B-AD-Q4_K-IQ4_XS.gguf")

RUBRIC = ('Score the 3D viewport of this patient-education screenshot 0-10 on '
          'framing, centring, frontality, legibility, clarity and overall. '
          'Reply with ONLY JSON: {"framing":N,"centred":N,"frontal":N,"legible":N,'
          '"clarity":N,"overall":N,"worst_problem":"one short sentence",'
          '"frame_percent":N}')


def mbp_vision(png_path):
    """Send one image to MTPLX. It is bound to 127.0.0.1 on the MBP, so the JSON
    body is piped over ssh into curl running there."""
    b64 = base64.b64encode(open(png_path, "rb").read()).decode()
    body = {
        "model": VISION_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": RUBRIC},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
        ]}],
        "max_tokens": 2400, "temperature": 0.0,
    }
    cmd = ("curl -s --max-time 260 -X POST %s "
           "-H 'Content-Type: application/json' --data-binary @-" % VISION_URL)
    p = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", MBP, cmd],
                       input=json.dumps(body).encode(), capture_output=True, timeout=300)
    txt = p.stdout.decode(errors="replace")
    try:
        return json.loads(txt)["choices"][0]["message"]["content"]
    except Exception:
        return None


def parse_json(txt):
    """Models wrap JSON in prose or fences; pull out the first object."""
    if not txt:
        return None
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(txt[i:j + 1])
    except Exception:
        return None


def adjudicate(node_url, model, findings, auth=None):
    """Stage 2: a text-only node judges stage 1's findings. It never sees the
    image, so it cannot invent new visual claims - only weigh the ones given."""
    prompt = (
        "A vision model reviewed screenshots of a patient-education app for "
        "thyroid FNAC. Here are its findings as JSON, one entry per step:\n\n"
        + json.dumps(findings, indent=1)[:6000] +
        "\n\nJudge these findings. Reply with ONLY this JSON:\n"
        '{"confirmed":[list of step keys that are REAL defects],'
        '"likely_hallucinated":[list of step keys the vision model probably got wrong],'
        '"top_priority":"the single step key and issue to fix first",'
        '"pattern":"one sentence naming the underlying cause if several share one"}'
    )
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 9000, "temperature": 0.1,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(node_url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    if auth:
        req.add_header("Authorization", "Bearer " + auth)
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.load(r)
        return parse_json(d["choices"][0]["message"]["content"]) or d["choices"][0]["message"]["content"]
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}


def main():
    shots_dir = sys.argv[1] if len(sys.argv) > 1 else "shots"
    files = sorted(f for f in os.listdir(shots_dir) if f.endswith(".png"))
    if not files:
        sys.exit("no PNGs in " + shots_dir)

    print("STAGE 1 - vision review by MTPLX (%d steps)\n" % len(files))
    findings = {}
    for f in files:
        key = f.replace(".png", "")
        txt = mbp_vision(os.path.join(shots_dir, f))
        d = parse_json(txt)
        findings[key] = d if d else {"raw": (txt or "no reply")[:200]}
        if d:
            print("  %-6s overall %-3s  frame %-4s%%  worst: %s"
                  % (key, d.get("overall", "?"), d.get("frame_percent", "?"),
                     str(d.get("worst_problem", ""))[:70]))
        else:
            print("  %-6s UNPARSEABLE" % key)

    json.dump(findings, open("judge_findings.json", "w"), indent=1)
    print("\n  -> judge_findings.json")

    print("\nSTAGE 2 - text-only nodes adjudicate the findings\n")
    x13key = os.environ.get("LLAMACPP_API_KEY", "llamacpp")
    v1 = adjudicate(X13, X13_MODEL, findings, auth=x13key)
    print("  X13 (gemma-4-26b):", json.dumps(v1)[:400])
    v2 = adjudicate(ORNITH, ORNITH_MODEL, findings)
    print("  Ornith-35B       :", json.dumps(v2)[:400])

    out = {"findings": findings, "x13": v1, "ornith": v2}
    json.dump(out, open("judge_verdict.json", "w"), indent=1)
    print("\n  -> judge_verdict.json")

    # Agreement is measured, not assumed.
    try:
        a, b = v1.get("confirmed", []), v2.get("confirmed", [])
        both = sorted(set(a) & set(b))
        print("\n  CONFIRMED BY BOTH: %s" % (both or "none agreed"))
    except Exception:
        print("\n  (could not compute agreement)")


if __name__ == "__main__":
    main()
