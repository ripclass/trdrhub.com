# Exporter Phase 2.5 Product Audit

Date: 2026-04-03
Status: Active

## Scope

Exporter backend validation is now frozen to blocker-fix mode.

Phase 2.5 is the launch-prep pass for the exporter product surface:

1. Overview clarity
2. Documents review flow
3. Customs and submission flow
4. Final discrepancy-lane polish if still needed

## Current Surface Audit

### Overview

Status: Functional but too dense

What is good:
- timeline is real and wired to the runtime payload
- required-doc checklist is real and truth-driven
- extraction-stage warning is shown when validation is provisional

Current gaps:
- some cards remain hidden in the page instead of being removed cleanly
- summary/next-step guidance is spread across too many sections
- AI insights card intentionally returns `null` when backend enrichment is absent, which is honest but leaves a visible product gap

### Documents

Status: Strong backend truth, heavy operator load

What is good:
- document cards are truth-driven
- drawer supports field confirmation and evidence review
- requirement-match / review-status framing is already present

Current gaps:
- the tab is visually dense for first-pass triage
- unresolved documents are not elevated enough above already-clean documents
- optional supporting documents and required documents still compete for attention in the same scan path

### Issues

Status: Closest tab to launch-ready

What is good:
- final issues and provisional issues are separated
- overall validation note is contract-aware
- documentary, compliance, and manual-review framing exists

Current gaps:
- likely only minor polish remains unless user testing shows confusion
- AI insights surface is still absent when no backend enrichment block is available

### Customs Pack

Status: Needs launch-path cleanup

What is good:
- customs pack and submission surfaces exist
- bank selection / manifest preview flow exists
- submission history component exists

Current gaps:
- customs, submission, and history responsibilities are bundled into one broad lane
- this is likely the biggest launch UX risk after Documents
- the tab needs clearer primary action, readiness explanation, and submission-state hierarchy

## Immediate Product Priorities

## Progress This Pass

- [x] surfaced the Overview next-action card instead of leaving it hidden
- [x] sorted the Documents tab by operator urgency so unresolved required documents rise above clean uploads

### Priority 1: Overview

- remove dead/hidden legacy surfaces instead of leaving them in-place
- collapse the top-level story into one clear readiness summary
- make next action obvious within one screen

### Priority 2: Documents

- sort unresolved / blocked documents above clean ones
- emphasize required missing or partially covered documents first
- reduce scan fatigue on clean documents

### Priority 3: Customs Pack

- separate "ready to submit", "not ready", and "already submitted" states clearly
- tighten the bank selection and manifest preview path
- make submission history secondary, not competing with the primary CTA

## Guardrails

- do not reopen broad backend validation rollout unless a real exporter flow is blocked
- do not reintroduce mock or simulated UI state
- do not change backend/frontend payload contract casually during Phase 2.5
- prefer removing dead UI over hiding it
