# Sprint-0 Technical Notes

## Design Decisions

### Model Architecture
- YOLOv8n chosen for pill segmentation (speed/accuracy trade-off for <5s target)
- CNN metric learning + FAISS for pill identification (avoids unsafe one-shot certainty)
- PaddleOCR + BioBERT NER for label parsing

### Dataset Strategy
- MEDISEG: instance segmentation masks, 8,262 images, 32 pill types
- NIH Pillbox: reference database for pill identification lookup
- C3PI: consumer packaging images for OCR training

### Governance
- No raw PHI collected at any stage
- All datasets are public domain
- LLM receives only structured, de-identified pipeline output

## References
1. Buckley et al. (2025). MEDISEG. arXiv:2603.10825
2. Wang et al. (2024). YOLOv9. arXiv:2402.13616
3. Dang et al. (2024). Real-Time Pill ID. arXiv:2405.05983
