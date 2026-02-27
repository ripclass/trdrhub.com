#!/usr/bin/env python3
from day3_pipeline_core import bootstrap_dirs

if __name__ == "__main__":
    dirs = bootstrap_dirs()
    for d in dirs:
        print(d)
