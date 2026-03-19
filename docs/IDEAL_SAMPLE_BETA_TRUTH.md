# IDEAL_SAMPLE_BETA_TRUTH.md

Purpose: canonical beta truth contract for the Export LC golden sample.

Golden sample source:
`F:\New Download\LC Copies\Synthetic\Export LC\IDEAL SAMPLE`

Files:
- `LC.pdf`
- `Invoice.pdf`
- `Bill_of_Lading.pdf`
- `Packing_List.pdf`
- `Certificate_of_Origin.pdf`
- `Insurance_Certificate.pdf`
- `Inspection_Certificate.pdf`
- `Beneficiary_Certificate.pdf`

This file is not a screenshot log. It is the expected product truth for this sample.

---

## 1. Scope

This contract is for:
- Export LC upload summary
- required-doc detection
- document-card truth
- checklist truth
- issue-card truth
- top-level readiness/compliance truth
- customs-pack readiness truth

This contract should be used to:
- guide fixes
- prevent regressions
- evaluate whether the beta is truthful

This contract should **not** be satisfied by sample-specific hardcoding.
Fixes must generalize across the same document families and truth model.

---

## 2. Core Beta Principle

For beta, the system must prefer:
- truthful uncertainty
- truthful review-needed states
- truthful source-document absence

over:
- fake certainty
- fake compliance
- fake readiness
- invented discrepancy logic

Allowed beta states:
- `Review needed`
- `Review recommended`
- `Extraction incomplete`
- `Unable to confirm from source document`
- `Uploaded but not required by LC`

Disallowed if unresolved review truth remains:
- `READY TO SUBMIT`
- `All documents comply with LC terms`
- `Documents appear compliant`
- any equivalent green-complete wording

---

## 3. Canonical LC Truth

### 3.1 Core LC identity
- Workflow: `Export LC`
- Instrument: `Documentary Credit`
- Terms: `Irrevocable`

### 3.2 Canonical dates
From LC fields:
- `31D: 261015USA` -> expiry date = `2026-10-15`
- `44C: 260930` -> latest shipment date = `2026-09-30`

These must never be reversed.

### 3.3 Uploadable required documents
The LC-required uploadable document set for this sample is:
1. Commercial Invoice
2. Bill of Lading
3. Packing List
4. Certificate of Origin
5. Inspection Certificate
6. Beneficiary Certificate

### 3.4 Conditions, not uploadable core docs
These are presentation/wording conditions, not separate core required document families:
- non-negotiable documents to be sent in one set by courier service within the required timeline
- all documents must show LC number / contract number / BIN number / TIN number where applicable

The UI must not invent fake required docs from these conditions.

### 3.5 Insurance requirement truth
This sample is FOB and the LC does not require insurance in the core required-doc contract.

Therefore:
- Insurance may be uploaded as an extra document
- Insurance must not be framed as a failed required document
- Insurance must not reduce requirement coverage as if it were LC-mandated

---

## 4. Per-Document Canonical Truth

## 4.1 LC document
Expected truth:
- LC number, amount, instrument/workflow semantics, goods description, key conditions should be materially correct
- expiry date must be `2026-10-15`
- latest shipment must be `2026-09-30`

Allowed status:
- matched / extracted / ready

Disallowed:
- reversed expiry/latest-shipment values

---

## 4.2 Commercial Invoice
Expected source truth:
- contains LC reference
- contains PO reference
- contains issuer/seller information
- contains line items
- contains quantities
- contains unit prices
- contains total amount
- does **not** contain gross weight or net weight in the source invoice

Canonical beta policy:
- invoice must not hard-fail or be review-blocked purely because invoice gross/net weight is absent
- invoice gross/net weight for this workflow should be treated as cross-document information, not invoice-critical source truth

Allowed status:
- matched / extracted / review only if caused by real source ambiguity or extraction ambiguity

Disallowed false review reasons:
- missing gross weight as invoice-critical failure
- missing net weight as invoice-critical failure

---

## 4.3 Bill of Lading
Expected source truth:
- vessel present: `MAERSK INFINITY`
- voyage present: `MX24A`
- shipment date present: `2026-09-24`
- ports and weight information materially present

Allowed status:
- matched / extracted / ready

Disallowed:
- pretending vessel data is missing when source clearly contains it

---

## 4.4 Packing List
Expected source truth:
- core commercial/packing anchors present
- PO no present
- BIN/TIN present
- net weight present
- gross weight present
- source document appears not to contain a date

Canonical beta policy:
- if date is absent in source, this may be a review note
- but wording must make clear this is source-document absence or policy review, not a fake extraction miss

Allowed status:
- review required if clearly labeled as source-document absence or policy review

Disallowed misleading wording:
- implying extraction failure if the field is simply not present in the source PDF

---

## 4.5 Certificate of Origin
Expected source truth:
- origin-related certificate content present
- issuer/authority context present
- exporter/importer/goods context materially present
- source does **not** clearly contain a certificate number
- LC does **not** explicitly require a certificate number for this sample

Canonical beta policy:
- COO must not be marked partial/failed purely because `certificate_number` is absent
- absence of certificate number may be informational at most if source truly lacks it

Allowed status:
- matched / extracted / acceptable with note if needed

Disallowed false review reasons:
- missing certificate number as hard or partial requirement failure

---

## 4.6 Insurance Certificate
Expected source truth:
- insurance document may parse successfully
- but this document is extra / non-required for this LC sample

Canonical beta policy:
- show as uploaded extra document, optional, or informational
- do not frame as requirement failure
- do not let it drag required-doc completion down

Allowed status:
- uploaded extra document
- non-required
- informational

Disallowed:
- `requirement partial` if that implies LC requirement failure

---

## 4.7 Inspection Certificate
Expected source truth:
- inspection content is present
- certificate contains quality/quantity/packing-related statements
- azo-dye / EU / US style language is materially present in the sample

Canonical beta policy:
- manual review may be acceptable in beta
- but wording must explain that this is conservative policy review or review-needed validation, not necessarily a detected discrepancy

Allowed status:
- matched / extracted / review required

Disallowed misleading wording:
- implying source failure when the source contains the expected attestation content

---

## 4.8 Beneficiary Certificate
Expected source truth:
- declaration/attestation content present
- LC reference present in the sample source
- PO reference present
- BIN/TIN present
- date present
- source does **not** clearly contain a certificate number

Canonical beta policy:
- beneficiary certificate must not fail because `certificate_number` is absent if the source does not contain one
- beneficiary certificate must not be marked missing LC reference if source clearly contains LC number
- beneficiary certificate is an attestation/declaration-style document and should be evaluated by truthful attestation semantics, not distorted neighboring-family assumptions

Allowed status:
- matched / extracted / acceptable or review-needed only for real extraction uncertainty

Disallowed false review reasons:
- missing LC reference when source contains it
- missing certificate number as a hard/partial requirement failure

---

## 5. Top-Level Truth Contract

## 5.1 Single truth principle
Top-level readiness, issues, overview summary, document cards, and customs-pack readiness must not contradict each other.

If unresolved review-needed document truth remains, then the product must not simultaneously claim full readiness/compliance.

## 5.2 Ready/compliant gating rule
The system must not say any variant of:
- `READY TO SUBMIT`
- `Documents appear compliant`
- `All documents comply with LC terms`

unless all of the following are true:
- no unresolved review-needed checklist states remain
- no unresolved per-document review-required states remain
- no unresolved issue-card-worthy problems remain
- customs/presentation readiness also agrees

## 5.3 Issues empty-state rule
An empty issues array does **not** automatically equal full compliance.

If issue cards are empty but review-needed states remain, the empty state must be truthful, for example:
- `No issue cards generated yet`
- `No rule-triggered issues detected, but document review is still required`

It must not say:
- `All documents comply with LC terms`

unless the broader truth contract supports that statement.

## 5.4 Customs-pack alignment rule
Customs-pack readiness must align with:
- checklist truth
- per-document review truth
- top-level readiness truth

Customs-pack must not be more optimistic than the document/checklist truth engine.

---

## 6. Requirement Framing Rules

### 6.1 Required vs uploaded-extra
The UI must distinguish between:
- required by LC
- uploaded and relevant
- uploaded but not required
- condition/presentation rule

### 6.2 No fake requirement failure
A document that is not LC-required must not be framed as a failed required document.

### 6.3 No fake missing-doc inflation
Conditions and wording requirements must not be inflated into fake document families.

---

## 7. Review-Reason Rules

Review reasons must distinguish clearly between:
- source-document absence
- extraction uncertainty
- normalization gap
- policy review
- deterministic contradiction
- compliance alert

The UI should not collapse these into vague or misleading generic failure text.

### Examples
Good:
- `Source document does not show a packing-list date`
- `Manual review required for attestation wording`
- `No issue card generated, but review is still required`

Bad:
- `Field not found` when the field is genuinely absent from the source and that is expected
- `All documents comply` when review-needed states remain

---

## 8. Discrepancy / Compliance Rules

### 8.1 Price discrepancy safety rule
The system must never present total invoice amount as if it were a unit price.

If safe unit-price basis is unavailable:
- suppress the unit-price discrepancy card
- or label the comparison as unavailable / incomplete

### 8.2 Sanctions alert safety rule
The system must not generate a sanctions-style alert from missing or unknown flag-state data alone in a way that appears like a real sanctions hit.

Real explainable sanctions/name matches may still alert.
False escalation from missing enrichment must not.

---

## 9. Progress / Processing Truth Rules

If progress UI is simulated or estimated, it must not imply exact backend-truth progress.

Allowed:
- `Estimated progress`
- `Processing documents... this may take 1–2 minutes`
- stage labels clearly presented as estimated

Disallowed:
- exact-looking backend truth claims if the UI is only heuristic/simulated

---

## 10. Ship Blockers For This Sample

These are ship blockers if still present:
- contradictory top-level states
- false `ready/compliant` states
- reversed LC dates
- false required-doc framing for insurance
- false beneficiary missing-LC-reference review reason
- false COO missing-certificate-number partial/failure state
- invoice hard-fail/review due solely to missing invoice gross/net weights
- fake or unsafe unit-price discrepancy generation
- false sanctions escalation from missing flag-risk enrichment

---

## 11. Acceptable Beta Debt For This Sample

These may remain for beta if truthfully labeled:
- lower extraction confidence on secondary docs
- manual review on inspection/attestation wording
- review-needed states where source is ambiguous
- incomplete subtype specialization for supporting-doc families
- generic supporting-document handling that is honest about uncertainty
- slower processing if the product remains truthful and stable

Not acceptable beta debt:
- contradictions between truth engines
- fake readiness/compliance
- known false review reasons
- invented discrepancy/compliance logic

---

## 12. Acceptance Checklist

A fix is acceptable against this contract only if all of the following hold:
- upload summary shows correct dates
- required docs list matches the LC
- conditions are not inflated into fake docs
- insurance is not treated as failed requirement coverage
- beneficiary cert is not falsely marked missing LC reference
- COO is not penalized for missing certificate number in this sample
- invoice is not falsely blocked for missing gross/net weights
- top-level readiness does not contradict document/checklist/customs truth
- issues empty state does not overclaim compliance
- no fake unit-price discrepancy is generated
- no false sanctions escalation is generated from missing flag-state logic

---

## 13. Usage Instructions For Agents

When using this file:
- treat it as the canonical expected truth for the golden sample
- do not hardcode specifically to this sample’s filenames/values unless the change is truly LC-field mapping or general truth logic
- prefer global truth-model fixes over screen-specific patches
- add regression coverage where possible
- if local code and live behavior differ, classify as deploy/path/runtime mismatch rather than mutating the truth contract
