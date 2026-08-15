"""CB4 (Answer Voice) -- C4 level-3 component diagram, A4 landscape, PDF.

Fifth and last in the set with `build_rx_reader_c4.py`, `build_imb1_c4.py`,
`build_sb2_c4.py` and `build_bb3_c4.py`; shares their canvas, palette, legend
idiom and generator machinery. Standalone -- not part of the poster.

Where the BB3 page draws the whole question->answer path with CB4 as one
component, this page does the complementary C4 zoom: BB3 collapses to a
single container on the right and the API container's interior expands --
route, prompt contract, the Claude call, and the guard-retry loop that owns
the protocol the sidecar deliberately does not.

Sources, all read 2026-08-12:
  * `PillSafe/dev/backend/app/services/cb4_service.py` -- SYSTEM_PROMPT_TEMPLATE
    (7 rules, rule 7 = the language substitution), `_call_claude` (the exact
    request body), `answer_question` (the retry loop: entity -> ingredient
    consistency -> polarity, one corrective retry + one re-check each, then a
    hard refusal), the F9-04 relabel and the caution note.
  * `PillSafe/dev/backend/app/api/v1/routes/qa.py` -- the voice switch:
    `cb4_enabled()` picks context mode + CB4, no key falls through to the
    sidecar's `mode="full"` local 7B, marked voice="local_7b".
  * `PillSafe/dev/backend/app/core/config.py` -- LLM_MODEL = claude-haiku-4-5,
    LLM_API_KEY = "" by default.
  * `PillSafe/dev/brains/qa.py` -- `run_guards()`, explicitly single-shot:
    "No retry logic here -- the app backend owns the retry protocol."
  * `PillSafe/dev/frontend/src/pages/dashboard/QAChatPage.tsx` -- the five
    language codes, sent as `language` and substituted into rule 7.

Two claims on this page are load-bearing and were checked, not recalled:
  1. the guard-retry protocol is the app's, the sidecar's is single-shot;
  2. this is the only cloud call in the system -- `anthropic` is imported in
     exactly one file, and Rx parsing runs on local Ollama (rx_extract.py,
     qwen2.5:7b-instruct), so nothing else leaves the network.

    python build_cb4_c4.py    ->  cb4-c4-a4.svg + .pdf + .png
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

#: Tag colours for the card's right-hand chips. Red is the page's boundary
#: colour throughout -- so red marks what crosses it, not what is dangerous.
CARD_TAGS = {"CROSSES": RED, "STAYS": GREEN}
CARD_PITCH = 24


def tw(s: str, fs: float) -> float:
    return len(s) * fs * 0.53


BOXES: dict[str, dict] = {
    "patient": dict(
        cls="person", x=40, y=340, w=210, h=280,
        name=["Patient"], type=["[Person]"],
        desc=["Asks a medication", "question, and picks", "the language the",
              "answer comes", "back in: English,", "French, Spanish,", "Arabic or Tamil"],
    ),

    # --- droplet -----------------------------------------------------------
    "api": dict(
        cls="cont", x=460, y=175, w=840, h=670,
        name=["API"], type=["[Container: FastAPI, Python]"],
        desc=["Owns the Q&A route, the prompt contract, the retry loop and the only cloud key"],
        header_only=True,
    ),
    "route": dict(
        cls="comp", x=480, y=275, w=800, h=125,
        name=["Q&A Route"],
        type=["[Component: POST /api/v1/qa/chat \u2014 patient-scoped, authenticated]"],
        desc=["A configured key selects the cloud voice and BB3's context mode; with no key the request",
              "falls through to the sidecar's own local 7B and the answer is marked voice=\"local_7b\"."],
        ann=["The patient is authenticated here \u2014 and nothing that identifies them travels any further."],
    ),
    "prompt": dict(
        cls="comp", x=480, y=410, w=800, h=125,
        name=["Prompt Contract"],
        type=["[Component: cb4_service.SYSTEM_PROMPT_TEMPLATE \u2014 a fixed constant, never assembled per call]"],
        desc=["Seven rules, numbered 1:1 against BB3's own template: answer only from the given sources,",
              "cite every one used, never a dose from a generated reference, and preserve every polarity."],
        ann=["Rule 7 is the only variable part \u2014 it substitutes the language the patient picked in the app."],
    ),
    "call": dict(
        cls="comp", x=480, y=545, w=800, h=125,
        name=["The Claude Call"],
        type=["[Component: cb4_service._call_claude \u2014 model claude-haiku-4-5]"],
        desc=["One user message per turn: BB3's packed SOURCE SECTIONS, then the question. The reply is",
              "forced into a JSON schema, and any source tag BB3 did not offer is dropped from it."],
        ann=["A failed call or an unparseable reply returns nothing, which the loop below treats as a retry."],
    ),
    "guards": dict(
        cls="comp", x=480, y=680, w=800, h=145,
        name=["Guard Retry Protocol"],
        type=["[Component: cb4_service.answer_question \u2014 mirrors bb3.guards.check_and_fix]"],
        desc=["Entity, then ingredient consistency, then polarity: each violation earns one corrective",
              "retry and one re-check. Fail the same guard twice and the draft is discarded, not patched.",
              "A structural-abstention mismatch is flagged on the way out, and never retried."],
        ann=["The sidecar's /qa/guard is single-shot by design; this loop is the only place retry policy lives."],
    ),

    # --- brains host -------------------------------------------------------
    "llm": dict(
        cls="cont", x=1540, y=175, w=500, h=130,
        name=["Local Language Model"], type=["[Container: Ollama, qwen2.5:7b-instruct]"],
        desc=["BB3's own generator \u2014 the offline", "fallback, and never the production voice."],
    ),
    "bb3": dict(
        cls="cont", x=1540, y=345, w=500, h=415,
        name=["BB3 \u2014 Monograph Retrieval"],
        type=["[Container: the frozen bb3 package,", "on the brains sidecar]"],
        desc=["Resolves the question to Canadian DINs \u2014", "or asks, when it cannot: confirm,",
              "pick_list, not_found. Retrieves only", "those monographs' passages and packs",
              "them with their source tags."],
        ann=["It resolves, retrieves and checks. It", "does not speak: generation moved out",
             "after its local 7B answered the opposite", "of a contraindication it had itself cited.",
             "/qa/guard runs the same four checks on", "CB4's answer that it ran on its own."],
    ),

    # --- outside every boundary --------------------------------------------
    "claude": dict(
        cls="ext", x=440, y=900, w=560, h=290,
        name=["Claude API"], type=["[External system: Anthropic, claude-haiku-4-5]"],
        desc=["Phrases the answer from the passages it is", "handed, in the language it is told to use.",
              "It retrieves nothing, holds no tools, and", "decides nothing."],
        ann=["The one and only cloud call in MyPillSafe.", "Every other model on this page runs on",
             "hardware the project owns."],
    ),
}

BOUNDARIES = [
    ("Droplet \u2014 public internet, mypillsafe.ca", 440, 125, 880, 749),
    ("Brains Host \u2014 private network, GPU, never public", 1520, 125, 540, 675),
]

# (points, label_lines, (x, baseline_of_first_line), dashed, badge, style)
# style: "" normal | "inner" (on a navy container) | "red" (leaves the network)
EDGES = [
    ([(250, 400), (460, 400)], ["Asks a question", "[HTTPS]"], (355, 348), False, (282, 400, "1"), ""),
    ([(460, 500), (250, 500)], ["The answer, cited,", "in their language"], (355, 448), False, (428, 500, "5"), ""),

    ([(1300, 380), (1540, 380)], ["POST /qa/chat", "mode=context"], (1420, 328), False, (1316, 380, "2"), ""),
    ([(1540, 450), (1300, 450)], ["context_ready \u2014 the", "packed passages and", "the JSON schema"],
     (1420, 394), True, None, ""),

    ([(1300, 700), (1540, 700)], ["POST /qa/guard \u2014", "BB3 checks the answer"], (1420, 648),
     False, (1316, 700, "4"), ""),
    ([(1540, 745), (1300, 745)], ["violations, or none"], (1420, 723), True, None, ""),

    ([(1790, 345), (1790, 305)], ["offline fallback only \u2014 no cloud key configured"], (1790, 332),
     False, None, ""),

    ([(700, 845), (700, 900)], ["the one cloud call [HTTPS]"], (900, 892), False, (700, 874, "3"), "red"),
    ([(760, 900), (760, 845)], [], (0, 0), True, None, "red"),
]

CARD_BOX = (1040, 900, 1020, 290)
CARD_TITLE = "What the request to Anthropic actually contains \u2014 and what has no field in it at all"
CARD_ROWS = [
    ("system  \u2014  the seven fixed rules, rule 7 substituted to the language the patient chose", "CROSSES"),
    ("user  \u2014  \u201cSOURCE SECTIONS:\u201d and BB3's packed passages, then \u201cUSER QUESTION:\u201d and the typed text", "CROSSES"),
    ("output_config  \u2014  a JSON schema: answer, sources_used, abstained; additionalProperties false", "CROSSES"),
    ("on a retry  \u2014  one corrective sentence naming the guard that fired, appended to the question", "CROSSES"),
    ("", ""),
    ("who is asking  \u2014  the route authenticates the patient, then forwards nothing that names them", "STAYS"),
    ("the medication profile  \u2014  a DIN bypass reaches BB3 on our own network, never this request", "STAYS"),
    ("pill photos, prescription images, database rows  \u2014  no such path reaches this service", "STAYS"),
    ("earlier turns  \u2014  every call is one user message; nothing from a previous question is resent", "STAYS"),
]
CARD_FOOT = "Four fields go out. Who is asking has no field at all \u2014 the request's shape, not a policy."

NOTES_Y, NOTES_H = 1215, 100
NOTES = [
    ("BB3 retrieves and checks; CB4 speaks",
     ["Generation moved out of BB3 after its local 7B answered the opposite of a",
      "contraindication it had itself cited. The guards that caught it run here."]),
    ("One retry per guard, then a refusal",
     ["Entity, ingredient consistency and polarity each get one corrective retry",
      "and one re-check. Fail the same guard twice and the draft is discarded."]),
    ("The language is a parameter, not a second step",
     ["The patient's choice is substituted into rule 7 and the model answers in it",
      "directly. Nothing is translated afterwards, so no meaning can drift."]),
]

LEGEND_Y = 1350
LEGEND = [
    ("person", "Person"),
    ("cont",   "Container"),
    ("comp",   "Component"),
    ("ext",    "External system"),
    ("solid",  "Request"),
    ("dashed", "Response"),
    ("red",    "Leaves our network"),
]

TITLE = "Answer Voice (CB4) \u2014 Component Diagram (C4 level 3)"
SUBTITLE = ("How a guarded, cited answer is generated in the patient's own language \u2014 and exactly what "
            "crosses the one boundary that leaves our network.")
FOOTER = ("MyPillSafe  \u00b7  Answer Voice, brain 5 of 5  \u00b7  C4 level 3, components  \u00b7  "
          "drawn from the shipped code, 2026-08-12")

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
    ty = y + 32 if b.get("header_only") else y + (h - block) / 2 + lh_n - 7
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


def card_svg(x: float, y: float, w: float, h: float) -> str:
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{CARD_F}" '
         f'stroke="{CARD_B}" stroke-width="2"/>']
    check(CARD_TITLE, 19, w - 44, "card.title")
    o.append(f'<text x="{x+22}" y="{y+34}" class="kt">{esc(CARD_TITLE)}</text>')
    ry = y + 64
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
    o.append(f'<text x="{x+22}" y="{ry+8}" class="kf">{esc(CARD_FOOT)}</text>')
    return "\n".join(o)


def swatch(kind: str, x: float, y: float) -> str:
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
        check(label, FS_BND, w - 36, "boundary")
        p.append(f'<text x="{x+18}" y="{y+28}" class="bd">{esc(label)}</text>')

    for bid in ("patient", "api", "llm", "bb3", "claude"):
        p.append(box_svg(bid))
    for bid in ("route", "prompt", "call", "guards"):
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

    ly = LEGEND_Y
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
    render(build(), Path(__file__).with_name("cb4-c4-a4"))
    for w in WARNINGS:
        # ASCII-safe: this console is cp1252 and the labels carry en dashes.
        print("  OVERFLOW  " + w.encode("ascii", "replace").decode())
    print(f"canvas {W}x{H} units = 297x210 mm  ({1/MM_PER_UNIT:.2f} units/mm)")
