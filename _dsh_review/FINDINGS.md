# FNAC Webapp: state of `index.html`, 2026-10-11

Work done on the copy in this folder, which is byte-identical to the Duet build
(`/home/alex/Documents/FNAC_Webapp`) and to what was uploaded to the shared Drive folder
(`1ZazGhen6MJnuBa8cuuqKUvNV5DQoMaL0`, verified 372/372 files, 2026-10-11 01:22).

Nothing has been pushed to Duet or Drive. The Drive copy is still the broken one below.

## 1. The shipped file had no working 3D animation

`apply_review.py` wired a click handler to `#btnRotate`, an element that was never added to
the markup. That line throws before the renderer is created, so the initialiser aborts and
the stage stays an empty dark box in every step, on every device.

```
TypeError: Cannot set properties of null (setting 'onclick')
```

The canvas was still at its default 300x150 with zero pixels drawn. The file tested was md5
`4d412f98803222f40cbec32d4bc2f8ba`. `index.html.bak-prereview` has no `#btnRotate`
reference, so the review pass introduced the regression, and the reviewed file was uploaded
without ever being opened in a browser.

## 2. Mobile layout overflowed the viewport

`.stage` had `aspect-ratio` plus `min-height:320px`, and the `max-width:520px` rule switches
it to 4/3, so the 320px floor forced a 426px width. At a 390px viewport the whole page
overflowed and clipped on the right, including the step chips and the Play button.

Found and fixed. The stage is now 350px in a 390px viewport with no overflowing elements.

## 3. The v6 scene in the shipped file had never been seen, and is a regression

The same review edit replaced the whole scene builder with a "v6 human form" version, which
nobody could have viewed because the page threw first. `v5_vs_v6_scene.png` compares them
step for step: the previous builder reads as a neck cross section, the v6 one as a mannequin
bust with a black hair cap, protruding facial spheres and a flat disc for shoulders.

## 4. The scene now comes from the Blender model

`index.html` is rebuilt on the department's Blender model. The viscera in it are real
Z-Anatomy geometry: thyroid, trachea with cartilage rings, larynx, epiglottis, pharynx,
parathyroids and tongue. The probe, needle and dressing are the same authored instruments,
and the needle geometry is translated along its own axis until its tip sits in the nodule
(it stops about 5 cm short as exported).

Three defects in `model/fnac_scene.glb` had to be worked around, and they are worth knowing
because `viewer.html` still renders that file directly:

- **Its procedural body is in a different orientation from its anatomy.** The patient mesh
  is laid out supine along Z while the viscera form an upright neck along Y. The body mesh
  is therefore unusable as a skin surface and is discarded.
- **Its "skin" role is the two platysma sheets**, not a body surface, which is why the
  earlier viewer renders looked like a hanging sheet.
- **The exported needle does not reach the nodule marker**, despite
  `fnac_scene_report.json` recording `tip_inside_nodule: true` for the Blender scene.

The skin envelope is now derived from the viscera themselves: slice along the neck axis,
take the furthest vertex from the axis in each slice, smooth that radius and add a margin.
A hand-drawn profile was either too tight and let the gland poke through or too fat to read
as a neck.

`model/fnac_scene_web.glb` (1.2 MB) is the pruned model the page is built from: room,
clinician, face parts, platysma sheets and the supine body mesh are removed. It is inlined
into `index.html` as base64, so the leaflet is still one self-contained offline file, now
2.3 MB.

Verified in headless Chrome: canvas 958x598, nine step chips, seven labels, zero page
errors, text size cycling, contrast toggle and Play all working, no overflow at 390px.
Evidence: `after_glb_9steps.png`, `after_glb_step5_probe.png`, `after_glb_phone.png`.

## 5. Still open

- **Phone layout of the stage.** At 348x318 the scene labels collide with each other and
  with the step banner, and the colour legend is hidden below 520px, so the gland and nodule
  key is lost on the device most patients will use.
- **The dressing is hard to see** at the last step. It is present and visible, but it sits
  close to the skin surface and reads as a small pale patch.
- **The on-screen step text is a nine step variant** ("Your neck and head" ...) that matches
  neither `narration_en.json` nor `text_reviewed_current.json`, both of which hold a
  reviewed ten step script and are what `viewer.html` uses.
- **`audio/en/step_01..10.wav` is orphaned.** Nothing in `index.html` plays it, so the
  leaflet is silent.
- `assets/three.min.js`, used by `viewer.html`, is an older build than the three.js inlined
  in `index.html` (no `CapsuleGeometry`). Not a defect in itself, but the two pages do not
  share a rendering version.

## Files

| file | state |
|---|---|
| `index.html` | fixed and rebuilt on the GLB scene, 2.3 MB, self-contained |
| `index.html.bak-before-rotatefix` | the file exactly as shipped, for rollback |
| `index.html.bak-before-glbscene` | the three bug fixes with the old procedural scene |
| `model/fnac_scene_web.glb` | pruned model used by the build, kept for provenance |
| `_dsh_review/` | before and after screenshots |

`viewer.html`, the original GLB, the Blender scene and the build scripts were not touched.
