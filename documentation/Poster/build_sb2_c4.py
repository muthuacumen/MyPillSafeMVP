"""SB2 (Deterministic Matcher) -- C4 level-3 component diagram, A4 landscape, PDF.

Third in the set with `build_rx_reader_c4.py` and `build_bb3_c4.py`: same canvas,
palette and legend idiom. Standalone -- not part of the poster.

WHY THIS ONE CARRIES A STATE KEY
--------------------------------
SB2 is mid-migration, so a single-state drawing would be wrong on 2026-08-12
whichever state it chose. Every box therefore carries a chip saying what it is
TODAY, and annotations prefixed "ARRIVING:" say what the v3 / C6 / C7 / C8 work
changes. The three states are:

  LIVE         in production `SB2/` right now
  BUILT · OFF  exists in `SB2_Prototype/`, default-off, NOT promoted
  STEP 7       designed and specified, not built

Sources, all read 2026-08-12:
  * `SB2/CONTRACT.md` Sec1-7 -- the shipped record, weights, thresholds, the
    three decision states and the two abstain actions.
  * `SB2/sb2/matcher.py` -- WEIGHTS/THRESH, the scorers, LOGO handling.
  * `SB2_Prototype/sb2/__init__.py` -- `match_pill` RAISES NotImplementedError
    on a `contract_version == "C6"` record today; `sb2/c6_flip.py` is built and
    default-off.
  * `NB08_Notebook/specs/NB08_C6_Contract_Build.md` -- C6 (faces/presence/
    margin), C7 (profile flows into IMB1 + the two-list guard), C8 (allowlist,
    11 supported / 4 excluded, final 2026-08-11), Sec6 (three UI messages).
  * `NB08_Notebook/specs/NB08_C5_Reference_Schema_Build.md` Sec1 + Sec12 --
    `ca_appearance_harmonized_v3.xlsx`, 7,055 x 53, additive, gold-15 populated.
  * `NB08_Notebook/HANDOFF_2026-08-12.md` -- promotion state, D-1..D-4.
  * `PillSafe/dev/backend/app/api/v1/routes/pill.py` + `dev/brains/app.py` --
    the live route names.

    python build_sb2_c4.py    ->  sb2-c4-a4.svg + .pdf + .png
"""
from __future__ import annotations

import subprocess
from pathlib import Path

W, H = 2100, 1485
MM_PER_UNIT = 297.0 / W

NAVY   = "#1E3A5F"
NAVY_S = "#16293F"
GREY   = "#8B99A6"
GREY_S = "#6F7C87"
TEAL   = "#2A9D8F"
TEAL_S = "#1F7A6E"
AMBER  = "#E09B3D"
GREEN  = "#2E7D5B"
RED    = "#D64045"
LINE   = "#7A8894"
BND    = "#9AA4AD"
BNDTXT = "#5A6570"
INNER  = "#9FB6CC"
INNERT = "#CBDAE7"
NOTE_B = "#D8E0E7"
NOTE_F = "#F7F9FB"
CARD_B = "#E09B3D"
CARD_F = "#FDF8F1"

FS_TITLE, FS_SUB = 40, 20
FS_NAME, FS_TYPE, FS_DESC, FS_ANN = 23, 15, 17, 14.5
FS_CNAME, FS_CTYPE, FS_CDESC = 19, 14, 15.5
FS_EDGE, FS_BND, FS_LEG, FS_FOOT = 16, 19, 16, 15
FS_CHIP = 12

LH_NAME, LH_TYPE, LH_DESC, LH_ANN = 28, 19, 21, 18
LH_CNAME, LH_CTYPE, LH_CDESC = 24, 18, 20

STATES = {
    "live": (GREEN, "LIVE"),
    "off":  (AMBER, "BUILT \u00b7 OFF"),
    "next": (GREY_S, "STEP 7"),
}


def tw(s: str, fs: float) -> float:
    return len(s) * fs * 0.53


BOXES: dict[str, dict] = {
    "patient": dict(
        cls="person", x=40, y=250, w=190, h=220,
        name=["Patient"], type=["[Person]"],
        desc=["Photographs one", "loose pill on the", "capture card"],
    ),

    # --- droplet -----------------------------------------------------------
    "api": dict(
        cls="cont", x=440, y=180, w=450, h=485,
        name=["API"], type=["[Container: FastAPI, Python]"],
        desc=["Sends the photo and the patient's own DINs"],
        header_only=True,
    ),
    "route": dict(
        cls="comp", x=460, y=285, w=410, h=180, state="live",
        name=["Pill Route"], type=["[Component: POST /analyze/pill/v2]"],
        desc=["Sends the photo and the DINs of",
              "medications the patient already",
              "approved. Pill photos are never stored."],
        ann=["ARRIVING (C7): one profile object must reach",
             "IMB1 and SB2, or the boundary fails loudly."],
    ),
    "presenter": dict(
        cls="comp", x=460, y=485, w=410, h=160, state="live",
        name=["Result Presenter"], type=["[Component: app UI]"],
        desc=["Shows every ranked candidate and the",
              "abstain action — never a bare yes/no."],
        ann=["ARRIVING: three messages are built and",
             "nothing renders them yet."],
    ),
    "db": dict(
        cls="store", x=440, y=700, w=450, h=195, state="live",
        name=["Database"], type=["[Container: PostgreSQL]"],
        desc=["Approved prescriptions — where", "the profile DINs come from"],
        ann=["The DIN join happens once, at prescription time."],
    ),

    # --- brains host -------------------------------------------------------
    "imb1": dict(
        cls="cont", x=1170, y=175, w=870, h=145, state="live",
        name=["Pill Vision (IMB1)"],
        type=["[Container: IMB1_v0 — FastSAM · colorimetric colour · shape CNN · imprint OCR]"],
        desc=["Describes the pill. It never decides which medication it is."],
        ann=["ARRIVING: a two-stage reader — A3 (Qwen3-VL 8.8B, Ollama) says whether text is present at all;",
             "A4c (Qwen3-VL 4B, transformers) ranks a closed lexicon built from this patient's own candidates."],
    ),
    "sb2": dict(
        cls="cont", x=1170, y=360, w=870, h=600,
        name=["SB2 — Deterministic Matcher"],
        # No desc line: the header must clear row 1, which starts at y=445.
        type=["[Container: sb2 package — no model, no retrieval, no network, no cloud key]"],
        header_only=True,
    ),
    "cand": dict(
        cls="comp", x=1190, y=445, w=405, h=180, state="live",
        name=["Candidate Builder"], type=["[Component: sb2.reference]"],
        desc=["Joins the profile's DINs to their",
              "reference rows — typically five,",
              "never the 7,055-row formulary."],
        ann=["ARRIVING (C8): an allowlist of 11 supported",
             "and 4 excluded. An unsupported member of",
             "the profile is surfaced, never dropped."],
    ),
    "flip": dict(
        cls="comp", x=1615, y=445, w=405, h=180, state="off",
        name=["Face & Flip Resolver"], type=["[Component: sb2.c6_flip]"],
        desc=["Maps each photographed face onto the",
              "reference's ordered sides, and decides",
              "when to ask for the other face."],
        ann=["IMB1 never says which side it photographed:",
             "which side a face IS is the reference's",
             "business, and it is settled here."],
    ),
    "appearance": dict(
        cls="comp", x=1190, y=645, w=405, h=180, state="live",
        name=["Appearance Scorers"], type=["[Component: sb2.matcher]"],
        desc=["colour 0.25 · shape 0.15 · type 0.05.",
              "Colour is compared as a set; a mismatch",
              "scores zero and never rejects alone."],
        ann=["Without an imprint the ceiling is 0.45",
             "against an accept gate of 0.70 — appearance",
             "alone can never verify, and v3 keeps it so."],
    ),
    "imprint": dict(
        cls="comp", x=1615, y=645, w=405, h=180, state="live",
        name=["Imprint Scorer"], type=["[Component: sb2.matcher — 0.55 of the score]"],
        desc=["Exact tier, then fuzzy above 0.80.",
              "LOGO is a reference value, not an OCR",
              "failure: reading nothing off it matches."],
        ann=["ARRIVING: the dual i1+i3 fusion gives way",
             "to one gated read. gated=true means NO",
             "read — that flag IS the safety mechanism."],
    ),
    "decision": dict(
        cls="comp", x=1190, y=845, w=830, h=100, state="live",
        name=["Decision Gate"],
        type=["[Component: sb2.matcher — THRESH: accept 0.70 · reject 0.25 · margin 0.05]"],
        desc=["verify   ·   reject   ·   abstain → ask_to_flip  or  shortlist",
              "Tuned to minimise false accepts; abstaining is the common case here, not an edge case."],
    ),
    "ref": dict(
        cls="store", x=1170, y=990, w=430, h=195, state="off",
        name=["Reference Data"], type=["[Data store: ca_appearance_harmonized_v3.xlsx]"],
        desc=["7,055 rows × 53 columns, additive —", "every v2 column retained."],
        ann=["Real values on the 15 gold OTC DINs only."],
    ),
    "allow": dict(
        cls="store", x=1620, y=990, w=420, h=195, state="next",
        name=["Supported DINs"], type=["[Data store: supported_dins.csv]"],
        desc=["Configuration Muthu owns:", "din · status · reason · evidence."],
        ann=["Confusable pairs enter and leave together."],
    ),
}

BOUNDARIES = [
    ("Droplet — public internet, mypillsafe.ca", 420, 125, 490, 795),
    ("Brains Host — private network, GPU, never public", 1150, 125, 910, 1085),
]

EDGES = [
    ([(230, 300), (440, 300)], ["Photographs a pill", "[HTTPS]"], (335, 248), False, (262, 300, "1"), ""),
    ([(440, 420), (230, 420)], ["What it decided,", "and why"], (335, 368), False, (408, 420, "5"), ""),

    ([(890, 250), (1170, 250)], ["POST /pill/analyze —", "the photo + profile DINs"], (1030, 198), False, (922, 250, "2"), ""),
    ([(1170, 520), (890, 520)], ["verify · reject · abstain", "+ every ranked candidate"], (1030, 468), True, None, ""),

    ([(665, 665), (665, 700)], ["reads the approved DINs"], (665, 690), False, None, ""),

    ([(1605, 320), (1605, 360)], ["the record — see the contract card, lower left"], (1665, 348), False, (1400, 340, "3"), ""),

    ([(1595, 535), (1615, 535)], [], (0, 0), False, None, "inner"),
    ([(1392, 625), (1392, 645)], [], (0, 0), False, None, "inner"),
    ([(1822, 625), (1822, 645)], [], (0, 0), False, None, "inner"),
    ([(1392, 825), (1392, 845)], [], (0, 0), False, (1392, 835, "4"), "inner"),
    ([(1822, 825), (1822, 845)], [], (0, 0), False, None, "inner"),

    ([(1385, 960), (1385, 990)], ["Reads the profile's reference rows"], (1385, 980), False, None, ""),
    ([(1830, 960), (1830, 990)], ["Which products are supported"], (1830, 980), False, None, ""),
]

# The contract card -- (text, tag).  tag: "" | "unchanged" | "NEW" | "GONE"
CARD_TITLE = "The IMB1 → SB2 record — what the C6 contract changes"
CARD_ROWS = [
    ("colour_modes  ·  shape_out + conf  ·  type_out + conf", "unchanged"),
    ("faces[ ]  — one entry per face actually photographed", "NEW"),
    ("     face_id  — opaque; never side1/side2, SB2 resolves the side", "NEW"),
    ("     presence  — TEXT | UNREADABLE | NONE, from the A3 gate and only there", "NEW"),
    ("     read{ top1, margin, gated, threshold, lexicon_id }", "NEW"),
    ("imprint_reads{ i1, i3 }  — diagnostic only, out of the input contract", "GONE"),
    ("contract_version: “C6”  — so a consumer can refuse what it cannot read", "NEW"),
]
CARD_FOOT = ("Today match_pill RAISES on a C6 record rather than mis-score it. Step 7 turns this "
             "contract into a pipeline.")
CARD_BOX = (40, 940, 960, 245)

NOTES_Y, NOTES_H = 1230, 95
NOTES = [
    ("SB2 verifies; it does not identify",
     ["It only ever compares a pill against the patient's own medications.",
      "Open-set identification across the formulary was measured, and rejected."]),
    ("The thesis narrowed on 2026-08-12",
     ["SB2 no longer re-derives the imprint — the reader does that. SB2",
      "independently REFUSES; that refusal is what it contributes."]),
    ("None of this is promoted yet",
     ["Production SB2/ is content-hash identical to the 2026-08-10 snapshot.",
      "Promotion is a schema migration, not a file copy."]),
]

STATEKEY_Y = 1345
LEGEND_Y = 1385

LEGEND = [
    ("person", "Person"),
    ("cont",   "Container"),
    ("comp",   "Component"),
    ("store",  "Data store"),
    ("solid",  "Request"),
    ("dashed", "Response"),
]

STATE_KEY = [
    ("live", "in production SB2/ today"),
    ("off",  "in SB2_Prototype/, default-off, not promoted"),
    ("next", "specified, not built — see the handoff"),
]

TITLE = "Deterministic Matcher (SB2) — Component Diagram (C4 level 3)"
SUBTITLE = ("What ships today, what is built but switched off, and what the v3 reference and the C6 record "
            "change — as of 2026-08-12.")
FOOTER = ("MyPillSafe  ·  Deterministic Matcher, brain 3 of 5  ·  C4 level 3, components  ·  "
          "drawn from the shipped code and the NB08 specs, 2026-08-12")

WARNINGS: list[str] = []


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def check(text: str, fs: float, avail: float, where: str) -> None:
    if tw(text, fs) > avail:
        WARNINGS.append(f"{where}: {tw(text, fs):.0f}u > {avail:.0f}u  {text!r}")


def chip_svg(state: str, x: float, y: float) -> str:
    """The state pill, top-right inside a box."""
    fill, label = STATES[state]
    w = tw(label, FS_CHIP) + 20
    return (f'<rect x="{x-w}" y="{y}" width="{w}" height="20" rx="10" fill="{fill}"/>'
            f'<text x="{x-w/2}" y="{y+14}" class="ch">{esc(label)}</text>')


def box_svg(bid: str) -> str:
    b = BOXES[bid]
    cls, x, y, w, h = b["cls"], b["x"], b["y"], b["w"], b["h"]
    fill, stroke = {"person": (GREY, GREY_S), "cont": (NAVY, NAVY_S),
                    "store": (NAVY, NAVY_S), "comp": (TEAL, TEAL_S)}[cls]

    o: list[str] = []
    top_pad = bot_pad = 0
    if cls == "store":
        ry = 18
        bot_pad = ry + 4
        o.append(f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 1 {w},0 v{h-2*ry} '
                 f'a{w/2},{ry} 0 0 1 {-w},0 z" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        o.append(f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 0 {w},0" fill="none" '
                 f'stroke="#43617F" stroke-width="1.8"/>')
        top_pad = 2 * ry + 6
    else:
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')

    comp = cls == "comp"
    fs_n, fs_t, fs_d = (FS_CNAME, FS_CTYPE, FS_CDESC) if comp else (FS_NAME, FS_TYPE, FS_DESC)
    lh_n, lh_t, lh_d = (LH_CNAME, LH_CTYPE, LH_CDESC) if comp else (LH_NAME, LH_TYPE, LH_DESC)
    cls_n, cls_t, cls_d = ("cn", "ct", "cd") if comp else ("nm", "tp", "ds")

    names, types, body = b["name"], b["type"], b.get("desc", [])
    ann = b.get("ann", [])
    avail = w - (30 if comp else 34)
    for ln in names:
        check(ln, fs_n, avail, f"{bid}.name")
    for ln in types:
        check(ln, fs_t, avail, f"{bid}.type")
    for ln in body:
        check(ln, fs_d, avail, f"{bid}.body")
    for ln in ann:
        check(ln, FS_ANN, avail, f"{bid}.ann")

    block = (lh_n * len(names) + 5 + lh_t * len(types) + 8 + lh_d * len(body)
             + (10 + LH_ANN * len(ann) if ann else 0))
    ty = y + 32 if b.get("header_only") else \
        y + top_pad + (h - top_pad - bot_pad - block) / 2 + lh_n - 7
    cx = x + w / 2

    for ln in names:
        o.append(f'<text x="{cx}" y="{ty}" class="{cls_n}">{esc(ln)}</text>')
        ty += lh_n
    ty += 5
    for ln in types:
        o.append(f'<text x="{cx}" y="{ty}" class="{cls_t}">{esc(ln)}</text>')
        ty += lh_t
    ty += 8
    for ln in body:
        o.append(f'<text x="{cx}" y="{ty}" class="{cls_d}">{esc(ln)}</text>')
        ty += lh_d
    if ann:
        ty += 10
        acls = "anc" if comp else "an"
        for ln in ann:
            o.append(f'<text x="{cx}" y="{ty}" class="{acls}">{esc(ln)}</text>')
            ty += LH_ANN

    if b.get("state"):
        o.append(chip_svg(b["state"], x + w - 10, y + (30 if cls == "store" else 10)))
    return "\n".join(o)


def edge_svg(pts, lines, anchor, dashed, badge, style) -> str:
    col = INNER if style == "inner" else LINE
    o = []
    d = " ".join(f"{px},{py}" for px, py in pts)
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    head = "ah_inner" if style == "inner" else "ah"
    o.append(f'<polyline points="{d}" fill="none" stroke="{col}" '
             f'stroke-width="{1.7 if style == "inner" else 2.1}"{dash} marker-end="url(#{head})"/>')
    if lines:
        ax, ay = anchor
        bw = max(tw(ln, FS_EDGE) for ln in lines) + 14
        back = NAVY if style == "inner" else "#FFFFFF"
        o.append(f'<rect x="{ax-bw/2}" y="{ay-FS_EDGE+1}" width="{bw}" '
                 f'height="{FS_EDGE*1.3*len(lines)+6}" fill="{back}"/>')
        klass = "eli" if style == "inner" else "el"
        for i, ln in enumerate(lines):
            o.append(f'<text x="{ax}" y="{ay + i*FS_EDGE*1.3}" class="{klass}">{esc(ln)}</text>')
    if badge:
        bx, by, num = badge
        o.append(f'<circle cx="{bx}" cy="{by}" r="14" fill="{NAVY}" stroke="#FFFFFF" stroke-width="2"/>')
        o.append(f'<text x="{bx}" y="{by+6}" class="bg">{num}</text>')
    return "\n".join(o)


def card_svg(x: float, y: float, w: float, h: float) -> str:
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{CARD_F}" '
         f'stroke="{CARD_B}" stroke-width="2"/>']
    check(CARD_TITLE, 19, w - 44, "card.title")
    o.append(f'<text x="{x+22}" y="{y+34}" class="kt">{esc(CARD_TITLE)}</text>')
    ry = y + 66
    for text, tag in CARD_ROWS:
        check(text, 15.5, w - 200, "card.row")
        o.append(f'<text x="{x+22}" y="{ry}" class="kr">{esc(text)}</text>')
        if tag:
            fill = {"NEW": AMBER, "GONE": RED, "unchanged": GREY}[tag]
            twid = tw(tag, 12) + 18
            o.append(f'<rect x="{x+w-22-twid}" y="{ry-14}" width="{twid}" height="19" rx="9.5" fill="{fill}"/>')
            o.append(f'<text x="{x+w-22-twid/2}" y="{ry-1}" class="ch">{esc(tag)}</text>')
        ry += 23
    check(CARD_FOOT, 15, w - 44, "card.foot")
    o.append(f'<text x="{x+22}" y="{ry+14}" class="kf">{esc(CARD_FOOT)}</text>')
    return "\n".join(o)


def swatch(kind: str, x: float, y: float) -> str:
    if kind == "store":
        sw, sh, ry = 38, 24, 6
        return (f'<path d="M{x},{y+ry} a{sw/2},{ry} 0 0 1 {sw},0 v{sh-2*ry} '
                f'a{sw/2},{ry} 0 0 1 {-sw},0 z" fill="{NAVY}" stroke="{NAVY_S}" stroke-width="1.4"/>')
    if kind in ("solid", "dashed"):
        dash = ' stroke-dasharray="7 5"' if kind == "dashed" else ""
        return (f'<line x1="{x}" y1="{y+12}" x2="{x+34}" y2="{y+12}" stroke="{LINE}" '
                f'stroke-width="2.1"{dash} marker-end="url(#ah)"/>')
    fill, stroke = {"person": (GREY, GREY_S), "cont": (NAVY, NAVY_S), "comp": (TEAL, TEAL_S)}[kind]
    return (f'<rect x="{x}" y="{y}" width="38" height="24" rx="3" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.4"/>')


def build() -> str:
    p: list[str] = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="Arial, Helvetica, sans-serif">')
    p.append(f"""<defs>
  <marker id="ah" markerWidth="10" markerHeight="8" refX="9.5" refY="4" orient="auto">
    <polygon points="0,0 10,4 0,8" fill="{LINE}"/></marker>
  <marker id="ah_inner" markerWidth="10" markerHeight="8" refX="9.5" refY="4" orient="auto">
    <polygon points="0,0 10,4 0,8" fill="{INNER}"/></marker>
</defs>
<style>
  .ti {{ font-size:{FS_TITLE}px; font-weight:700; fill:#12283F; }}
  .su {{ font-size:{FS_SUB}px; fill:#4A5966; }}
  .nm {{ font-size:{FS_NAME}px; font-weight:700; fill:#FFFFFF; text-anchor:middle; }}
  .tp {{ font-size:{FS_TYPE}px; fill:#DCE4EC; text-anchor:middle; }}
  .ds {{ font-size:{FS_DESC}px; fill:#EAF0F5; text-anchor:middle; }}
  .cn {{ font-size:{FS_CNAME}px; font-weight:700; fill:#FFFFFF; text-anchor:middle; }}
  .ct {{ font-size:{FS_CTYPE}px; fill:#E4F5F1; text-anchor:middle; }}
  .cd {{ font-size:{FS_CDESC}px; fill:#F1FAF8; text-anchor:middle; }}
  .an {{ font-size:{FS_ANN}px; font-style:italic; fill:#C3D2DF; text-anchor:middle; }}
  .anc {{ font-size:{FS_ANN}px; font-style:italic; fill:#D7F2EB; text-anchor:middle; }}
  .el {{ font-size:{FS_EDGE}px; fill:#3E4B57; text-anchor:middle; }}
  .eli {{ font-size:{FS_EDGE}px; fill:{INNERT}; text-anchor:middle; }}
  .bg {{ font-size:16px; font-weight:700; fill:#FFFFFF; text-anchor:middle; }}
  .ch {{ font-size:{FS_CHIP}px; font-weight:700; fill:#FFFFFF; text-anchor:middle; }}
  .bd {{ font-size:{FS_BND}px; fill:{BNDTXT}; }}
  .lg {{ font-size:{FS_LEG}px; fill:#33404B; }}
  .kt {{ font-size:19px; font-weight:700; fill:#12283F; }}
  .kr {{ font-size:15.5px; fill:#2B3742; }}
  .kf {{ font-size:15px; font-style:italic; fill:#6B5433; }}
  .nt {{ font-size:16px; font-weight:700; fill:#1E3A5F; }}
  .nb {{ font-size:15px; fill:#3E4B57; }}
  .ft {{ font-size:{FS_FOOT}px; fill:#6F7C87; }}
</style>""")
    p.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

    p.append(f'<text x="40" y="62" class="ti">{esc(TITLE)}</text>')
    check(SUBTITLE, FS_SUB, W - 90, "subtitle")
    p.append(f'<text x="40" y="100" class="su">{esc(SUBTITLE)}</text>')

    for label, x, y, w, h in BOUNDARIES:
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="none" '
                 f'stroke="{BND}" stroke-width="1.6" stroke-dasharray="9 6"/>')
        p.append(f'<text x="{x+18}" y="{y+28}" class="bd">{esc(label)}</text>')

    for bid in ("patient", "api", "db", "imb1", "sb2", "ref", "allow"):
        p.append(box_svg(bid))
    for bid in ("route", "presenter", "cand", "flip", "appearance", "imprint", "decision"):
        p.append(box_svg(bid))
    for pts, lines, anchor, dashed, badge, style in EDGES:
        p.append(edge_svg(pts, lines, anchor, dashed, badge, style))

    p.append(card_svg(*CARD_BOX))

    nw, gap = (W - 80 - 2 * 30) / 3, 30
    for i, (title, body) in enumerate(NOTES):
        x = 40 + i * (nw + gap)
        p.append(f'<rect x="{x}" y="{NOTES_Y}" width="{nw}" height="{NOTES_H}" rx="4" '
                 f'fill="{NOTE_F}" stroke="{NOTE_B}" stroke-width="1.4"/>')
        check(title, 16, nw - 36, "note.title")
        p.append(f'<text x="{x+18}" y="{NOTES_Y+28}" class="nt">{esc(title)}</text>')
        for j, ln in enumerate(body):
            check(ln, 15, nw - 36, "note.body")
            p.append(f'<text x="{x+18}" y="{NOTES_Y + 54 + j*22}" class="nb">{esc(ln)}</text>')

    # state key row
    kcell = (W - 80) / 3
    for i, (state, text) in enumerate(STATE_KEY):
        x = 40 + i * kcell
        cw = tw(STATES[state][1], FS_CHIP) + 20
        p.append(chip_svg(state, x + cw, STATEKEY_Y))
        check(text, FS_LEG, kcell - cw - 30, "statekey")
        p.append(f'<text x="{x+cw+14}" y="{STATEKEY_Y+15}" class="lg">{esc(text)}</text>')

    ly = LEGEND_Y
    cell = (W - 80) / len(LEGEND)
    p.append(f'<line x1="40" y1="{ly}" x2="{W-40}" y2="{ly}" stroke="{NOTE_B}" stroke-width="1.4"/>')
    for i, (kind, text) in enumerate(LEGEND):
        x = 40 + i * cell
        p.append(swatch(kind, x, ly + 16))
        p.append(f'<text x="{x+50}" y="{ly+34}" class="lg">{esc(text)}</text>')

    p.append(f'<text x="40" y="{ly+84}" class="ft">{esc(FOOTER)}</text>')
    p.append("</svg>")
    return "\n".join(p)


CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def render(svg_text: str, stem: Path) -> None:
    svg_path = stem.with_suffix(".svg")
    svg_path.write_text(svg_text, encoding="utf-8")

    shell = stem.parent / f"_{stem.name}_print.html"
    shell.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "@page{size:A4 landscape;margin:0}"
        "html,body{margin:0;padding:0;background:#fff;"
        "-webkit-print-color-adjust:exact;print-color-adjust:exact}"
        "svg{display:block;width:297mm;height:210mm}"
        "</style></head><body>" + svg_text + "</body></html>", encoding="utf-8")

    pdf = stem.with_suffix(".pdf")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", shell.resolve().as_uri()], check=True)

    png = stem.with_suffix(".png")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={W},{H}", "--force-device-scale-factor=3",
                    f"--screenshot={png}", svg_path.resolve().as_uri()], check=True)
    shell.unlink()
    print(f"wrote {svg_path.name}, {pdf.name}, {png.name}")


if __name__ == "__main__":
    render(build(), Path(__file__).with_name("sb2-c4-a4"))
    for w in WARNINGS:
        print("  OVERFLOW  " + w.encode("ascii", "replace").decode())
    print(f"canvas {W}x{H} units = 297x210 mm  ({1/MM_PER_UNIT:.2f} units/mm)")
