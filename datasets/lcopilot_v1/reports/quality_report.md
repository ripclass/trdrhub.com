# LCopilot Dataset v1 - Quality Report

## Distribution Summary
- Total cases: 200
- Verdicts: pass=80, warn=80, reject=40
- Splits: train=140, val=30, test=30
- Roles: exporter=100, importer=100
- Modes: sea=80, air=80, multimodal=40
- Scan variants: clean=100, ocr_noisy=100

## Coverage Matrix (verdict x role x mode)

### PASS
- exporter: sea=18 air=20 multimodal=9
- importer: sea=9 air=14 multimodal=10

### WARN
- exporter: sea=18 air=9 multimodal=11
- importer: sea=16 air=21 multimodal=5

### REJECT
- exporter: sea=8 air=6 multimodal=1
- importer: sea=11 air=10 multimodal=4

## Scenario Issue Coverage
- missing_doc: 30
- mismatch: 28
- sanctions_risk: 10
- clause_edge: 33
- ocr-related: 19

## Known Limitations
- Documents are synthetic and intentionally simplified one-page PDFs for deterministic testing.
- No real customer/beneficiary entities are included (PII-safe).
- Sanctions scenarios are rule-trigger simulations, not live sanctions list matches.

## Quick Usage Commands
```bash
python scripts/build_lcopilot_dataset_v1.py
python scripts/validate_lcopilot_dataset_v1.py
```