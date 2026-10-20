#!/usr/bin/env python3
"""Split the shipped index.html into editable source fragments.

Contract (1-based, inclusive line ranges of the ORIGINAL index.html):

    head_top  1..6     doctype/head/meta/title
    css       8..177   the <style> block body
    head_body 179..447 body markup
    lib    450..456  three.js build, vendored verbatim (never hand-edit)
    glb    457..550  GLB parser, accessors, ROLE_COL
    scene  551..705  buildThreeScene() - the 3D scene + skin envelope
    app    706..991  UI, step machine, render loop, controls
    tail   992..994  </script></body></html>

Line 448 is the opening <script> and line 449 is the app banner comment;
both are constants in build.py so the JOIN stays byte-exact.

Run `python3 tools/build.py --check` afterwards: it rebuilds and diffs.
"""
import hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

SPANS = {
    "head_top":  (1, 6),
    "css":       (8, 177),
    "head_body": (179, 447),
    "lib":       (450, 456),
    "glb":       (457, 550),
    "scene":     (551, 705),
    "app":       (706, 991),
    "tail":      (992, 994),
}
NAMES = {
    "head_top":  "head_top.html",
    "css":       "style.css",
    "head_body": "head_body.html",
    "lib":       "lib/three.min.js",
    "glb":       "app_glb.js",
    "scene":     "app_scene.js",
    "app":       "app_app.js",
    "tail":      "tail.html",
}


def main():
    src_html = os.path.join(ROOT, "index.html")
    with open(src_html, "rb") as fh:
        raw = fh.read()
    lines = raw.split(b"\n")
    if lines[-1] != b"":
        raise SystemExit("index.html does not end with a newline; aborting")
    lines = lines[:-1]

    assert lines[6] == b"<style>", lines[6][:60]
    assert lines[177] == b"</style>", lines[177][:60]
    assert lines[447] == b"<script>", lines[447][:60]
    assert b"GEOMETRY" in lines[448], lines[448][:60]
    assert lines[449].startswith(b"console.warn('Scripts"), lines[449][:60]
    assert lines[550].startswith(b"function buildThreeScene"), lines[550][:60]
    assert lines[705].startswith(b"(function(){"), lines[705][:60]
    assert lines[991] == b"</script>", lines[991][:60]

    for key, (a, b) in SPANS.items():
        out = os.path.join(SRC, NAMES[key])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        chunk = b"\n".join(lines[a - 1:b]) + b"\n"
        if key == "glb":
            # keep the fragment small and diffable: build.py regenerates the
            # literal from manifest["model"] on every build
            chunk = re.sub(rb"const GLB_B64='[A-Za-z0-9+/=]*';",
                           b"const GLB_B64='';", chunk)
        with open(out, "wb") as fh:
            fh.write(chunk)
        print(f"  {NAMES[key]:22s} lines {a:4d}..{b:4d}  {len(chunk):>9d} bytes")

    manifest = {
        "note": "line ranges into the original index.html; see tools/split.py",
        "spans": {k: list(v) for k, v in SPANS.items()},
        "files": NAMES,
        # replaceable assets: build.py regenerates these from the real files
        "model": "model/fnac_scene_web.glb",
        "audio_glob": "audio/en/leaflet/step*.mp3",
        "source_index_sha256": hashlib.sha256(raw).hexdigest(),
        "source_index_bytes": len(raw),
    }
    os.makedirs(SRC, exist_ok=True)
    with open(os.path.join(SRC, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    print(f"\nindex.html sha256 {manifest['source_index_sha256'][:16]}… "
          f"{len(raw)} bytes -> src/manifest.json")


if __name__ == "__main__":
    sys.exit(main())
