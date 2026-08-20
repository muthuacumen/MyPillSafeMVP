"""BB3 (Monograph Retrieval) -- C4 level-3 component diagram, A4 landscape, as PDF.

Companion to `build_rx_reader_c4.py`: same canvas, palette, legend idiom and
generator machinery, different subsystem. Standalone -- not part of the poster.

Verified against the shipped code 2026-08-12:
  * `BB3/bb3/` -- resolver, enumerate, retrieve (+ intent), store, guards;
    CONTRACT.md Sec1-7 for the frozen resolver outcome table and guard set.
  * `PillSafe/dev/brains/qa.py` -- the sidecar's "context mode": it mirrors
    `BB3Engine.chat()`'s control flow field for field but STOPS before
    generation and returns `status:"context_ready"` with the packed context.
  * `PillSafe/dev/backend/app/services/cb4_service.py` -- CB4, the production
    voice: the one and only cloud call in the system, and the owner of the
    guard retry protocol (the sidecar's /qa/guard is single-shot).
  * `PillSafe/dev/backend/app/api/v1/routes/qa.py` -- picks context mode when
    an LLM_API_KEY exists, else the sidecar's local-7B `mode="full"`.

The architectural point the drawing has to carry: BB3 resolves, scopes,
retrieves and guards -- it does not speak. Generation is CB4's, over one
clearly marked hop that leaves the network, and BB3's guards then run on
CB4's output exactly as they ran on the local 7B's.

    python build_bb3_c4.py    ->  bb3-c4-a4.svg + .pdf + .png
"""
from __future__ import annotations

import subprocess
from pathlib import Path

W, H = 2100, 1485          # A4 landscape aspect (1.4143)
MM_PER_UNIT = 297.0 / W

NAVY   = "#1E3A5F"
NAVY_S = "#16293F"
GREY   = "#8B99A6"
GREY_S = "#6F7C87"
TEAL   = "#2A9D8F"
TEAL_S = "#1F7A6E"
RED    = "#D64045"
LINE   = "#7A8894"
BND    = "#9AA4AD"
BNDTXT = "#5A6570"
INNER  = "#9FB6CC"
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
    return len(s) * fs * 0.53


BOXES: dict[str, dict] = {
    "patient": dict(
        cls="person", x=40, y=330, w=190, h=250,
        name=["Patient"], type=["[Person]"],
        desc=["Asks about a", "medication, in", "their own", "language"],
    ),

    # --- droplet -----------------------------------------------------------
    "api": dict(
        cls="cont", x=440, y=180, w=450, h=600,
        name=["API"], type=["[Container: FastAPI, Python]"],
        desc=["Owns the Q&A route and the only cloud key"],
        header_only=True,
    ),
    "route": dict(
        cls="comp", x=460, y=285, w=410, h=190,
        name=["Q&A Route"], type=["[Component: POST /api/v1/qa/chat]"],
        desc=["Patient-scoped. Carries the DIN of a", "medication the patient already", "confirmed, when they picked one."],
        ann=["Chooses the cloud voice when a key is", "configured, the offline one when not."],
    ),
    "cb4": dict(
        cls="comp", x=460, y=505, w=410, h=245,
        name=["CB4 Answer Voice"], type=["[Component: cb4_service]"],
        desc=["Sends BB3's packed passages to the", "cloud model, then puts the answer", "back through BB3's guards."],
        ann=["One corrective retry per violation,", "then a hard refusal. The only place", "in the system an API key exists."],
    ),

    # --- outside every boundary --------------------------------------------
    "claude": dict(
        cls="ext", x=440, y=880, w=450, h=200,
        name=["Claude API"], type=["[External system: Anthropic,", "claude-haiku-4-5]"],
        desc=["Phrases the final answer from the", "passages it is handed. Decides nothing."],
        ann=["The only cloud call in MyPillSafe: no identity,", "no medication profile and no photo cross this line."],
    ),

    # --- brains host -------------------------------------------------------
    "bs": dict(
        cls="cont", x=1170, y=180, w=870, h=680,
        name=["Brains Service"], type=["[Container: FastAPI, Python]"],
        desc=["Hosts the frozen BB3 package \u2014 POST /qa/chat  \u00b7  POST /qa/guard"],
        header_only=True,
    ),
    "resolver": dict(
        cls="comp", x=1190, y=285, w=830, h=145,
        name=["Resolver"], type=["[Component: bb3.resolver \u2014 the only door into retrieval]"],
        desc=["Free text, brand, ingredient or DIN \u2192 a resolved set of Canadian DINs. If it cannot, it asks:",
              "one near-match \u2192 confirm, more than one \u2192 pick_list, never auto-picked; none \u2192 not_found."],
        ann=["Fuzzy threshold 80 on words of six characters or more. A DIN the app already holds skips this stage."],
    ),
    "retrieve": dict(
        cls="comp", x=1190, y=460, w=395, h=180,
        name=["Scoped Retrieval"], type=["[Component: bb3.retrieve + bb3.intent]"],
        desc=["Hybrid dense + lexical search, RRF-", "fused, over the resolved DINs'", "passages and nothing else. Intent", "routes to the right sections."],
        ann=["There is no full-corpus path in this", "package: it was deleted, not disabled."],
    ),
    "enumerate": dict(
        cls="comp", x=1625, y=460, w=395, h=180,
        name=["Enumeration"], type=["[Component: bb3.enumerate]"],
        desc=["\u201cWhich products contain", "acetaminophen?\u201d is answered by SQL", "over the formulary and returns", "immediately \u2014 no model involved."],
        ann=["A deterministic list, with the", "excluded count always stated."],
    ),
    "gate": dict(
        cls="comp", x=1190, y=670, w=395, h=170,
        name=["Dosing Gate & Packing"], type=["[Component: bb3.engine rules]"],
        desc=["Refuses a dosing question when every", "surviving source is a generated", "ingredient reference, then packs the", "rest with their source tags."],
        ann=["A hard gate: on refusal no model", "is called at all."],
    ),
    "guards": dict(
        cls="comp", x=1625, y=670, w=395, h=170,
        name=["Generation Guards"], type=["[Component: bb3.guards]"],
        desc=["Run on the answer that comes back:", "entity \u00b7 ingredient-consistency \u00b7", "structured abstention \u00b7 claim-source", "polarity."],
        ann=["Single-shot here \u2014 the API owns the", "retry loop."],
    ),
    "store": dict(
        cls="store", x=1170, y=910, w=440, h=240,
        name=["Monograph Store"], type=["[Data store: SQLite FTS5", "+ memory-mapped vectors]"],
        desc=["6,803 Health Canada monographs", "and 27 ingredient references \u2014", "3.9 million searchable passages"],
        ann=["Memory-mapped, never loaded whole."],
    ),
    "llm": dict(
        cls="cont", x=1630, y=910, w=410, h=240,
        name=["Local Language", "Model"], type=["[Container: Ollama,", "qwen2.5:7b-instruct]"],
        desc=["BB3's own generator, used only", "when no cloud key is configured."],
        ann=["Kept as the offline fallback and the", "evaluation harness \u2014 not the production", "voice: it once answered the opposite of", "a contraindication it had itself cited."],
    ),
}

BOUNDARIES = [
    ("Droplet \u2014 public internet, mypillsafe.ca", 420, 125, 490, 690),
    ("Brains Host \u2014 private network, GPU, never public", 1150, 125, 910, 1045),
]

# (points, label_lines, (x, baseline_of_first_line), dashed, badge, style)
# style: "" normal | "inner" (on a navy container) | "red" (leaves the network)
EDGES = [
    ([(230, 360), (440, 360)], ["Asks a question", "[HTTPS]"], (335, 308), False, (262, 360, "1"), ""),
    ([(440, 440), (230, 440)], ["The answer, cited,", "in their language"], (335, 388), False, (408, 440, "7"), ""),

    ([(890, 290), (1170, 290)], ["POST /qa/chat", "mode=context"], (1030, 238), False, (922, 290, "2"), ""),
    ([(1170, 385), (890, 385)], ["context_ready: the packed,", "cited passages \u2014 or a", "short-circuit answer"], (1030, 330), True, None, ""),

    ([(665, 475), (665, 505)], ["context_ready"], (665, 497), False, None, "inner"),

    ([(610, 750), (610, 880)], ["Question + retrieved", "passages only [HTTPS];", "answer JSON back"], (805, 800), False, (610, 845, "5"), "red"),
    ([(690, 880), (690, 750)], [], (0, 0), True, None, "red"),

    ([(890, 600), (1170, 600)], ["POST /qa/guard \u2014", "BB3 checks the answer"], (1030, 548), False, (922, 600, "6"), ""),
    ([(1170, 680), (890, 680)], ["violations, or none"], (1030, 658), True, None, ""),

    ([(1387, 430), (1387, 460)], ["DIN set"], (1387, 452), False, (1305, 445, "3"), "inner"),
    ([(1822, 430), (1822, 460)], ["list intent"], (1822, 452), False, None, "inner"),
    ([(1387, 640), (1387, 670)], [], (0, 0), False, None, "inner"),

    ([(1250, 860), (1250, 910)], ["Reads only the resolved DINs' passages"], (1450, 890), False, (1250, 885, "4"), ""),
    ([(1830, 860), (1830, 910)], ["Offline fallback only \u2014 no cloud key configured"], (1830, 890), False, None, ""),
]

NOTES = [
    ("Resolve first, retrieve second",
     ["The resolver is the only door: retrieval is always scoped to a resolved",
      "DIN set. When it cannot resolve the question it asks \u2014 confirm, pick_list",
      "or not_found \u2014 and no model runs at all."]),
    ("BB3 retrieves and guards; it does not speak",
     ["The local model stays as the offline fallback and the evaluation harness.",
      "The production voice is a cloud model, and BB3's guards run on its answer",
      "exactly as they ran on the local one's."]),
    ("One hop leaves our network, and only one",
     ["It carries the question and the passages BB3 already retrieved \u2014 no",
      "identity, no medication profile, no photo. Everything else on this page",
      "runs on hardware the project owns."]),
]

LEGEND = [
    ("person", "Person"),
    ("cont",   "Container"),
    ("comp",   "Component"),
    ("store",  "Data store"),
    ("ext",    "External system"),
    ("solid",  "Request"),
    ("dashed", "Response"),
    ("red",    "Leaves our network"),
]

TITLE = "Monograph Retrieval (BB3) \u2014 Component Diagram (C4 level 3)"
SUBTITLE = ("How a medication question is resolved, scoped, retrieved and guarded \u2014 and the single hop "
            "that leaves our network.")
FOOTER = ("MyPillSafe  \u00b7  Monograph Retrieval, brain 4 of 5, with the Answer Voice  \u00b7  C4 level 3, "
          "components  \u00b7  drawn from the shipped code, 2026-08-12")

WARNINGS: list[str] = []


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def check(text: str, fs: float, avail: float, where: str) -> None:
    if tw(text, fs) > avail:
        WARNINGS.append(f"{where}: {tw(text, fs):.0f}u > {avail:.0f}u  {text!r}")


def box_svg(bid: str) -> str:
    b = BOXES[bid]
    cls, x, y, w, h = b["cls"], b["x"], b["y"], b["w"], b["h"]
    fill, stroke = {
        "person": (GREY, GREY_S), "cont": (NAVY, NAVY_S), "store": (NAVY, NAVY_S),
        "comp": (TEAL, TEAL_S), "ext": (GREY, RED),
    }[cls]

    o: list[str] = []
    top_pad = bot_pad = 0
    if cls == "store":
        ry = 18
        bot_pad = ry + 4  # the bottom cap bulges down; keep text off its curve
        o.append(f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 1 {w},0 v{h-2*ry} '
                 f'a{w/2},{ry} 0 0 1 {-w},0 z" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        o.append(f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 0 {w},0" fill="none" '
                 f'stroke="#43617F" stroke-width="1.8"/>')
        top_pad = 2 * ry + 6
    else:
        sw = 4 if cls == "ext" else 1.8
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

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
    if b.get("header_only"):
        ty = y + 32
    else:
        ty = y + top_pad + (h - top_pad - bot_pad - block) / 2 + lh_n - 7
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
    return "\n".join(o)


def edge_svg(pts, lines, anchor, dashed, badge, style) -> str:
    col = {"inner": INNER, "red": RED, "": LINE}[style]
    width = 2.6 if style == "red" else (1.7 if style == "inner" else 2.1)
    head = {"inner": "ah_inner", "red": "ah_red", "": "ah"}[style]
    o = []
    d = " ".join(f"{px},{py}" for px, py in pts)
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    o.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{width}"'
             f'{dash} marker-end="url(#{head})"/>')
    if lines:
        ax, ay = anchor
        bw = max(tw(ln, FS_EDGE) for ln in lines) + 14
        back = NAVY if style == "inner" else "#FFFFFF"
        o.append(f'<rect x="{ax-bw/2}" y="{ay-FS_EDGE+1}" width="{bw}" '
                 f'height="{FS_EDGE*1.3*len(lines)+6}" fill="{back}"/>')
        klass = {"inner": "eli", "red": "elr", "": "el"}[style]
        for i, ln in enumerate(lines):
            o.append(f'<text x="{ax}" y="{ay + i*FS_EDGE*1.3}" class="{klass}">{esc(ln)}</text>')
    if badge:
        bx, by, num = badge
        bc = RED if style == "red" else NAVY
        o.append(f'<circle cx="{bx}" cy="{by}" r="14" fill="{bc}" stroke="#FFFFFF" stroke-width="2"/>')
        o.append(f'<text x="{bx}" y="{by+6}" class="bg">{num}</text>')
    return "\n".join(o)


def swatch(kind: str, x: float, y: float) -> str:
    if kind == "store":
        w, h, ry = 38, 24, 6
        return (f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 1 {w},0 v{h-2*ry} '
                f'a{w/2},{ry} 0 0 1 {-w},0 z" fill="{NAVY}" stroke="{NAVY_S}" stroke-width="1.4"/>')
    if kind in ("solid", "dashed", "red"):
        dash = ' stroke-dasharray="7 5"' if kind == "dashed" else ""
        col = RED if kind == "red" else LINE
        hd = "ah_red" if kind == "red" else "ah"
        return (f'<line x1="{x}" y1="{y+12}" x2="{x+34}" y2="{y+12}" stroke="{col}" '
                f'stroke-width="{2.6 if kind == "red" else 2.1}"{dash} marker-end="url(#{hd})"/>')
    fill, stroke = {"person": (GREY, GREY_S), "cont": (NAVY, NAVY_S),
                    "comp": (TEAL, TEAL_S), "ext": (GREY, RED)}[kind]
    sw = 3.5 if kind == "ext" else 1.4
    return (f'<rect x="{x}" y="{y}" width="38" height="24" rx="3" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def build() -> str:
    p: list[str] = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="Arial, Helvetica, sans-serif">')
    p.append(f"""<defs>
  <marker id="ah" markerWidth="10" markerHeight="8" refX="9.5" refY="4" orient="auto">
    <polygon points="0,0 10,4 0,8" fill="{LINE}"/></marker>
  <marker id="ah_inner" markerWidth="10" markerHeight="8" refX="9.5" refY="4" orient="auto">
    <polygon points="0,0 10,4 0,8" fill="{INNER}"/></marker>
  <marker id="ah_red" markerWidth="10" markerHeight="8" refX="9.5" refY="4" orient="auto">
    <polygon points="0,0 10,4 0,8" fill="{RED}"/></marker>
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
  .elr {{ font-size:{FS_EDGE}px; font-weight:700; fill:{RED}; text-anchor:middle; }}
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

    for bid in ("patient", "api", "claude", "bs", "store", "llm"):
        p.append(box_svg(bid))
    for bid in ("route", "cb4", "resolver", "retrieve", "enumerate", "gate", "guards"):
        p.append(box_svg(bid))
    for pts, lines, anchor, dashed, badge, style in EDGES:
        p.append(edge_svg(pts, lines, anchor, dashed, badge, style))

    nw, gap = (W - 80 - 2 * 30) / 3, 30
    for i, (title, body) in enumerate(NOTES):
        x = 40 + i * (nw + gap)
        p.append(f'<rect x="{x}" y="1205" width="{nw}" height="135" rx="4" '
                 f'fill="{NOTE_F}" stroke="{NOTE_B}" stroke-width="1.4"/>')
        check(title, 16, nw - 36, "note.title")
        p.append(f'<text x="{x+18}" y="1235" class="nt">{esc(title)}</text>')
        for j, ln in enumerate(body):
            check(ln, 15, nw - 36, "note.body")
            p.append(f'<text x="{x+18}" y="{1261 + j*22}" class="nb">{esc(ln)}</text>')

    ly = 1375
    cell = (W - 80) / len(LEGEND)
    p.append(f'<line x1="40" y1="{ly}" x2="{W-40}" y2="{ly}" stroke="{NOTE_B}" stroke-width="1.4"/>')
    for i, (kind, text) in enumerate(LEGEND):
        x = 40 + i * cell
        p.append(swatch(kind, x, ly + 18))
        check(text, FS_LEG, cell - 60, "legend")
        p.append(f'<text x="{x+50}" y="{ly+36}" class="lg">{esc(text)}</text>')

    p.append(f'<text x="40" y="{ly+92}" class="ft">{esc(FOOTER)}</text>')
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
    stem = Path(__file__).with_name("bb3-c4-a4")
    render(build(), stem)
    for w in WARNINGS:
        # ASCII-safe: this console is cp1252 and the labels carry en dashes/arrows.
        print("  OVERFLOW  " + w.encode("ascii", "replace").decode())
    print(f"canvas {W}x{H} units = 297x210 mm  ({1/MM_PER_UNIT:.2f} units/mm)")
