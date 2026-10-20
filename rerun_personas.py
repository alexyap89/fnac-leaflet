#!/usr/bin/env /usr/bin/python3
"""Patient-perspective re-review of the FNAC viewer, run to a file.

Written after the first harness lost three background runs to a swallowed
exception: every persona is wrapped in try/except, every print is flushed, and
results are appended to the output file as they arrive so a partial run still
produces usable evidence.

Only the desktop Ornith node is used. The X13 llama.cpp node was measured to
spend its entire token budget on hidden reasoning and then return an EMPTY body
with finish_reason "length" — it is not usable for this task without a much
larger budget, and one productive node is better than two where one silently
returns nothing.
"""
import hashlib
import json
import re
import sys
import traceback
import urllib.request

VIEWER = "/home/alex/Documents/FNAC_Webapp/viewer.html"
OUT = "/home/alex/Documents/FNAC_Webapp/persona_rerun.json"

URL = "http://100.93.142.121:11435/v1"
MODEL = "Ornith-1.5-35B-A3B-AD-Q4_K-IQ4_XS.gguf"

PERSONAS = [
    ("P1_low_literacy_elderly",
     "You are a 72-year-old patient in Singapore with a primary-school education. "
     "English is your second language. You read slowly and get lost in long "
     "sentences. You are nervous about needles. You do NOT know medical words."),
    ("P2_working_adult",
     "You are a 45-year-old working adult in Singapore with a polytechnic diploma. "
     "You read English well. You want to know what happens, how long it takes, and "
     "whether you need time off work. You skim."),
    ("P3_graduate_anxious",
     "You are a 34-year-old university graduate in Singapore. You read very "
     "carefully and you worry about cancer. You notice when something is vague or "
     "when a reassurance is not backed by a fact."),
    ("P4_caregiver",
     "You are a 50-year-old Singaporean reading this on behalf of your elderly "
     "parent. You need to explain it to them in simple words afterwards. You look "
     "for what you must tell them to do."),
]

TYPE_FIX = {"worrying": "worry", "worried": "worry", "confusing": "unclear",
            "absent": "missing", "clear": "good", "reassuring": "good"}


def _accepted():
    """Findings the department has decided to leave as they are.

    Without this, every run re-raises the same items (no phone number, no
    percentage) and they read as unfixed defects when they are settled decisions.
    """
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                      "swarm_accepted_findings.json")
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return {}


def page_state():
    """Read what the app says RIGHT NOW, from the file, including the footer."""
    s = open(VIEWER, encoding="utf-8").read()
    # the hash makes the reviewed revision unambiguous: a result can only be
    # compared to the file it actually read
    source_sha = hashlib.sha256(s.encode()).hexdigest()[:16]
    steps = re.findall(r'\{ t: "([^"]+)", d: "([^"]+)"', s)
    f = re.search(r"<footer>(.*?)</footer>", s, re.S)
    footer = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", f.group(1))).strip() if f else ""
    # The GLOSSARY is on screen with the steps, so the reviewers must see it.
    # Without it they report jargon as undefined when the app already defines it.
    g = re.search(r'<dl class="gloss">(.*?)</dl>', s, re.S)
    gloss = ""
    if g:
        pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", g.group(1), re.S)
        gloss = " | ".join(
            f"{re.sub(r'\s+',' ',a).strip()}: {re.sub(r'\s+',' ',b).strip()}"
            for a, b in pairs)
    return steps, footer, source_sha, gloss


def build_prompt(steps, footer, source_sha="", gloss=""):
    block = "\n".join(f"{i}. {t} — {d}" for i, (t, d) in enumerate(steps, 1))
    gloss_block = f"\nWords explained on the same screen: {gloss}\n" if gloss else ""
    return f"""Read this patient information screen about a thyroid FNAC procedure.

{block}
{gloss_block}
Footer: {footer}

Report ONLY what you personally find unclear, worrying, or missing. Answer as a
patient, not as a doctor. Do NOT explain medical facts or suggest new wording.
A word defined in "Words explained on the same screen" IS explained - do not
report it as undefined.

Return one JSON object per line with keys type, where, quote, why.
Quote the screen's words EXACTLY. Maximum 6 lines."""


def ask(system, prompt):
    # An empty body with finish_reason "length" means the model burned the whole
    # budget on hidden reasoning. This is intermittent, so retry: escalate, but
    # also try a SHORT budget, which discourages extended reasoning. Return as
    # soon as any attempt produces content.
    last = ""
    for mt, temp in ((1400, 0.35), (3000, 0.5), (700, 0.6), (5000, 0.3)):
        payload = {"model": MODEL,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": prompt}],
                   "temperature": temp, "max_tokens": mt}
        req = urllib.request.Request(
            URL + "/chat/completions", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                out = json.loads(r.read().decode())
        except Exception as e:
            last = f"request failed: {type(e).__name__}: {e}"
            continue
        ch = out["choices"][0]
        c = ch["message"].get("content") or ""
        if c.strip():
            if mt != 1400:
                print(f"      (recovered at max_tokens={mt})", flush=True)
            return c
        last = f"empty content, finish_reason={ch.get('finish_reason')}, max_tokens={mt}"
    raise RuntimeError(last)


def main():
    steps, footer, source_sha, gloss = page_state()
    corpus = " ".join([footer] + [t + " " + d for t, d in steps]).lower()
    print(f"re-reviewing {len(steps)} steps (footer included in scope)", flush=True)

    def norm(x):
        return re.sub(r"[^a-z0-9 ]", " ", (x or "").lower())

    def supported(q):
        w = [x for x in norm(q).split() if len(x) > 3]
        return bool(w) and sum(1 for x in w if x in corpus) / len(w) >= 0.6

    all_rows, errors = [], []
    prompt = build_prompt(steps, footer, source_sha, gloss)

    for pid, voice in PERSONAS:
        try:
            raw = ask(voice + " You always answer in JSONL.", prompt)
            got = []
            for line in raw.splitlines():
                line = line.strip().strip(",")
                if not line.startswith("{"):
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if not (isinstance(o, dict) and o.get("type") and o.get("why")):
                    continue
                o["type"] = TYPE_FIX.get(str(o["type"]).lower(), str(o["type"]).lower())
                o["persona"] = pid
                got.append(o)
            all_rows.extend(got)
            print(f"  {pid}: {len(got)} findings", flush=True)
            for g in got:
                print(f"      [{g['type']:7}] {str(g.get('where',''))[:14]:16} "
                      f"{str(g.get('why',''))[:92]}", flush=True)
            # checkpoint after every persona so a later crash still leaves evidence
            json.dump(all_rows, open(OUT, "w"), indent=1)
        except Exception as e:
            errors.append({"persona": pid, "error": f"{type(e).__name__}: {e}"})
            print(f"  {pid}: ERROR {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()

    kept = [r for r in all_rows
            if supported(r.get("quote", "")) or (r["type"] == "missing" and not r.get("quote"))]
    dropped = [r for r in all_rows if r not in kept]

    from collections import defaultdict
    loc = defaultdict(set)
    for r in kept:
        if r["type"] != "good":
            loc[str(r.get("where", "?")).strip().lower()].add(r["persona"])

    report = {
        "steps_reviewed": len(steps),
        "personas_run": len(PERSONAS) - len(errors),
        "errors": errors,
        "raw": len(all_rows), "kept": len(kept), "dropped_unsupported": len(dropped),
        "by_type": {t: sum(1 for r in kept if r["type"] == t)
                    for t in ("unclear", "worry", "missing", "good")},
        "consensus": {k: sorted(v) for k, v in loc.items() if len(v) >= 2},
        "findings": kept,
        "source_sha256": source_sha,
        "accepted_not_defects": _accepted(),
    }
    json.dump(report, open(OUT, "w"), indent=1)

    print(f"\n=== RE-REVIEW RESULT ===", flush=True)
    print(f"  personas run : {report['personas_run']}/4", flush=True)
    print(f"  raw findings : {report['raw']}", flush=True)
    print(f"  kept         : {report['kept']}   (dropped unsupported: {report['dropped_unsupported']})", flush=True)
    print(f"  by type      : {report['by_type']}", flush=True)
    print(f"  consensus    : {json.dumps(report['consensus'], indent=1)}", flush=True)
    print(f"\nwrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
