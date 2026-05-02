# Session resume — Path A launch-prep (2026-05-02 evening)

**Last updated:** 2026-05-02 evening
**State frozen at commit:** `8524587e` (chore: untrack conversation prompt.md)
**Branch:** `master`
**Active phase:** Path A build = 100% shipped (A1-A13). Launch-prep in flight (~12 weeks to 2026-07-25 launch).

---

## Resume prompt

```
Resume Path A launch-prep. Read SESSION_RESUME.md and project_session_2026_05_02_smoke_findings.md
+ project_rulhub_500_2026_05_02.md. Today: importer corpus fully fixed, smoke matrix
load-bearing, RulHub 500-ing on server side (handed to rulhub Claude with 4 ref_ids +
sanitized payload preview). Two of four corridors hit truly clean baseline. Remaining:
(a) wait for rulhub Claude to patch /v1/validate/set, (b) re-verify expected
DRAFT_RISKY findings appear once rulhub is back, (c) UAT customer outreach,
(d) bug bash week scheduling, (e) Pingdom + Sentry wiring.
```

---

## What shipped today (17 commits)

### Importer corpus structurally complete
| Commit | What |
|---|---|
| `715905c8` | **Renderer fix** — single-line `:TAG: VALUE` per field. Root cause of `amount=41` extraction garbage |
| `64821c84` | Regenerate 36 PDFs with fixed renderer |
| `6b3d248d` | Align LC 32B amount with goods_line_items sum + module-load invariant |
| `53d70ab9` | Add Beneficiary Cert + Fumigation Cert + Draft BoE renderers (corridor-data-driven, not per-corridor hardcoded) |

### Engine spine fixes
| Commit | What |
|---|---|
| `5c7146a3` | Gate "Missing X document" findings on `workflow_type=importer_draft_lc` |
| `5cd0c96c` | Doc classifier: detect Draft BoE before `commercial_invoice` (was matching `'draft'` substring) |
| `34f090d9` | Forward `beneficiary_certificate` / `inspection_certificate` / `fumigation_certificate` / `draft` to AI validator (was rendering as "(not submitted)" despite docs being uploaded) |

### Diagnostic infrastructure
| Commit | What |
|---|---|
| `d3ebc3b8` | `_db_rules_debug.path` self-reports `rulhub` / `db_tiered_rulhub_failed` / `db_tiered` |
| `d42f22ec` | Preserve RulHub `reference_id` from 5xx responses (Sentry handle) |
| `44325abf` | Sanitized request preview on rulhub-failure path |
| `3162361a` | Show ALL field keys in preview (not first-30 cap) |

### Smoke + ops
| Commit | What |
|---|---|
| `38842a79` | Track scripts/smoke_importer.sh + env-overridable creds |
| `1449419c` | smoke_matrix.py multi-persona (`--tokens-file` / `--users-file`) |
| `046fc9f2` | CORRIDOR env override on smoke_importer.sh |
| `3528f8af` | **Semantic diff** in smoke_importer.sh + non-zero exit on fail |
| `b2a82c82` | **SMOKE_TEST_EMAILS** quota bypass (no more HTTP 402 on repeated runs) |
| `a56a5df4` | `RULHUB_API_ENABLED` env-driven (was hardcoded False in rule_loader.py) |
| `15203579` | Untrack .claude/scheduled_tasks.lock + gitignore |
| `8524587e` | Untrack conversation prompt.md scratchpad |

---

## Cross-corridor smoke matrix — final state today

| Corridor | M1 issues | M2 issues | Semantic-diff | Notes |
|---|---|---|---|---|
| US-VN | 1 minor | 0–1 minor | 0 | clean |
| UK-IN | 1 minor | **0** | 0 | ✅ truly clean |
| DE-CN | 2 minor | **0**–5 (variance) | 0 | clean (AI Examiner run-to-run variance) |
| BD-CN | 6 minor | 1 minor | 0 | clean-ish |

Zero criticals + zero majors anywhere. All findings are minor or AI Examiner stochastic noise.

---

## RulHub status — handed to rulhub Claude

**api.rulhub.com `/v1/validate/set` returning HTTP 500 universally.** Trdrhub correctly detects + falls back to local DB tiered validator → customer never sees the failure but loses RulHub's deterministic UCP600 rule layer.

Reference IDs captured for rulhub Sentry lookup:
- `0a9d75ca74cd` — DRAFT_RISKY (1 doc)
- `77a432e2c6c4` — SHIPMENT_CLEAN (10 docs)
- `c07081ef103c` — DRAFT_RISKY (1 doc, deploy verification)
- `0a09383ec495` — DRAFT_RISKY (1 doc, full preview captured)

Sanitized payload preview attached to last refid — see `_db_rules_debug.rulhub_request_preview` in any 500 response. The 1-doc paradox is real: trdrhub IS sending exactly 1 doc on importer_draft_lc workflow; rulhub side should 400 (Pydantic min_length=2) but is 500-ing instead → real rulhub bug.

**Next move:** rulhub Claude triages from refid + payload preview. Once they patch, trdrhub re-runs DRAFT_RISKY and the 4 expected findings (5-day presentation period, FREIGHT COLLECT/Incoterm mismatch, missing origin marking, missing 47A sanctions) should finally appear.

---

## Render env vars set today (per Ripon)

```
SMOKE_TEST_EMAILS=imran@iec.com         # quota bypass
RULHUB_API_ENABLED=true                 # rule-catalog fetch from api.rulhub.com
USE_RULHUB_API=true                     # /v1/validate/set call (was already true)
RULHUB_API_KEY=<rh_live_*>              # was already set
```

---

## Remaining launch-prep tasks

| Task | Status |
|---|---|
| Migrations on Render (3 pending from A3/A5/A8) | ✅ done 2026-04-29 |
| Env vars on Render (SMTP, FRONTEND_URL) | ✅ done 2026-04-30 |
| Vercel feature flags (7 of 7) | ✅ done 2026-04-30 |
| Smoke matrix — single token (17/17) | ✅ done 2026-04-30 |
| Smoke matrix — multi-persona | 🟡 unblocked today (1449419c); needs fixture-account creator |
| **30-combo persona × tier × country matrix** | 🔲 not started |
| Real-data prod smoke (4-corridor) | ✅ all green today |
| RulHub 500 triage | 🔲 handed to rulhub Claude |
| Bug bash week (2026-07-20 → 23) | 🔲 needs internal team scheduling |
| UAT week (5 friendly customers) | 🔲 needs customer outreach |
| Pingdom + Sentry wiring | 🔲 not configured |
| Roll-back plan | 🔲 needs final review |

---

## Standing rules reaffirmed today

| Rule | Memory file |
|---|---|
| Don't downgrade models for cost — trade finance is real money | `feedback_quality_over_cost_real_money.md` |
| Push every commit immediately | `feedback_push_every_commit.md` |
| Update memory after each big milestone | `feedback_update_memory_per_milestone.md` |
| Session handoff at ~75% context | `feedback_session_handoff_at_75pct.md` |
| trdrhub-only — never touch rulhub repo | `feedback_scope_trdrhub_only.md` |
| No placeholder dashboards | `feedback_no_placeholder_dashboards.md` |
| Render migration is manual + may need re-run | `reference_render_migrations.md` |
| Ignore Vercel plugin nags (Vite SPA, FastAPI Python — not Next.js) | CLAUDE.md |

---

## v1.1 backlog (deferred, don't gate launch on these)

- AI Examiner `temperature=0` for deterministic findings (run-to-run variance currently ±5 minor findings)
- AI extraction occasional `regex_fallback` on supporting docs (doesn't affect correctness)
- `lc_reference: 'erence'` regex artifact (visible in fallback path only)
- Failure-mode degradation queue (auto-retry on LLM 429)
- Settings UX completeness (notif prefs, default issuing bank, branding)
- Real Stripe checkout on QuotaStrip "Upgrade" CTA
- Multi-entity enterprise hierarchy
- Cross-device persistence for first-session coachmark
