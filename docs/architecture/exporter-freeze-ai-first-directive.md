# Exporter Freeze And AI-First Directive

Date: 2026-04-01
Status: Active

## Purpose

This directive replaces open-ended exporter firefighting with a bounded path:

1. Freeze exporter around a stable validation baseline.
2. Remove temporary rule-specific bridges that would become long-term hardcoding.
3. Return to the AI-first validation architecture in the ADR once exporter is stable enough.
4. Move to exporter UX polish, then importer dashboard.

## Non-Negotiables

- Exporter stays the primary workstream until the freeze checklist is satisfied.
- Validation stays ahead of extraction. Extraction changes are allowed only when a rule is blocked by a missing fact.
- Every new failure must be classified as exactly one of:
  - engine bug
  - ruleset/data issue
  - missing fact
- Reusable engine fixes come before rule-specific workarounds.
- The temporary ICC-to-legacy suppression bridge must be retired; it is allowed only as a short-lived transition aid.
- AI-first is still the target validation architecture:
  1. AI L1
  2. AI L2
  3. AI L3
  4. deterministic
  5. veto/arbitration

## Current Audit

### What Is Solid

- [x] `validation_contract_v1` exists and is driving readiness.
- [x] Immediate `/api/validate/` and persisted `/api/results/{id}` agree on proven paths.
- [x] Deterministic ICC rule execution is working live.
- [x] Release-gated gold corpus exists and is meaningful.

### Live-Proven Rule Paths

- [x] `UCP600-18A`
- [x] `UCP600-18B`
- [x] `UCP600-18C`
- [x] `UCP600-18D`
- [x] `UCP600-20C`
- [x] `UCP600-20D`
- [x] `UCP600-20E`
- [x] `UCP600-28A`
- [x] `UCP600-28D`
- [x] `UCP600-28E`
- [x] `CROSSDOC-EXACT-WORDING`
- [x] `CROSSDOC-PO-NUMBER`
- [x] `CROSSDOC-BIN`
- [x] `CROSSDOC-TIN`

### Remaining Exporter Risks

- [x] Replace rule-id-specific ICC-vs-legacy suppression with a generic overlap/dedup mechanism.
- [x] Promote the insurance undercoverage path to `UCP600-28E` with generic valuation/arithmetic support.
- [x] Finish one bounded exporter validation batch without drifting into endless atomic rollout.
- [ ] Freeze exporter on a documented baseline.
- [ ] Implement explicit AI L1/L2/L3 staging ahead of deterministic rules.

## Exporter Freeze Checklist

- [x] Immediate and persisted results parity on proven validation paths
- [x] Contract-driven readiness parity on proven validation paths
- [x] Core invoice-family live proof started
- [x] Core transport-family live proof started
- [x] Core insurance-family live proof started
- [x] Generic overlap/dedup replaces the temporary rule-id bridge
- [x] Final bounded exporter validation batch completed
- [ ] Exporter moved to blocker-fix mode only

### Post-Batch Audit

- Remaining staged UCP candidates such as `UCP600-20A/B/F/G` and `UCP600-28B/C/F/G` are now primarily missing-fact seams, not overlap/governance seams.
- That means the next exporter decision is explicit:
  - either open one bounded missing-fact batch for advanced transport/insurance flags
  - or freeze exporter here and move to Phase 2 AI-first integration plus Phase 2.5 UX polish
- Phase 2 now starts with an honest contract milestone:
  - [x] project current AI validation into explicit `L1` / `L2` / `L3` layers
  - [ ] move runtime ordering from post-deterministic projection to true AI-first execution

## Phase Sequence

### Phase 1: Exporter Freeze

- Prove the remaining high-value exporter rule classes.
- Fix only reusable engine behavior or blocker issues.
- Eliminate the specific `UCP -> CROSSDOC` suppression map.

### Phase 2: AI-First Validation

- Expose AI L1, AI L2, and AI L3 as explicit staged outputs.
- Keep deterministic rules after AI stages.
- Keep veto/arbitration last.
- Merge all layers through the same validation contract.
- Preserve truth in the contract:
  - if a layer is not implemented yet, mark it as `not_run`
  - if current execution is still post-deterministic, say so explicitly instead of faking AI-first completion

### Phase 2.5: Exporter Product Polish

- Fix dashboard tabs
- Fix user flow gaps
- Fix UI/UX rough edges
- Make exporter launch-ready

### Phase 3: Importer Dashboard

- Start importer only after exporter is frozen enough.
- Reuse the same stable validation contract.

## Guardrails

- Do not keep adding bespoke rule-id suppression entries as architecture.
- Do not drift back into extraction-led work.
- Do not skip the AI-first directive once exporter freeze is reached.
- Do not overlook a concern raised by the user simply because a rule path is currently green.
