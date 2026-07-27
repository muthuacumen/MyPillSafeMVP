"""Prescription-label OCR, torch-free subprocess (Task A1.1).

torch and paddle cannot share one Windows process (cuDNN WinError 127) --
this module is invoked as `sys.executable rx_ocr_sub.py --image ... --out-json
...` by `POST /ocr/prescription` (app.py) via `subprocess.run`, never
imported into the torch-holding process. It deliberately does NOT import
`config.py` (that module's only job is inserting the torch-bearing IMB1/SB2/
BB3 roots onto sys.path -- this script must stay independent of that).

Modeled closely on `IMB1_v0/imb1/ocr_sub.py` (the sibling pill-imprint OCR
subprocess): same modelscope stub, same version-tolerant PaddleOCR
constructor, same result-shape handling across the 3.x/2.x PaddleOCR APIs --
but reading a whole prescription LABEL (arbitrary multi-line text) rather
than a single masked pill-imprint crop, so there is no dual-read/CLAHE
variant here, just one pass over the uploaded image.
"""
from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

# paddleocr's import chain pulls torch in ONLY via modelscope's DDP log-noise
# check (modelscope/utils/logger.py -> torch_utils). Stub that module out
# BEFORE paddleocr is imported so this process stays torch-free (diagnosed
# 2026-07-09, IMB1_Prototype ADR; same fix as IMB1_v0/imb1/ocr_sub.py).
_torch_utils_stub = types.ModuleType("modelscope.utils.torch_utils")
_torch_utils_stub.is_dist = lambda: False
_torch_utils_stub.is_master = lambda: True
sys.modules.setdefault("modelscope.utils.torch_utils", _torch_utils_stub)


def make_ocr():
    """Version-tolerant PaddleOCR constructor (3.x pipeline API vs 2.x legacy).

    NOTE: the backend's old CPU engine (removed in Task A2.1) passed
    `enable_mkldnn=False` to dodge a paddlepaddle 3.3.1 CPU-build oneDNN
    crash. This sidecar venv runs `paddlepaddle-gpu`, which does not hit
    that bug -- do not carry the flag over blindly.
    """
    from paddleocr import PaddleOCR
    for kwargs in (
        dict(use_doc_orientation_classify=False, use_doc_unwarping=False,
             use_textline_orientation=True, lang="en"),
        dict(use_angle_cls=True, lang="en", show_log=False),
    ):
        try:
            return PaddleOCR(**kwargs)
        except (TypeError, ValueError):
            continue
    return PaddleOCR(lang="en")


def run_ocr(ocr, img_path: Path) -> list[tuple[str, float]]:
    """Return [(text, confidence), ...] under either PaddleOCR API."""
    if hasattr(ocr, "predict"):
        try:
            results = ocr.predict(str(img_path))
            out = []
            for r in results:
                texts = r.get("rec_texts") if hasattr(r, "get") else None
                scores = r.get("rec_scores") if hasattr(r, "get") else None
                if texts is None and isinstance(r, dict):
                    texts, scores = r.get("rec_texts"), r.get("rec_scores")
                if texts:
                    scores = scores if scores is not None else [0.0] * len(texts)
                    out.extend(zip(texts, scores))
            return out
        except (AttributeError, TypeError):
            pass
    raw = ocr.ocr(str(img_path), cls=True)
    out = []
    for page in raw or []:
        for line in page or []:
            text, conf = line[1][0], float(line[1][1])
            out.append((text, conf))
    return out


def read_label(image_path: Path) -> dict:
    ocr = make_ocr()
    pairs = run_ocr(ocr, image_path)
    lines = [text for text, _conf in pairs if text]
    return {"raw_text": "\n".join(lines), "lines": lines, "line_count": len(lines)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="path to a prescription label photo")
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    image_path = Path(args.image)
    try:
        result = read_label(image_path)
    except Exception as exc:  # noqa: BLE001 -- any OCR failure must surface as a non-zero exit, never a silent empty result
        print(f"[rx_ocr_sub] OCR failed for {args.image}: {exc!r}", file=sys.stderr, flush=True)
        sys.exit(1)

    Path(args.out_json).write_text(json.dumps(result), encoding="utf-8")
    print(f"[rx_ocr_sub] {args.image} -> {result['line_count']} line(s)", flush=True)


if __name__ == "__main__":
    main()
