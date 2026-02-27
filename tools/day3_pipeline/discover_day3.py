#!/usr/bin/env python3
from day3_pipeline_core import bootstrap_dirs, discover_inputs

if __name__ == "__main__":
    bootstrap_dirs()
    rows = discover_inputs()
    print(f"discovered={len(rows)}")
