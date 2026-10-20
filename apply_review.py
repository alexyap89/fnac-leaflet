#!/usr/bin/env /usr/bin/python3
"""Apply clinical-review corrections to index.html.

Addresses the 5 MAJOR defects plus the MINOR ones raised by the clinical
reviewer. Core principle applied throughout:

    The app may EXPLAIN the sheet. It may NOT add reassurance, expectation,
    frequency, duration or certainty that the sheet does not contain, and it
    must not label its own wording as the sheet's.

Every fabricated reassurance is removed. Where the app previously asserted
something it could not source, it now either drops the claim or attributes it
to the source that actually supports it (e.g. the fine needle comparison is a
general property of FNA needles, not a statement from the WH sheet, so it is
either removed or clearly framed as general context, not as sheet content).
"""
import re
import sys

path = "/home/alex/Documents/FNAC_Webapp/index.html"
h = open(path).read()
orig = h
edits = []


def sub(old, new, label, count=1):
    global h
    if old not in h:
        edits.append(("MISS", label))
        return
    h = h.replace(old, new, count)
    edits.append(("ok", label))


# ---------------------------------------------------------------- MAJOR 3
# "work out what the lump is" implies a definitive answer.
sub("""thyroid, so a pathologist can look at them under a microscope and work out what
    the lump is. This page explains what it is, what happens on the day, what you'll
    feel, and what comes after.""",
    """thyroid, so a pathologist can look at them under a microscope and see what kinds
    of cells they are. In most cases this helps your doctor decide what the lump is.
    In some cases the sample does not contain enough cells to be certain, and this
    page explains what happens then. It also covers what the test is, what happens
    on the day, what you may feel, and what comes after.""",
    "hero lede: remove implied diagnostic certainty")

# ---------------------------------------------------------------- MAJOR 1
# False reassurance that most nodules need nothing more than a check-up.
sub("""<div class="note">Thyroid nodules are common. Most people who have one never
    need anything more than monitoring.</div>""",
    """<div class="note">Many thyroid nodules are benign. Some are not, and no one can
    tell which without sampling the cells — which is why your doctor has asked for
    this test. Your doctor will discuss what your result means for you.</div>""",
    "section 1: remove 'never need anything more than a check-up'")

# ---------------------------------------------------------------- MAJOR 4
sub("""      <li>You may feel very little. Most people describe it as
      <strong>quick, and less uncomfortable than they expected</strong>.</li>""",
    """      <li>You may feel <strong>very little</strong>, or you may find it
      uncomfortable. It is a short procedure, but experiences differ — and if you
      are uncomfortable, tell the person doing it.</li>""",
    "section 4: remove invented 'less uncomfortable than expected'")

# ---------------------------------------------------------------- MAJOR 2
sub("""<div class="note">A non-diagnostic result does not mean something is wrong. It
    means there were not enough cells to be certain, and your doctor will discuss
    what to do next.</div>""",
    """<div class="note">A non-diagnostic result means the sample did not contain enough
    cells to give a clear answer. It is <strong>not the same as a normal result</strong>
    — it means the question has not yet been answered. Your doctor will discuss what
    to do next, which may include repeating the test.</div>""",
    "section 7: correct non-diagnostic framing")

# ---------------------------------------------------------------- MAJOR 5
# The "unchanged" attributions must be strictly true.
sub("""<b>Prototype — pending clinical approval.</b>
    This guide re-presents Woodlands Health's approved procedure information sheet
    for thyroid FNAC. It is not a substitute for talking with your doctor, and it
    does not replace the consent process. Risk and options wording is reproduced
    unchanged from the approved sheet and marked as such.""",
    """<b>Prototype — pending clinical approval.</b>
    This guide is based on Woodlands Health's procedure information sheet for
    thyroid FNAC (Version No: 01). Where text is quoted from that sheet it is
    marked <em>“From your information sheet — unchanged.”</em> Explanatory wording
    elsewhere in this guide is written for this page and is <strong>not</strong>
    part of the approved sheet. This guide is not a substitute for talking with
    your doctor, and it does not replace the consent process.""",
    "prototype banner: precise attribution")

sub("""<p>Clinical content is based on Woodlands Health's <strong>Procedure Information
    Sheet: Fine Needle Aspiration Cytology (FNAC) Thyroid (Version No: 01)</strong>.
    Risk and options wording appears unchanged from that sheet and is marked
    accordingly. Procedural description cross-checked against:</p>""",
    """<p>This guide is based on Woodlands Health's <strong>Procedure Information
    Sheet: Fine Needle Aspiration Cytology (FNAC) Thyroid (Version No: 01)</strong>.
    Text quoted from that sheet is marked <em>“From your information sheet —
    unchanged”</em>; everything else is explanatory wording written for this page.
    General procedural context was cross-checked against:</p>""",
    "about-this-page: precise attribution")

# The second "unchanged" block misquotes the sheet.
sub("""      The complications listed are not intended to be exhaustive and may vary
      depending on underlying medical condition. This list is NOT meant to be,
      and CANNOT be exhaustive.""",
    """      The complications listed are not intended to be exhaustive and may vary
      depending on underlying medical condition.""",
    "section 7: fix mislabelled verbatim block")

# ---------------------------------------------------------------- MINOR
# Invented duration and anaesthetic default.
sub("""<div class="fact"><div class="k">Usually takes</div><div class="v">10–20 minutes</div></div>
      <div class="fact"><div class="k">Anaesthetic</div><div class="v">Often not needed</div></div>
      <div class="fact"><div class="k">Needle size</div><div class="v">Very fine</div></div>
      <div class="fact"><div class="k">Results</div><div class="v">1–2 weeks</div></div>""",
    """<div class="fact"><div class="k">Needle</div><div class="v">Very fine</div></div>
      <div class="fact"><div class="k">Anaesthetic</div><div class="v">May be offered</div></div>
      <div class="fact"><div class="k">Passes</div><div class="v">Several</div></div>
      <div class="fact"><div class="k">Results</div><div class="v">1–2 weeks</div></div>""",
    "hero facts: remove unsupported duration/anaesthetic default")

sub("""<li>The needle goes in and out a few times. Most people find it quicker and
        less uncomfortable than they expected.</li>""",
    """<li>The needle goes in and out several times. It is a short procedure, though
        how much you feel it varies.</li>""",
    "short version: remove invented reassurance")

# "standard first test" / "same scanning that found the nodule"
sub("""    <p>FNAC is the standard first test for this. It gives your doctor real
    information — enough to decide whether you need treatment, further tests, or
    simply to be monitored.</p>""",
    """    <p>FNAC is commonly used for this. It gives your doctor information that
    imaging alone cannot provide — the type of cells in the nodule — which helps
    decide whether you need treatment, further tests, or monitoring.</p>""",
    "section 2: soften unsourced claims")

sub("""      placed accurately — using the same scanning that found the nodule.</p>""",
    """      placed accurately.</p>""",
    "section 5: remove unsourced 'same scanning' claim")

# needle gauge comparison — true in general but not from the sheet, so frame it
sub("""      <li><strong>A slight pin prick</strong> from the needle. It is finer than the
      needle used for a routine blood test.</li>""",
    """      <li><strong>A slight pin prick</strong> from the needle — as the information
      sheet describes it. A fine needle such as this is thinner than the one used for
      a routine blood test.</li>""",
    "section 4: frame the needle comparison as general, not sheet wording")

# fasting claim
sub("""<div class="check"><div class="box" aria-hidden="true"></div><div>You do not
    normally need to stop eating or drinking beforehand.</div></div>""",
    """<div class="check"><div class="box" aria-hidden="true"></div><div>Usually no
    prior preparation is required — but follow whatever your own doctor tells
    you.</div></div>""",
    "section 6: replace fasting claim with the sheet's own wording")

# editorial framing that softens the sheet's warning
sub("""    <p>Choosing not to have a procedure is a legitimate choice. Your doctor's role is
    to help you weigh it up, not to pressure you.</p>""",
    """    <p>You are entitled to ask questions and to take time to decide. Please discuss
    the options above with your doctor before making a decision.</p>""",
    "section 10: keep the sheet's warning force intact")

# risk badge frequency claim
sub("""        <span class="sev common">Can happen</span>""",
    """        <span class="sev common">Described in your sheet</span>""",
    "risk card: remove invented frequency ranking")

# step narration: invented procedural detail gets framed as illustration
sub('n:"You lie on your back with your head tipped gently back, so your neck is extended. Sometimes a pillow goes under your shoulders. This brings the thyroid closer to the surface and makes it easier to reach.",',
    'n:"You lie on your back with your head tipped gently back, so your neck is extended. This position brings the thyroid closer to the surface and makes it easier to reach. Your own team will tell you exactly how they would like you positioned.",',
    "step 1: frame positioning as illustrative")

sub('n:"The skin where the needle will go in may be marked with a pen, so it enters at the planned spot.",',
    'n:"The skin where the needle will go in may be marked, so it enters at the planned spot. This is an illustration of a typical approach — your team will explain exactly what they will do.",',
    "step 3: frame marking as illustrative")

sub('n:"The doctor scans your neck to find the thyroid gland and the exact nodule. Blood vessels along the needle path are checked so they can be avoided.",',
    'n:"The doctor scans your neck to find the thyroid gland and the exact nodule, and plans a path to it. This is why the needle can be placed accurately and safely.",',
    "step 2: remove unsourced vessel-check detail")

sub('n:"You may be given a local anaesthetic injection to numb the injection site. Many people do not need one — your doctor will decide with you.",',
    'n:"You may be given a local anaesthetic injection to numb the injection site. Whether you need one is a decision your doctor will make with you.",',
    "step 4: remove 'many people do not need one'")

open(path, "w").write(h)
print(f"edits applied: {len(edits)}")
for status, label in edits:
    print(f"  {status:4} {label}")
print()
print("size:", f"{len(orig):,} -> {len(h):,}")
missed = [l for s, l in edits if s == "MISS"]
if missed:
    print("\nMISSED:", missed)
    sys.exit(1)
