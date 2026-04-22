"""
Build the importer synthetic corpus.

Generates a directory tree of MT700-shaped LCs plus supporting document
bundles under apps/web/tests/fixtures/importer-corpus/. Corridors and
modes are controlled by CLI flags; by default it builds the full matrix.

Usage:
    python scripts/build_importer_corpus.py
    python scripts/build_importer_corpus.py --corridor US-VN
    python scripts/build_importer_corpus.py --corridor US-VN --mode DRAFT_CLEAN
    python scripts/build_importer_corpus.py --out /tmp/corpus-test

The output:
    <out>/<corridor>/DRAFT_CLEAN/LC.pdf
    <out>/<corridor>/DRAFT_RISKY/LC.pdf
    <out>/<corridor>/SHIPMENT_CLEAN/{LC, Invoice, Bill_of_Lading,
                                     Packing_List, Certificate_of_Origin,
                                     Insurance_Certificate,
                                     Inspection_Certificate}.pdf

No external GTK / cairo deps — pure ReportLab. Runs on Windows, macOS,
and Linux identically.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.importer_corpus.corridors import CORRIDORS, corridor_keys, get_corridor
from scripts.importer_corpus.render import (
    render_bill_of_lading,
    render_certificate_of_origin,
    render_inspection_certificate,
    render_insurance_certificate,
    render_invoice,
    render_lc,
    render_packing_list,
)

MODES = ["DRAFT_CLEAN", "DRAFT_RISKY", "SHIPMENT_CLEAN"]
DEFAULT_OUT = ROOT / "apps" / "web" / "tests" / "fixtures" / "importer-corpus"


def build_set(corridor_key: str, mode: str, out_root: Path) -> List[Path]:
    """Generate one corridor+mode bundle. Returns list of files produced."""
    c = get_corridor(corridor_key)
    target = out_root / corridor_key / mode
    produced: List[Path] = []

    lc_path = target / "LC.pdf"
    render_lc(c, mode, lc_path)
    produced.append(lc_path)

    if mode == "SHIPMENT_CLEAN":
        pairs = [
            ("Invoice.pdf", render_invoice),
            ("Bill_of_Lading.pdf", render_bill_of_lading),
            ("Packing_List.pdf", render_packing_list),
            ("Certificate_of_Origin.pdf", render_certificate_of_origin),
            ("Insurance_Certificate.pdf", render_insurance_certificate),
            ("Inspection_Certificate.pdf", render_inspection_certificate),
        ]
        for filename, fn in pairs:
            path = target / filename
            fn(c, path)
            produced.append(path)

    return produced


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corridor",
        choices=corridor_keys() + ["all"],
        default="all",
        help="Which corridor to build (default: all).",
    )
    parser.add_argument(
        "--mode",
        choices=MODES + ["all"],
        default="all",
        help="Which mode to build (default: all).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output directory (default: {DEFAULT_OUT}).",
    )
    args = parser.parse_args()

    corridors = corridor_keys() if args.corridor == "all" else [args.corridor]
    modes = MODES if args.mode == "all" else [args.mode]

    total = 0
    for corridor in corridors:
        for mode in modes:
            produced = build_set(corridor, mode, args.out)
            total += len(produced)
            print(
                f"[{corridor}/{mode}] wrote {len(produced)} file(s): "
                + ", ".join(p.name for p in produced)
            )

    try:
        where = str(args.out.relative_to(ROOT))
    except ValueError:
        where = str(args.out)
    print(f"\nDone — {total} file(s) under {where}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
