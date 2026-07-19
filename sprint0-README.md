# Sprint-0 — PillSafe ML Baseline

## Objectives
- Collect and version the MEDISEG + NIH Pillbox datasets
- Train a baseline YOLOv8 segmentation model (3-pill classes)
- Validate OCR pipeline on synthetic label images
- Establish MLOps scaffold (DVC, MLflow, GitHub Actions)

## Folder Structure
```
Sprint-0/
├── orchestrator.ipynb       ← End-to-end pipeline notebook
├── data-collection/         ← Dataset download and preprocessing scripts
├── training/
│   └── trained-model-v0.h5  ← Baseline model artifact (placeholder)
├── dev/
│   └── dev-run-v0.py        ← Quick smoke-test script
└── documentation/           ← Sprint notes, design decisions
```

## Key Metrics (targets)
| Model | Metric | Target |
|-------|--------|--------|
| Pill Segmentation (YOLOv8) | mAP@50 | ≥ 80% |
| Pill Identification (CNN+FAISS) | Recall@3 | ≥ 75% |
| Label NLP (BioBERT NER) | F1 | ≥ 0.80 |

## Datasets
- **MEDISEG** — 8,262 images, 32 pill types (Buckley et al., 2025)
- **NIH Pillbox** — 10,000+ reference entries
- **C3PI** — Consumer product image archive

## How to Run
```bash
# 1. Install ML dependencies
pip install -r requirements-ml.txt

# 2. Pull datasets (DVC)
dvc pull

# 3. Open orchestrator notebook
jupyter notebook orchestrator.ipynb
```
