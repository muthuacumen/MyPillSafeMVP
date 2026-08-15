"""IMB1 (Pill Vision) -- C4 level-3 component diagram, A4 landscape, PDF.

Fourth in the set with `build_rx_reader_c4.py`, `build_bb3_c4.py` and
`build_sb2_c4.py`; shares their canvas, palette and legend idiom, and SB2's
three-state chip because IMB1 is mid-migration too. Standalone -- not the poster.

  LIVE         in production `IMB1_v0/` right now
  BUILT · OFF  exists in `NB08_Notebook/src/`, default-off, NOT promoted
  STEP 7       designed and specified, not wired into the deployed pipeline

Sources, all read 2026-08-12:
  * `IMB1_v0/CONTRACT.md` Sec1-3 -- the capture assumptions, the shipped record,
    and the NB07 measurement (including the shape head's real-photo penalty).
  * `IMB1_v0/imb1/` -- pipeline, card_calib, colour, shape_geom, ocr_sub.
  * `NB08_Notebook/src/nb08_presence.py` -- Stage 1 (A3), truth-free by
    construction: the three-way verdict is the model's own sentinel, consumed.
  * `NB08_Notebook/src/nb08_constrained.py` -- Stage 2 (A4c), closed-lexicon
    scoring; a read outside the ballot is impossible rather than merely rare.
  * `NB08_Notebook/src/nb08_lexicon.py` -- the ballot: profile DINs INTERSECT
    allowlist -> reference lookup -> lexicon + NULL; scoring vs recognition tier.
  * `NB08_Notebook/src/nb08_record.py` -- the C6 record + the C7 two-list guard.
  * `NB08_Notebook/specs/NB08_C6_Contract_Build.md` Sec1 -- three local models,
    two runtimes, one GPU; why Ollama cannot host A4c (no logprobs).
  * `NB08_Notebook/HANDOFF_2026-08-12.md` -- D-4 (the deployed pair, margin gate
    > 8.5949 strict) and the promotion state.

    python build_imb1_c4.py    ->  imb1-c4-a4.svg + .pdf + .png
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
    "off":  (AMBER, "BUILT · OFF"),
    "next": (GREY_S, "STEP 7"),
}

#: Tag colours for the card's right-hand chips.
CARD_TAGS = {"LIVE": GREEN, "STEP 7": GREY_S, "NEW": AMBER, "GONE": RED, "unchanged": GREY}
CARD_PITCH = 26


def tw(s: str, fs: float) -> float:
    return len(s) * fs * 0.53


BOXES: dict[str, dict] = {
    "patient": dict(
        cls="person", x=40, y=230, w=190, h=220,
        name=["Patient"], type=["[Person]"],
        desc=["Puts one pill on", "the capture card", "and shoots it"],
    ),

    # --- droplet -----------------------------------------------------------
    "api": dict(
        cls="cont", x=440, y=180, w=450, h=320,
        name=["API"], type=["[Container: FastAPI, Python]"],
        desc=["Hands the photo over; keeps none of it"],
        header_only=True,
    ),
    "route": dict(
        cls="comp", x=460, y=285, w=410, h=200, state="live",
        name=["Pill Route"], type=["[Component: POST /analyze/pill/v2]"],
        desc=["Forwards the photo and the DINs of",
              "medications the patient already",
              "approved. The pill photo is never stored."],
        ann=["ARRIVING (C7): the profile now has to reach",
             "IMB1 as well, because the reader's ballot is",
             "built from it. That inverts the old rule."],
    ),
    "db": dict(
        cls="store", x=440, y=545, w=450, h=195, state="live",
        name=["Database"], type=["[Container: PostgreSQL]"],
        desc=["Approved prescriptions — where", "the profile DINs come from"],
        ann=["Pill photos are never written here, or anywhere."],
    ),

    # --- brains host -------------------------------------------------------
    "imb1": dict(
        cls="cont", x=1170, y=175, w=870, h=600,
        name=["IMB1 — Pill Vision"],
        type=["[Container: IMB1_v0 — describes the pill; it never decides which medication it is]"],
        header_only=True,
    ),
    "detect": dict(
        cls="comp", x=1190, y=258, w=405, h=162, state="live",
        name=["Detector"], type=["[Component: FastSAM, zero-shot]"],
        desc=["Isolates the pill on the capture card.",
              "Detected 180 of 180 real photos."],
        ann=["The detector fine-tuned on studio images",
             "missed 28% of these. Zero-shot ships."],
    ),
    "colour": dict(
        cls="comp", x=1615, y=258, w=405, h=162, state="live",
        name=["Card Calibration & Colour"], type=["[Component: imb1.card_calib + imb1.colour]"],
        desc=["The card's printed patches white-balance",
              "the frame; the pill's corrected colour is",
              "looked up in a 13-class table."],
        ann=["Calculated, never learned."],
    ),
    "shape": dict(
        cls="comp", x=1190, y=440, w=405, h=162, state="live",
        name=["Shape & Type"], type=["[Component: imb1.shape_geom + the S2 CNN]"],
        desc=["11 outline classes, plus a geometry rule",
              "for the D-shape. Type is tablet or capsule,",
              "and carries the lowest weight of all."],
        ann=["Wins in a studio eval, and costs accuracy", "on real capture-card photos."],
    ),
    "ocr": dict(
        cls="comp", x=1615, y=440, w=405, h=162, state="live",
        name=["Imprint OCR"], type=["[Component: imb1.ocr_sub — torch-free subprocess]"],
        desc=["PaddleOCR twice over the same face: i1",
              "zero-shot and i3 CLAHE-enhanced. The two",
              "reads are complementary, never pre-fused."],
        ann=["torch and paddle cannot share one Windows", "process, so this is its own subprocess."],
    ),
    "lexicon": dict(
        cls="comp", x=1190, y=622, w=405, h=143, state="off",
        name=["Ballot Builder"], type=["[Component: nb08_lexicon]"],
        desc=["profile DINs ∩ allowlist → reference rows →",
              "a closed ballot, plus an explicit NULL."],
        ann=["Assembled per call. No product is named in code."],
    ),
    "record": dict(
        cls="comp", x=1615, y=622, w=405, h=143, state="off",
        name=["Record Builder"], type=["[Component: nb08_record — C6 + the C7 guard]"],
        desc=["Assembles the record SB2 consumes, and",
              "fails loudly if the two profiles disagree."],
        ann=["presence is consumed, never inferred."],
    ),

    "a3": dict(
        cls="cont", x=1170, y=815, w=420, h=180, state="next",
        name=["A3 — Presence Gate"], type=["[Container: Qwen3-VL 8.8B, via Ollama]"],
        desc=["Stage 1. Answers one question about the",
              "face: is there an imprint at all?",
              "TEXT  ·  UNREADABLE  ·  NONE"],
        ann=["The three-way verdict is the model's own", "sentinel, and it is consumed, not re-derived."],
    ),
    "a4c": dict(
        cls="cont", x=1630, y=815, w=410, h=180, state="next",
        name=["A4c — Ballot Reader"], type=["[Container: Qwen3-VL 4B NF4, transformers]"],
        desc=["Stage 2. Does not generate a string: it",
              "scores the closed ballot and returns the",
              "winner with a PMI margin."],
        ann=["Under transformers, not Ollama: Ollama exposes", "no logprobs, and the margin IS the safety."],
    ),
    "ref": dict(
        cls="store", x=1170, y=1025, w=870, h=150, state="off",
        name=["Reference & Allowlist"], type=["[Data store: ca_appearance_harmonized_v3.xlsx  +  supported_dins.csv]"],
        desc=["The ballot's vocabulary: which products exist, and which of them are supported"],
    ),
}

BOUNDARIES = [
    ("Droplet — public internet, mypillsafe.ca", 420, 125, 490, 635),
    ("Brains Host — private network, GPU, never public", 1150, 125, 910, 1073),
]

EDGES = [
    ([(230, 280), (440, 280)], ["Photographs a pill", "[HTTPS]"], (335, 228), False, (262, 280, "1"), ""),
    ([(440, 400), (230, 400)], ["What it saw,", "and what SB2 made of it"], (335, 348), False, (408, 400, "6"), ""),

    ([(890, 250), (1170, 250)], ["POST /pill/analyze —", "the photo + profile DINs"], (1030, 198), False, (922, 250, "2"), ""),
    ([(1170, 330), (890, 330)], ["the record — see the card,", "lower left"], (1030, 278), True, None, ""),

    ([(665, 500), (665, 545)], ["reads the approved DINs"], (665, 535), False, None, ""),

    # into the two-stage reader, and back
    ([(1300, 775), (1300, 815)], ["the face crop"], (1213, 800), False, (1300, 795, "3"), ""),
    ([(1560, 775), (1560, 792), (1750, 792), (1750, 815)], ["the closed ballot"], (1700, 802), False, (1560, 792, "4"), ""),
    ([(1590, 905), (1630, 905)], ["TEXT ⇒ read it"], (1610, 878), False, (1610, 930, "5"), ""),
    ([(1960, 815), (1960, 775)], ["the read"], (1960, 800), True, None, ""),

    # the ballot's vocabulary, routed down the channel left of IMB1
    ([(1190, 745), (1160, 745), (1160, 1100), (1170, 1100)],
     ["profile DINs ∩ allowlist", "→ the reference rows"], (1050, 1075), False, None, ""),

    # inside IMB1
    ([(1595, 339), (1615, 339)], [], (0, 0), False, None, "inner"),
    ([(1392, 420), (1392, 440)], [], (0, 0), False, None, "inner"),
    ([(1822, 420), (1822, 440)], [], (0, 0), False, None, "inner"),
    ([(1822, 602), (1822, 622)], [], (0, 0), False, None, "inner"),
    ([(1595, 693), (1615, 693)], ["lexicon_id"], (1605, 672), False, None, "inner"),
]

CARD_TITLE = "The four attributes — how each one is actually produced"
CARD_ROWS = [
    ("Detection — FastSAM, zero-shot. The detector we fine-tuned collapsed on real photos.", "LIVE"),
    ("Colour — calculated: card patches → white balance → CIELAB → a 13-class lookup.", "LIVE"),
    ("Shape + type — an S2 CNN over the mask, with a geometry rule for the D-shape.", "LIVE"),
    ("Imprint — PaddleOCR twice, i1 zero-shot and i3 CLAHE. Complementary, never pre-fused.", "LIVE"),
    ("", ""),
    ("Imprint, arriving — A3 says whether text is there; A4c ranks a closed ballot.", "STEP 7"),
    ("      TEXT, and margin > 8.5949   →   a read that carries 0.55 into SB2", "STEP 7"),
    ("      TEXT but gated → no read  ·  UNREADABLE → reshoot  ·  NONE → out of scope", "STEP 7"),
]
CARD_FOOT = ("Zero-shot beat fine-tuned on two of the three trained heads. That result is the paper, "
             "not a footnote.")
CARD_BOX = (40, 800, 900, 350)

NOTES_Y, NOTES_H = 1215, 95
NOTES = [
    ("Zero-shot won twice, and it was measured",
     ["The fine-tuned detector missed pills the zero-shot one found, and the trained",
      "shape head wins in a studio eval while costing accuracy on real photos."]),
    ("Colour is measured, not classified",
     ["The card's printed patches white-balance the frame before the colour is",
      "looked up. No training set gets a vote on what colour a pill is."]),
    ("Two stages, two runtimes, one GPU",
     ["A3 asks whether an imprint exists; A4c ranks a ballot and reports a margin.",
      "They are different models on different runtimes, swapped on demand."]),
]

STATEKEY_Y = 1330
LEGEND_Y = 1368

LEGEND = [
    ("person", "Person"),
    ("cont",   "Container"),
    ("comp",   "Component"),
    ("store",  "Data store"),
    ("solid",  "Request"),
    ("dashed", "Response"),
]

STATE_KEY = [
    ("live", "in production IMB1_v0/ today"),
    ("off",  "in NB08_Notebook/src/, default-off, not promoted"),
    ("next", "specified, not wired into the pipeline"),
]

TITLE = "Pill Vision (IMB1) — Component Diagram (C4 level 3)"
SUBTITLE = ("What ships today, what is built but switched off, and how the two-stage reader arriving behind "
            "it changes the imprint — as of 2026-08-12.")
FOOTER = ("MyPillSafe  ·  Pill Vision, brain 2 of 5  ·  C4 level 3, components  ·  "
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
        cy = y + h - 30 if b.get("chip_bottom") else y + (30 if cls == "store" else 10)
        o.append(chip_svg(b["state"], x + w - 10, cy))
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
        if text:
            check(text, 15.5, w - 200, "card.row")
            o.append(f'<text x="{x+22}" y="{ry}" class="kr">{esc(text)}</text>')
        if tag:
            fill = CARD_TAGS[tag]
            twid = tw(tag, 12) + 18
            o.append(f'<rect x="{x+w-22-twid}" y="{ry-14}" width="{twid}" height="19" rx="9.5" fill="{fill}"/>')
            o.append(f'<text x="{x+w-22-twid/2}" y="{ry-1}" class="ch">{esc(tag)}</text>')
        ry += CARD_PITCH
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

    for bid in ("patient", "api", "db", "imb1", "a3", "a4c", "ref"):
        p.append(box_svg(bid))
    for bid in ("route", "detect", "colour", "shape", "ocr", "lexicon", "record"):
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
    render(build(), Path(__file__).with_name("imb1-c4-a4"))
    for w in WARNINGS:
        print("  OVERFLOW  " + w.encode("ascii", "replace").decode())
    print(f"canvas {W}x{H} units = 297x210 mm  ({1/MM_PER_UNIT:.2f} units/mm)")
