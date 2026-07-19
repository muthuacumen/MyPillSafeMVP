"""PaddleOCR wrapper for prescription label text extraction (Priority 1B).

Gated by OCR_PIPELINE_ENABLED. PaddleOCR/PaddlePaddle are heavy native
dependencies that are not installed in every dev environment — import is
lazy and failures degrade to the demo path instead of crashing the request.
"""
import logging
import threading

logger = logging.getLogger(__name__)

_ocr_engine = None
_engine_lock = threading.Lock()


class OcrUnavailableError(Exception):
    pass


def _get_engine():
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    with _engine_lock:
        if _ocr_engine is None:
            try:
                from paddleocr import PaddleOCR  # noqa: PLC0415
            except ImportError as exc:
                raise OcrUnavailableError(
                    "paddleocr is not installed — run `pip install paddleocr paddlepaddle` "
                    "to enable the real OCR pipeline."
                ) from exc
            # paddleocr 3.x removed `use_angle_cls`/`show_log` (constructor
            # raises ValueError on unknown kwargs, it doesn't just warn) --
            # the doc-orientation/unwarping/textline-orientation extras are
            # disabled since prescription label photos are already
            # upright-ish and it keeps CPU inference fast.
            # `enable_mkldnn=False` works around a real bug found while
            # installing this into the backend's CPU-only venv (Phase 3):
            # with oneDNN on, the text-detection model crashes with
            # `NotImplementedError: ConvertPirAttribute2RuntimeAttribute
            # not support [pir::ArrayAttribute<pir::DoubleAttribute>]` on
            # every call (paddlepaddle 3.3.1 CPU build) -- disabling oneDNN
            # avoids the broken code path entirely.
            _ocr_engine = PaddleOCR(
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
            )
    return _ocr_engine


def extract_text(image_bytes: bytes) -> str:
    """Run PaddleOCR over raw image bytes and return concatenated text lines."""
    engine = _get_engine()  # raises OcrUnavailableError before touching numpy/PIL

    import io
    import numpy as np
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # paddleocr 3.x's `.ocr()`/`.predict()` returns a list of dict-like
    # `OCRResult` objects (one per page), each carrying a flat `rec_texts`
    # list -- a different shape from the pre-3.x nested
    # `[[box, (text, conf)], ...]` per-page format this used to parse.
    result = engine.ocr(np.array(image))

    lines: list[str] = []
    for page in result or []:
        texts = page.get("rec_texts") if isinstance(page, dict) else None
        for text in texts or []:
            if text:
                lines.append(text)
    return "\n".join(lines)
