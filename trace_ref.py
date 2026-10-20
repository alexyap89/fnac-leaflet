#!/usr/bin/env /usr/bin/python3
"""Trace the reference illustration into clean, ROLE-NAMED SVG layers.

Why this file exists in this shape:

Seven attempts at hand-coded anatomy produced 2-3/10 artwork. Alex's reference
image is already a competent medical illustration, so the right move is to
vectorise it and animate the layers.

The first tracing attempt failed for an instructive reason. Median-cut
quantisation optimises *photographic* colour error, and it merged the dark
outlines into the skin fills because their RGB values are close. But an outline
is not a colour — it is a ROLE. The drawing is carried by the outline pixels
(3.4% of the frame) plus a small flat palette. Merging at a distance of 26 then
collapsed the whole image to three colours and 851 bytes.

So this script segments by ROLE instead:
  * luminance + saturation threshold -> the outline layer
  * nearest-palette in RGB           -> each fill layer
Each layer is traced separately and NAMED for what it depicts, so the animator
can move structures (probe, needle) as whole units.
"""
import json
import os
import sys

import numpy as np
import potrace
from PIL import Image

BASE = "/home/alex/Documents/FNAC_Webapp"
SRC = "/home/alex/.hermes/cache/images/img_e949b93b820d.jpg"
OUT = os.path.join(BASE, "trace.svg")
REPORT = os.path.join(BASE, "trace_report.json")

# The reference's actual palette, read off the measured histogram. Each entry is
# (name, rgb, role). Roles drive the animation, so they matter more than the
# exact colour values.
PALETTE = [
    ("background", (226, 242, 243), "bg"),
    ("skin",       (243, 210, 178), "anatomy"),
    ("skinshade",  (233, 190, 163), "anatomy"),
    ("skinlight",  (244, 228, 199), "anatomy"),
    ("probe",      (114, 178, 197), "equipment"),
    ("probelight", (162, 196, 210), "equipment"),
    ("thyroid",    (136, 132, 118), "lesion"),
    ("nodule",     (212, 166, 164), "lesion"),
    ("hair",       (88, 84, 76),    "anatomy"),
    ("white",      (243, 243, 243), "equipment"),
]

# Outline pixels: dark and low-saturation. Threshold tuned against the measured
# histogram (the outline bucket sits around 64-80 luminance).
OUTLINE_MAX_LUM = 118


def load(path):
    im = Image.open(path).convert("RGB")
    return np.asarray(im).astype(np.float32), im.size


def luminance(a):
    return 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]


def saturation(a):
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)


def assign(a):
    """Return an integer label per pixel: 0 = outline, 1..N = palette[i-1]."""
    lum = luminance(a)
    sat = saturation(a)
    outline = (lum < OUTLINE_MAX_LUM) & (sat < 0.55)

    flat = a.reshape(-1, 3)
    best = np.full(flat.shape[0], 1e18, dtype=np.float32)
    label = np.zeros(flat.shape[0], dtype=np.int32)
    for i, (name, rgb, role) in enumerate(PALETTE):
        d = ((flat[:, 0] - rgb[0]) ** 2) + ((flat[:, 1] - rgb[1]) ** 2) \
            + ((flat[:, 2] - rgb[2]) ** 2)
        m = d < best
        best[m] = d[m]
        label[m] = i + 1
    label = label.reshape(a.shape[:2])
    label[outline] = 0
    return label


def trace_mask(mask, turdsize=10):
    """Trace a boolean mask to SVG path data.

    The dtype matters and is not cosmetic. potracer given a uint32 array
    silently produces a single full-frame rectangle instead of the shapes — a
    probe with a 5x5 block of 1s in a 20x20 grid returned ONE curve spanning
    0..20 because the dtype was uint32; with bool it returned the full frame
    PLUS the block, correctly. That bug made every one of the eleven layers
    paint the whole canvas, so the last layer drawn (the dark outline) covered
    everything and the trace rendered as a solid rectangle.
    """
    data = np.asarray(mask).astype(bool)
    if not data.any():
        return ""
    bmp = potrace.Bitmap(data)
    path = bmp.trace(turdsize=turdsize,
                     turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                     alphamax=1.0, opticurve=1, opttolerance=0.35)

    def pt(o):
        return float(o.x), float(o.y)

    d = []
    for curve in path:
        sx, sy = pt(curve.start_point)
        d.append(f"M {sx:.1f} {sy:.1f}")
        for seg in curve:
            if seg.is_corner:
                cx, cy = pt(seg.c)
                ex, ey = pt(seg.end_point)
                d.append(f"L {cx:.1f} {cy:.1f} L {ex:.1f} {ey:.1f}")
            else:
                c1x, c1y = pt(seg.c1)
                c2x, c2y = pt(seg.c2)
                ex, ey = pt(seg.end_point)
                d.append(f"C {c1x:.1f} {c1y:.1f} {c2x:.1f} {c2y:.1f} "
                         f"{ex:.1f} {ey:.1f}")
        d.append("Z")
    return " ".join(d)


def _spans_frame(d, W, H):
    """True if the path data contains a subpath covering the whole canvas."""
    import re as _re
    nums = [float(x) for x in _re.findall(r"-?\d+\.?\d*", d[:4000])]
    if len(nums) < 8:
        return False
    xs = nums[0::2][:200]
    ys = nums[1::2][:200]
    if not xs or not ys:
        return False
    return (min(xs) <= 1 and max(xs) >= W - 1) and (min(ys) <= 1 and max(ys) >= H - 1)


def main():
    a, (W, H) = load(SRC)
    label = assign(a)
    total = W * H
    print(f"source {W}x{H}")

    counts = {i: int((label == i).sum()) for i in range(len(PALETTE) + 1)}
    print("\nsegmentation:")
    print(f"  {'OUTLINE':12} {counts[0]/total*100:5.2f}%  ({counts[0]} px)")
    for i, (name, rgb, role) in enumerate(PALETTE):
        print(f"  {name:12} {counts[i+1]/total*100:5.2f}%  ({counts[i+1]} px)"
              f"  role={role}")

    # fills large-first so later layers paint over earlier ones
    order = sorted(range(len(PALETTE)), key=lambda i: -counts[i + 1])

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}">']
    svg.append(f'  <rect width="{W}" height="{H}" fill="rgb(226,242,243)"/>')

    report = {"source": SRC, "size": [W, H], "layers": []}

    for i in order:
        name, rgb, role = PALETTE[i]
        if counts[i + 1] < total * 0.0006:
            continue
        d = trace_mask(label == i + 1)
        if not d:
            continue
        hexc = "#%02x%02x%02x" % rgb
        svg.append(f'  <g id="{name}" data-role="{role}" data-rgb="{hexc}" '
                   f'data-coverage="{counts[i+1]/total:.4f}">')
        svg.append(f'    <path d="{d}" fill="{hexc}" fill-rule="evenodd"/>')
        svg.append('  </g>')
        report["layers"].append({"name": name, "role": role, "hex": hexc,
                                 "coverage": round(counts[i + 1] / total, 5),
                                 "path_chars": len(d),
                                 "bbox_full_frame": _spans_frame(d, W, H)})

    # the outline goes on top: it is the drawing
    d = trace_mask(label == 0, turdsize=6)
    if d:
        svg.append('  <g id="outline" data-role="linework">')
        svg.append(f'    <path d="{d}" fill="#3a3a3a" fill-rule="evenodd"/>')
        svg.append('  </g>')
        report["layers"].append({"name": "outline", "role": "linework",
                                 "hex": "#3a3a3a",
                                 "coverage": round(counts[0] / total, 5),
                                 "path_chars": len(d)})

    svg.append('</svg>')
    out = "\n".join(svg)
    open(OUT, "w").write(out)
    report["bytes"] = len(out)
    json.dump(report, open(REPORT, "w"), indent=1)
    # sanity: a traced path whose bbox is the whole frame for a small-coverage
    # layer means the trace is wrong (the failure mode above).
    W_, H_ = W, H
    for L in report["layers"]:
        if L["coverage"] < 0.30 and L.get("bbox_full_frame"):
            print(f"  !! {L['name']}: coverage {L['coverage']} but the path "
                  f"spans the whole frame — trace polarity/dtype is suspect")

    print(f"\nwrote {OUT} ({len(out):,} bytes, {len(report['layers'])} layers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
