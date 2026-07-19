"""
collect_pillbox.py — Download and preprocess the NIH Pillbox dataset.

Sprint-0 data collection script.
Outputs a DVC-tracked dataset directory at data/raw/pillbox/.

Usage:
    python data-collection/collect_pillbox.py --output data/raw/pillbox
"""
import argparse
import pathlib


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect NIH Pillbox dataset")
    p.add_argument("--output", type=pathlib.Path, default=pathlib.Path("data/raw/pillbox"))
    p.add_argument("--max-records", type=int, default=None, help="Limit records for dev testing")
    return p.parse_args()


def download_pillbox(output_dir: pathlib.Path, max_records: int | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Output directory: {output_dir.resolve()}")

    # TODO Sprint-0: implement actual download from NIH Pillbox API
    # Base URL: https://pillbox.nlm.nih.gov/API/
    print("[STUB] NIH Pillbox download not yet implemented.")
    print("[STUB] See: https://pillbox.nlm.nih.gov/developer.html")

    # Placeholder manifest
    manifest = output_dir / "manifest.txt"
    manifest.write_text("# Pillbox dataset manifest — populated after download\n")
    print(f"[INFO] Wrote placeholder manifest to {manifest}")


if __name__ == "__main__":
    args = parse_args()
    download_pillbox(args.output, args.max_records)
