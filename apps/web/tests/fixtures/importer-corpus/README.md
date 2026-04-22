# Importer synthetic corpus

Synthetic MT700 Import LCs plus matching supplier-document bundles for
testing the importer flows (Draft LC Review + Supplier Document Review)
across multiple trade corridors.

## Regeneration

```
python scripts/build_importer_corpus.py                 # all corridors + modes
python scripts/build_importer_corpus.py --corridor US-VN
python scripts/build_importer_corpus.py --corridor US-VN --mode DRAFT_CLEAN
```

Generator: `scripts/build_importer_corpus.py`
Corridor configs: `scripts/importer_corpus/corridors.py`
Renderers: `scripts/importer_corpus/render.py`

## Layout

```
importer-corpus/
├── US-VN/                    # US importer ← Vietnam supplier, USD, FOB
│   ├── DRAFT_CLEAN/          # Draft LC, pre-issuance, no issues
│   │   └── LC.pdf
│   ├── DRAFT_RISKY/          # Draft LC with clauses the examiner should flag
│   │   └── LC.pdf
│   └── SHIPMENT_CLEAN/       # Full presentation bundle, consistent end-to-end
│       ├── LC.pdf
│       ├── Invoice.pdf
│       ├── Bill_of_Lading.pdf
│       ├── Packing_List.pdf
│       ├── Certificate_of_Origin.pdf
│       ├── Insurance_Certificate.pdf
│       └── Inspection_Certificate.pdf
├── UK-IN/                    # UK importer ← India supplier, GBP, CIF
├── DE-CN/                    # Germany importer ← China supplier, EUR, FCA
└── BD-CN/                    # Bangladesh importer ← China supplier, USD, CFR
```

## Corridor mix

| Corridor | Importer | Supplier | Currency | Incoterm | Issuing Bank | Tax-ID regime |
|---|---|---|---|---|---|---|
| US-VN | US (LA, CA) | Vietnam (Hai Phong) | USD | FOB | JPMorgan Chase | EIN / DUNS / IOR |
| UK-IN | UK (London) | India (Jaipur) | GBP | CIF | HSBC UK | VAT / EORI / Companies House |
| DE-CN | Germany (Osnabrück) | China (Shanghai) | EUR | FCA | Deutsche Bank | USt-IdNr / EORI / HRB |
| BD-CN | Bangladesh (Savar) | China (Ningbo) | USD | CFR | Islami Bank BD | TIN / BIN / IRC |

No jurisdiction is hardcoded in renderer code — every piece of data
(party names, tax IDs, banks, ports, clauses) is driven by the corridor
config. Adding a new corridor is a dict addition in `corridors.py`.

## Modes

### DRAFT_CLEAN
Draft LC marked "NOT YET ISSUED / SUBJECT TO APPLICANT APPROVAL".
All clauses well-formed. Baseline — the examiner shouldn't raise
substantive issues.

### DRAFT_RISKY
Draft LC with red-flag modifications the examiner should catch:
- Presentation period tightened to 5 days (UCP default 21)
- Partial shipments allowed combined with tight delivery window
- `FREIGHT PREPAID` BL instruction flipped to `FREIGHT COLLECT`
  creating an Incoterm/BL-freight-term mismatch
- Country-of-origin marking requirement dropped
- 47A sanctions block removed

Expected examiner findings: presentation-period too tight, Incoterm /
BL freight mismatch, missing origin marking, missing sanctions clause.

### SHIPMENT_CLEAN
Complete 7-document presentation bundle:
- LC (issued)
- Commercial Invoice (signed, line-items sum correctly to grand total)
- Bill of Lading (clean, on-board, matching vessel/voyage/containers)
- Packing List (carton-wise breakdown, weights)
- Certificate of Origin (chamber-appropriate for corridor)
- Insurance Certificate (110% of CIF value, ICC (A) + War + Strikes)
- Inspection Certificate (corridor-appropriate body)

All documents reference the same LC number, invoice number, vessel,
voyage, and port pair. Cross-document consistency is intentional so
this set acts as the "clean baseline" — any finding the validator
raises against this bundle is likely a false positive worth investigating.
