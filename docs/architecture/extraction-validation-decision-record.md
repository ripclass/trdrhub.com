# ADR: Extraction Truth Before Validation

Status: Accepted  
Date: 2026-03-25

## Decision

TRDR Hub / LCopilot will treat documentary credit checking as a requirements-and-evidence decision system.

The product flow is:

1. compile LC requirements
2. extract document evidence into a closed fact set
3. ask the SME only bounded confirmation questions when needed
4. run layered validation against closed facts
5. emit a readiness decision and action list

This replaces the mixed model where extraction uncertainty, review flags, validation findings, and readiness state all leak into one shared workflow surface.

## Why This Decision Exists

The current system has spent too long in a transitional state where truth is spread across:

- `extracted_fields`
- `field_details`
- `fact_graph_v1`
- `resolution_queue_v1`
- `fact_resolution_v1`
- `missing_required_fields`
- `parse_complete`
- `review_required`
- `review_reasons`
- workflow-stage and contract overlays

That causes predictable failure modes:

- queue and stage count drift
- legacy parser debt leaking into fact-backed docs
- validation being shown before truth is closed
- SMEs being asked to resolve specialist ambiguity
- repeated live fixes without a stable architectural boundary

## Product Rulebook

### 1. LCopilot is not a document-checker workbench

LCopilot is an SME-facing documentary credit decision system.

Its job is to:

- understand the LC
- understand what the uploaded documents evidence
- determine whether the evidence satisfies the LC requirements
- ask the user only a few bounded questions when the system cannot close a critical fact

It is not the user's job to interpret LC clauses, non-documentary conditions, or bank-practice semantics.

### 2. Requirements, Facts, Findings

Only three workflow-driving concepts matter:

- `RequirementsGraph`: what the LC requires
- `FactSet`: what the uploaded documents evidence
- `Findings`: whether the facts satisfy the requirements

Everything else is support structure, debug data, or backward-compatibility baggage.

### 3. Validation starts only after facts are closed enough

Validation may precompute internal candidates, but no user-facing validation verdict, readiness surface, or discrepancy workflow is authoritative until facts are closed enough for the current case version.

That means:

- extraction review is not validation
- unresolved extraction must not be promoted as final discrepancy truth
- readiness cannot be final while fact closure is still open

### 4. User tasks are bounded and evidence-backed

The SME may only be asked to:

- confirm a suggested value
- reject a suggested value
- choose among a small set of candidates
- upload a missing document
- accept an explicit residual risk

The SME must not be asked to:

- interpret `47A` or other clause text
- decide documentary vs non-documentary status
- discover specialist fields from scratch
- manually reconcile trade-finance ambiguity without evidence

### 5. Authority rules are source-specific

- `structured_mt`: parser-authoritative
- `structured_iso`: parser-authoritative
- `rendered_lc`: AI-authoritative with evidence anchors
- supporting documents: AI-authoritative with deterministic normalization and verification

AI may interpret narrative text around structured LC messages, but it does not override structured message semantics.

### 6. Legacy extraction fields are non-authoritative for fact-backed docs

If a supported document family has `fact_graph_v1` or its successor, the following are not workflow truth:

- `missing_required_fields`
- `parse_complete`
- `review_required`
- `review_reasons`
- raw `field_details`

They may remain for:

- telemetry
- debug
- provenance
- backward compatibility

They must not drive:

- workflow stage
- SME queue creation
- readiness state
- review state
- validation findings

## Canonical Runtime Objects

### RequirementsGraph

Built from the LC and versioned per case.

Contains:

- required documents
- dates and deadlines
- amounts and currencies
- transport requirements
- party requirements
- documentary conditions
- non-documentary conditions classified and demoted appropriately

### FactSet

Built from document evidence and versioned per case.

Contains:

- normalized facts
- provenance and evidence anchors
- resolution status
- explicit unknowns

Current implementation seed:

- `fact_graph_v1`
- fact builders under `apps/api/app/services/facts/`

### ResolutionTasks

Built from unresolved facts and requirements.

Contains only bounded, candidate-backed, SME-confirmable items.

Current implementation seed:

- `resolution_queue_v1`
- `fact_resolution_v1`
- `apps/api/app/services/resolution/queue_builder.py`

### Findings and Decision

Built only after fact closure.

Contains:

- requirement-level pass/fail/unknown findings
- evidence references
- fix guidance
- final readiness decision

## Validation Stack

After fact closure, validation runs in this order:

1. AI L1: basic document-level checks
2. AI L2: LC-to-document and cross-document consistency
3. AI L3: advanced anomaly, ambiguity, and TBML-style reasoning
4. deterministic rules: Rulhub, UCP, ISBP, bank-policy checks
5. veto/arbitration: final merge and conflict resolution

Users never see L1/L2/L3 labels. They see only findings and recommended actions.

## Repo Mapping

### Source routing and LC ingestion

- `apps/api/app/services/extraction/launch_pipeline.py`
- `apps/api/app/services/extraction/smart_lc_extractor.py`
- `apps/api/app/services/extraction/structured_lc_builder.py`

Target role:

- route source type
- preserve subtype truth
- build requirements and evidence inputs
- stop acting as a mixed truth owner

### Fact compilation

- `apps/api/app/services/facts/document_facts.py`
- `apps/api/app/services/facts/lc_facts.py`
- `apps/api/app/services/facts/invoice_facts.py`
- `apps/api/app/services/facts/bl_facts.py`
- `apps/api/app/services/facts/packing_list_facts.py`
- `apps/api/app/services/facts/coo_facts.py`
- `apps/api/app/services/facts/insurance_facts.py`
- `apps/api/app/services/facts/inspection_facts.py`
- `apps/api/app/services/facts/supporting_facts.py`

Target role:

- own canonical fact compilation
- own normalization boundaries
- feed validation input only through resolved facts

### Resolution

- `apps/api/app/services/resolution/queue_builder.py`

Target role:

- emit only bounded SME tasks
- depend on requirements plus facts
- never leak parser-era uncertainty directly

### Validation

- `apps/api/app/routers/validate.py`
- `apps/api/app/services/validator.py`
- `apps/api/app/services/crossdoc.py`

Target role:

- consume closed facts and requirements
- emit findings only
- stop reading legacy extraction truth directly

### Projection and refresh

- `apps/api/app/routers/validation/response_shaping.py`
- `apps/api/app/routers/validation/result_finalization.py`
- `apps/api/app/routers/validation/session_refresh.py`
- `apps/api/app/routers/validation/presentation_contract.py`

Target role:

- project one stable case snapshot
- not compensate for mixed truth stores

### Frontend

- `apps/web/src/lib/exporter/resultsMapper.ts`
- `apps/web/src/pages/ExporterResults.tsx`
- `apps/web/src/components/lcopilot/DocumentDetailsDrawer.tsx`

Target role:

- render backend-owned truth
- stop reconstructing workflow meaning from mixed legacy flags

## Immediate Migration Order

1. Seal fact authority for all fact-backed document families.
2. Introduce `RequirementsGraph` as an explicit LC output.
3. Make resolution tasks depend on requirements plus facts, not legacy extraction debt.
4. Enforce the gate: no user-facing validation before fact closure.
5. Split validation implementation into AI, deterministic, and veto layers behind one findings contract.
6. Keep the frontend as a projection layer only.

## Definition Of Done For Extraction

Extraction is not considered done until fresh live cases show all of the following:

- bounded SME task queue
- candidate-backed confirmation tasks only
- no clause-heavy or specialist-only user tasks
- no legacy parser debt driving fact-backed documents
- same-session confirm/reject returns clean success and updates the case snapshot
- validation starts from closed facts, not mixed extraction state

## Non-Goals

This decision does not require:

- a full rewrite
- immediate event sourcing or CQRS adoption
- deleting every legacy field immediately

It does require:

- finishing the cut already started
- demoting legacy truth carriers
- making requirements, facts, and findings the only workflow-driving layers
