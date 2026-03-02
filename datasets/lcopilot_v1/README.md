# LCopilot Dataset v1

Deterministic synthetic dataset for LC importer/exporter workflow testing.

## Structure
- `cases/`: 200 case-level truth JSON files
- `pdf/`: 200 synthetic PDF documents (one per case)
- `manifests/master_manifest.csv`: runner ingestion manifest
- `manifests/master_manifest.jsonl`: JSONL manifest
- `reports/quality_report.md`: distribution + coverage checks
- `schema.json`: JSON schema for truth records

## Rebuild
```bash
python scripts/build_lcopilot_dataset_v1.py
python scripts/validate_lcopilot_dataset_v1.py
```
