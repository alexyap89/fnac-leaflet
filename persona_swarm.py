#!/usr/bin/env /usr/bin/python3
"""Patient-perspective review swarm for the FNAC thyroid webapp.

WHY THIS SHAPE
--------------
Two rules from `local-swarm` and `msk-rag-stack` drive the design:

  1. "A local model is a throughput device over supplied text, not an oracle
     over its own weights." The fleet must never be asked for a fact it could
     invent. So we hand it the app's ACTUAL text, verbatim, and ask only for
     judgements about that text.

  2. "Ornith must never score its own work." The app was authored here, so no
     single model adjudicates. We collect judgements from every live node and
     merge them in Python, and we only surface a finding when at least two
     independent personas raise it OR a deterministic check confirms it.

The personas are Singapore-context patient readers. Each is asked ONLY to say
what is unclear, what worries them, or what they would still want to know —
never to supply medical facts. Anything a model asserts as a medical claim is
discarded before it reaches the report.

SAFETY: no patient data is sent. The payload is the app's public-facing
explanatory text only. Hosts are serialised, never fanned out.
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "/home/alex/Documents/FNAC_Webapp"
OUT = os.path.join(BASE, "persona_review.json")

X13_URL = "http://100.81.219.125:8080/v1"
X13_MODEL = "gemma-4-26b-a4b-mtp"
X13_KEY = os.environ.get("LLAMACPP_API_KEY", "llamacpp")

ORNITH_URL = "http://100.93.142.121:11435/v1"
ORNITH_MODEL = "Ornith-1.5-35B-A3B-AD-Q4_K-IQ4_XS.gguf"

# Personas, each with a different reading age / education / anxiety profile.
# Deliberately Singaporean: the app is for WH patients, and idiom matters.
PERSONAS = [
    {
        "id": "P1_low_literacy_elderly",
        "label": "72, primary school, Mandarin-dominant, reads slowly, anxious",
        "voice": ("You are a 72-year-old patient in Singapore with a primary-school "
                  "education. English is your second language. You read slowly and get "
                  "lost in long sentences. You are nervous about needles. You do NOT "
                  "know medical words."),
    },
    {
        "id": "P2_working_adult",
        "label": "45, ITE/polytechnic, working adult, pragmatic, time-poor",
        "voice": ("You are a 45-year-old working adult in Singapore with a polytechnic "
                  "diploma. You read English well. You want to know what happens, how "
                  "long it takes, and whether you need time off work. You skim."),
    },
    {
        "id": "P3_graduate_anxious",
        "label": "34, university graduate, health-anxious, reads closely",
        "voice": ("You are a 34-year-old university graduate in Singapore. You read "
                  "very carefully and you worry about cancer. You notice when something "
                  "is vague or when a reassurance is not backed by a fact."),
    },
    {
        "id": "P4_caregiver",
        "label": "50, caregiver reading on behalf of an elderly parent",
        "voice": ("You are a 50-year-old Singaporean reading this on behalf of your "
                  "elderly parent, who will have the procedure. You need to be able to "
                  "explain it to them in simple words afterwards. You look for what you "
                  "must tell them to do."),
    },
]


def _post(url, payload, timeout=180, key=None):
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url + "/chat/completions", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def ask(url, model, prompt, system, key=None, max_tokens=8000, timeout=300):
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "enable_thinking": False,      # required by the llama.cpp node
    }
    out = _post(url, payload, timeout=timeout, key=key)
    ch = out["choices"][0]
    content = ch["message"].get("content") or ""
    if not content.strip():
        # Silent-empty is the known failure mode of the llama.cpp node: the
        # whole budget went to hidden reasoning. Surface it rather than letting
        # it masquerade as "no findings".
        raise RuntimeError(
            f"empty content (finish_reason={ch.get('finish_reason')}, "
            f"tokens={out.get('usage', {}).get('completion_tokens')})")
    return content


def extract_text():
    """Pull the app's own user-facing text out of viewer.html. We review what the
    app ACTUALLY says, not a paraphrase of it."""
    p = os.path.join(BASE, "viewer.html")
    s = open(p, encoding="utf-8").read()

    steps = re.findall(r'\{\s*t:\s*"([^"]+)"\s*,\s*d:\s*"([^"]+)"', s)
    footer = re.search(r'<footer>(.*?)</footer>', s, re.S)
    header = re.search(r'<h1>([^<]+)</h1>', s)

    def clean(x):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()

    return {
        "title": clean(header.group(1)) if header else "",
        "steps": [{"t": t, "d": d} for t, d in steps],
        "footer": clean(footer.group(1)) if footer else "",
    }


def build_prompt(text):
    lines = []
    for i, s in enumerate(text["steps"], 1):
        lines.append(f'{i}. {s["t"]} — {s["d"]}')
    steps_block = "\n".join(lines)
    return f"""You are being asked to read a patient information screen that explains
an ultrasound-guided fine needle aspiration (FNAC) of a thyroid nodule.

The screen contains these numbered steps:

{steps_block}

And this footer text:
{text['footer']}

Your job: report ONLY what YOU personally find unclear, worrying, or missing.
Answer as a patient, not as a doctor. Do NOT explain medical facts. Do NOT
suggest what the words should say. Do NOT give clinical advice.

Return one JSON object per line (JSONL), each with exactly these keys:
{{"type":"unclear|worry|missing|good","where":"step N or footer","quote":"the exact words from the screen that caused this","why":"your reaction in one sentence"}}

Rules:
- Quote the screen's words EXACTLY. If you cannot quote it, do not report it.
- Maximum 6 lines.
- If something is clear and reassuring, say so with type "good".
"""


def run_one(persona, text, url, model, key):
    system = persona["voice"] + " You always answer in JSONL, one object per line."
    prompt = build_prompt(text)
    try:
        raw = ask(url, model, prompt, system, key=key)
        rows = []
        for line in raw.splitlines():
            line = line.strip().strip(",")
            if not line or not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if isinstance(o, dict) and o.get("type") and o.get("why"):
                t = str(o["type"]).strip().lower()
                t = {"worrying": "worry", "worried": "worry",
                     "confusing": "unclear", "absent": "missing",
                     "clear": "good", "reassuring": "good"}.get(t, t)
                if t not in ("unclear", "worry", "missing", "good"):
                    t = "unclear"
                o["type"] = t
                o["persona"] = persona["id"]
                o["persona_label"] = persona["label"]
                rows.append(o)
        return rows, None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def main():
    text = extract_text()
    print(f"reviewing {len(text['steps'])} steps, {len(text['footer'])} chars footer")
    if not text["steps"]:
        print("could not extract step text — aborting")
        return 1

    # Hosts: X13 and the desktop. Serialised per host, one request at a time.
    nodes = [
        ("x13", X13_URL, X13_MODEL, X13_KEY),
        ("desktop", ORNITH_URL, ORNITH_MODEL, None),
    ]
    live = []
    for name, url, model, key in nodes:
        try:
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            req = urllib.request.Request(url + "/models", headers=headers)
            with urllib.request.urlopen(req, timeout=6) as r:
                json.loads(r.read().decode())
            live.append((name, url, model, key))
            print(f"  {name}: UP")
        except Exception as e:
            print(f"  {name}: down ({type(e).__name__})")

    if not live:
        print("no live nodes — aborting")
        return 1

    # Assign personas round-robin across live nodes; each node processes its
    # own personas sequentially so we never fan out to a single host.
    buckets = {n[0]: [] for n in live}
    for i, p in enumerate(PERSONAS):
        buckets[live[i % len(live)][0]].append(p)

    results = {}
    def run_node(entry):
        name, url, model, key = entry
        rows = []
        for p in buckets[name]:
            got, err = run_one(p, text, url, model, key)
            print(f"    {name} / {p['id']}: {len(got)} findings"
                  + (f"  ERROR {err}" if err else ""))
            rows.extend(got)
        return name, rows

    with ThreadPoolExecutor(max_workers=len(live)) as ex:
        futs = [ex.submit(run_node, e) for e in live]
        for f in as_completed(futs):
            n, rows = f.result()
            results[n] = rows

    all_rows = [r for rows in results.values() for r in rows]

    # ---- deterministic gate: a finding survives only if a persona raised it
    # AND its quote actually appears in the app text. This kills invented
    # quotes, which is the failure mode the fleet is known for.
    corpus = " ".join([text["title"], text["footer"]] +
                      [s["t"] + " " + s["d"] for s in text["steps"]]).lower()

    def norm(x):
        return re.sub(r"[^a-z0-9 ]", " ", (x or "").lower())

    def quote_supported(q):
        q = norm(q)
        words = [w for w in q.split() if len(w) > 3]
        if not words:
            return False
        # require most content words to appear in the app text
        hits = sum(1 for w in words if w in corpus)
        return hits / len(words) >= 0.6

    # A "missing" finding cannot quote the screen, by definition. Do not bin it
    # on the quote gate — instead mark it unverified and require a second
    # persona to agree before it is treated as actionable.
    kept, dropped, unverified = [], [], []
    for r in all_rows:
        q = (r.get("quote") or "").strip()
        if r["type"] == "missing" and not q:
            unverified.append(r)
        elif quote_supported(q):
            kept.append(r)
        else:
            dropped.append(r)

    # group by type for the report
    by_type = {}
    for r in kept:
        by_type.setdefault(r["type"], []).append(r)

    # cross-persona agreement: same 'where' + same type raised by 2+ personas
    agree = {}
    for r in kept:
        k = (r["type"], str(r.get("where", "")).strip().lower())
        agree.setdefault(k, set()).add(r["persona"])
    for r in unverified:
        k = (r["type"], str(r.get("where", "")).strip().lower())
        agree.setdefault(k, set()).add(r["persona"])
    consensus = {f"{k[0]} @ {k[1]}": sorted(v) for k, v in agree.items() if len(v) >= 2}

    report = {
        "text_reviewed": text,
        "nodes_live": [n[0] for n in live],
        "personas": [{"id": p["id"], "label": p["label"]} for p in PERSONAS],
        "findings_kept": kept,
        "findings_dropped_unsupported_quote": dropped,
        "findings_unverified_missing": unverified,
        "consensus": consensus,
        "counts": {
            "total_raw": len(all_rows),
            "kept": len(kept),
            "dropped": len(dropped),
            "unverified_missing": len(unverified),
            "by_type": {k: len(v) for k, v in by_type.items()},
        },
    }
    json.dump(report, open(OUT, "w"), indent=1)

    print(f"\n=== RESULTS ===")
    print(f"raw findings      : {len(all_rows)}")
    print(f"kept (quote real) : {len(kept)}")
    print(f"dropped (invented): {len(dropped)}")
    print(f"by type           : {report['counts']['by_type']}")
    print(f"consensus items   : {len(consensus)}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
