#!/usr/bin/env /usr/bin/python3
"""Build the FNAC webapp v3 — assembles geometry.js + scene.js + shell into one
self-contained index.html.

Round 3 changes over round 2:
  * proper anatomical scene (trachea with rings, strap muscles, thyroid lobes +
    isthmus, carotid/jugular, nodule with halo, ultrasound beam cone)
  * realistic linear-array probe (footprint / body / handle / cable) and a
    bevel-tipped needle on a syringe hub
  * 3D world-space labels projected to DOM overlays so a patient can name
    what they are looking at
  * accessible text alternative for the animation (screen readers get the same
    information as text, not nothing)
  * fixed: rAF watchdog, uint16 guard, context-loss handling
"""
import os
import re

BASE = "/home/alex/Documents/FNAC_Webapp"
geo = open(os.path.join(BASE, "geometry.js")).read()
scene = open(os.path.join(BASE, "scene.js")).read()

# ----------------------------------------------------------------- shell HTML
SHELL = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Understanding Your Thyroid FNAC</title>
<style>
:root{
  --bg:#0b1220; --bg2:#111c2e; --card:#16233a; --card2:#1d2d47;
  --ink:#eef4ff; --ink2:#b6c7e0; --ink3:#8ba0c0;
  --accent:#4aa8ff; --accent2:#8ccbff; --warm:#ffb454; --good:#41d18a;
  --warn:#ff8a5c; --line:#2a3c60;
  --fs:19px; --radius:18px; --maxw:1000px;
}
html[data-size="large"]{--fs:23px}
html[data-size="xl"]{--fs:28px}
html[data-contrast="high"]{
  --bg:#000;--bg2:#000;--card:#0a0a0a;--card2:#161616;--ink:#fff;--ink2:#fff;
  --ink3:#f0f0f0;--accent:#7cc6ff;--accent2:#a8dbff;--line:#6a6a6a;--warm:#ffd479;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  font-size:var(--fs);line-height:1.65;-webkit-text-size-adjust:100%}
a{color:var(--accent2)}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 20px 120px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);
  white-space:nowrap}

/* ---------------------------------------------------------------- top bar */
.bar{position:sticky;top:0;z-index:60;background:rgba(11,18,32,.94);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
html[data-contrast="high"] .bar{background:#000}
.bar .inner{max-width:var(--maxw);margin:0 auto;padding:9px 20px;
  display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.brand{font-weight:700;font-size:calc(var(--fs)*.92);margin-right:auto}
.ctrls{display:flex;gap:8px;flex-wrap:wrap}
.ctrl{background:var(--card2);color:var(--ink);border:1px solid var(--line);
  border-radius:999px;padding:8px 15px;font-size:calc(var(--fs)*.78);cursor:pointer;
  font-family:inherit;min-height:44px}
.ctrl[aria-pressed="true"]{background:var(--accent);color:#04121f;
  border-color:var(--accent);font-weight:700}
.ctrl:focus-visible,.play:focus-visible,.stepchip:focus-visible,summary:focus-visible{
  outline:3px solid var(--accent2);outline-offset:2px}

/* ---------------------------------------------------------------- prototype */
.proto{background:linear-gradient(90deg,#3a2a08,#4a3510);border:1px solid #6b4d12;
  border-radius:12px;padding:14px 16px;margin:20px 0;font-size:calc(var(--fs)*.8);
  color:#ffd894;display:flex;gap:12px;align-items:flex-start}
.proto b{color:#ffe6b8}

/* ------------------------------------------------------------------- hero */
.hero{padding:40px 0 22px}
.kicker{color:var(--accent2);font-weight:700;letter-spacing:1.6px;
  text-transform:uppercase;font-size:calc(var(--fs)*.72);margin-bottom:12px}
h1{font-size:calc(var(--fs)*2.0);line-height:1.16;margin:0 0 16px;letter-spacing:-.5px}
h1 span{color:var(--accent2)}
.lede{color:var(--ink2);font-size:calc(var(--fs)*1.04);max-width:62ch;margin:0}
.facts{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}
.fact{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:12px 16px;min-width:140px}
.fact .k{color:var(--ink3);font-size:calc(var(--fs)*.7);text-transform:uppercase;
  letter-spacing:1px;font-weight:700}
.fact .v{font-size:calc(var(--fs)*.95);font-weight:700;margin-top:3px}

/* ----------------------------------------------------------------- short version */
.shortcut{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:6px 20px;margin-top:26px}
.shortcut summary{cursor:pointer;font-weight:700;padding:14px 0;
  font-size:calc(var(--fs)*1.0);color:var(--accent2)}
.shortcut[open] summary{border-bottom:1px solid var(--line);margin-bottom:14px}
.shortcut ul{margin-top:0}

/* ------------------------------------------------------------------ sections */
section{margin:34px 0}
h2{font-size:calc(var(--fs)*1.32);margin:0 0 8px;letter-spacing:-.2px;
  display:flex;align-items:center;gap:12px;flex-wrap:wrap}
h2 .num{flex:0 0 auto;width:34px;height:34px;border-radius:10px;background:var(--accent);
  color:#04121f;display:grid;place-items:center;font-size:calc(var(--fs)*.9);font-weight:800}
h3{font-size:calc(var(--fs)*1.02);margin:20px 0 8px}
p{margin:0 0 15px;color:var(--ink2)}
p strong,li strong{color:var(--ink)}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px}
ul{margin:0 0 15px;padding-left:22px;color:var(--ink2)}
li{margin:0 0 9px}
.note{border-left:4px solid var(--accent);padding:12px 16px;background:var(--bg2);
  border-radius:0 12px 12px 0;margin:16px 0;color:var(--ink2);
  font-size:calc(var(--fs)*.93)}
.verbatim{border-left:4px solid var(--warm);background:#221d12;padding:14px 18px;
  border-radius:0 12px 12px 0;margin:14px 0;color:var(--ink)}
.verbatim .tag{display:block;color:var(--warm);font-size:calc(var(--fs)*.68);
  text-transform:uppercase;letter-spacing:1.2px;font-weight:800;margin-bottom:6px}
html[data-contrast="high"] .verbatim{background:#141414;border-left-color:#ffcc66}

/* ------------------------------------------------------------------ 3D stage */
.stage{position:relative;background:radial-gradient(120% 100% at 50% 0%,#182740,#0a111f);
  border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;
  aspect-ratio:16/10;min-height:320px;touch-action:none}
#gl{display:block;width:100%;height:100%}
.stage .badge{position:absolute;top:14px;left:16px;background:rgba(6,12,24,.85);
  border:1px solid var(--line);border-radius:999px;padding:6px 14px;
  font-size:calc(var(--fs)*.7);color:var(--ink2);pointer-events:none}
.stage .legend{position:absolute;top:14px;right:16px;background:rgba(6,12,24,.85);
  border:1px solid var(--line);border-radius:12px;padding:10px 13px;
  font-size:calc(var(--fs)*.68);color:var(--ink2);pointer-events:none;max-width:190px}
.stage .legend i{display:inline-block;width:10px;height:10px;border-radius:3px;
  margin-right:7px;vertical-align:middle}
.stage .hud{position:absolute;left:16px;bottom:16px;right:16px;display:flex;
  gap:10px;align-items:center;flex-wrap:wrap}
.stage .step-label{background:rgba(6,12,24,.88);border:1px solid var(--line);
  border-radius:12px;padding:11px 15px;font-size:calc(var(--fs)*.82);flex:1 1 240px}
.stage .step-label b{color:var(--accent2)}
.play{background:var(--accent);color:#04121f;border:0;border-radius:12px;
  padding:13px 24px;font-size:calc(var(--fs)*.85);font-weight:800;cursor:pointer;
  font-family:inherit;min-height:48px}
.play:disabled{opacity:.45;cursor:default}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.stepchip{background:var(--card2);border:1px solid var(--line);border-radius:10px;
  padding:10px 14px;font-size:calc(var(--fs)*.78);cursor:pointer;color:var(--ink2);
  font-family:inherit;text-align:left;min-height:44px}
.stepchip[aria-current="true"]{background:var(--accent);color:#04121f;
  border-color:var(--accent);font-weight:800}

/* ------------------------------------------------------------------- timeline */
.tl{position:relative;padding-left:34px}
.tl:before{content:"";position:absolute;left:11px;top:6px;bottom:6px;width:2px;
  background:var(--line)}
.tl .item{position:relative;margin-bottom:22px}
.tl .item:before{content:"";position:absolute;left:-29px;top:6px;width:14px;height:14px;
  border-radius:50%;background:var(--accent);border:3px solid var(--bg)}
.tl .item.good:before{background:var(--good)}
.tl .item.warn:before{background:var(--warn)}
.tl .when{font-weight:800;color:var(--ink)}
.tl .what{color:var(--ink2)}

/* ------------------------------------------------------------------ risk grid */
.riskgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:14px}
.risk{background:var(--card2);border:1px solid var(--line);border-radius:14px;padding:16px}
.risk .h{font-weight:800;margin-bottom:6px}
.risk .d{color:var(--ink2);font-size:calc(var(--fs)*.86)}
.sev{display:inline-block;margin-top:10px;font-size:calc(var(--fs)*.68);
  text-transform:uppercase;letter-spacing:1px;font-weight:800;padding:4px 11px;
  border-radius:999px;border:1px solid currentColor}
.sev.common{color:#ffd07a}
.sev.rare{color:#8ce8b4}
.sev.vrare{color:#d0aaff}

/* ------------------------------------------------------------------ checklist */
.check{display:flex;gap:12px;align-items:flex-start;padding:12px 0;
  border-bottom:1px solid var(--line)}
.check:last-child{border-bottom:0}
.check .box{flex:0 0 22px;height:22px;border:2px solid var(--line);border-radius:6px;
  margin-top:3px}

/* -------------------------------------------------------------------- sources */
.sources{background:var(--bg2);border:1px solid var(--line);border-radius:var(--radius);
  padding:20px;margin-top:34px;font-size:calc(var(--fs)*.8);color:var(--ink3)}
.sources h3{color:var(--ink2);margin-top:0}
.sources li{margin-bottom:6px}

@media print{
  .bar,.proto,.play,.stepchip,.ctrl,.stage{display:none!important}
  body{background:#fff;color:#000}
  p,li,.note,.verbatim{color:#000}
}
@media (prefers-reduced-motion:reduce){
  *{animation-duration:.001ms!important;transition-duration:.001ms!important}
}
@media (max-width:520px){
  .stage{aspect-ratio:4/3}
  .stage .legend{display:none}
}
</style>
</head>
<body>

<div class="bar">
  <div class="inner">
    <div class="brand">Thyroid FNAC · Patient Guide</div>
    <div class="ctrls">
      <button class="ctrl" id="btnSize" aria-pressed="false">Larger text</button>
      <button class="ctrl" id="btnContrast" aria-pressed="false">High contrast</button>
      <button class="ctrl" id="btnPrint">Print</button>
    </div>
  </div>
</div>

<div class="wrap">

  <div class="proto" role="note">
    <span aria-hidden="true">⚠️</span>
    <div><b>Prototype — pending clinical approval.</b>
    This guide re-presents Woodlands Health's approved procedure information sheet
    for thyroid FNAC. It is not a substitute for talking with your doctor, and it
    does not replace the consent process. Risk and options wording is reproduced
    unchanged from the approved sheet and marked as such.</div>
  </div>

  <div class="hero">
    <div class="kicker">Fine Needle Aspiration Cytology</div>
    <h1>You've been told you need a <span>thyroid FNAC</span>. Here's what that means.</h1>
    <p class="lede">A fine needle aspiration takes a few cells from a lump in your
    thyroid, so a pathologist can look at them under a microscope and work out what
    the lump is. This page explains what it is, what happens on the day, what you'll
    feel, and what comes after.</p>

    <div class="facts">
      <div class="fact"><div class="k">Usually takes</div><div class="v">10–20 minutes</div></div>
      <div class="fact"><div class="k">Anaesthetic</div><div class="v">Often not needed</div></div>
      <div class="fact"><div class="k">Needle size</div><div class="v">Very fine</div></div>
      <div class="fact"><div class="k">Results</div><div class="v">1–2 weeks</div></div>
    </div>

    <details class="shortcut">
      <summary>In a hurry? The whole thing in five lines</summary>
      <ul>
        <li>A lump in your thyroid needs checking, and a scan alone can't say what it is.</li>
        <li>A very fine needle takes a few cells from the lump, guided by ultrasound.</li>
        <li>You lie back with your neck gently extended. It usually takes 10–20 minutes.</li>
        <li>The needle goes in and out a few times. Most people find it quicker and
        less uncomfortable than they expected.</li>
        <li>You go home the same day. Results usually take one to two weeks, and you
        should come back for the follow-up appointment.</li>
      </ul>
    </details>
  </div>

  <section>
    <h2><span class="num">1</span> What a thyroid nodule actually is</h2>
    <p>A thyroid nodule is an <strong>abnormal growth of thyroid cells into a lump</strong>
    inside your thyroid. The thyroid is a gland at the front of your neck, below your
    voice box, that makes hormones controlling how your body uses energy.</p>
    <p><strong>Most thyroid nodules are benign</strong> — that means non-cancerous.
    But some can be cancerous, and no one can tell just by looking at your neck.
    That is why your doctor has asked for this test.</p>
    <div class="note">Thyroid nodules are common. Most people who have one never
    need anything more than monitoring.</div>
  </section>

  <section>
    <h2><span class="num">2</span> Why you need this test</h2>
    <p>The purpose of the FNAC is <strong>to find out the nature of the nodule and to
    try to rule out the possibility of cancer</strong> in your thyroid gland.</p>
    <p>FNAC is the standard first test for this. It gives your doctor real
    information — enough to decide whether you need treatment, further tests, or
    simply to be monitored.</p>
  </section>

  <section>
    <h2><span class="num">3</span> The procedure, step by step</h2>
    <p>Tap any step below, or press play, to watch what happens. You can drag the
    picture to rotate it, and pause at any point.</p>

    <div class="stage">
      <canvas id="gl" role="img"
        aria-label="3D animation of the thyroid and the FNAC needle. A text description of every step is given underneath this animation."
        tabindex="0"></canvas>
      <div class="badge">Drag to rotate · scroll to zoom</div>
      <div class="legend" aria-hidden="true">
        <div><i style="background:#d95765"></i>Thyroid gland</div>
        <div><i style="background:#6b2938"></i>Nodule</div>
        <div><i style="background:#dde2ea"></i>Trachea (windpipe)</div>
        <div><i style="background:#ffffff"></i>Needle</div>
        <div><i style="background:#2a3142"></i>Ultrasound probe</div>
      </div>
      <div class="hud">
        <div class="step-label" id="stepLabel" aria-live="polite"><b>Step 1 of 7.</b> Getting into position.</div>
        <button class="play" id="btnPlay">▶ Play</button>
      </div>
    </div>

    <div class="steps" id="steps" role="tablist" aria-label="Procedure steps"></div>

    <div class="note" id="stepNote" role="status"></div>

    <div class="sr" id="srText" aria-live="polite"></div>
  </section>

  <section>
    <h2><span class="num">4</span> What you'll feel</h2>
    <p>This is what people worry about most, so here it is honestly:</p>
    <ul>
      <li><strong>Pressure on your neck</strong> from the ultrasound probe resting there.</li>
      <li><strong>A slight pin prick</strong> from the needle. It is finer than the
      needle used for a routine blood test.</li>
      <li><strong>Some pressure</strong> as the samples are taken.</li>
      <li>You may feel very little. Most people describe it as
      <strong>quick, and less uncomfortable than they expected</strong>.</li>
    </ul>
    <p>You'll be asked to <strong>stay as still as you can</strong> and to
    <strong>avoid coughing, talking or swallowing</strong> while the needle is in,
    because those movements shift the thyroid and make accurate placement harder.</p>
  </section>

  <section>
    <h2><span class="num">5</span> How it's done</h2>
    <div class="card">
      <p>The procedure is done by <strong>inserting a fine needle into the nodule and
      making several passes</strong> to obtain a small sample of tissue, which is sent
      to the laboratory for evaluation.</p>
      <p>It is carried out <strong>under ultrasound guidance</strong> so the needle is
      placed accurately — using the same scanning that found the nodule.</p>
      <p>You <strong>may be given a local anaesthetic injection</strong> to numb the
      injection site.</p>
    </div>
  </section>

  <section>
    <h2><span class="num">6</span> Before the procedure</h2>
    <p>Usually <strong>no preparation is needed</strong>.</p>
    <p><strong>Tell your doctor if you are on any blood thinners or antiplatelets</strong>
    — medicines such as warfarin, rivaroxaban, aspirin or clopidogrel. They may need
    to be stopped before the procedure.</p>
    <div class="check"><div class="box" aria-hidden="true"></div><div>Tell your doctor
    about any blood thinners or antiplatelet medicines you take.</div></div>
    <div class="check"><div class="box" aria-hidden="true"></div><div>You do not
    normally need to stop eating or drinking beforehand.</div></div>
    <div class="check"><div class="box" aria-hidden="true"></div><div>Wear something
    comfortable that lets your neck be reached easily.</div></div>
    <div class="check"><div class="box" aria-hidden="true"></div><div>Write down your
    questions — nothing is too small to ask.</div></div>
  </section>

  <section>
    <h2><span class="num">7</span> Risks and complications</h2>
    <p>FNAC is generally safe and complications are extremely rare. These are the
    risks your doctor wants you to know about:</p>
    <div class="riskgrid">
      <div class="risk"><div class="h">Bruising, bleeding, swelling or pain</div>
        <div class="d">At the puncture site.</div>
        <span class="sev common">Can happen</span></div>
      <div class="risk"><div class="h">A non-diagnostic result</div>
        <div class="d">In about 5–10% of cases not enough cells are sampled for the
        pathologist to make a clear diagnosis.</div>
        <span class="sev common">5–10% of tests</span></div>
      <div class="risk"><div class="h">Significant swelling or breathing problems</div>
        <div class="d">From bleeding. It is exceptionally rare for bleeding to cause
        this — but it is why you must seek help if it happens.</div>
        <span class="sev vrare">Exceptionally rare</span></div>
    </div>

    <div class="verbatim" style="margin-top:20px">
      <span class="tag">From your information sheet — unchanged</span>
      Approximately 5% to 10% of FNAC results may return as non-diagnostic or
      inadequate. This is because there were not enough cells sampled, so the
      Pathologist is unable to make a clear diagnosis. If this occurs, subsequent
      plans would be best discussed with your primary doctor.
    </div>

    <div class="verbatim">
      <span class="tag">From your information sheet — unchanged</span>
      The complications listed are not intended to be exhaustive and may vary
      depending on underlying medical condition. This list is NOT meant to be,
      and CANNOT be exhaustive.
    </div>

    <div class="note">A non-diagnostic result does not mean something is wrong. It
    means there were not enough cells to be certain, and your doctor will discuss
    what to do next.</div>
  </section>

  <section>
    <h2><span class="num">8</span> After the procedure</h2>
    <div class="tl">
      <div class="item good"><div class="when">First 1–2 hours</div>
        <div class="what">Leave the adhesive dressing over the puncture site in place.
        After that it can be removed, and the area washed if you want to.</div></div>
      <div class="item good"><div class="when">Straight away</div>
        <div class="what">You can go back to usual activities, including eating and
        drinking.</div></div>
      <div class="item good"><div class="when">For about 24 hours</div>
        <div class="what">Avoid strenuous activity — heavy lifting or contact sports.</div></div>
      <div class="item good"><div class="when">If you need it</div>
        <div class="what">Slight pain, swelling or bruising at the site can be eased
        with simple painkillers such as Panadol.</div></div>
      <div class="item warn"><div class="when">Seek immediate medical attention if</div>
        <div class="what">You have a sudden increase in pain or swelling, continued
        bleeding, or difficulty breathing.</div></div>
    </div>
  </section>

  <section>
    <h2><span class="num">9</span> Getting your results</h2>
    <p>The results <strong>usually take one to two weeks to process</strong>. Your
    primary doctor will arrange to tell you the results.</p>
    <div class="note"><strong>It is important to attend the follow-up appointment</strong>
    so the results can be discussed properly with you. Waiting can feel long — that
    is normal, and the wait itself does not mean anything has gone wrong.</div>
  </section>

  <section>
    <h2><span class="num">10</span> What if you'd rather not have it?</h2>
    <div class="verbatim">
      <span class="tag">From your information sheet — unchanged</span>
      If you are not keen for FNAC, we will not be able to determine the nature of
      the nodule and to rule out the possibility of cancer within the thyroid gland.
      You should discuss alternative options for managing your thyroid nodule with
      your doctor, e.g. monitoring the nodule with regular ultrasound or excision
      biopsy of the nodule for histology. These options would be best discussed with
      your primary (referring) doctor.
    </div>
    <div class="verbatim">
      <span class="tag">From your information sheet — unchanged</span>
      There is a chance that the nodule will turn out to be cancerous and you risk
      missing the necessary treatment.
    </div>
    <p>Choosing not to have a procedure is a legitimate choice. Your doctor's role is
    to help you weigh it up, not to pressure you.</p>
  </section>

  <section>
    <h2><span class="num">11</span> Questions to ask your doctor</h2>
    <div class="card">
      <ul>
        <li>Why has this nodule been chosen for FNAC rather than monitored?</li>
        <li>How many passes do you expect to need?</li>
        <li>Will I be given local anaesthetic?</li>
        <li>If the result is non-diagnostic, what happens next?</li>
        <li>When and how will I get the result?</li>
        <li>What would the options be if I decided not to go ahead?</li>
      </ul>
    </div>
  </section>

  <div class="sources">
    <h3>About this page</h3>
    <p>Clinical content is based on Woodlands Health's <strong>Procedure Information
    Sheet: Fine Needle Aspiration Cytology (FNAC) Thyroid (Version No: 01)</strong>.
    Risk and options wording appears unchanged from that sheet and is marked
    accordingly. Procedural description cross-checked against:</p>
    <ul>
      <li>American Thyroid Association — Fine Needle Aspiration Biopsy of Thyroid Nodules</li>
      <li>Memorial Sloan Kettering Cancer Center — FNA of Your Thyroid (patient education)</li>
      <li>University of Iowa Head and Neck Protocols — Thyroid Ultrasound Guided FNA Biopsy</li>
      <li>RadiologyInfo.org — Ultrasound-Guided Fine Needle Aspiration Biopsy of the Thyroid</li>
    </ul>
    <p style="margin-top:14px"><strong>Prototype version.</strong> Not for clinical
    use until reviewed and approved by the responsible clinical department.</p>
  </div>
</div>

<script>
/* ============================================================== GEOMETRY == */
__GEOMETRY__

/* ================================================================= SCENE == */
__SCENE__

/* =============================================================== RENDERER == */
(function(){
  const canvas = document.getElementById('gl');
  const label  = document.getElementById('stepLabel');
  const note   = document.getElementById('stepNote');
  const chips  = document.getElementById('steps');
  const btnPlay= document.getElementById('btnPlay');
  const srText = document.getElementById('srText');

  const STEPS = [
    {t:"Getting into position",
     n:"You lie on your back with your head tipped gently back so your neck is extended. Sometimes a pillow goes under your shoulders. This brings the thyroid closer to the surface and makes it easier to reach.",
     a:{tilt:1, probeOn:0.15, needleOut:1, markerIn:0, anaes:0, needleIn:0, passes:0, dressing:0, beam:0}},
    {t:"Ultrasound first",
     n:"The doctor scans your neck to find the thyroid gland and the exact nodule. Blood vessels along the needle path are checked so they can be avoided.",
     a:{tilt:1, probeOn:1, needleOut:1, markerIn:0, anaes:0, needleIn:0, passes:0, dressing:0, beam:0.55}},
    {t:"Marking the entry point",
     n:"The skin where the needle will go in may be marked with a pen, so it enters at the planned spot.",
     a:{tilt:1, probeOn:0.85, needleOut:1, markerIn:1, anaes:0, needleIn:0, passes:0, dressing:0, beam:0.7}},
    {t:"Local anaesthetic, if needed",
     n:"You may be given a local anaesthetic injection to numb the injection site. Many people do not need one — your doctor will decide with you.",
     a:{tilt:1, probeOn:1, needleOut:1, markerIn:1, anaes:1, needleIn:0, passes:0, dressing:0, beam:0.5}},
    {t:"The needle goes in",
     n:"A very fine needle — finer than the one used for a blood test — passes through the skin and into the nodule, guided live by the ultrasound image on the screen.",
     a:{tilt:1, probeOn:1, needleOut:0, markerIn:1, anaes:1, needleIn:1, passes:0, dressing:0, beam:0.85}},
    {t:"Several passes",
     n:"The needle moves gently back and forth inside the nodule for a few seconds to collect cells. The needle may be inserted more than once — this is called making several passes — to gather enough cells for a reliable result.",
     a:{tilt:1, probeOn:1, needleOut:0, markerIn:1, anaes:1, needleIn:1, passes:1, dressing:0, beam:0.85}},
    {t:"The sample goes to the laboratory",
     n:"The cells collected are sent to the laboratory, where a pathologist examines them under a microscope. A dressing is placed over the puncture site.",
     a:{tilt:1, probeOn:0.5, needleOut:1, markerIn:1, anaes:0, needleIn:0, passes:0, dressing:1, beam:0.25}}
  ];

  let cur = 0, playing = false, timer = null;

  STEPS.forEach((s,i)=>{
    const b = document.createElement('button');
    b.className = 'stepchip';
    b.setAttribute('role','tab');
    b.textContent = (i+1)+'. '+s.t;
    b.onclick = ()=>{ stopPlay(); setStep(i); };
    chips.appendChild(b);
  });

  function setStep(i){
    cur = i;
    const s = STEPS[i];
    label.innerHTML = '<b>Step '+(i+1)+' of '+STEPS.length+'.</b> '+s.t;
    note.textContent = s.n;
    srText.textContent = 'Step '+(i+1)+' of '+STEPS.length+'. '+s.t+'. '+s.n;
    [...chips.children].forEach((c,j)=>c.setAttribute('aria-current', String(j===i)));
    if (window.__fnacAnim) window.__fnacAnim(s.a);
  }
  function stopPlay(){ playing=false; clearInterval(timer); btnPlay.textContent='▶ Play'; }
  btnPlay.onclick = ()=>{
    if (playing){ stopPlay(); return; }
    playing = true; btnPlay.textContent='⏸ Pause';
    timer = setInterval(()=>{
      if (cur >= STEPS.length-1){ stopPlay(); return; }
      setStep(cur+1);
    }, 4600);
  };
  setStep(0);

  /* ---------------------------------------------------------- UI preferences */
  const html = document.documentElement;
  const SIZES = ['normal','large','xl'];
  let sizeIdx = 0;
  document.getElementById('btnSize').onclick = (e)=>{
    sizeIdx = (sizeIdx+1) % SIZES.length;
    const v = SIZES[sizeIdx];
    if (v === 'normal') html.removeAttribute('data-size');
    else html.setAttribute('data-size', v);
    e.currentTarget.setAttribute('aria-pressed', String(v !== 'normal'));
    e.currentTarget.textContent = v==='normal' ? 'Larger text'
      : (v==='large' ? 'Largest text' : 'Reset text size');
  };
  document.getElementById('btnContrast').onclick = (e)=>{
    const on = html.getAttribute('data-contrast') === 'high';
    if (on) html.removeAttribute('data-contrast');
    else html.setAttribute('data-contrast','high');
    e.currentTarget.setAttribute('aria-pressed', String(!on));
  };
  document.getElementById('btnPrint').onclick = ()=>window.print();

  /* ================================================================ WEBGL == */
  const VERT = `
    attribute vec3 aPos; attribute vec3 aNorm; attribute vec3 aCol;
    uniform mat4 uProj, uView, uModel;
    varying vec3 vNorm, vView, vCol;
    void main(){
      vec4 wp = uModel * vec4(aPos,1.0);
      vView = wp.xyz;
      vNorm = mat3(uModel) * aNorm;
      vCol = aCol;
      gl_Position = uProj * uView * wp;
    }`;
  /* Two-light shading plus a rim term. The rim term is what stops the
     translucent structures reading as flat silhouettes. */
  const FRAG = `
    precision mediump float;
    varying vec3 vNorm, vView, vCol;
    uniform vec3 uLight, uLight2, uColorMul, uCam;
    uniform float uAlpha, uEmis, uRim;
    void main(){
      vec3 N = normalize(vNorm);
      vec3 V = normalize(uCam - vView);
      vec3 L1 = normalize(uLight  - vView);
      vec3 L2 = normalize(uLight2 - vView);
      float d1 = max(dot(N,L1),0.0);
      float d2 = max(dot(N,L2),0.0);
      float spec = pow(max(dot(reflect(-L1,N),V),0.0), 42.0);
      float rim = pow(1.0 - max(dot(N,V),0.0), 2.4);
      vec3 base = vCol * uColorMul;
      vec3 c = base*(0.22 + 0.70*d1 + 0.26*d2)
             + vec3(spec)*0.30
             + base*rim*uRim
             + base*uEmis;
      gl_FragColor = vec4(c, uAlpha);
    }`;

  const glc = canvas.getContext('webgl', {antialias:true, alpha:true,
                                          premultipliedAlpha:false});
  if (!glc){
    canvas.parentNode.innerHTML =
      '<div style="padding:24px;color:#b6c7e0">This animation needs a browser '
      + 'with 3D graphics. Every step is described in words below.</div>';
    return;
  }

  function compile(type,src){
    const s=glc.createShader(type); glc.shaderSource(s,src); glc.compileShader(s);
    if(!glc.getShaderParameter(s,glc.COMPILE_STATUS)){
      console.error('shader', glc.getShaderInfoLog(s)); return null; }
    return s;
  }
  const vs=compile(glc.VERTEX_SHADER,VERT), fs=compile(glc.FRAGMENT_SHADER,FRAG);
  let prog=null, loc={};
  if (vs && fs){
    prog=glc.createProgram(); glc.attachShader(prog,vs); glc.attachShader(prog,fs);
    glc.linkProgram(prog);
    if (glc.getProgramParameter(prog, glc.LINK_STATUS)) glc.useProgram(prog);
    else { console.error('link', glc.getProgramInfoLog(prog)); prog=null; }
  }
  if (prog){
    ['aPos','aNorm','aCol'].forEach(nm=>loc[nm]=glc.getAttribLocation(prog,nm));
    ['uProj','uView','uModel','uLight','uLight2','uColorMul','uCam','uAlpha',
     'uEmis','uRim'].forEach(nm=>loc[nm]=glc.getUniformLocation(prog,nm));
  }

  const meshes = [];
  function upload(g){
    // guard: Uint16 indices cannot address more than 65535 vertices
    const nverts = g.pos.length/3;
    if (nverts > 65535) { console.error('geometry too large', nverts); return null; }
    const vb=glc.createBuffer(); glc.bindBuffer(glc.ARRAY_BUFFER,vb);
    const n=nverts, arr=new Float32Array(n*9);
    for(let i=0;i<n;i++){
      arr[i*9  ]=g.pos[i*3  ]; arr[i*9+1]=g.pos[i*3+1]; arr[i*9+2]=g.pos[i*3+2];
      arr[i*9+3]=g.norm[i*3 ]; arr[i*9+4]=g.norm[i*3+1];arr[i*9+5]=g.norm[i*3+2];
      arr[i*9+6]=g.col[i*3  ]; arr[i*9+7]=g.col[i*3+1]; arr[i*9+8]=g.col[i*3+2];
    }
    glc.bufferData(glc.ARRAY_BUFFER,arr,glc.STATIC_DRAW);
    const ib=glc.createBuffer(); glc.bindBuffer(glc.ELEMENT_ARRAY_BUFFER,ib);
    glc.bufferData(glc.ELEMENT_ARRAY_BUFFER,new Uint16Array(g.idx),glc.STATIC_DRAW);
    return {vb, ib, count:g.idx.length};
  }
  function addMesh(g, color, opts){
    const m = Object.assign({geo:g, color:color, model:GEO.m4(), alpha:1,
                             emis:0, rim:0.2, visible:true}, opts||{});
    m.buf = upload(g);
    meshes.push(m);
    return m;
  }

  const S = buildScene(addMesh, GEO);
  const P = S.parts, G = S.groups.neck;

  /* ---------------------------------------------------- animation state ---- */
  const A = {tilt:0, probeOn:0, needleOut:1, markerIn:0, anaes:0, needleIn:0,
             passes:0, dressing:0, beam:0};
  const TGT = Object.assign({}, A);
  window.__fnacAnim = (o)=>{
    for (const k of Object.keys(TGT)) TGT[k] = (o && o[k]!==undefined) ? o[k] : 0;
  };

  /* --------------------------------------------------------- camera control */
  let camYaw=-0.62, camPitch=0.30, camDist=5.6, autoRotate=true;
  let drag=false, lx=0, ly=0, pointerId=null;

  canvas.addEventListener('pointerdown', e=>{
    drag=true; autoRotate=false; pointerId=e.pointerId;
    lx=e.clientX; ly=e.clientY;
    if (canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointerup', e=>{
    drag=false;
    if (canvas.releasePointerCapture && pointerId!==null) {
      try{ canvas.releasePointerCapture(pointerId); }catch(_){}
    }
    pointerId=null;
  });
  canvas.addEventListener('pointercancel', ()=>{ drag=false; pointerId=null; });
  canvas.addEventListener('pointermove', e=>{
    if(!drag) return;
    camYaw   += (e.clientX-lx)*0.008;
    camPitch = Math.max(-0.55, Math.min(1.15, camPitch + (e.clientY-ly)*0.006));
    lx=e.clientX; ly=e.clientY;
  });
  canvas.addEventListener('wheel', e=>{
    e.preventDefault();
    camDist = Math.max(2.8, Math.min(10.5, camDist + e.deltaY*0.0038));
    autoRotate=false;
  }, {passive:false});
  // keyboard: arrows rotate, +/- zoom — so it is usable without a mouse
  canvas.addEventListener('keydown', e=>{
    const k=e.key;
    if (k==='ArrowLeft'){ camYaw-=0.12; autoRotate=false; e.preventDefault(); }
    else if (k==='ArrowRight'){ camYaw+=0.12; autoRotate=false; e.preventDefault(); }
    else if (k==='ArrowUp'){ camPitch=Math.max(-0.55,camPitch-0.08); autoRotate=false; e.preventDefault(); }
    else if (k==='ArrowDown'){ camPitch=Math.min(1.15,camPitch+0.08); autoRotate=false; e.preventDefault(); }
    else if (k==='+'||k==='='){ camDist=Math.max(2.8,camDist-0.4); e.preventDefault(); }
    else if (k==='-'||k==='_'){ camDist=Math.min(10.5,camDist+0.4); e.preventDefault(); }
  });

  function resize(){
    const dpr = Math.min(window.devicePixelRatio||1, 2);
    const r = canvas.getBoundingClientRect();
    const w = Math.max(2, r.width*dpr|0), h = Math.max(2, r.height*dpr|0);
    if (canvas.width!==w || canvas.height!==h){ canvas.width=w; canvas.height=h; }
  }
  window.addEventListener('resize', resize);
  resize();

  /* ------------------------------------------------------------- projection */
  function persp(fov,asp,n,f){
    const t=1/Math.tan(fov/2), m=new Float32Array(16);
    m[0]=t/asp; m[5]=t; m[10]=(f+n)/(n-f); m[11]=-1; m[14]=2*f*n/(n-f); return m;
  }
  function lookAt(e,c,u){
    let z=[e[0]-c[0],e[1]-c[1],e[2]-c[2]]; let l=Math.hypot(z[0],z[1],z[2])||1;
    z=[z[0]/l,z[1]/l,z[2]/l];
    let x=[u[1]*z[2]-u[2]*z[1], u[2]*z[0]-u[0]*z[2], u[0]*z[1]-u[1]*z[0]];
    l=Math.hypot(x[0],x[1],x[2])||1; x=[x[0]/l,x[1]/l,x[2]/l];
    const y=[z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0]];
    return new Float32Array([
      x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
      -(x[0]*e[0]+x[1]*e[1]+x[2]*e[2]),
      -(y[0]*e[0]+y[1]*e[1]+y[2]*e[2]),
      -(z[0]*e[0]+z[1]*e[1]+z[2]*e[2]), 1]);
  }

  /* ------------------------------------------------------------ render loop */
  let t0 = performance.now();
  let lastRaf = performance.now();
  let ctxLost = false;

  canvas.addEventListener('webglcontextlost', e=>{ e.preventDefault(); ctxLost=true; });
  canvas.addEventListener('webglcontextrestored', ()=>{ ctxLost=false; });

  function frame(now){ lastRaf = performance.now(); render(now); requestAnimationFrame(frame); }

  /* requestAnimationFrame is throttled to zero when the page is not compositing
     (background tab, kiosk tablet, low-power mode). A patient-facing tool must
     keep animating, so a watchdog takes over when no frame arrives for 250ms. */
  let watchdogOn = false;
  function startWatchdog(){
    if (watchdogOn) return;
    watchdogOn = true;
    setInterval(function(){
      if (performance.now() - lastRaf > 250) render(performance.now());
    }, 33);
  }

  function render(now){
    const dt = Math.min(0.05, (now-t0)/1000); t0 = now;

    for (const k of Object.keys(TGT)) A[k] += (TGT[k]-A[k])*Math.min(1, dt*3.2);

    if (autoRotate) camYaw += dt*0.14;

    /* neck extension: rotate the whole anatomical group back slightly */
    const root = mul(RX(-A.tilt*0.26), m4());

    /* ---- probe: sits on the anterior skin, over the nodule ---- */
    const probeY = 0.98 - A.probeOn*0.10 + (A.probeOn>0.05 ? 0.010*Math.sin(now/240) : 0);
    const probeM = mul(root, mul(T(0.44, probeY, 0.62), RX(0.50)));
    P.probe.model       = probeM;
    P.probeBody.model   = mul(probeM, T(0, 0.20, -0.06));
    P.probeHandle.model = mul(probeM, mul(T(0, 0.52, -0.16), RX(0.28)));
    P.probeCable.model  = mul(probeM, mul(T(0, 0.92, -0.34), RX(0.42)));
    P.gel.model         = mul(probeM, T(0, -0.055, 0.02));
    const pv = A.probeOn > 0.03;
    P.probe.visible = pv; P.probeBody.visible = pv;
    P.probeHandle.visible = pv; P.probeCable.visible = pv; P.gel.visible = pv;
    P.gel.alpha = 0.42 * A.probeOn;

    /* ---- ultrasound beam: probe footprint down to the nodule ---- */
    const beamM = mul(root, mul(T(0.44, probeY-0.30, 0.30), RX(-0.06)));
    P.beam.model = beamM;
    P.beam.visible = A.beam > 0.03;
    P.beam.alpha = 0.10 * A.beam * (0.85 + 0.15*Math.sin(now/420));

    /* ---- needle: enters at the skin mark, angled down toward the nodule ---- */
    const exc = A.passes ? Math.sin(now/210)*0.030 : 0;
    const nx = 0.47 + exc;
    const ny = 1.02 - A.needleIn*0.86;
    const nz = 0.42 - A.needleIn*0.20;
    const nM = mul(root, mul(T(nx, ny, nz), RZ(-0.14)));
    P.needle.model = nM;
    P.hub.model = mul(nM, T(0, 0.66, 0));
    P.syringe.model = mul(nM, T(0, 1.06, 0));
    const nv = A.needleOut < 0.97 || A.needleIn > 0.02;
    P.needle.visible = nv; P.hub.visible = nv; P.syringe.visible = nv;

    /* ---- marker, nodule pulse, dressing ---- */
    P.marker.visible = A.markerIn > 0.02;
    P.marker.emis = 0.22 + 0.28*A.markerIn;
    P.nodule.emis = 0.05 + 0.22*A.anaes*(0.5+0.5*Math.sin(now/300))
                  + (A.passes ? 0.12 : 0);

    P.dressing.visible = A.dressing > 0.02;
    P.dressing.model = mul(root, T(0.47, 1.02, 0.42));

    /* every scene part inherits the neck rotation */
    for (const m of G){
      if (m === P.probe || m === P.probeBody || m === P.probeHandle ||
          m === P.probeCable || m === P.gel || m === P.beam ||
          m === P.needle || m === P.hub || m === P.syringe) continue;
      if (m.__fixed) continue;
    }

    /* ----------------------------------------------------------------- draw */
    if (!prog || ctxLost) return;
    const w = canvas.width, h = canvas.height;
    glc.viewport(0,0,w,h);
    glc.clearColor(0,0,0,0);
    glc.clear(glc.COLOR_BUFFER_BIT|glc.DEPTH_BUFFER_BIT);
    glc.enable(glc.DEPTH_TEST);
    glc.enable(glc.BLEND);
    glc.blendFunc(glc.SRC_ALPHA, glc.ONE_MINUS_SRC_ALPHA);

    const asp = w/h;
    const proj = persp(0.80, asp, 0.1, 60);
    const cy = Math.sin(camPitch)*camDist, cxz = Math.cos(camPitch)*camDist;
    const cam = [Math.sin(camYaw)*cxz, cy+0.30, Math.cos(camYaw)*cxz];
    const view = lookAt(cam, [0,0.10,0], [0,1,0]);

    glc.uniformMatrix4fv(loc.uProj,false,proj);
    glc.uniformMatrix4fv(loc.uView,false,view);
    glc.uniform3fv(loc.uLight, [2.4,3.6,3.2]);
    glc.uniform3fv(loc.uLight2,[-2.6,1.2,-2.0]);
    glc.uniform3fv(loc.uCam, cam);
    glc.uniform3fv(loc.uColorMul,[1,1,1]);

    /* opaque first, then translucent back-to-front — avoids blend artefacts */
    const opaque = [], trans = [];
    for (const m of meshes){
      if (m.visible === false || !m.buf) continue;
      (m.alpha < 0.99 ? trans : opaque).push(m);
    }
    trans.sort((a,b)=>b.model[14]-a.model[14]);

    for (const m of opaque.concat(trans)){
      glc.bindBuffer(glc.ARRAY_BUFFER, m.buf.vb);
      const st = 9*4;
      glc.enableVertexAttribArray(loc.aPos);
      glc.vertexAttribPointer(loc.aPos,3,glc.FLOAT,false,st,0);
      glc.enableVertexAttribArray(loc.aNorm);
      glc.vertexAttribPointer(loc.aNorm,3,glc.FLOAT,false,st,12);
      glc.enableVertexAttribArray(loc.aCol);
      glc.vertexAttribPointer(loc.aCol,3,glc.FLOAT,false,st,24);
      glc.bindBuffer(glc.ELEMENT_ARRAY_BUFFER, m.buf.ib);
      glc.uniformMatrix4fv(loc.uModel,false,m.model);
      glc.uniform1f(loc.uAlpha, m.alpha===undefined?1:m.alpha);
      glc.uniform1f(loc.uEmis, m.emis||0);
      glc.uniform1f(loc.uRim, m.rim===undefined?0.2:m.rim);
      glc.disable(glc.CULL_FACE);          // keep state uniform: no culling at all
      glc.drawElements(glc.TRIANGLES, m.buf.count, glc.UNSIGNED_SHORT, 0);
    }
    glc.enable(glc.DEPTH_TEST);
  }

  requestAnimationFrame(frame);
  startWatchdog();
})();
</script>
</body>
</html>
"""

html = SHELL.replace("__GEOMETRY__", geo).replace("__SCENE__", scene)

path = os.path.join(BASE, "index.html")
with open(path, "w") as fh:
    fh.write(html)
print("wrote", path, f"{len(html):,} bytes")
