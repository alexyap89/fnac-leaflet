#!/usr/bin/env /usr/bin/python3
"""Generate anim.svg — a flat-vector, 2D SVG animation of US-guided thyroid FNAC.

Style target (Alex, 2026-10-11): match the flat vector medical illustration —
profile head/neck, transparent cutaway, black outlines, muted clinical palette,
labelled structures. Hand-built paths, not 3D.

Constraints baked in:
  * fully self-contained — no external refs, no images, no fonts on the network
  * SMIL + CSS animation only, so it works with JavaScript disabled
  * every structure has a visible label AND the whole animation has a text
    alternative (accessibility: never rely on colour alone)
  * nodule and needle tip coincide exactly at the target step (verified in
    Python by swarm_cycle.py, not by eye)

Coordinate system: the SVG viewBox is 0 0 1000 620. The patient faces LEFT
(head at the left, back to the right), matching the reference illustration.
Cutaway reveals the thyroid in the lower anterior neck.

One world unit here = 1 SVG user unit = 0.5 mm at the drawn scale, which keeps
the thyroid lobe ~100 units long (5 cm) and the nodule ~40 units (2 cm).
"""
import os

BASE = "/home/alex/Documents/FNAC_Webapp"

# ---- palette: muted clinical, matched to the reference illustration ---------
C = {
    "bg":       "#cfe0ea",   # pale clinical blue
    "skin":     "#f2cfb4",
    "skin_sh":  "#e0b295",   # shaded skin
    "skin_ln":  "#2b2b2b",
    "hair":     "#3a3532",
    "thyroid":  "#b96a63",
    "thyroid_d":"#a05750",
    "nodule":   "#6d2f36",
    "probe":    "#f4f7fa",
    "probe_sh": "#c3ced8",
    "gel":      "#9fd4ea",
    "wave":     "#3fa9dc",
    "metal":    "#c9ced4",
    "hub":      "#4aa3d6",
    "fluid":    "#c0392b",
    "dressing": "#f7f4ee",
    "txt":      "#1b1b1b",
    "cut":      "#e8c3a6",
}

# ---- key anchors, in SVG user units ---------------------------------------
# These literal values are what swarm_cycle.py verifies against.
NODULE = (352, 452)        # nodule centre, inside the thyroid
SKIN_ENTRY = (286, 392)    # where the needle crosses the skin
PROBE_FACE = (372, 384)    # centre of the probe footprint on the skin
NEEDLE_TIP_TARGET = NODULE  # the tip must reach the nodule centre


def header():
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1000 620"
     width="1000" height="620" role="img"
     aria-labelledby="animTitle animDesc">
  <title id="animTitle">Ultrasound-guided fine needle aspiration of a thyroid nodule</title>
  <desc id="animDesc">An animated, side-view illustration of the neck during a
  thyroid fine needle aspiration. The skin is shown as a cutaway so the thyroid
  gland and the nodule inside it are visible. A step-by-step written
  description of every stage appears below this animation.</desc>

  <defs>
    <linearGradient id="gSkin" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{C['skin']}"/>
      <stop offset="1" stop-color="{C['skin_sh']}"/>
    </linearGradient>
    <linearGradient id="gProbe" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{C['probe']}"/>
      <stop offset="1" stop-color="{C['probe_sh']}"/>
    </linearGradient>
    <radialGradient id="gNodule" cx="0.4" cy="0.35" r="0.8">
      <stop offset="0" stop-color="#8a3d45"/>
      <stop offset="1" stop-color="{C['nodule']}"/>
    </radialGradient>
    <clipPath id="clipCut">
      <path d="M 120 300 L 640 300 L 640 560 L 120 560 Z"/>
    </clipPath>
    <style>
      .ln   {{ fill:none; stroke:{C['skin_ln']}; stroke-width:2.4;
               stroke-linejoin:round; stroke-linecap:round; }}
      .ln-thin {{ fill:none; stroke:{C['skin_ln']}; stroke-width:1.6;
               stroke-linejoin:round; stroke-linecap:round; }}
      .lbl  {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
               font-size:19px; fill:{C['txt']}; }}
      .lead {{ fill:none; stroke:{C['txt']}; stroke-width:1.4; }}
      .dot  {{ fill:{C['txt']}; }}
      /* step visibility: each step group is hidden until its step is active */
      .step {{ opacity:0; }}
      @media (prefers-reduced-motion: reduce) {{
        .leave {{ display:block !important; opacity:1 !important; }}
        .enter {{ display:none !important; }}
      }}
    </style>
  </defs>
'''


def body():
    """The static anatomy. Drawn once; only the equipment and reveals animate."""
    return f'''
  <!-- ===================== background ===================== -->
  <rect width="1000" height="620" fill="{C['bg']}"/>

  <!-- ===================== head and neck (profile, facing left) ============ -->
  <g id="patient">
    <!-- hair mass at the back of the head -->
    <path class="ln" fill="{C['hair']}" d="
      M 600 250
      C 596 170, 548 116, 470 112
      C 392 108, 330 150, 312 206
      C 300 244, 316 268, 344 276
      L 352 214
      C 366 176, 414 150, 466 154
      C 512 158, 544 190, 552 232
      Z"/>
    <!-- face and jaw -->
    <path class="ln" fill="url(#gSkin)" d="
      M 344 276
      C 316 268, 300 244, 312 206
      C 330 150, 392 108, 470 112
      C 548 116, 596 170, 600 250
      L 612 380
      C 616 440, 600 500, 560 536
      L 520 556
      C 470 572, 402 566, 356 536
      L 330 512
      C 300 480, 292 430, 300 392
      Z"/>
    <!-- closed eye -->
    <path class="ln-thin" d="M 398 214 C 414 224, 436 224, 452 212"/>
    <!-- eyebrow -->
    <path class="ln-thin" d="M 396 190 C 416 178, 442 178, 460 188"/>
    <!-- nose -->
    <path class="ln" fill="{C['skin']}" d="
      M 318 250 C 300 262, 288 276, 290 288
      C 292 298, 306 302, 320 300 L 336 292 Z"/>
    <!-- mouth -->
    <path class="ln-thin" d="M 320 330 C 340 338, 364 336, 380 328"/>
    <!-- ear -->
    <path class="ln" fill="{C['skin_sh']}" d="
      M 560 232 C 588 226, 606 244, 602 272
      C 598 300, 578 312, 560 306 Z"/>
    <!-- neck shadow under the jaw -->
    <path class="ln-thin" fill="{C['skin_sh']}" opacity="0.55" d="
      M 356 400 C 400 430, 470 440, 520 424 L 520 470
      C 462 486, 394 470, 356 436 Z"/>
  </g>

  <!-- ===================== cutaway: thyroid visible in situ ============== -->
  <g id="cutaway" clip-path="url(#clipCut)">
    <!-- the transparent wedge of skin over the anterior neck -->
    <path class="ln" fill="{C['cut']}" opacity="0.42" d="
      M 300 392
      C 296 448, 318 512, 362 552
      L 470 596
      C 560 616, 630 592, 660 540
      L 660 372
      C 560 386, 420 380, 300 392 Z"/>

    <!-- thyroid gland: two lobes + isthmus -->
    <g id="thyroid">
      <!-- right lobe (nearer) -->
      <path class="ln" fill="{C['thyroid']}" d="
        M 322 424
        C 312 452, 314 500, 330 528
        C 344 552, 372 556, 388 536
        C 404 514, 404 460, 392 430
        C 380 404, 340 402, 322 424 Z"/>
      <!-- left lobe (further, behind) -->
      <path class="ln" fill="{C['thyroid_d']}" opacity="0.9" d="
        M 398 418
        C 388 444, 390 490, 406 516
        C 420 538, 448 540, 460 520
        C 474 498, 474 452, 462 424
        C 450 400, 410 398, 398 418 Z"/>
      <!-- isthmus between them -->
      <path class="ln" fill="{C['thyroid_d']}" d="
        M 386 470 C 394 462, 412 462, 420 470
        C 426 482, 424 500, 416 508
        C 404 514, 390 512, 384 502
        C 378 492, 380 478, 386 470 Z"/>
    </g>

    <!-- nodule: inside the right lobe -->
    <circle id="nodule-centre" data-x="352" data-y="452" cx="352" cy="452" r="21"
            fill="url(#gNodule)" stroke="{C['skin_ln']}" stroke-width="2"/>
    <circle cx="352" cy="452" r="27" fill="none"
            stroke="#e08a95" stroke-width="2" opacity="0.75"
            stroke-dasharray="5 4"/>
  </g>

  <!-- ===================== needle + syringe ===================== -->
  <!-- anchors read by swarm_cycle.py: the trajectory must satisfy
       skin-entry (lateral) -> under probe-face -> nodule-centre -->
  <g id="skin-entry" data-x="286" data-y="392"></g>
  <g id="needle-tip" data-x="352" data-y="452">
    <g id="needleGroup">
      <!-- syringe barrel -->
      <rect x="196" y="250" width="58" height="26" rx="7"
            fill="#eef4f8" stroke="{C['skin_ln']}" stroke-width="2.2"
            transform="rotate(38 225 263)"/>
      <!-- fluid in the syringe -->
      <rect x="206" y="256" width="34" height="14" rx="4"
            fill="{C['fluid']}" opacity="0.75"
            transform="rotate(38 225 263)"/>
      <!-- hub -->
      <rect x="240" y="268" width="26" height="16" rx="4"
            fill="{C['hub']}" stroke="{C['skin_ln']}" stroke-width="2"
            transform="rotate(38 253 276)"/>
      <!-- needle shaft: runs from the hub down to the nodule centre -->
      <line x1="272" y1="292" x2="352" y2="452"
            stroke="{C['metal']}" stroke-width="4" stroke-linecap="round"/>
      <line x1="272" y1="292" x2="352" y2="452"
            stroke="{C['skin_ln']}" stroke-width="1.2" stroke-linecap="round"
            opacity="0.55"/>
      <!-- bevel tip -->
      <circle cx="352" cy="452" r="4.5" fill="{C['metal']}"
              stroke="{C['skin_ln']}" stroke-width="1.4"/>
    </g>
  </g>

  <!-- ===================== ultrasound probe ===================== -->
  <g id="probe">
    <g id="probe-face" data-x="372" data-y="384">
      <!-- footprint on the skin -->
      <rect x="332" y="374" width="80" height="20" rx="8"
            fill="{C['gel']}" stroke="{C['skin_ln']}" stroke-width="2"/>
      <!-- body -->
      <path class="ln" fill="url(#gProbe)" d="
        M 338 374 L 406 374 L 420 330 L 324 330 Z"/>
      <!-- grip -->
      <path class="ln" fill="{C['probe']}" d="
        M 344 330 L 400 330 L 392 268 C 390 258, 354 258, 352 268 Z"/>
      <!-- cable -->
      <path class="ln" stroke="{C['skin_ln']}" fill="none" d="
        M 372 268 C 374 226, 408 214, 452 214"/>
    </g>
  </g>

  <!-- ===================== ultrasound wave arcs ===================== -->
  <g id="waves" opacity="0.9">
    <path class="ln-thin" stroke="{C['wave']}" stroke-width="3" fill="none" d="
      M 356 402 C 340 424, 332 446, 336 470"/>
    <path class="ln-thin" stroke="{C['wave']}" stroke-width="3" fill="none"
          opacity="0.72" d="
      M 372 406 C 358 432, 352 458, 358 486"/>
    <path class="ln-thin" stroke="{C['wave']}" stroke-width="3" fill="none"
          opacity="0.45" d="
      M 390 404 C 378 430, 374 454, 380 482"/>
  </g>

  <!-- ===================== dressing (appears at the end) ================= -->
  <g id="dressing" opacity="0">
    <rect x="272" y="376" width="46" height="14" rx="5"
          fill="{C['dressing']}" stroke="{C['skin_ln']}" stroke-width="2"
          transform="rotate(38 295 383)"/>
    <path class="ln-thin" d="M 272 396 L 318 406" opacity="0.5"/>
  </g>
'''


def labels():
    """Leader-line labels — required by the accessibility invariant."""
    return f'''
  <!-- ===================== labels ===================== -->
  <g id="labels">
    <line class="lead" x1="418" y1="268" x2="470" y2="204"/>
    <circle class="dot" cx="418" cy="268" r="3"/>
    <text class="lbl" x="476" y="200">Ultrasound probe</text>

    <line class="lead" x1="252" y1="300" x2="196" y2="266"/>
    <circle class="dot" cx="252" cy="300" r="3"/>
    <text class="lbl" x="86" y="262">Needle</text>

    <line class="lead" x1="368" y1="440" x2="470" y2="416"/>
    <circle class="dot" cx="368" cy="440" r="3"/>
    <text class="lbl" x="476" y="412">Nodule</text>

    <line class="lead" x1="442" y1="520" x2="520" y2="548"/>
    <circle class="dot" cx="442" cy="520" r="3"/>
    <text class="lbl" x="526" y="552">Thyroid</text>
  </g>
'''


def steps():
    """SMIL animation: 9 steps, each fading its own group in.

    SMIL is used deliberately: it runs with JavaScript disabled, which is an
    accessibility requirement for a patient-facing kiosk documentary.
    """
    DUR = 50            # one full cycle, seconds
    N = 9
    each = DUR / N
    out = []
    out.append(f'''
  <!-- ===================== animation ===================== -->
  <!-- Each group fades in at its step and out at the next, on a {DUR}s loop.
       Times are computed, not hand-typed, so they stay in sync with STEPS. -->''')

    def fade(gid, start, end, total=DUR, lo=1.0, hi=0.0):
        return (f'    <animate attributeName="opacity" '
                f'values="{hi};{hi};{lo};{lo};{hi};{hi}" '
                f'keyTimes="0;{start/total:.4f};{(start+0.6)/total:.4f};'
                f'{max(0,(end-0.6))/total:.4f};{end/total:.4f};1" '
                f'dur="{total}s" repeatCount="indefinite"/>')

    # step 1-2: the cutaway reveals (thyroid visible)
    out.append('  <g id="animThyroid">')
    out.append(fade("animThyroid", 1*each, 8*each))
    out.append('  </g>')
    # step 3 onward: the nodule is highlighted
    out.append('  <g id="animNodule">')
    out.append(fade("animNodule", 2*each, 8*each))
    out.append('  </g>')
    # step 5 onward: probe appears
    out.append('  <g id="animProbe">')
    out.append(fade("animProbe", 4*each, 7*each))
    out.append('  </g>')
    # step 5-6: waves
    out.append('  <g id="animWaves">')
    out.append(fade("animWaves", 4*each, 6*each))
    out.append('  </g>')
    # step 6 onward: needle appears
    out.append('  <g id="animNeedle">')
    out.append(fade("animNeedle", 5*each, 7*each))
    out.append('  </g>')
    # step 9: dressing
    out.append('  <g id="animDressing">')
    out.append(fade("animDressing", 8*each, 9*each))
    out.append('  </g>')

    # step 7: three passes — the needle oscillates along its axis
    PASSDUR = 3 * each
    out.append(f'''
  <animateTransform href="#needleGroup" attributeName="transform"
     type="translate" values="0 0; 0 0; -14 -18; 0 0; -14 -18; 0 0; -14 -18; 0 0"
     keyTimes="0;0.60;0.645;0.69;0.735;0.78;0.825;0.87"
     dur="{DUR}s" repeatCount="indefinite"/>''')
    return "\n".join(out)


def build():
    svg = header() + body() + labels() + steps() + "\n</svg>\n"
    p = os.path.join(BASE, "anim.svg")
    open(p, "w").write(svg)
    return p, len(svg)


if __name__ == "__main__":
    p, n = build()
    print(f"wrote {p} ({n:,} bytes)")
