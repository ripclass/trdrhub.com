# Session resume — outage recovery + AWS exit + authority matrix (2026-06-12)

**Last updated:** 2026-06-12
**State at commit:** `bf636af7` — branch `master`, pushed, deployed to Render, live-verified.
**Launch:** 2026-07-25 (~6 weeks). Code freeze 2026-07-24.

---

## Resume prompt

```
Resume from bf636af7 (2026-06-12 session: outage + AWS exit + authority
matrix, all shipped + live-verified). Read memory:
project_prod_db_outage_2026_06_11, reference_storage_supabase_s3,
reference_rulhub_v1_schema, project_authority_matrix. Open items:
(1) relay the 2-item RulHub prompt to rulhub Claude (partial_shipments
rule config + invoice.quantity==bl.gross_weight rule — text in the
2026-06-12 conversation / authority memory); (2) optional cleanup:
remove the rulhub_sent_fields/insurance_rule_context_keys diagnostic
from _db_rules_debug once stable (e1ee3f45); (3) launch-prep calendar
items: UAT outreach, bug-bash week 2026-07-20→23, Sentry. Standing
rules: push every commit; Supabase DB via aws-1 session pooler (never
the direct host); all S3 via app/utils/s3_client.py factory; never
downgrade models for cost.
```

---

## What happened this session (12 commits, `95bbae57..bf636af7`)

1. **Prod DB outage diagnosed + fixed.** Down 2026-06-11 10:28 UTC → 2026-06-12 02:36 UTC (~16h): Supabase IPv4 add-on disabled → direct host IPv6-only → Render (IPv4-only) unreachable. Fix: `DATABASE_URL` + `DIRECT_DATABASE_URL` → **aws-1**-ap-southeast-2 session pooler (5432, user `postgres.<ref>`). Permanent; add-on stays off.
2. **`95bbae57`** `/health/ready` computed 503 but returned 200 always — fixed; live-verified both ways.
3. **Monitoring** `fb2209db` — `.github/workflows/prod-health-monitor.yml`: GH Actions cron */15 probes /health/ready + /health/db-schema, fails loudly (GitHub email). Verified green run.
4. **AWS exit** `88337c3a` — account locked Ripon out. All 11 S3 sites → `app/utils/s3_client.py` factory → Supabase Storage S3 endpoint (path-style + SigV4). Bucket `lcopilot-docs-prod` created; put/get/presign verified. Textract dormant; CloudWatch self-disables. `/health/ready` fully green first time ever.
5. **Full prod smoke** — matrix 17/17, importer e2e both moments PASS, bulk 5/5.
6. **RulHub re-lit** `041bee23` — validate-request v1.0.0 alignment (type enum: `inspection`/`beneficiary_cert`; minItems=2 → skip single-doc sets with `db_tiered_rulhub_skipped`). Live `path=rulhub`, rules_checked≈732. Dark since ~2026-04-30.
7. **Authority matrix — ALL 5 items** (Ripon's design): `f55b1c39` veto asymmetry (suppress-never-create, downgrade-never-upgrade) + disagreement log (`_db_rules_debug.authority_veto_events`); `d088a1b2` reconcile/dedup (deterministic wins arithmetic/dates); `dbd4ae97` presence screen + semantic routing (near-match → advisory; semantic excluded from auto-confirm); `da2847ac` presence-screen lookup union + doc-scoped aliases.
8. **Insurance chimera bug** (pre-existing, major): beneficiary cert shadowed the real insurance cert in `_resolve_insurance_rule_context` (first-type-match + `_INSURANCE_RULE_DOCUMENT_TYPES` includes beneficiary types) — insurance rules validated against wrong doc's fields forever. Fixed `485c7b80` (projection merges over raw fields) + `bf636af7` (two-tier priority). Diagnostic `e1ee3f45` (`rulhub_sent_fields`) still in _db_rules_debug — keep until stable, then strip.

**Final live numbers (clean US-VN corridor):** morning 12 findings (10 FP) → **3 findings (1 major + 2 minor, all legitimate cross-ref advisories), 0 false positives.** Test suites: 33/33 authority + 6/6 insurance-context.

## RulHub relay (pending — Ripon hands to rulhub Claude)
Two rule bugs, both fire MAJOR on clean docs: (1) `partial_shipments` rule demands value 'allowed' — flags LCs that prohibit partial shipment; (2) `invoice.quantity == bl.gross_weight` compares pieces to kg. Full prompt text in the 2026-06-12 conversation + project_authority_matrix memory.
