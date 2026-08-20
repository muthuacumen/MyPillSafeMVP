"""Build the MyPillSafe C4 Level-2 container diagram as hand-placed SVG.

Why this exists
---------------
Three image-model attempts (v5/v6/v7) each returned a structural defect -- a
duplicated box, a relationship bound to the wrong source container, a re-spelt
label -- because a diffusion model has no mechanism that fixes element count or
glyph identity. Mermaid (v8) fixed all of that, but its auto-layout could not be
steered: best packing was aspect 2.02 with a quarter of the canvas empty.

Here every box coordinate is written down, so layout is a decision rather than an
outcome, and the text is vector and cannot drift.

Component list verified against the codebase 2026-08-06; the two OCR workers
verified 2026-08-11 against dev/brains/app.py:11-23 (torch and paddle cannot
share one Windows process, so imprint OCR and prescription OCR are two separate
subprocesses).

Usage:  python build_c4_svg.py   ->  architecture-c4-v9.svg
"""
from pathlib import Path

W, H = 2150, 1105

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

FS_NAME, FS_TYPE, FS_DESC = 21, 14, 15.5
LH_NAME, LH_TYPE, LH_DESC = 26, 18, 20

# id: (class, x, y, w, h, name_lines, type_lines, desc_lines, chip)
# chip = (name, [type_lines]) drawn as a nested teal component inside the box.
BOXES = {
    "patient": ("person", 25, 150, 230, 145, ["Patient"], ["[Person]"],
                ["Takes several medications;", "may not read English"], None),
    "admin":   ("person", 25, 345, 230, 160, ["Administrator"], ["[Person]"],
                ["Operates the platform; blocked", "from patient health data"], None),

    "web":  ("cont", 430, 125, 205, 175, ["Web App"],
             ["[Container: React 18,", "TypeScript, Vite, PWA]"],
             ["Installable single-page", "app in English and French"], None),
    "gw":   ("cont", 675, 125, 205, 175, ["Gateway"], ["[Container: nginx + TLS]"],
             ["Public entry point", "at mypillsafe.ca"], None),
    "api":  ("cont", 920, 125, 255, 220, ["API"], ["[Container: FastAPI, Python]"],
             ["Orchestration, sessions,", "patient approval"],
             ("Safety Guardrails", ["[Component: deterministic rules]"])),

    "db":     ("store", 430, 445, 205, 175, ["Database"], ["[Container: PostgreSQL]"],
               ["Accounts, medication", "profiles, scan outcomes"], None),
    "photos": ("cont", 675, 445, 205, 175, ["Photo Store"], ["[Container: file volume]"],
               ["Prescription photos; pill", "photos are never stored"], None),

    "bs":   ("cont", 935, 550, 250, 235, ["Brains Service"], ["[Container: FastAPI, Python]"],
             ["Hosts pill vision, the matcher", "and monograph retrieval"],
             ("Deterministic Matcher", ["[Component: verify · reject · abstain]"])),
    "llm":  ("cont", 1230, 460, 235, 155, ["Local Language Model"],
             ["[Container: Ollama, qwen2.5:7b]"],
             ["Proposes medications from", "label text; fully offline"], None),
    "iocr": ("cont", 1230, 655, 235, 155, ["Imprint OCR Worker"],
             ["[Container: PaddleOCR,", "isolated subprocess]"],
             ["Reads imprint text from", "a photographed pill"], None),
    "rocr": ("cont", 1230, 850, 235, 170, ["Prescription", "OCR Worker"],
             ["[Container: PaddleOCR,", "torch-free subprocess]"],
             ["Turns a photographed", "prescription label into text"], None),
    "ref":  ("store", 1520, 460, 250, 185, ["Reference Data"], ["[Data store: workbook]"],
             ["Appearance and identifiers for", "marketed Canadian products"], None),
    "mono": ("store", 1520, 710, 250, 195, ["Monograph Index"],
             ["[Data store: SQLite FTS5", "+ memory-mapped vectors]"],
             ["Searchable Canadian", "product monographs"], None),

    "claude": ("person", 1905, 125, 225, 195, ["Claude API"],
               ["[External system: Anthropic,", "claude-haiku-4-5]"],
               ["Phrases the final answer;", "decides nothing"], None),
    "drugs":  ("person", 1905, 605, 225, 225, ["Drug Reference", "Sources"],
               ["[External system: Health Canada", "DPD and monographs;", "openFDA OTC labels]"],
               ["Ingested offline; never", "called at runtime"], None),
}

# (label, x, y, w, h)
BOUNDARIES = [
    ("MyPillSafe", 400, 40, 1480, 1035),
    ("Brains Host — private network, GPU, never public", 905, 385, 950, 675),
]

# (points, label, label_anchor(x,y), red?)
EDGES = [
    ([(255, 222), (340, 222), (340, 195), (430, 195)], "Uses [HTTPS]", (325, 186), False),
    ([(255, 425), (340, 425), (340, 255), (430, 255)], "Administers [HTTPS]", (325, 246), False),
    ([(635, 205), (675, 205)], "Calls [HTTPS]", (655, 112), False),
    ([(880, 205), (920, 205)], "Proxies [HTTP]", (900, 112), False),
    ([(920, 310), (760, 310), (760, 445)], "Stores prescription photos", (760, 362), False),
    ([(920, 332), (532, 332), (532, 445)], "Reads and writes [SQL]", (532, 392), False),
    ([(1047, 345), (1047, 550)], "Calls [HTTP, private network]", (1047, 372), False),
    ([(1175, 200), (1905, 200)], "Sends question and cited passages only [HTTPS]", (1540, 183), True),
    ([(1185, 600), (1207, 600), (1207, 540), (1230, 540)], "Prompts [HTTP, localhost]", (1348, 449), False),
    ([(1185, 650), (1207, 650), (1207, 745), (1230, 745)], "Spawns [subprocess]", (1348, 644), False),
    ([(1185, 700), (1196, 700), (1196, 950), (1230, 950)], "Spawns [subprocess]", (1348, 839), False),
    ([(960, 550), (960, 425), (1645, 425), (1645, 460)], "Reads", (1400, 416), False),
    ([(985, 785), (985, 1040), (1645, 1040), (1645, 905)], "Reads", (1400, 1031), False),
    ([(1905, 660), (1838, 660), (1838, 520), (1770, 520)], "Ingested offline", (1820, 497), False),
    ([(1905, 700), (1860, 700), (1860, 800), (1770, 800)], "Ingested offline", (1826, 838), False),
]

# Two placements, kept in one generator so the variants cannot drift apart.
#   "inside"  -> fills the lower-left dead zone, but sits within the MyPillSafe boundary
#   "outside" -> below Administrator in the people column, outside every boundary
LEGEND_INSIDE  = (430, 835, 390, 225)
LEGEND_OUTSIDE = (25, 620, 230, 225)
LEGEND = LEGEND_INSIDE


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box_svg(bid):
    cls, x, y, w, h, names, types, descs, chip = BOXES[bid]
    fill, stroke = {"person": (GREY, GREY_S), "cont": (NAVY, NAVY_S),
                    "store": (NAVY, NAVY_S)}[cls]
    o = []
    if cls == "store":
        # cylinder: elliptical cap, straight sides
        ry = 16
        o.append(
            f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 1 {w},0 v{h-2*ry} '
            f'a{w/2},{ry} 0 0 1 {-w},0 z" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        )
        o.append(
            f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0 0 {w},0" fill="none" '
            f'stroke="#4A6party" stroke-width="1.5"/>'.replace("#4A6party", "#43617F")
        )
        top_pad = 2 * ry + 4
    else:
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        top_pad = 0

    chip_h = 0
    if chip:
        chip_h = 26 + LH_TYPE * len(chip[1]) + 14

    block = LH_NAME * len(names) + 4 + LH_TYPE * len(types) + 6 + LH_DESC * len(descs)
    cy = y + top_pad + (h - top_pad - chip_h - block) / 2
    cx = x + w / 2

    ty = cy + LH_NAME - 6
    for ln in names:
        o.append(f'<text x="{cx}" y="{ty}" class="nm">{esc(ln)}</text>')
        ty += LH_NAME
    ty += 4
    for ln in types:
        o.append(f'<text x="{cx}" y="{ty}" class="tp">{esc(ln)}</text>')
        ty += LH_TYPE
    ty += 6
    for ln in descs:
        o.append(f'<text x="{cx}" y="{ty}" class="ds">{esc(ln)}</text>')
        ty += LH_DESC

    if chip:
        cname, ctypes = chip
        ch = 26 + LH_TYPE * len(ctypes) + 8
        cxx, cyy, cww = x + 14, y + h - ch - 14, w - 28
        o.append(f'<rect x="{cxx}" y="{cyy}" width="{cww}" height="{ch}" rx="4" '
                 f'fill="{TEAL}" stroke="{TEAL_S}" stroke-width="1.5"/>')
        cty = cyy + 21
        o.append(f'<text x="{cxx+cww/2}" y="{cty}" class="cn">{esc(cname)}</text>')
        cty += 18
        for ln in ctypes:
            o.append(f'<text x="{cxx+cww/2}" y="{cty}" class="ct">{esc(ln)}</text>')
            cty += LH_TYPE
    return "\n".join(o)


def edge_svg(pts, label, anchor, red):
    col = RED if red else LINE
    wdt = 2.6 if red else 1.6
    d = " ".join(f"{x},{y}" for x, y in pts)
    o = [f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{wdt}" '
         f'marker-end="url(#{"ah_red" if red else "ah"})"/>']
    if label:
        ax, ay = anchor
        tw = len(label) * 6.5 + 10
        o.append(f'<rect x="{ax-tw/2}" y="{ay-13}" width="{tw}" height="18" fill="#FFFFFF"/>')
        o.append(f'<text x="{ax}" y="{ay}" class="el" fill="{col}">{esc(label)}</text>')
    return "\n".join(o)


def legend_svg(box=None):
    x, y, w, h = box or LEGEND
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="#FFFFFF" '
         f'stroke="{BND}" stroke-width="1.2"/>',
         f'<text x="{x+14}" y="{y+26}" class="lgt">Legend</text>']
    rows = [(GREY, GREY_S, "Person / External system", "rect"),
            (NAVY, NAVY_S, "Container", "rect"),
            (TEAL, TEAL_S, "Component", "rect"),
            (NAVY, NAVY_S, "Data store", "cyl")]
    ry = y + 46
    for fill, stroke, txt, shape in rows:
        if shape == "cyl":
            sw, sh, cr = 34, 22, 5
            o.append(f'<path d="M{x+14},{ry+cr} a{sw/2},{cr} 0 0 1 {sw},0 v{sh-2*cr} '
                     f'a{sw/2},{cr} 0 0 1 {-sw},0 z" fill="{fill}" stroke="{stroke}" '
                     f'stroke-width="1.2"/>')
            o.append(f'<path d="M{x+14},{ry+cr} a{sw/2},{cr} 0 0 0 {sw},0" fill="none" '
                     f'stroke="#43617F" stroke-width="1.2"/>')
        else:
            o.append(f'<rect x="{x+14}" y="{ry}" width="34" height="22" rx="3" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        o.append(f'<text x="{x+58}" y="{ry+16}" class="lg">{esc(txt)}</text>')
        ry += 34
    o.append(f'<line x1="{x+14}" y1="{ry+11}" x2="{x+48}" y2="{ry+11}" stroke="{RED}" '
             f'stroke-width="2.6" marker-end="url(#ah_red)"/>')
    o.append(f'<text x="{x+58}" y="{ry+16}" class="lg">Leaves our network</text>')
    return "\n".join(o)


def build(LEGEND_BOX=None):
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="Arial, Helvetica, sans-serif">')
    p.append(f"""<defs>
  <marker id="ah" markerWidth="9" markerHeight="7" refX="8.5" refY="3.5" orient="auto">
    <polygon points="0,0 9,3.5 0,7" fill="{LINE}"/></marker>
  <marker id="ah_red" markerWidth="9" markerHeight="7" refX="8.5" refY="3.5" orient="auto">
    <polygon points="0,0 9,3.5 0,7" fill="{RED}"/></marker>
</defs>
<style>
  text {{ dominant-baseline: auto; }}
  .nm {{ font-size:{FS_NAME}px; font-weight:700; fill:#FFFFFF; text-anchor:middle; }}
  .tp {{ font-size:{FS_TYPE}px; fill:#DCE4EC; text-anchor:middle; }}
  .ds {{ font-size:{FS_DESC}px; fill:#EAF0F5; text-anchor:middle; }}
  .cn {{ font-size:16px; font-weight:700; fill:#FFFFFF; text-anchor:middle; }}
  .ct {{ font-size:{FS_TYPE}px; fill:#EAF7F4; text-anchor:middle; }}
  .el {{ font-size:14px; text-anchor:middle; }}
  .bd {{ font-size:16px; fill:{BNDTXT}; }}
  .lgt {{ font-size:15px; font-weight:700; fill:{BNDTXT}; }}
  .lg {{ font-size:14px; fill:#33404B; }}
</style>""")
    p.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

    for label, x, y, w, h in BOUNDARIES:
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="none" '
                 f'stroke="{BND}" stroke-width="1.4" stroke-dasharray="7 5"/>')
        p.append(f'<text x="{x+16}" y="{y+24}" class="bd">{esc(label)}</text>')

    for pts, lbl, anc, red in EDGES:
        p.append(edge_svg(pts, lbl, anc, red))
    for bid in BOXES:
        p.append(box_svg(bid))
    p.append(legend_svg(LEGEND_BOX))
    p.append("</svg>")
    return "\n".join(p)


SCALE = 1.6  # raster scale; 1.6 -> 3440 x 1768


def rasterise(svg_path):
    """Rasterise via headless Chrome (no cairo/inkscape needed on this machine)."""
    import subprocess
    here = svg_path.parent
    shot = here / "_shot.html"
    pw, ph = int(W * SCALE), int(H * SCALE)
    shot.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "html,body{margin:0;padding:0;background:#fff}"
        f"img{{display:block;width:{pw}px;height:{ph}px}}</style></head>"
        f"<body><img src='{svg_path.name}'></body></html>", encoding="utf-8")
    png = svg_path.with_suffix(".png")
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={pw},{ph}", f"--screenshot={png}",
                    shot.resolve().as_uri()], check=True)
    shot.unlink()
    print(f"wrote {png}  ({pw}x{ph})")


if __name__ == "__main__":
    import sys
    outside = "--legend-outside" in sys.argv
    if outside:
        LEGEND = LEGEND_OUTSIDE
        name = "architecture-c4-v9b.svg"
    else:
        name = "architecture-c4-v9.svg"
    out = Path(__file__).with_name(name)
    out.write_text(build(LEGEND), encoding="utf-8")
    print(f"wrote {out}  ({W}x{H}, aspect {W/H:.2f}, legend "
          f"{'outside' if outside else 'inside'})")
    rasterise(out)
