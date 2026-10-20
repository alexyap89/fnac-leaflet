#!/usr/bin/env /usr/bin/python3
"""Build the FNAC thyroid patient education webapp as a single self-contained HTML file.

Design basis:
  * Clinical content: WH "Procedure Information Sheet: FNAC Thyroid (Version No: 01)"
    -- paraphrased only where plain language clearly preserves meaning; all RISK
    and OPTION wording kept verbatim from the approved sheet.
  * Procedure detail cross-checked against ATA, MSKCC, and University of Iowa
    head-and-neck protocols (see SOURCES at the foot of the page).

No external assets, no network calls, no patient data. Works offline on a
hospital tablet.
"""
import os

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Understanding Your Thyroid FNAC</title>
<style>
:root{
  --bg:#0b1220; --bg2:#111c2e; --card:#16233a; --card2:#1d2d47;
  --ink:#eef4ff; --ink2:#a9bcd8; --ink3:#7d92b3;
  --accent:#4aa8ff; --accent2:#7cc4ff; --warm:#ffb454; --good:#41d18a;
  --warn:#ff8a5c; --line:#26375a;
  --fs:18px; --radius:18px; --maxw:980px;
}
html[data-size="large"]{--fs:22px}
html[data-size="xl"]{--fs:27px}
html[data-contrast="high"]{
  --bg:#000;--bg2:#000;--card:#0a0a0a;--card2:#141414;--ink:#fff;--ink2:#fff;
  --ink3:#e8e8e8;--accent:#6fc0ff;--accent2:#9fd6ff;--line:#5a5a5a;--warm:#ffcc66;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  font-size:var(--fs);line-height:1.62;-webkit-text-size-adjust:100%}
a{color:var(--accent2)}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 20px 120px}

/* ---------- top bar ---------- */
.bar{position:sticky;top:0;z-index:50;background:rgba(11,18,32,.92);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
html[data-contrast="high"] .bar{background:#000}
.bar .inner{max-width:var(--maxw);margin:0 auto;padding:10px 20px;
  display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{font-weight:700;letter-spacing:.2px;font-size:calc(var(--fs)*.95);margin-right:auto}
.ctrls{display:flex;gap:8px;flex-wrap:wrap}
.ctrl{background:var(--card2);color:var(--ink);border:1px solid var(--line);
  border-radius:999px;padding:7px 14px;font-size:calc(var(--fs)*.78);cursor:pointer;
  font-family:inherit;min-height:40px}
.ctrl[aria-pressed="true"]{background:var(--accent);color:#04121f;border-color:var(--accent);font-weight:700}
.ctrl:hover{border-color:var(--accent)}

/* ---------- prototype flag ---------- */
.proto{background:linear-gradient(90deg,#3a2a08,#4a3510);border:1px solid #6b4d12;
  border-radius:12px;padding:14px 16px;margin:20px 0;font-size:calc(var(--fs)*.8);
  color:#ffd894;display:flex;gap:12px;align-items:flex-start}
.proto b{color:#ffe6b8}

/* ---------- hero ---------- */
.hero{padding:44px 0 26px}
.kicker{color:var(--accent2);font-weight:700;letter-spacing:1.6px;
  text-transform:uppercase;font-size:calc(var(--fs)*.72);margin-bottom:12px}
h1{font-size:calc(var(--fs)*2.05);line-height:1.16;margin:0 0 16px;letter-spacing:-.5px}
h1 span{color:var(--accent2)}
.lede{color:var(--ink2);font-size:calc(var(--fs)*1.04);max-width:62ch;margin:0}
.facts{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}
.fact{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:12px 16px;min-width:132px}
.fact .k{color:var(--ink3);font-size:calc(var(--fs)*.7);text-transform:uppercase;
  letter-spacing:1px;font-weight:700}
.fact .v{font-size:calc(var(--fs)*.95);font-weight:700;margin-top:3px}

/* ---------- sections ---------- */
section{margin:34px 0}
h2{font-size:calc(var(--fs)*1.34);margin:0 0 6px;letter-spacing:-.2px;
  display:flex;align-items:center;gap:12px}
h2 .num{flex:0 0 auto;width:34px;height:34px;border-radius:10px;background:var(--accent);
  color:#04121f;display:grid;place-items:center;font-size:calc(var(--fs)*.9);font-weight:800}
h3{font-size:calc(var(--fs)*1.03);margin:22px 0 8px}
p{margin:0 0 15px;color:var(--ink2)}
p strong,li strong{color:var(--ink)}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px}
ul{margin:0 0 15px;padding-left:22px;color:var(--ink2)}
li{margin:0 0 9px}
.note{border-left:4px solid var(--accent);padding:12px 16px;background:var(--bg2);
  border-radius:0 12px 12px 0;margin:16px 0;color:var(--ink2);
  font-size:calc(var(--fs)*.92)}
.verbatim{border-left:4px solid var(--warm);background:#1e1a10;padding:14px 18px;
  border-radius:0 12px 12px 0;margin:14px 0;color:var(--ink)}
.verbatim .tag{display:block;color:var(--warm);font-size:calc(var(--fs)*.68);
  text-transform:uppercase;letter-spacing:1.2px;font-weight:800;margin-bottom:6px}
html[data-contrast="high"] .verbatim{background:#141414;border-left-color:#ffcc66}

/* ---------- 3D stage ---------- */
.stage{position:relative;background:radial-gradient(120% 100% at 50% 0%,#16243c,#0a111f);
  border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;
  aspect-ratio:16/10;min-height:300px}
#gl{display:block;width:100%;height:100%}
.stage .hud{position:absolute;left:16px;bottom:16px;right:16px;display:flex;
  gap:10px;align-items:center;flex-wrap:wrap}
.stage .step-label{background:rgba(6,12,24,.82);border:1px solid var(--line);
  border-radius:12px;padding:10px 14px;font-size:calc(var(--fs)*.82);flex:1 1 240px}
.stage .step-label b{color:var(--accent2)}
.stage .badge{position:absolute;top:14px;left:16px;background:rgba(6,12,24,.82);
  border:1px solid var(--line);border-radius:999px;padding:6px 14px;
  font-size:calc(var(--fs)*.72);color:var(--ink2);letter-spacing:.5px}
.play{background:var(--accent);color:#04121f;border:0;border-radius:12px;
  padding:12px 22px;font-size:calc(var(--fs)*.85);font-weight:800;cursor:pointer;
  font-family:inherit;min-height:46px}
.play:disabled{opacity:.45;cursor:default}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.stepchip{background:var(--card2);border:1px solid var(--line);border-radius:10px;
  padding:9px 13px;font-size:calc(var(--fs)*.78);cursor:pointer;color:var(--ink2);
  font-family:inherit;text-align:left;min-height:42px}
.stepchip[aria-current="true"]{background:var(--accent);color:#04121f;
  border-color:var(--accent);font-weight:800}

/* ---------- timeline ---------- */
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

/* ---------- risk meter ---------- */
.riskgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}
.risk{background:var(--card2);border:1px solid var(--line);border-radius:14px;padding:16px}
.risk .h{font-weight:800;margin-bottom:6px}
.risk .d{color:var(--ink2);font-size:calc(var(--fs)*.86)}
.risk .sev{display:inline-block;margin-top:9px;font-size:calc(var(--fs)*.68);
  text-transform:uppercase;letter-spacing:1px;font-weight:800;padding:3px 10px;
  border-radius:999px}
.sev.common{background:#2a2416;color:#ffcf7a}
.sev.rare{background:#1c2a20;color:#7fe0ab}
.sev.vrare{background:#241c2a;color:#c9a2ff}

/* ---------- checklist ---------- */
.check{display:flex;gap:12px;align-items:flex-start;padding:12px 0;
  border-bottom:1px solid var(--line)}
.check:last-child{border-bottom:0}
.check .box{flex:0 0 22px;height:22px;border:2px solid var(--line);border-radius:6px;
  margin-top:2px}

/* ---------- footer ---------- */
.sources{background:var(--bg2);border:1px solid var(--line);border-radius:var(--radius);
  padding:20px;margin-top:34px;font-size:calc(var(--fs)*.8);color:var(--ink3)}
.sources h3{color:var(--ink2);margin-top:0}
.sources li{margin-bottom:6px}

@media print{
  .bar,.proto,.play,.stepchip,.ctrl{display:none!important}
  body{background:#fff;color:#000}
  .stage{display:none}
}
@media (prefers-reduced-motion:reduce){
  *{animation-duration:.001ms!important;transition-duration:.001ms!important}
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

  <div class="proto">
    <span aria-hidden="true">⚠️</span>
    <div><b>Prototype — pending clinical approval.</b>
    This guide re-presents the content of Woodlands Health's approved procedure
    information sheet for thyroid FNAC. It is not a substitute for discussion with
    your doctor, and it does not replace the consent process. Risk and options
    wording is reproduced unchanged from the approved sheet.</div>
  </div>

  <div class="hero">
    <div class="kicker">Fine Needle Aspiration Cytology</div>
    <h1>You've been told you need a <span>thyroid FNAC</span>. Here's exactly what that means.</h1>
    <p class="lede">A fine needle aspiration is a small test that takes a few cells
    from a lump in your thyroid, so a pathologist can look at them under a
    microscope and work out what the lump is. This page walks you through it —
    what it is, what happens on the day, what you'll feel, and what comes after.</p>

    <div class="facts">
      <div class="fact"><div class="k">Usually takes</div><div class="v">10–20 minutes</div></div>
      <div class="fact"><div class="k">Anaesthetic</div><div class="v">Often not needed</div></div>
      <div class="fact"><div class="k">Needle size</div><div class="v">Very fine</div></div>
      <div class="fact"><div class="k">Results</div><div class="v">1–2 weeks</div></div>
    </div>
  </div>

  <!-- 1 -->
  <section>
    <h2><span class="num">1</span> What a thyroid nodule actually is</h2>
    <p>A thyroid nodule is an <strong>abnormal growth of thyroid cells into a lump</strong>
    within your thyroid gland. The thyroid sits at the front of your neck, just below
    your voice box, and makes hormones that control how your body uses energy.</p>
    <p><strong>Most thyroid nodules are benign</strong> — that means non-cancerous.
    But some nodules can be cancerous, and there is no way to tell just by looking
    at your neck. That is why your doctor has asked for this test.</p>
    <div class="note">Finding a nodule is common. Most people who have one never
    need anything more than a check-up.</div>
  </section>

  <!-- 2 -->
  <section>
    <h2><span class="num">2</span> Why you need this test</h2>
    <p>The purpose of the FNAC is <strong>to determine the nature of the nodule and to
    try to rule out the possibility of cancer</strong> within the thyroid gland.</p>
    <p>FNAC is the standard first test for this. It gives your doctor real
    information — the kind that lets them decide whether you need treatment,
    further tests, or simply to be monitored.</p>
  </section>

  <!-- 3 -->
  <section>
    <h2><span class="num">3</span> The procedure, step by step</h2>
    <p>Tap any step, or press play, to watch it happen. You can pause at any point.</p>

    <div class="stage">
      <canvas id="gl" aria-label="3D animation of the thyroid and the FNAC needle"></canvas>
      <div class="badge">Drag to rotate · scroll to zoom</div>
      <div class="hud">
        <div class="step-label" id="stepLabel"><b>Step 1 of 7.</b> Getting into position.</div>
        <button class="play" id="btnPlay">▶ Play</button>
      </div>
    </div>

    <div class="steps" id="steps"></div>

    <div class="note" id="stepNote"></div>
  </section>

  <!-- 4 -->
  <section>
    <h2><span class="num">4</span> What you'll feel</h2>
    <p>This is the part people worry about most, so here it is honestly:</p>
    <ul>
      <li><strong>Neck pressure</strong> from the ultrasound probe resting on your neck.</li>
      <li><strong>A slight pin prick</strong> from the needle — the needle is finer than
      the one used for a routine blood test.</li>
      <li><strong>Some pressure</strong> as the samples are taken.</li>
      <li>You may feel nothing much at all. Most people describe it as
      <strong>quick and less uncomfortable than they expected</strong>.</li>
    </ul>
    <p>You'll be asked to <strong>stay as still as you can</strong> and to
    <strong>avoid coughing, talking or swallowing</strong> while the needle is in —
    these move the thyroid and make it harder to place the needle accurately.</p>
  </section>

  <!-- 5 -->
  <section>
    <h2><span class="num">5</span> How it's done</h2>
    <div class="card">
      <p>The procedure is performed by <strong>inserting a fine needle into the
      nodule and making several passes</strong> to obtain a small sample of tissue,
      which is sent to the laboratory for evaluation.</p>
      <p>It is carried out <strong>under ultrasound guidance</strong> for accurate
      placement of the needle — the same scanning that was used to find the nodule
      in the first place.</p>
      <p>You <strong>may be given a local anaesthetic injection</strong> to numb the
      injection site.</p>
    </div>
  </section>

  <!-- 6 -->
  <section>
    <h2><span class="num">6</span> Before the procedure</h2>
    <p>Usually <strong>no prior preparation is required</strong>.</p>
    <p><strong>Let your doctor know if you are on any blood thinners or
    antiplatelets</strong> — medicines such as warfarin, rivaroxaban, aspirin or
    clopidogrel. They may need to be stopped before the procedure.</p>
    <div class="check"><div class="box"></div><div>Tell your doctor about any blood
    thinners or antiplatelet medicines you take.</div></div>
    <div class="check"><div class="box"></div><div>You do not normally need to fast.</div></div>
    <div class="check"><div class="box"></div><div>Wear something comfortable that
    lets your neck be reached easily.</div></div>
    <div class="check"><div class="box"></div><div>Bring your questions — nothing is
    too small to ask.</div></div>
  </section>

  <!-- 7 -->
  <section>
    <h2><span class="num">7</span> Risks and complications</h2>
    <p>FNAC is generally safe and complications are extremely rare. These are the
    risks your doctor wants you to know about:</p>
    <div class="riskgrid">
      <div class="risk"><div class="h">Bruising, bleeding, swelling or pain</div>
        <div class="d">At the puncture site.</div>
        <span class="sev common">More common</span></div>
      <div class="risk"><div class="h">A non-diagnostic result</div>
        <div class="d">In about 5–10% of cases, not enough cells are sampled for the
        pathologist to make a clear diagnosis.</div>
        <span class="sev common">5–10%</span></div>
      <div class="risk"><div class="h">Significant swelling or breathing problems</div>
        <div class="d">From bleeding. It is exceptionally rare for bleeding to cause
        this, but it is the reason you must seek help if you have these symptoms.</div>
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
    means the sample did not contain enough cells to be sure — and your doctor will
    discuss what to do next.</div>
  </section>

  <!-- 8 -->
  <section>
    <h2><span class="num">8</span> After the procedure</h2>
    <div class="tl">
      <div class="item good"><div class="when">For the first 1–2 hours</div>
        <div class="what">Leave the adhesive dressing over the puncture site in place.
        After that it can be removed, and the area washed if you want to.</div></div>
      <div class="item good"><div class="when">Right away</div>
        <div class="what">You can resume usual activities, including eating and
        drinking.</div></div>
      <div class="item good"><div class="when">For about 24 hours</div>
        <div class="what">Avoid strenuous physical activity — heavy lifting or
        contact sports.</div></div>
      <div class="item good"><div class="when">If you need it</div>
        <div class="what">Slight pain, swelling or bruising at the site can be
        eased with simple painkillers such as Panadol.</div></div>
      <div class="item warn"><div class="when">Seek immediate medical attention if</div>
        <div class="what">You have a sudden increase in pain or swelling, continued
        bleeding, or difficulty breathing.</div></div>
    </div>
  </section>

  <!-- 9 -->
  <section>
    <h2><span class="num">9</span> Getting your results</h2>
    <p>The results of the test <strong>usually take a week or two to process</strong>.
    Your primary doctor should be making arrangements to communicate them to you.</p>
    <div class="note"><strong>It is important to attend the follow-up appointment</strong>
    so the results can be discussed with you properly. Waiting for results can feel
    like a long time — that is normal, and the wait does not mean anything has gone
    wrong.</div>
  </section>

  <!-- 10 -->
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
    <p>Deciding not to have a procedure is a legitimate choice, and your doctor's
    role is to help you weigh it up — not to pressure you.</p>
  </section>

  <!-- 11 -->
  <section>
    <h2><span class="num">11</span> Questions to ask your doctor</h2>
    <div class="card">
      <ul>
        <li>Why has this nodule been chosen for FNAC rather than monitored?</li>
        <li>How many passes do you expect to need?</li>
        <li>Will I have local anaesthetic?</li>
        <li>If the result is non-diagnostic, what happens next?</li>
        <li>When and how will I get the result?</li>
        <li>What would the options be if I decided not to go ahead?</li>
      </ul>
    </div>
  </section>

  <div class="sources">
    <h3>About this page</h3>
    <p>Clinical content is based on Woodlands Health's
    <strong>Procedure Information Sheet: Fine Needle Aspiration Cytology (FNAC)
    Thyroid (Version No: 01)</strong>. Risk and options wording appears unchanged
    from that sheet, marked accordingly. Procedure description cross-checked against
    the sources below.</p>
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
/* ------------------------------------------------------------------ UI prefs */
const html = document.documentElement;
const SIZES = ['normal','large','xl'];
let sizeIdx = 0;
document.getElementById('btnSize').onclick = (e)=>{
  sizeIdx = (sizeIdx+1) % SIZES.length;
  const v = SIZES[sizeIdx];
  if (v === 'normal') html.removeAttribute('data-size');
  else html.setAttribute('data-size', v);
  e.currentTarget.setAttribute('aria-pressed', v !== 'normal');
  e.currentTarget.textContent = v === 'normal' ? 'Larger text'
    : (v === 'large' ? 'Largest text' : 'Reset text size');
};
document.getElementById('btnContrast').onclick = (e)=>{
  const on = html.getAttribute('data-contrast') === 'high';
  if (on) html.removeAttribute('data-contrast');
  else html.setAttribute('data-contrast','high');
  e.currentTarget.setAttribute('aria-pressed', String(!on));
};
document.getElementById('btnPrint').onclick = ()=>window.print();

/* ------------------------------------------------------------- 3D procedure */
(function(){
  const canvas = document.getElementById('gl');
  const label  = document.getElementById('stepLabel');
  const note   = document.getElementById('stepNote');
  const chips  = document.getElementById('steps');
  const btnPlay= document.getElementById('btnPlay');

  const STEPS = [
    {t:"Getting into position",
     n:"You lie on your back with your head tipped gently backwards so your neck is extended. Sometimes a pillow is placed under your shoulders. This brings the thyroid closer to the surface and makes it easier to reach.",
     anim:{needleOut:1, probeOut:1, tilt:1, markerIn:0, flash:0}},
    {t:"Ultrasound first",
     n:"The doctor scans your neck with the ultrasound probe to find the thyroid gland and the exact nodule. Blood vessels in the path are checked so they can be avoided.",
     anim:{needleOut:1, probeOn:1, tilt:1, markerIn:0, flash:0}},
    {t:"Marking the entry point",
     n:"The skin at the entry point may be marked with a pen, so the needle goes in at the planned spot.",
     anim:{needleOut:1, probeOn:0.45, tilt:1, markerIn:1, flash:0}},
    {t:"Local anaesthetic (if needed)",
     n:"You may be given a local anaesthetic injection to numb the injection site. Many people do not need one — your doctor will decide with you.",
     anim:{needleOut:1, probeOn:1, tilt:1, markerIn:1, anaes:1, flash:0}},
    {t:"The needle goes in",
     n:"A very fine needle — finer than the one used for a blood test — passes through the skin and into the nodule, guided live by the ultrasound image on screen.",
     anim:{needleIn:1, probeOn:1, tilt:1, markerIn:1, flash:0}},
    {t:"Several passes",
     n:"The needle moves gently back and forth within the nodule for a few seconds to collect cells. The needle may be inserted more than once — this is called making several passes — to gather enough cells for a reliable result.",
     anim:{needleIn:1, probeOn:1, tilt:1, markerIn:1, passes:1, flash:0}},
    {t:"Sample sent to the laboratory",
     n:"The cells collected are sent to the laboratory, where a pathologist examines them under a microscope. A dressing is placed over the puncture site.",
     anim:{needleOut:1, probeOn:0.6, tilt:0.3, markerIn:1, dressing:1, flash:0}},
  ];

  let cur = 0, playing = false, playTimer = null;

  STEPS.forEach((s,i)=>{
    const b = document.createElement('button');
    b.className = 'stepchip';
    b.textContent = (i+1)+'. '+s.t;
    b.onclick = ()=>{ stopPlay(); setStep(i); };
    chips.appendChild(b);
  });

  function setStep(i){
    cur = i;
    const s = STEPS[i];
    label.innerHTML = '<b>Step '+(i+1)+' of '+STEPS.length+'.</b> '+s.t;
    note.textContent = s.n;
    [...chips.children].forEach((c,j)=>c.setAttribute('aria-current', String(j===i)));
    if (window.__fnacSetAnim) window.__fnacSetAnim(s.anim);
  }
  function stopPlay(){ playing=false; clearInterval(playTimer); btnPlay.textContent='▶ Play'; }
  btnPlay.onclick = ()=>{
    if (playing){ stopPlay(); return; }
    playing = true; btnPlay.textContent='⏸ Pause';
    playTimer = setInterval(()=>{
      if (cur >= STEPS.length-1){ stopPlay(); return; }
      setStep(cur+1);
    }, 4200);
  };
  setStep(0);

  /* ------------------------------ three.js, inlined minimal WebGL renderer -- */
  /* If WebGL is unavailable the canvas shows a labelled 2D fallback instead.   */
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
  const FRAG = `
    precision mediump float;
    varying vec3 vNorm, vView, vCol;
    uniform vec3 uLight, uColorMul, uCam, uTint;
    uniform float uAlpha, uTintAmt, uEmis;
    void main(){
      vec3 N = normalize(vNorm);
      vec3 L = normalize(uLight - vView);
      vec3 V = normalize(uCam - vView);
      float diff = max(dot(N,L),0.0);
      float spec = pow(max(dot(reflect(-L,N),V),0.0), 34.0);
      vec3 base = mix(vCol*uColorMul, uTint, uTintAmt);
      vec3 c = base*(0.30 + 0.82*diff) + vec3(spec)*0.36 + base*uEmis;
      gl_FragColor = vec4(c, uAlpha);
    }`;

  function mesh(geo, color, opts){
    return Object.assign({geo, color, model:m4(), alpha:1, tint:[0,0,0], tintAmt:0,
      emis:0, visible:true}, opts||{});
  }
  function m4(){ return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]); }
  function mul(a,b){
    const o=new Float32Array(16);
    for(let i=0;i<4;i++)for(let j=0;j<4;j++){let s=0;
      for(let k=0;k<4;k++) s+=a[k*4+j]*b[i*4+k]; o[i*4+j]=s;}
    return o;
  }
  function T(x,y,z){const m=m4();m[12]=x;m[13]=y;m[14]=z;return m;}
  function S(x,y,z){const m=m4();m[0]=x;m[5]=y;m[10]=z;return m;}
  function RX(a){const m=m4();m[5]=Math.cos(a);m[6]=Math.sin(a);m[9]=-Math.sin(a);m[10]=Math.cos(a);return m;}
  function RY(a){const m=m4();m[0]=Math.cos(a);m[2]=-Math.sin(a);m[8]=Math.sin(a);m[10]=Math.cos(a);return m;}
  function RZ(a){const m=m4();m[0]=Math.cos(a);m[1]=Math.sin(a);m[4]=-Math.sin(a);m[5]=Math.cos(a);return m;}
  function persp(fov,asp,n,f){
    const t=1/Math.tan(fov/2), m=new Float32Array(16);
    m[0]=t/asp; m[5]=t; m[10]=(f+n)/(n-f); m[11]=-1; m[14]=2*f*n/(n-f); return m;
  }
  function lookAt(e,c,u){
    let z=[e[0]-c[0],e[1]-c[1],e[2]-c[2]]; let l=Math.hypot(...z); z=z.map(v=>v/l);
    let x=[u[1]*z[2]-u[2]*z[1], u[2]*z[0]-u[0]*z[2], u[0]*z[1]-u[1]*z[0]];
    l=Math.hypot(...x)||1; x=x.map(v=>v/l);
    const y=[z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0]];
    return new Float32Array([x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
      -x[0]*e[0]-x[1]*e[1]-x[2]*e[2], -y[0]*e[0]-y[1]*e[1]-y[2]*e[2],
      -z[0]*e[0]-z[1]*e[1]-z[2]*e[2], 1]);
  }

  /* geometry builders: return {pos:[],norm:[],col:[]} */
  function ellipsoid(rx,ry,rz,color,seg,ring){
    seg=seg||36; ring=ring||22;
    const p=[],n=[],c=[];
    for(let i=0;i<=ring;i++){
      const v=i/ring*Math.PI;
      for(let j=0;j<=seg;j++){
        const u=j/seg*Math.PI*2;
        const x=Math.sin(v)*Math.cos(u), y=Math.cos(v), z=Math.sin(v)*Math.sin(u);
        p.push(x*rx,y*ry,z*rz);
        const nx=x/(rx||1), ny=y/(ry||1), nz=z/(rz||1);
        const l=Math.hypot(nx,ny,nz)||1; n.push(nx/l,ny/l,nz/l);
        c.push(color[0],color[1],color[2]);
      }
    }
    const idx=[];
    for(let i=0;i<ring;i++)for(let j=0;j<seg;j++){
      const a=i*(seg+1)+j, b=a+seg+1;
      idx.push(a,b,a+1, b,b+1,a+1);
    }
    return {pos:p,norm:n,col:c,idx};
  }
  function cylinder(r1,r2,h,color,seg){
    seg=seg||26; const p=[],n=[],c=[],idx=[];
    for(let i=0;i<=seg;i++){
      const a=i/seg*Math.PI*2, x=Math.cos(a), z=Math.sin(a);
      p.push(x*r1,-h/2,z*r1); n.push(x,0,z); c.push(...color);
      p.push(x*r2, h/2,z*r2); n.push(x,0,z); c.push(...color);
    }
    for(let i=0;i<seg;i++){const a=i*2; idx.push(a,a+1,a+2, a+1,a+3,a+2);}
    for(const sgn of [-1,1]){
      const base=p.length/3;
      p.push(0,sgn*h/2,0); n.push(0,sgn,0); c.push(...color);
      for(let i=0;i<=seg;i++){
        const a=i/seg*Math.PI*2;
        p.push(Math.cos(a)*r2,-0+ sgn*h/2,Math.sin(a)*r2); n.push(0,sgn,0); c.push(...color);
      }
      for(let i=0;i<seg;i++) idx.push(base, base+1+i, base+2+i);
    }
    return {pos:p,norm:n,col:c,idx};
  }
  function box(w,h,d,color){
    const p=[],n=[],c=[],idx=[];
    const f=[[[1,1,-1],[-1,1,-1],[-1,-1,-1],[1,-1,-1],[0,0,-1]],
             [[1,1,1],[1,-1,1],[-1,-1,1],[-1,1,1],[0,0,1]],
             [[1,1,-1],[1,1,1],[-1,1,1],[-1,1,-1],[0,1,0]],
             [[1,-1,-1],[-1,-1,-1],[-1,-1,1],[1,-1,1],[0,-1,0]],
             [[1,1,-1],[1,-1,-1],[1,-1,1],[1,1,1],[1,0,0]],
             [[-1,1,-1],[-1,1,1],[-1,-1,1],[-1,-1,-1],[-1,0,0]]];
    for(const face of f){
      const base=p.length/3;
      for(let i=0;i<4;i++){
        const v=face[i];
        p.push(v[0]*w/2,v[1]*h/2,v[2]*d/2);
        n.push(face[4][0],face[4][1],face[4][2]);
        c.push(...color);
      }
      idx.push(base,base+1,base+2, base,base+2,base+3);
    }
    return {pos:p,norm:n,col:c,idx};
  }

  const SKIN=[0.92,0.76,0.66], THY=[0.88,0.42,0.44], NOD=[0.55,0.24,0.30],
        MUSC=[0.62,0.28,0.28], TRACH=[0.80,0.82,0.86], STEEL=[0.86,0.90,0.96],
        PROBE=[0.20,0.24,0.32], MARK=[0.20,0.85,0.75];

  const glc = canvas.getContext('webgl', {antialias:true, alpha:true});
  let prog=null, loc={}, bufs=[], meshes=[];

  function compile(type,src){
    const s=glc.createShader(type); glc.shaderSource(s,src); glc.compileShader(s);
    if(!glc.getShaderParameter(s,glc.COMPILE_STATUS)){ console.error(glc.getShaderInfoLog(s)); return null;}
    return s;
  }
  function upload(g){
    const vb=glc.createBuffer(); glc.bindBuffer(glc.ARRAY_BUFFER,vb);
    const n=g.pos.length/3, arr=new Float32Array(n*9);
    for(let i=0;i<n;i++){
      arr[i*9+0]=g.pos[i*3]; arr[i*9+1]=g.pos[i*3+1]; arr[i*9+2]=g.pos[i*3+2];
      arr[i*9+3]=g.norm[i*3]; arr[i*9+4]=g.norm[i*3+1]; arr[i*9+5]=g.norm[i*3+2];
      arr[i*9+6]=g.col[i*3]; arr[i*9+7]=g.col[i*3+1]; arr[i*9+8]=g.col[i*3+2];
    }
    glc.bufferData(glc.ARRAY_BUFFER,arr,glc.STATIC_DRAW);
    const ib=glc.createBuffer(); glc.bindBuffer(glc.ELEMENT_ARRAY_BUFFER,ib);
    glc.bufferData(glc.ELEMENT_ARRAY_BUFFER,new Uint16Array(g.idx),glc.STATIC_DRAW);
    return {vb, ib, count:g.idx.length};
  }

  if (glc){
    const vs=compile(glc.VERTEX_SHADER,VERT), fs=compile(glc.FRAGMENT_SHADER,FRAG);
    if (vs && fs){
      prog=glc.createProgram(); glc.attachShader(prog,vs); glc.attachShader(prog,fs);
      glc.linkProgram(prog);
      glc.useProgram(prog);
      ['aPos','aNorm','aCol'].forEach((nm,i)=>loc[nm]=glc.getAttribLocation(prog,nm));
      ['uProj','uView','uModel','uLight','uColorMul','uCam','uTint','uAlpha',
       'uTintAmt','uEmis'].forEach(nm=>loc[nm]=glc.getUniformLocation(prog,nm));
    }
  }

  function addMesh(geo,color,opts){
    const m = mesh(geo,color,opts);
    if (glc && prog) m.buf = upload(geo);
    meshes.push(m); return m;
  }

  /* ---- scene graph ------------------------------------------------------- */
  const scene = {skin:null, lobes:[], nodule:null, trachea:null, muscle:null,
                 probe:null, needle:null, needleTip:null, mark:null, dressing:null};

  addMesh(box(6,6,6,[0.03,0.05,0.09]),[0,0,0],{visible:false}); // dummy slot 0
  meshes.length = 0; // rebuild cleanly

  scene.trachea = addMesh(cylinder(0.30,0.30,2.6,TRACH), TRACH);
  scene.muscle  = addMesh(ellipsoid(1.30,0.62,1.50,MUSC), MUSC, {alpha:0.30});
  scene.skin    = addMesh(ellipsoid(1.55,0.95,1.30,SKIN), SKIN, {alpha:0.16});

  const lobeGeo = ellipsoid(0.30,0.46,0.24,THY);
  scene.lobes.push(addMesh(lobeGeo, THY, {model:T( 0.42,0.05,0.20)}));
  scene.lobes.push(addMesh(lobeGeo, THY, {model:T(-0.42,0.05,0.20)}));
  scene.lobes.push(addMesh(ellipsoid(0.22,0.10,0.14,THY), THY, {model:T(0,0.02,0.26)}));

  const nodGeo = ellipsoid(0.135,0.16,0.115,NOD);
  scene.nodule = addMesh(nodGeo, NOD, {model:T(0.44,0.10,0.30), emis:0.10});

  scene.mark = addMesh(ellipsoid(0.055,0.010,0.055,MARK), MARK,
                       {model:T(0.44,0.83,0.30), emis:0.35});

  scene.probe = addMesh(box(0.55,0.34,1.35,PROBE), PROBE);
  scene.probeBody = addMesh(box(0.42,0.26,0.85,[0.14,0.17,0.23]),[0.14,0.17,0.23]);

  scene.needle = addMesh(cylinder(0.012,0.008,1.65,STEEL), STEEL, {emis:0.25});
  scene.hub    = addMesh(cylinder(0.045,0.045,0.30,[0.75,0.55,0.30]),[0.75,0.55,0.30]);

  scene.dressing = addMesh(box(0.34,0.03,0.34,[0.95,0.93,0.88]),[0.95,0.93,0.88]);

  /* ---- animation state --------------------------------------------------- */
  const A = {needleIn:0, probeOn:0, tilt:0, markerIn:0, passes:0, dressing:0,
             anaes:0, flash:0};
  const TARGET = {needleIn:0, probeOn:0, tilt:0, markerIn:0, passes:0, dressing:0,
                  anaes:0, flash:0};
  window.__fnacSetAnim = (o)=>{
    for (const k of Object.keys(TARGET)) TARGET[k] = (o && o[k]!==undefined) ? o[k] : 0;
  };

  let camYaw=-0.55, camPitch=0.28, camDist=5.2, autoRotate=true;
  let drag=false, lx=0, ly=0;

  canvas.addEventListener('pointerdown', e=>{drag=true; autoRotate=false; lx=e.clientX; ly=e.clientY;});
  window.addEventListener('pointerup', ()=>drag=false);
  window.addEventListener('pointermove', e=>{
    if(!drag) return;
    camYaw   += (e.clientX-lx)*0.008;
    camPitch = Math.max(-0.5, Math.min(1.1, camPitch + (e.clientY-ly)*0.006));
    lx=e.clientX; ly=e.clientY;
  });
  canvas.addEventListener('wheel', e=>{
    e.preventDefault();
    camDist = Math.max(2.6, Math.min(9.5, camDist + e.deltaY*0.0035));
    autoRotate=false;
  }, {passive:false});

  function resize(){
    const dpr = Math.min(window.devicePixelRatio||1, 2);
    const r = canvas.getBoundingClientRect();
    canvas.width = Math.max(2, r.width*dpr|0);
    canvas.height= Math.max(2, r.height*dpr|0);
  }
  window.addEventListener('resize', resize);
  resize();

  let t0 = performance.now();
  let lastRaf = performance.now();
  let watchdog = null;
  let rafAlive = true;

  function frame(now){
    lastRaf = performance.now();
    render(now);
    requestAnimationFrame(frame);
  }

  /* requestAnimationFrame is throttled to zero when the page is not compositing
     (background tab, kiosk tablet, low-power mode, some remote-display setups).
     A patient-facing tool must keep animating in those conditions, so a
     watchdog takes over the render loop when no frame has arrived for 250ms. */
  function startWatchdog(){
    if (watchdog) return;
    watchdog = setInterval(function(){
      const gap = performance.now() - lastRaf;
      if (gap > 250){
        rafAlive = false;
        render(performance.now());
      }
    }, 33);
  }

  function render(now){
    const dt = Math.min(0.05, (now-t0)/1000); t0 = now;

    for (const k of Object.keys(TARGET)) A[k] += (TARGET[k]-A[k])*Math.min(1, dt*3.4);

    if (autoRotate) camYaw += dt*0.16;

    /* --- position the patient: neck extension tilt --- */
    const tilt = A.tilt * 0.30;
    const root = mul(RX(-tilt), m4());

    scene.trachea.model = mul(root, T(0, 0.05, -0.30));
    scene.muscle.model  = mul(root, m4());
    scene.skin.model    = mul(root, m4());
    scene.lobes[0].model= mul(root, T( 0.42,0.05,0.20));
    scene.lobes[1].model= mul(root, T(-0.42,0.05,0.20));
    scene.lobes[2].model= mul(root, T(0,0.02,0.26));
    scene.nodule.model  = mul(root, T(0.44,0.10,0.30));
    if (scene.mark) scene.mark.model = mul(root, T(0.44,0.83,0.30));

    /* --- ultrasound probe --- */
    const px = 0.62 + 0.05*Math.sin(now/900);
    const py = 1.02 - A.probeOn*0.16 + 0.012*Math.sin(now/220)*(A.probeOn>0.02?1:0);
    const pz = 0.10;
    const probeM = mul(root, mul(T(px,py,pz), RX(0.62)));
    scene.probe.model = probeM;
    if (scene.probeBody)
      scene.probeBody.model = mul(probeM, T(0,0.30,-0.30));
    scene.probe.visible = A.probeOn > 0.01;

    /* --- needle: enters from upper-right, angled down-left toward nodule --- */
    const exc = A.passes ? Math.sin(now/230)*0.035 : 0;   // back-and-forth excursions
    const inAmt = A.needleIn;
    const startX = 1.35, startY = 1.55, startZ = 0.55;
    const endX   = 0.44, endY   = 0.10, endZ   = 0.30;
    const nx = startX + (endX-startX)*inAmt + exc;
    const ny = startY + (endY-startY)*inAmt;
    const nz = startZ + (endZ-startZ)*inAmt;
    const ang = -1.02;
    const nM = mul(root, mul(T(nx,ny,nz), RZ(ang)));
    scene.needle.model = nM;
    if (scene.hub) scene.hub.model = mul(nM, T(0,0.86,0));
    scene.needle.visible = (1-A.needleOut) > 0.01 || inAmt > 0.01;

    /* --- anaesthetic / marker hints --- */
    if (scene.mark)
      scene.mark.emis = 0.20 + 0.30*A.markerIn + 0.20*Math.sin(now/380)*A.markerIn;
    const anaesGlow = A.anaes * (0.5+0.5*Math.sin(now/300));
    scene.nodule.emis = 0.06 + 0.18*anaesGlow + (A.passes?0.10:0);

    /* --- dressing --- */
    if (scene.dressing){
      scene.dressing.visible = A.dressing > 0.01;
      scene.dressing.model = mul(root, T(0.44, 0.80, 0.30));
    }

    /* ------------------------------------------------------------------ draw */
    if (glc && prog){
      glc.viewport(0,0,canvas.width,canvas.height);
      glc.clearColor(0,0,0,0); glc.clear(glc.COLOR_BUFFER_BIT|glc.DEPTH_BUFFER_BIT);
      glc.enable(glc.DEPTH_TEST); glc.enable(glc.CULL_FACE);
      glc.enable(glc.BLEND); glc.blendFunc(glc.SRC_ALPHA, glc.ONE_MINUS_SRC_ALPHA);

      const asp = canvas.width/canvas.height;
      const proj = persp(0.78, asp, 0.1, 60);
      const cy = Math.sin(camPitch)*camDist, cxz=Math.cos(camPitch)*camDist;
      const cam=[Math.sin(camYaw)*cxz, cy+0.35, Math.cos(camYaw)*cxz];
      const view = lookAt(cam,[0,0.15,0],[0,1,0]);
      glc.uniformMatrix4fv(loc.uProj,false,proj);
      glc.uniformMatrix4fv(loc.uView,false,view);
      glc.uniform3fv(loc.uLight,[2.2,3.4,3.0]);
      glc.uniform3fv(loc.uCam,cam);
      glc.uniform3fv(loc.uColorMul,[1,1,1]);
      glc.uniform1f(loc.uTintAmt,0);
      glc.uniform3fv(loc.uTint,[0,0,0]);

      for(const m of meshes){
        if (m.visible === false) continue;
        if (!m.buf) continue;
        glc.bindBuffer(glc.ARRAY_BUFFER, m.buf.vb);
        const st = 9*4;
        glc.enableVertexAttribArray(loc.aPos); glc.vertexAttribPointer(loc.aPos,3,glc.FLOAT,false,st,0);
        glc.enableVertexAttribArray(loc.aNorm);glc.vertexAttribPointer(loc.aNorm,3,glc.FLOAT,false,st,12);
        glc.enableVertexAttribArray(loc.aCol); glc.vertexAttribPointer(loc.aCol,3,glc.FLOAT,false,st,24);
        glc.bindBuffer(glc.ELEMENT_ARRAY_BUFFER, m.buf.ib);
        glc.uniformMatrix4fv(loc.uModel,false,m.model);
        glc.uniform1f(loc.uAlpha, m.alpha===undefined?1:m.alpha);
        glc.uniform1f(loc.uEmis, m.emis||0);
        glc.uniform3fv(loc.uTint, m.tint||[0,0,0]);
        glc.uniform1f(loc.uTintAmt, m.tintAmt||0);
        if (m.alpha < 1) glc.disable(glc.CULL_FACE);
        glc.drawElements(glc.TRIANGLES, m.buf.count, glc.UNSIGNED_SHORT, 0);
        glc.enable(glc.CULL_FACE);
      }
    } else {
      /* ---- graceful fallback: 2D diagram if WebGL is unavailable ---- */
      const ctx = canvas.getContext('2d');
      if (ctx){
        const W=canvas.width, H=canvas.height;
        ctx.clearRect(0,0,W,H);
        ctx.fillStyle='#0d1626'; ctx.fillRect(0,0,W,H);
        ctx.fillStyle='#4aa8ff'; ctx.font='bold 22px sans-serif';
        ctx.fillText('Thyroid FNAC — step '+(cur+1), 24, 42);
        ctx.fillStyle='#a9bcd8'; ctx.font='16px sans-serif';
        ctx.fillText(STEPS[cur].t, 24, 72);
        ctx.fillStyle='#1d2d47'; ctx.beginPath();
        ctx.ellipse(W/2, H*0.62, W*0.16, H*0.10, 0, 0, 7); ctx.fill();
        ctx.fillStyle='#e0565c'; ctx.beginPath();
        ctx.ellipse(W/2, H*0.62, W*0.07, H*0.05, 0, 0, 7); ctx.fill();
        if (A.needleIn>0.02 || true){
          ctx.strokeStyle='#dde6f5'; ctx.lineWidth=3;
          ctx.beginPath(); ctx.moveTo(W*0.72, H*0.28);
          ctx.lineTo(W/2+W*0.07*A.needleIn, H*0.62);
          ctx.stroke();
        }
      }
    }
  }
  requestAnimationFrame(frame);
  startWatchdog();
})();
</script>
</body>
</html>
"""

out_dir = "/home/alex/Documents/FNAC_Webapp"
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, "index.html")
with open(path, "w") as fh:
    fh.write(HTML)
print("wrote", path, len(HTML), "bytes")
