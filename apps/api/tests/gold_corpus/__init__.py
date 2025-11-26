"""
Gold Corpus - Test suite for validation robustness.

Structure:
    gold_corpus/
    ├── documents/              # Test document sets
    │   ├── set_001_standard/   # Clean MT700 + supporting docs
    │   ├── set_002_messy/      # Low quality scans
    │   └── ...
    ├── expected/               # Expected validation results
    │   ├── set_001.json
    │   └── ...
    ├── run_corpus.py           # Main test runner
    └── metrics.py              # Metric calculations

Usage:
    python -m tests.gold_corpus.run_corpus
    python -m tests.gold_corpus.run_corpus --set set_001
    python -m tests.gold_corpus.run_corpus --baseline  # Save as baseline
"""

