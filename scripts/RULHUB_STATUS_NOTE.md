# RulHub status — from trdrhub-side probe (2026-04-21)

Probe: `scripts/rulhub_probe.py` + `scripts/rulhub_probe_sources.py` in the
trdrhub repo. POSTs a 12-document IDEAL-SAMPLE-shaped payload to
`api.rulhub.com/v1/validate/set`. Validation ID example
`69af8563-c092-45bf-8601-b29059d7befc`.

## Progress since 2026-04-17 evening

- Previous state: 70 findings, of which ~62 were `"Unknown condition type: X"`
  engine errors across 10+ distinct condition types.
- Current state: **4 findings**, zero "Unknown condition type" errors. Good
  cleanup — that layer of engine bugs is gone.

## What's still broken

### Engine bugs (3 of 4 findings, same pattern)

All have null `field_a`/`field_b`/`value_a`/`value_b`. trdrhub's engine-error
pre-veto filter drops them, but each represents a rule that fired and crashed
during condition evaluation instead of evaluating cleanly.

| rule_id | finding text | suspected cause |
|---|---|---|
| `CROSSDOC-INV-LC-1` | `"One or both values are not numeric"` | numeric comparator invoked on non-numeric path; preflight coercion returns error as finding |
| `CROSSDOC-INV-LC-8` | `"One or both values are not numeric"` | same category |
| `CROSSDOC-TIME-1`   | `"presentation_period requires max_days/value"` | rule JSON missing `max_days` / `value` param |

### Rule catalog mismatch (1 of 4 findings, false positive)

| rule_id | finding text | field_a |
|---|---|---|
| `CROSSDOC-BL-LC-12` | `"Required field 'bl.carrier_name' is missing"` | `bl.carrier_name` |

Payload explicitly sends `carrier_name: "MAERSK LINE"` under both `bl` and
`bill_of_lading` prefixes. Server's `per_document_results` confirms `bl`
received 32 fields. Rule still resolves `bl.carrier_name` to null.

Per the RulHub conventions memo, `bl` short-prefix schema lists:
`consignee, container_number, freight_terms, goods_description, notify_party,
number_of_packages, originals_issued, originals_presented, port_of_discharge,
port_of_loading, seal_number, shipment_date, shipper, shipping_marks,
transhipment, vessel_name`.

`carrier_name` is **not** in that list. It's only in the `bill_of_lading`
long-prefix schema. The rule needs either:
- Reference `bill_of_lading.carrier_name` (fixes it on rule side), or
- Add `carrier_name` to the `bl` short-prefix schema

### Entire rule catalogs not firing

The `rules` request parameter is **ignored** by the server. Six variants
(`None`, `"crossdoc"`, `"ucp600"`, `"isbp821"`, `"isbp745"`, `"ucp"`) all
return byte-identical responses: same 4 findings, same score 0.9471, same
`validation_id` format. Either the filter isn't wired, or every call uses
the same engine default.

Missing from the response regardless of filter:
- **UCP600 core rules** — UCP600-18A/B/C name/currency comparators. Payload
  has `invoice.issuer_name="Dhaka Knitwear..."` and
  `lc.beneficiary_name="Dhaka Knitwear..."` populated. No UCP600-prefix
  rule_ids appear in the response.
- **ISBP821 deep rules** — `isbp821_invoice_deep_2a`,
  `isbp821_transport_deep_2a`, `isbp821_certificate_deep_2a`,
  `isbp821_insurance_deep_2a`, `isbp821_general_a1_a39_deep_2a`. No
  ISBP821-prefix rule_ids appear.

Prior audit memo (2026-04-17) noted these catalogs had 60+ rules with titles
but zero conditions. Status of that backfill is unclear from the response —
from the consumer side it looks like 0 fire.

## Known IDEAL SAMPLE findings RulHub should (but doesn't) surface

These are real discrepancies Ripon verified by hand reading the PDFs. The
trdrhub AI Examiner catches most of them when OpenRouter credits are
available. RulHub is silent on all of them today:

1. **Invoice arithmetic gap** — invoice stated total $397,050, but
   Σ(qty × unit_price) = 30,000 × $15.30 = $459,000. $61,700 discrepancy.
2. **BL missing CLEAN ON-BOARD notation** — the BL text lacks the
   "CLEAN ON BOARD" stamp; LC 46A requires it.
3. **Invoice unsigned** — the invoice PDF has no signature block filled.
4. **Inspection cert shipment date mismatch** — cert shows 2026-04-20, BL
   shows 2026-09-24. Same shipment, different dates.
5. **PL carton-wise breakdown missing** — packing list reports total but no
   per-carton detail.
6. **FOB insurance extraneous** — LC is FOB, buyer arranges insurance; seller
   presenting insurance certificate is an extraneous document.

## Asks, in priority order

1. **Confirm whether ISBP821 deep rules have been unsilenced.** If the
   backfill is done but rules still don't fire, there's an engine-layer gate
   somewhere. If it's not done, is there an ETA?
2. **Engage UCP600 core rules on `/v1/validate/set`.** No UCP600-prefix
   findings appear. UCP600-18A/B/C should fire on any payload with
   `invoice.issuer_name` + `lc.beneficiary_name` populated. Check the
   source-filter / document-type routing in the set endpoint.
3. **Fix `CROSSDOC-BL-LC-12`** — point it at `bill_of_lading.carrier_name`,
   or add `carrier_name` to the `bl` schema. Trivial one-line fix.
4. **Fix 3 engine bugs**:
   - `CROSSDOC-INV-LC-1` + `CROSSDOC-INV-LC-8`: numeric preflight. Either
     coerce silently, or silent-pass when operand is non-numeric. Don't
     surface the coercion error as a finding.
   - `CROSSDOC-TIME-1`: rule JSON needs `max_days` or `value` parameter.

## Reference — full raw response (verbatim)

```json
{
  "compliant": false,
  "score": 0.9471,
  "documents_checked": 12,
  "cross_document_discrepancies": [
    {"rule_id": "CROSSDOC-INV-LC-1", "severity": "fail",
     "finding": "One or both values are not numeric",
     "documents_involved": ["beneficiary_certificate", "bill_of_lading", "bl", "coo", "credit", "inspection_certificate", "insurance", "insurance_doc", "invoice", "lc", "packing_list", "presentation"],
     "field_a": null, "value_a": null, "field_b": null, "value_b": null, "recommendation": null},
    {"rule_id": "CROSSDOC-INV-LC-8", "severity": "fail",
     "finding": "One or both values are not numeric",
     "documents_involved": ["... same 12 ..."],
     "field_a": null, "value_a": null, "field_b": null, "value_b": null, "recommendation": null},
    {"rule_id": "CROSSDOC-BL-LC-12", "severity": "fail",
     "finding": "Required field 'bl.carrier_name' is missing",
     "documents_involved": ["bl"],
     "field_a": "bl.carrier_name", "value_a": null, "field_b": null, "value_b": null,
     "recommendation": "Add the 'bl.carrier_name' field to your document"},
    {"rule_id": "CROSSDOC-TIME-1", "severity": "fail",
     "finding": "presentation_period requires max_days/value",
     "documents_involved": ["... same 12 ..."],
     "field_a": null, "value_a": null, "field_b": null, "value_b": null, "recommendation": null}
  ],
  "per_document_results": {
    "lc": {"fields": 28}, "credit": {"fields": 28},
    "invoice": {"fields": 18},
    "bl": {"fields": 32}, "bill_of_lading": {"fields": 32},
    "packing_list": {"fields": 8},
    "coo": {"fields": 10},
    "insurance": {"fields": 10}, "insurance_doc": {"fields": 10},
    "inspection_certificate": {"fields": 6},
    "beneficiary_certificate": {"fields": 4},
    "presentation": {"fields": 1}
  },
  "processing_time_ms": 15,
  "validation_id": "69af8563-c092-45bf-8601-b29059d7befc"
}
```

## Note on the response shape

No `rules_checked` / `rules_evaluated` / `applicable_rules` field. The
original RulHub OpenAPI schema (`V1ValidateSetResponse`) names
`rules_checked` — it's absent in production. Consider re-adding it as the
primary consumer-side diagnostic: "we have no way to tell whether 4 rules
fired or 400 rules fired and 396 silent-passed".

Field ordering in the response is `compliant / score / documents_checked /
cross_document_discrepancies / per_document_results / processing_time_ms /
validation_id`. `discrepancies` (per-doc findings) is absent entirely in
this response — may need explicit emit even when empty for consistency.
