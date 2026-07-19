"""
dev-run-v0.py — Sprint-0 smoke test

Loads the baseline model artifact and runs inference on a sample image
to verify the training pipeline produced a working checkpoint.

Usage:
    python dev/dev-run-v0.py --image path/to/pill.jpg
"""
import argparse
import pathlib
import sys

MODEL_PATH = pathlib.Path(__file__).parent.parent / "training" / "trained-model-v0.h5"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PillSafe v0 smoke test")
    p.add_argument("--image", type=pathlib.Path, help="Path to a test pill image")
    p.add_argument("--conf", type=float, default=0.5, help="Confidence threshold")
    return p.parse_args()


def run_inference(image_path: pathlib.Path, conf_threshold: float) -> None:
    if not MODEL_PATH.exists():
        print(f"[WARN] Model not found at {MODEL_PATH}. Run training first.")
        sys.exit(1)

    print(f"[INFO] Loading model from {MODEL_PATH}")
    # TODO Sprint-0: replace stub with actual YOLOv8 load
    # model = YOLO(MODEL_PATH)
    # results = model(str(image_path), conf=conf_threshold)

    print(f"[STUB] Would run inference on: {image_path}")
    print(f"[STUB] Confidence threshold: {conf_threshold}")
    print("[STUB] Detected pills: []  (model not yet trained)")


if __name__ == "__main__":
    args = parse_args()
    if args.image is None:
        print("[INFO] No image provided — running in stub mode")
        run_inference(pathlib.Path("sample.jpg"), args.conf)
    else:
        run_inference(args.image, args.conf)
