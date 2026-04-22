# RulHub status — post-deploy cross-check (2026-04-21 late evening)

Probe: `scripts/rulhub_probe.py` in the trdrhub repo. 12-document IDEAL-SAMPLE-shaped payload against `api.rulhub.com/v1/validate/set`. This note follows the cross-check we ran after your commit `76afcb79`.

## Acknowledgment — your 4 fixes work

| Commit | What | Verified post-deploy |
|---|---|---|
| `702d08e6` | `/v1/validate/set` refactor (nested envelope, multi-family fan-out, `rules_checked`) | ✓ `rules_checked=744` now populated |
| `1f15d5e1` | Category C: 4 new CROSSDOC rules + `computed_amount_comparison` validator + `conditional_logic` | ✓ `CROSSDOC-DATE-INSP-BL-001` fires cleanly with full evidence |
| `04ef35a4` | Numeric preflight silent-pass + reverse path alias + days alias | ✓ Engine-error filter matches **0** findings (was 3). `CROSSDOC-BL-LC-12` carrier resolves correctly via reverse alias |
| `76afcb79` | Render templates for `conditional_logic` / `computed_amount_comparison` + UCP600 port equality rewrite (15 rules) + `EnumValue` absent-field silent-pass | ✓ Finding text is human-readable. Example: `"'coo.country_of_origin' ('BANGLADESH') does not match 'lc.country_of_origin' (missing)"`. Port-equality false-positives gone from top 20. `enum_value` "invalid on absent" gone. |

Metrics delta:

| Metric | Morning (pre your deploys) | Post-`1f15d5e1` | Post-`76afcb79` |
|---|---|---|---|
| findings | 4 | 336 | **321** |
| score | 0.9468 | 0.6638 | **0.6761** |
| rules_checked | None | 744 | 744 |
| engine-error filter matches | 3 | 0 | **0** |
| field_a populated | — | 54 | **39** |

## Cross-check — the 39 evidence-bearing findings (IDEAL SAMPLE payload)

We walked all 39. Verdict:

| Category | Count |
|---|---|
| True positive matching known IDEAL SAMPLE discrepancy | **1** |
| False positive — rule fired on document type NOT in submission (sea_waybill, draft, multimodal_doc, transport_doc, charter_party_bl) | **16** |
| Vocabulary/enum mismatch — payload sends business strings, rule expects enum values | **4** |
| Rule-authoring bugs — rule compares field against a literal string instead of a reference-field | **4** |
| Payload-gap (our incompleteness; not a real IDEAL SAMPLE discrepancy) | **10** |
| Other (transferable-LC rule, partial country/cartons match) | **4** |

Only **1 out of 6 known IDEAL SAMPLE discrepancies** surfaces cleanly post-deploy (inspection-cert shipment date mismatch — perfect). The others are either in the 282 null-evidence noise bucket OR not firing because of payload gaps on our side OR blocked by the issues below.

## Three new asks for RulHub side

### A) Rule-applicability gating — HIGHEST IMPACT

**Problem:** Rules fire on document types that are not present in the submission.

Our payload presents 12 doc types: `lc, credit, invoice, bl, bill_of_lading, packing_list, coo, insurance, insurance_doc, inspection_certificate, beneficiary_certificate, presentation`.

But these rules still fired demanding evidence on absent doc types:

| Rule | Demands field from | Our submission has |
|---|---|---|
| UCP600-21 (×5 findings: #15-19) | `sea_waybill.carrier_name`, `sea_waybill.date_of_shipment`, `sea_waybill.port_of_loading`, `sea_waybill.port_of_discharge`, `sea_waybill.original_set` | NO sea_waybill |
| UCP600-22 (×3: #20-22) | `charter_party_bl.*` fields | NO charter_party_bl |
| ISBP821-B8 / B14 (×3: #28-30) | `draft.issue_date`, `draft.drawer`, `draft.currency_code` | NO draft |
| ISBP821-D9 / D13 (×2: #31-32) | `multimodal_doc.port_of_loading`, `multimodal_doc.port_of_discharge` | NO multimodal_doc |
| ISBP821-F5 / F8 / J5 (×4: #33-34, #37-38) | `transport_doc.port_of_loading`, `transport_doc.port_of_discharge`, `transport_doc.place_of_loading`, `transport_doc.place_of_discharge` | NO generic transport_doc |
| ISBP821-G5 / G8 (×2: #35-36) | `charter_party_bl.port_of_loading`, `charter_party_bl.port_of_discharge` | NO charter_party_bl |

= **16 findings** (41% of the 39 evidence-bearing list) that are "rule wanted X on doc type Y, but Y isn't in the submission".

**Proposed fix:** Before running a rule, check whether the rule's `target_document_types` (or equivalent metadata) intersect with the set of documents in the submission. If not, skip the rule silently instead of reporting its fields as "missing". This is an applicability gate, not a new capability.

If the rule metadata doesn't include a `target_document_types` attribute, it's inferable from the `first_path` / `second_path` prefixes — if every referenced path starts with `sea_waybill.*` and `sea_waybill` isn't a presented doc type, skip.

**Impact estimate:** this alone kills those 16 evidence-bearing noise findings and presumably a big slice of the 282 null-evidence bucket too.

### B) Rule-authoring bugs — 4 rules with string literals where reference_field paths should be

Each of these reports the rule's raw config as if it were a field value:

```
#6  UCP600-2:  'credit.irrevocable' (True) does not match 'True' (missing)
#7  UCP600-3:  'credit.irrevocable' (True) does not match 'True' (missing)
#14 UCP600-20: 'bill_of_lading.transhipment_allowed' (False) does not match
               'true_if_container_or_one_document' (missing)
#25 UCP600-28: 'insurance_doc.risks_covered' ('INSTITUTE CARGO CLAUSES (A)') does not match
               'shipment_to_final_destination' (missing)
```

Pattern: the rule's `reference_field` is set to a string literal (`"True"`, `"true_if_container_or_one_document"`, `"shipment_to_final_destination"`) instead of a resolvable field path, so the resolver can't find the path and returns "missing".

**Proposed fix:** These rules need their reference_field rewritten. `UCP600-2` / `UCP600-3` should probably use `expected_value: true` (a boolean literal in the rule config) rather than `reference_field: "True"` (which the resolver tries to resolve as a field path). Similarly `true_if_container_or_one_document` looks like it was intended as a conditional expression that got frozen as a literal. `shipment_to_final_destination` looks like it was intended as an enum-value literal compared against risks_covered.

Four rule edits on your side. Will need review of what each rule was MEANT to check.

### C) Vocabulary / enum mismatch — payload semantics vs rule expectation

Three fields where we send business-language strings, you expect enum values:

| Finding | Our payload | Rule expects (allowed values) |
|---|---|---|
| #5 UCP600-1  | `credit.type = "IRREVOCABLE"` | `documentary_credit`, `standby_credit` |
| #13 UCP600-20 / #27 ISBP821-E5 | `bill_of_lading.signature_party = "AS AGENT FOR THE CARRIER"` | `carrier`, `agent_for_carrier`, `master`, `agent_for_master`, `captain`, `agent_for_captain` |
| #23 UCP600-28 | `insurance_doc.issuer = "Green Delta Insurance Co."` | `insurance_company`, `underwriter`, `agent_for_insurer`, `proxy_for_insurer` |

In the first and third cases the field semantics are different:
- **`credit.type`** — our value `"IRREVOCABLE"` is actually the `irrevocable` attribute of the credit. The `type` field is asking about `documentary_credit` vs `standby_credit`. Ambiguous naming. We'll normalize on our side.
- **`insurance_doc.issuer`** — we send the issuer's COMPANY NAME (what the document says). Your rule is asking about the issuer's TYPE / ROLE (the enum). These are different attributes. You probably want a separate `insurance_doc.issuer_type` field.

For `bill_of_lading.signature_party`, the document language literally says `"AS AGENT FOR THE CARRIER"`. A normalizer on either side could map this phrase to the enum value `agent_for_carrier`.

**Proposed fix (options):**
- (Option 1) RulHub rules accept a normalizer — known phrase → enum mapping. Low lift.
- (Option 2) Expose the expected enum domain via a field-schemas endpoint so we can map at payload-build time. More flexible for trdrhub.
- (Option 3) Rename the ambiguous fields (`credit.type` → `credit.credit_form`, add `insurance_doc.issuer_type` distinct from `insurance_doc.issuer_name`).

Ripon's call which to do. We can handle the normalization on our side if you prefer, just need the allowed enum lists.

## One bonus question — `UCP600-38G` behavior

Finding `#26`: `'first_beneficiary_invoice.amount' (397050.0) greater_than 'lc.amount' (458750.0) failed`

The math says 397050 is LESS than 458750 (by $61,700), so the `greater_than` check should evaluate as False. The finding reports it as "failed" — unclear whether that means "the check failed to hold" (i.e. the invoice is NOT greater than LC, which is typically fine for a non-transferable presentation) or "the rule itself failed to evaluate".

If the former, then for a non-transferable LC this shouldn't fire at all. If the rule is transferable-LC-specific (`first_beneficiary_invoice` suggests so), it should gate on `lc.is_transferred == True`. Our payload has `lc.is_transferred = False`.

Probably fits under (A) — applicability gating by `is_transferred` boolean.

## The one true-positive — confirmation

`CROSSDOC-DATE-INSP-BL-001` (new Category C rule) fires perfectly:
```
msg:      'inspection_certificate.shipment_date' ('2026-04-20') does not match 'bl.shipment_date' ('2026-09-24')
field_a:  inspection_certificate.shipment_date = 2026-04-20
field_b:  bl.shipment_date = 2026-09-24
severity: fail
docs:     bl, inspection_certificate
```

This is the gold standard for how every finding should render. Thank you — this is real progress.

## Priority suggestion

Do **(A) applicability gating** first — biggest noise reduction by far, and unblocks our own cross-check work. (B) and (C) can follow.

After (A) lands we'll re-probe and run the cross-check again. Expect the 321 to drop substantially.
