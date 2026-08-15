"""Prescription Reader -- C4 level-3 (component) diagram, A4 landscape, as PDF.

Standalone: this page is NOT part of the poster and shares no geometry with
`build_c4_svg.py` (the level-2 container view). It exists to answer one
question the public page raises but does not draw:

    mypillsafe.ca/about/brains/prescription-reader says "Local qwen2.5:7b --
    what MyPillSafe uses" and "Shipped pipeline -- proposer + six
    deterministic guardrails". WHERE do those two things sit?

Answer, verified against the shipped code 2026-08-12:

  * The container literally named "Prescription OCR Worker" is PaddleOCR and
    nothing else -- `dev/brains/rx_ocr_sub.py`, a torch-free subprocess that
    turns a photo into raw text. It never sees qwen and never sees a guard.
  * qwen2.5:7b is a SIBLING container: Ollama on the same private host,
    reached over HTTP by `dev/brains/rx_extract.py` (POST /rx/extract).
  * The six guardrails are not on that host at all. They are
    `dev/backend/app/services/rx_guardrails.py` on the public droplet, and
    `routes/prescriptions.py::_propose_medications` runs them over BOTH
    proposers (qwen and the regex fallback).

So the drawn boundary is the whole read -> propose -> guard -> approve path,
with the OCR worker accented as the container the page is named for.

Two variants, one generator, identical coordinates -- they cannot drift:
    python build_rx_reader_c4.py              -> annotated  (default)
    python build_rx_reader_c4.py --plain      -> pure C4, no annotations
    python build_rx_reader_c4.py --both       -> both, each as .svg + .pdf

Canvas is 2100 x 1485 user units = A4 landscape (297 x 210 mm) at 7.07
units/mm, so a font-size of 21 units prints at almost exactly 8.4 pt.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

W, H = 2100, 1485          # A4 landscape aspect (1.4143)
MM_PER_UNIT = 297.0 / W

# --- palette (inherited from the level-2 diagram so the pair reads as a set)
NAVY   = "#1E3A5F"
NAVY_S = "#16293F"
GREY   = "#8B99A6"
GREY_S = "#6F7C87"
TEAL   = "#2A9D8F"
TEAL_S = "#1F7A6E"
ACCENT = "#E09B3D"          # the container this page is named for
LINE   = "#7A8894"
BND    = "#9AA4AD"
BNDTXT = "#5A6570"
INNER  = "#9FB6CC"          # arrows drawn on top of a navy container
INNERT = "#CBDAE7"
NOTE_B = "#D8E0E7"
NOTE_F = "#F7F9FB"

FS_TITLE, FS_SUB = 40, 20
FS_NAME, FS_TYPE, FS_DESC, FS_ANN = 23, 15, 17, 14.5
FS_CNAME, FS_CTYPE, FS_CDESC = 19, 14, 15.5
FS_EDGE, FS_BND, FS_LEG, FS_FOOT = 16, 19, 16, 15

LH_NAME, LH_TYPE, LH_DESC, LH_ANN = 28, 19, 21, 18
LH_CNAME, LH_CTYPE, LH_CDESC = 24, 18, 20


def tw(s: str, fs: float) -> float:
    """Arial width estimate. Only used for white label backings + the
    build-time overflow warnings, so a coarse per-character mean is fine."""
    return len(s) * fs * 0.53


# ---------------------------------------------------------------------------
# Boxes.  cls: person | cont | comp | store.  `left` renders left-aligned body
# lines instead of centred `desc` (the guard list).  `ann` renders only in the
# annotated variant, so both variants share every coordinate.
# ---------------------------------------------------------------------------
BOXES: dict[str, dict] = {
    "patient": dict(
        cls="person", x=40, y=380, w=200, h=250,
        name=["Patient"], type=["[Person]"],
        desc=["Photographs the", "label; approves", "or edits every", "proposal"],
    ),

    # --- droplet -----------------------------------------------------------
    "api": dict(
        cls="cont", x=460, y=195, w=680, h=715,
        name=["API"], type=["[Container: FastAPI, Python]"],
        desc=["Orchestrates the scan and owns every deterministic safety rule"],
        header_only=True,
    ),
    "orch": dict(
        cls="comp", x=480, y=295, w=311, h=165,
        name=["Scan Orchestrator"], type=["[Component: POST /prescriptions]"],
        desc=["Saves the photo, calls OCR,", "then asks the local model", "to propose the medications"],
    ),
    "regex": dict(
        cls="comp", x=809, y=295, w=311, h=165,
        name=["Regex Proposer"], type=["[Component: prescription_parser]"],
        desc=["Deterministic fallback, used", "only when the model cannot", "be reached"],
    ),
    "guards": dict(
        cls="comp", x=480, y=490, w=640, h=235,
        name=["Rx Guardrails  \u00b7  G1 to G6"],
        type=["[Component: deterministic rules, no model involved]"],
        left=[
            "G1  catalog \u2014 a name absent from the DIN reference is flagged",
            "G2  no-invention \u2014 unprinted time stripped, unprinted name flagged",
            "G3  schema \u2014 a frequency outside the enum becomes UNKNOWN",
            "G4  derivation \u2014 reminder times come from a fixed table, here",
            "G5  conflict \u2014 duplicate names or disagreeing strengths flagged",
            "G6  as-needed \u2014 read from the LABEL, never from the proposal",
        ],
        ann=["Applied to every proposal, whoever proposed it: the proposer is",
             "swappable by configuration, the guard set is not."],
    ),
    "gate": dict(
        cls="comp", x=480, y=750, w=435, h=140,
        name=["Approval Gate"], type=["[Component: PATCH /prescriptions/{id}]"],
        desc=["Blocking flags must be resolved or confirmed", "before a proposal becomes a medication"],
        ann=["Nothing auto-commits."],
    ),
    "photos": dict(
        cls="cont", x=460, y=950, w=330, h=185,
        name=["Photo Store"], type=["[Container: file volume]"],
        desc=["The prescription photo,", "kept for your review"],
    ),
    "db": dict(
        cls="store", x=810, y=950, w=330, h=185,
        name=["Database"], type=["[Container: PostgreSQL]"],
        desc=["Proposals stored as pending,", "with proposer and flags"],
    ),

    # --- brains host -------------------------------------------------------
    "bs": dict(
        cls="cont", x=1420, y=195, w=620, h=175,
        name=["Brains Service"], type=["[Container: FastAPI, Python]"],
        desc=["Private entry point on the ML tier \u2014",
              "POST /ocr/prescription  \u00b7  POST /rx/extract"],
        ann=["Reachable only over the private network."],
    ),
    "rocr": dict(
        cls="cont", x=1420, y=470, w=290, h=330, accent=True,
        name=["Prescription", "OCR Worker"],
        type=["[Container: PaddleOCR,", "torch-free subprocess]"],
        desc=["Turns the label photo into", "plain text. Spawned per", "scan; one pass, no re-read."],
        ann=["torch and paddle cannot share",
             "one Windows process \u2014 hence a",
             "separate subprocess. Any failure",
             "exits non-zero and becomes a",
             "503, never an empty success."],
    ),
    "llm": dict(
        cls="cont", x=1750, y=470, w=290, h=330,
        name=["Local Language", "Model"],
        type=["[Container: Ollama,", "qwen2.5:7b-instruct]"],
        desc=["Proposes medications from", "the label text. Runs on our", "own hardware \u2014 no cloud."],
        ann=["temperature 0 \u00b7 format json",
             "num_ctx 8192 set explicitly",
             "keep_alive 10m \u00b7 60 s budget,",
             "one corrective retry.",
             "Never asked for a reminder time."],
    ),
    "ref": dict(
        cls="store", x=1420, y=940, w=620, h=190,
        name=["Reference Data"], type=["[Data store: DIN reference workbook]"],
        desc=["11,609 marketed Canadian DINs \u2014 G1's catalog check",
              "and the DIN suggestions offered for confirmation"],
    ),
}

BOUNDARIES = [
    ("Droplet \u2014 public internet, mypillsafe.ca", 440, 140, 720, 1040),
    ("Brains Host \u2014 private network, GPU, never public", 1400, 140, 660, 1040),
]

# (points, label_lines, (label_x, label_y), dashed, badge or None, inner)
# `inner` = drawn on top of a navy container: light stroke, light text, no
# white backing.  label_y is the baseline of the FIRST line.
EDGES = [
    # patient -> API
    ([(240, 420), (460, 420)], ["Photographs the", "pharmacy label [HTTPS]"],
     (350, 368), False, (272, 420, "1"), False),
    # API -> photo store
    ([(490, 910), (490, 950)], ["Stores the photo"], (600, 915), False, (490, 930, "2"), False),
    # API -> brains service (OCR)
    ([(1140, 250), (1420, 250)], ["POST /ocr/prescription", "the photo [HTTP, private]"],
     (1290, 198), False, (1172, 250, "3"), False),
    # brains service -> OCR worker, and the raw text back
    ([(1495, 370), (1495, 470)], ["Spawns per scan", "[subprocess]"],
     (1495, 392), False, (1495, 442, "4"), False),
    ([(1630, 470), (1630, 370)], ["raw label text"], (1642, 442), True, None, False),
    # brains service -> API (the shared response channel)
    ([(1420, 310), (1140, 310)], ["Label text, then proposals", "\u2014 or 503, never invented"],
     (1290, 282), True, None, False),
    # API -> brains service (/rx/extract)
    ([(1140, 420), (1310, 420), (1310, 400), (1470, 400), (1470, 370)],
     ["POST /rx/extract", "the label text"], (1255, 368), False, (1160, 420, "5"), False),
    # brains service <-> ollama
    ([(1820, 370), (1820, 470)], ["Prompts [HTTP, localhost]"], (1878, 400), False,
     (1820, 442, "6"), False),
    ([(1960, 470), (1960, 370)], ["medication proposals"], (1938, 442), True, None, False),
    # inside the API: both proposers converge on one guard set
    ([(635, 460), (635, 490)], ["qwen's proposals"], (635, 482), False, (545, 475, "7"), True),
    ([(965, 460), (965, 490)], ["same guards"], (965, 482), False, None, True),
    ([(705, 725), (705, 750)], [], (0, 0), False, None, True),
    # guardrails -> DIN reference, via the brains service
    ([(1140, 600), (1370, 600), (1370, 430), (1425, 430), (1425, 370)],
     ["Searches the DIN", "reference (G1 catalog)"], (1255, 548), False, (1172, 600, "8"), False),
    ([(1730, 370), (1730, 940)], ["Reads"], (1730, 880), False, None, False),
    # guardrails -> database
    ([(1030, 725), (1030, 950)], ["Writes every proposal", "as pending, with its flags"],
     (1030, 800), False, (1030, 745, "9"), False),
    # API -> patient, patient -> approval gate, gate -> database
    ([(460, 560), (240, 560)], ["Shows the review", "screen with its flags"],
     (345, 508), False, (432, 560, "10"), False),
    ([(240, 610), (350, 610), (350, 810), (480, 810)], ["Approves", "or edits"],
     (350, 690), False, (268, 610, "11"), False),
    ([(760, 890), (760, 950)], ["approved \u2014 only now", "does a reminder fire"],
     (890, 900), False, (760, 905, "12"), False),
]

# Annotated variant only.  (title, [body lines])
NOTES = [
    ("The model proposes; it never decides",
     ["qwen2.5:7b is asked only for what the label says \u2014 name, strength, frequency,",
      "and clock times printed on the label. Reminder times are computed after it,",
      "by G4 from a fixed table, so the model cannot put a time on your schedule."]),
    ("One safety layer, two proposers",
     ["If the sidecar or Ollama cannot be reached, the regex proposer takes over.",
      "Both paths land in the same guard set, so a fallback changes which proposer",
      "spoke \u2014 never which rules were applied."]),
    ("Nothing on this page leaves our network",
     ["No arrow here reaches a cloud service: the photo, the text recognition and",
      "the model all run on hardware we own. MyPillSafe's one cloud brain, the",
      "answer voice, is not on this path."]),
]

LEGEND = [
    ("person", "Person"),
    ("cont",   "Container"),
    ("comp",   "Component"),
    ("store",  "Data store"),
    ("accent", "Subject of this diagram"),
    ("solid",  "Request"),
    ("dashed", "Response"),
]

TITLE = "Prescription Reader \u2014 Component Diagram (C4 level 3)"
SUBTITLE = ("How a photographed pharmacy label becomes an approved medication \u2014 and where the local "
            "model and the six deterministic guardrails actually sit.")
FOOTER = ("MyPillSafe  \u00b7  Prescription Reader, brain 1 of 5  \u00b7  C4 level 3, components  \u00b7  "
          "drawn from the shipped code, 2026-08-12")

WARNINGS: list[str] = []


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def check(text: str, fs: float, avail: float, where: str) -> None:
    if tw(text, fs) > avail:
        WARNINGS.append(f"{where}: {tw(text, fs):.0f}u > {avail:.0f}u  {text!r}")


def box_svg(bid: str, annotated: bool) -> str:
    b = BOXES[bid]
    cls, x, y, w, h = b["cls"], b["x"], b["y"], b["w"], b["h"]
    fill, stroke = {
        "person": (GREY, GREY_S), "cont": (NAVY, NAVY_S),
        "store": (NAVY, NAVY_S), "comp": (TEAL, TEAL_S),
    }[cls]
    if b.get("accent"):
        stroke = ACCENT

    o: list[str] = []
    top_pad = 0
    if cls == "store":
        ry = 18
        o.append(f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 1 {w},0 v{h-2*ry} '
                 f'a{w/2},{ry} 0 0 1 {-w},0 z" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        o.append(f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 0 {w},0" fill="none" '
                 f'stroke="#43617F" stroke-width="1.8"/>')
        top_pad = 2 * ry + 6
    else:
        sw = 4 if b.get("accent") else 1.8
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    comp = cls == "comp"
    fs_n, fs_t, fs_d = (FS_CNAME, FS_CTYPE, FS_CDESC) if comp else (FS_NAME, FS_TYPE, FS_DESC)
    lh_n, lh_t, lh_d = (LH_CNAME, LH_CTYPE, LH_CDESC) if comp else (LH_NAME, LH_TYPE, LH_DESC)
    cls_n, cls_t, cls_d = ("cn", "ct", "cd") if comp else ("nm", "tp", "ds")

    names, types = b["name"], b["type"]
    body = b.get("left") or b.get("desc") or []
    ann = b.get("ann", []) if annotated else []
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
    # The API is a shell holding components: its own text hugs the top.
    if b.get("header_only"):
        ty = y + 32
    else:
        ty = y + top_pad + (h - top_pad - block) / 2 + lh_n - 7
    cx = x + w / 2

    for ln in names:
        o.append(f'<text x="{cx}" y="{ty}" class="{cls_n}">{esc(ln)}</text>')
        ty += lh_n
    ty += 5
    for ln in types:
        o.append(f'<text x="{cx}" y="{ty}" class="{cls_t}">{esc(ln)}</text>')
        ty += lh_t
    ty += 8
    if b.get("left"):
        lx = x + 20
        for ln in body:
            o.append(f'<text x="{lx}" y="{ty}" class="cl">{esc(ln)}</text>')
            ty += lh_d
    else:
        for ln in body:
            o.append(f'<text x="{cx}" y="{ty}" class="{cls_d}">{esc(ln)}</text>')
            ty += lh_d
    if ann:
        ty += 10
        acls = "anc" if comp else "an"
        for ln in ann:
            o.append(f'<text x="{cx}" y="{ty}" class="{acls}">{esc(ln)}</text>')
            ty += LH_ANN
    return "\n".join(o)


def edge_svg(pts, lines, anchor, dashed, badge, inner) -> str:
    col = INNER if inner else LINE
    o = []
    d = " ".join(f"{px},{py}" for px, py in pts)
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    head = "ah_inner" if inner else ("ah_dash" if dashed else "ah")
    o.append(f'<polyline points="{d}" fill="none" stroke="{col}" '
             f'stroke-width="{1.7 if inner else 2.1}"{dash} marker-end="url(#{head})"/>')
    if lines:
        ax, ay = anchor
        width = max(tw(ln, FS_EDGE) for ln in lines) + 14
        # Backed either way, so the arrow never runs through the words; inside
        # a container the backing is the container's own fill.
        top = ay - FS_EDGE + 1
        o.append(f'<rect x="{ax-width/2}" y="{top}" width="{width}" '
                 f'height="{FS_EDGE*1.3*len(lines)+6}" fill="{NAVY if inner else "#FFFFFF"}"/>')
        klass = "eli" if inner else "el"
        for i, ln in enumerate(lines):
            o.append(f'<text x="{ax}" y="{ay + i*FS_EDGE*1.3}" class="{klass}">{esc(ln)}</text>')
    if badge:
        bx, by, num = badge
        o.append(f'<circle cx="{bx}" cy="{by}" r="14" fill="{NAVY}" stroke="#FFFFFF" stroke-width="2"/>')
        o.append(f'<text x="{bx}" y="{by+6}" class="bg">{num}</text>')
    return "\n".join(o)


def swatch(kind: str, x: float, y: float) -> str:
    if kind == "store":
        w, h, ry = 38, 24, 6
        return (f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 1 {w},0 v{h-2*ry} '
                f'a{w/2},{ry} 0 0 1 {-w},0 z" fill="{NAVY}" stroke="{NAVY_S}" stroke-width="1.4"/>')
    if kind in ("solid", "dashed"):
        dash = ' stroke-dasharray="7 5"' if kind == "dashed" else ""
        return (f'<line x1="{x}" y1="{y+12}" x2="{x+34}" y2="{y+12}" stroke="{LINE}" '
                f'stroke-width="2.1"{dash} marker-end="url(#ah)"/>')
    fill, stroke = {"person": (GREY, GREY_S), "cont": (NAVY, NAVY_S),
                    "comp": (TEAL, TEAL_S), "accent": (NAVY, ACCENT)}[kind]
    sw = 3.5 if kind == "accent" else 1.4
    return (f'<rect x="{x}" y="{y}" width="38" height="24" rx="3" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def build(annotated: bool) -> str:
    p: list[str] = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="Arial, Helvetica, sans-serif">')
    p.append(f"""<defs>
  <marker id="ah" markerWidth="10" markerHeight="8" refX="9.5" refY="4" orient="auto">
    <polygon points="0,0 10,4 0,8" fill="{LINE}"/></marker>
  <marker id="ah_dash" markerWidth="10" markerHeight="8" refX="9.5" refY="4" orient="auto">
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
  .cl {{ font-size:{FS_CDESC}px; fill:#F1FAF8; text-anchor:start; }}
  .an {{ font-size:{FS_ANN}px; font-style:italic; fill:#C3D2DF; text-anchor:middle; }}
  .anc {{ font-size:{FS_ANN}px; font-style:italic; fill:#D7F2EB; text-anchor:middle; }}
  .el {{ font-size:{FS_EDGE}px; fill:#3E4B57; text-anchor:middle; }}
  .eli {{ font-size:{FS_EDGE}px; fill:{INNERT}; text-anchor:middle; }}
  .bg {{ font-size:16px; font-weight:700; fill:#FFFFFF; text-anchor:middle; }}
  .bd {{ font-size:{FS_BND}px; fill:{BNDTXT}; }}
  .lg {{ font-size:{FS_LEG}px; fill:#33404B; }}
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

    # containers first, then components, then edges on top of both, then badges
    for bid in ("patient", "api", "photos", "db", "bs", "rocr", "llm", "ref"):
        p.append(box_svg(bid, annotated))
    for bid in ("orch", "regex", "guards", "gate"):
        p.append(box_svg(bid, annotated))
    for pts, lines, anchor, dashed, badge, inner in EDGES:
        p.append(edge_svg(pts, lines, anchor, dashed, badge, inner))

    # --- legend -------------------------------------------------------------
    ly = 1225
    if annotated:
        ly = 1375
        nx, nw, gap = 40, (W - 80 - 2 * 30) / 3, 30
        for i, (title, body) in enumerate(NOTES):
            x = nx + i * (nw + gap)
            p.append(f'<rect x="{x}" y="1205" width="{nw}" height="135" rx="4" '
                     f'fill="{NOTE_F}" stroke="{NOTE_B}" stroke-width="1.4"/>')
            check(title, 16, nw - 36, "note.title")
            p.append(f'<text x="{x+18}" y="1235" class="nt">{esc(title)}</text>')
            for j, ln in enumerate(body):
                check(ln, 15, nw - 36, "note.body")
                p.append(f'<text x="{x+18}" y="{1261 + j*22}" class="nb">{esc(ln)}</text>')

    cell = (W - 80) / len(LEGEND)
    p.append(f'<line x1="40" y1="{ly}" x2="{W-40}" y2="{ly}" stroke="{NOTE_B}" stroke-width="1.4"/>')
    for i, (kind, text) in enumerate(LEGEND):
        x = 40 + i * cell
        p.append(swatch(kind, x, ly + 18))
        p.append(f'<text x="{x+50}" y="{ly+36}" class="lg">{esc(text)}</text>')

    p.append(f'<text x="40" y="{ly+92}" class="ft">{esc(FOOTER)}</text>')
    p.append("</svg>")
    return "\n".join(p)


CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def render(svg_text: str, stem: Path) -> None:
    """One HTML shell -> A4 landscape PDF plus a PNG proof, via headless Chrome."""
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
    here = Path(__file__).parent
    want_plain = "--plain" in sys.argv
    want_both = "--both" in sys.argv

    targets = []
    if want_both or not want_plain:
        targets.append((True, here / "rx-reader-c4-a4"))
    if want_both or want_plain:
        targets.append((False, here / "rx-reader-c4-a4-plain"))

    for annotated, stem in targets:
        WARNINGS.clear()
        render(build(annotated), stem)
        for w in WARNINGS:
            print(f"  OVERFLOW  {w}")
    print(f"canvas {W}x{H} units = 297x210 mm  ({1/MM_PER_UNIT:.2f} units/mm)")
