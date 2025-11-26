# Gold Corpus - LCopilot Validation Test Suite

## Purpose

The Gold Corpus is a curated set of LC document bundles with known-correct validation outcomes. It serves as:

1. **Regression testing** - Ensure changes don't break existing functionality
2. **Quality measurement** - Track extraction and validation accuracy over time
3. **Benchmarking** - Compare different extraction strategies

## Structure

```
gold_corpus/
├── documents/              # Test document sets
│   ├── set_001_synthetic_bd/   # Synthetic Bangladesh export LC
│   ├── set_002_real_sight/     # Real sight LC (anonymized)
│   └── ...
├── expected/               # Expected validation results
│   ├── set_001_synthetic_bd.json
│   └── ...
├── baselines/              # Saved baseline metrics
│   ├── baseline_20250101.json
│   └── ...
├── results/                # Run results (gitignored)
│   └── ...
├── run_corpus.py           # Main test runner
├── metrics.py              # Metric calculations
├── expected.py             # Expected result schema
└── README.md
```

## Usage

### Run All Tests
```bash
cd apps/api
python -m tests.gold_corpus.run_corpus
```

### Run Specific Set
```bash
python -m tests.gold_corpus.run_corpus --set set_001_synthetic_bd
```

### Save Baseline
```bash
python -m tests.gold_corpus.run_corpus --baseline
```

### Compare Against Baseline
```bash
python -m tests.gold_corpus.run_corpus --compare baseline_20250101.json
```

## Adding New Test Sets

### 1. Create Document Directory
```
documents/set_XXX_description/
├── LC.pdf
├── Invoice.pdf
├── Bill_of_Lading.pdf
├── Certificate_of_Origin.pdf
├── Packing_List.pdf
└── Insurance_Certificate.pdf
```

### 2. Create Expected Results
Create `expected/set_XXX_description.json`:

```json
{
  "set_id": "set_XXX_description",
  "description": "Human-readable description",
  "version": "1.0",
  "expected_compliance_rate": 85.0,
  "compliance_tolerance": 5.0,
  "expected_status": "warning",
  "expected_fields": [
    {
      "document_type": "lc",
      "field_name": "lc_number",
      "expected_value": "LC123456",
      "match_type": "exact",
      "criticality": "critical"
    }
  ],
  "expected_issues": [
    {
      "rule_id": "UCP600-14A",
      "severity": "major",
      "document_type": "invoice",
      "title_contains": "amount mismatch"
    }
  ],
  "false_positive_checks": [
    {
      "rule_id": "CROSSDOC-PORT-1",
      "description": "Port names are equivalent"
    }
  ]
}
```

## Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Extraction Coverage | >95% | % of critical fields extracted |
| Critical Field Coverage | 100% | Critical fields must be extracted |
| F1 Score | >0.90 | Balance of precision and recall |
| False Positive Rate | <5% | Issues incorrectly raised |
| Critical Miss Rate | 0% | Critical issues must never be missed |

## Field Criticality

- **Critical**: Must be extracted (LC amount, beneficiary, currency)
- **Important**: Should be extracted (ports, dates, goods description)
- **Optional**: Nice to have (additional clauses)

## Match Types

- `exact`: Exact string match (case insensitive)
- `contains`: Expected value contained in actual
- `regex`: Regular expression match
- `numeric_tolerance`: Within percentage tolerance

## CI Integration

Add to CI pipeline:
```yaml
- name: Run Gold Corpus
  run: |
    cd apps/api
    python -m tests.gold_corpus.run_corpus --compare baseline_latest.json
```

The test fails if:
- Any critical field is not extracted
- Any critical issue is missed
- False positive rate increases
- F1 score decreases significantly

