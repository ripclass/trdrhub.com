# LCopilot Non-Bank $30k MRR Audit (Exporter-First)

**Date:** 2026-03-01  
**Scope:** Post-launch commercial ramp (non-bank features only), excluding bank-grade modules  
**Assumption:** Stripe Atlas available around **week 2** enabling card/ACH onboarding for international payments/contracting.

## Executive Decision

**Earliest realistic month to hit $30k MRR: end of Month 3 (if aggressive scenario holds).**

- Aggressive assumes early velocity, strong ICP matching, near-zero execution drag.
- Base scenario is realistic to hit in Month 6.
- Conservative scenario typically lands in Month 9 or later if inbound remains weak.

## 1) Three scenarios to $30k MRR

### Core modeling assumptions

- Formula: **MRR_t = New MRR_w × (1 - churn-adjustment over horizon)**
- **Leads → Demos → Paid conversion**:  
  `Paid customers = Leads × (Lead→Demo %) × (Demo→Paid %)`
- **Required leads for target**:  
  `Leads/wk = (MRR target/wk) / (Blended ARPA × Conversion × (1 - churn adjustment))`

| Scenario | Horizon to hit $30k | Blended ARPA | Lead→Demo | Demo→Paid | Total Conv | Sales Cycle | Churn (m) | 3 mo target | 6 mo target | 9 mo target |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Aggressive** | **~12 weeks (3 months)** | **$1,020** | **22%** | **45%** | **9.9%** | **10–14 days** | 11% | 8% | 6% |
| **Base** | **~26 weeks (6 months)** | **$730** | **12%** | **30%** | **3.6%** | **20–28 days** | 18% | 14% | 11% |
| **Conservative** | **~39 weeks (9 months)** | **$505** | **6%** | **22%** | **1.32%** | **35–45 days** | 34% | 30% | 25% |

Notes:
- Churn columns are **remaining revenue at horizon** (i.e., net discount), not monthly percentage retained.
- ARPA mix assumptions by segment are implicit in above blended numbers (see next section).

## 2) Core assumptions by scenario (segment mix)

### Aggressive
- **Segments**: 50% SMB Exporter ($300 ARPA), 30% Growth Exporter ($900 ARPA), 20% Agency/Exporter Ops Partner ($3,000 ARPA)
- **Blended ARPA**: ~**$1,020**
- **Sales motion**: outbound + outbound+content conversion loops
- **Why plausible:** referral pressure from launch wave, stronger urgency in compliance delays and customs paperwork bottlenecks.

### Base
- **Segments**: 55% SMB ($300), 35% Growth ($900), 10% Agency/Partner ($2,500)
- **Blended ARPA**: ~**$730**
- **Sales motion**: outbound-heavy, inbound from launch content
- **Why plausible:** slower trust build, modest case studies, standard sales qualification

### Conservative
- **Segments**: 70% SMB ($250), 20% Growth ($750), 10% Agency/Partner ($1,800)
- **Blended ARPA**: ~**$505**
- **Sales motion**: inbound-led, delayed buying due to migration concerns
- **Why plausible:** longer evaluation cycles, fewer high-intent leads, slower onboarding trust.

## 3) Required weekly funnel targets

### A) Aggressive scenario
| Horizon | Target gross new MRR needed/week | New paid customers needed/week | Demos needed/week | Leads needed/week |
|---|---:|---:|---:|---:|
| 3 months (w12) | ~$2.58k | 2.5 | 5.6 | **26** |
| 6 months (w26) | ~$1.27k | 1.2 | 2.7 | **13** |
| 9 months (w39) | ~$0.84k | 0.8 | 1.8 | **8** |

### B) Base scenario
| Horizon | Target gross new MRR needed/week | New paid customers needed/week | Demos needed/week | Leads needed/week |
|---|---:|---:|---:|---:|
| 3 months (w12) | ~$2.66k | 3.6 | 12.8 | **101** |
| 6 months (w26) | ~$1.30k | 1.8 | 15.0 | **50** |
| 9 months (w39) | ~$0.92k | 1.25 | 3.5 | **35** |

### C) Conservative scenario
| Horizon | Target gross new MRR needed/week | New paid customers needed/week | Demos needed/week | Leads needed/week |
|---|---:|---:|---:|---:|
| 3 months (w12) | ~$2.73k | 5.4 | 24.5 | **408** |
| 6 months (w26) | ~$1.37k | 2.7 | 12.4 | **206** |
| 9 months (w39) | ~$1.02k | 2.0 | 9.2 | **153** |

## 4) Top 10 blockers and mitigations

1. **Payment & entity readiness delays (Atlas late/failed onboarding)**  
   *Mitigation:* hard dependency checklist, legal + compliance parallel path; keep launch gate on billing smoke tests and fallback invoicing.

2. **Trust gap at launch (no proof)**  
   *Mitigation:* preload 3 pilot reference stories + usage benchmarks before public launch.

3. **Noisy ACV estimation (wrong segmenting leads to discounts)**  
   *Mitigation:* enforce qualification rubric + pricing ladder + approval limits.

4. **Slow demo-to-close handoff**  
   *Mitigation:* 15-minute demo playbook, decision-maker checklist, prebuilt ROI calculator in demo.

5. **Support load from onboarding failures**  
   *Mitigation:* in-app onboarding checklist, health checks, CSM handoff triggers, and FAQ + video set.

6. **Data import quality from customer systems**  
   *Mitigation:* hardened importer adapters + CSV template validators + migration support SOP.

7. **Churn from value-delivery mismatch**  
   *Mitigation:* day-14 and day-30 adoption checkpoints tied to mandatory outcomes.

8. **Channel dilution / too broad outbound list**  
   *Mitigation:* weekly ICP prune: keep only leads with declared export volume + immediate pains addressed by LCopilot.

9. **Feature debt in non-bank scope at launch**  
   *Mitigation:* strict “must-have only” scope freeze; defer low-value extras.

10. **Team bandwidth bottleneck (owner dependency, no coverage)**  
   *Mitigation:* 1-3 backups for GTM/CS playbooks; rotate weekly operating review with explicit owners.

## 5) 30/60/90 day operating plan (owners + outputs)

### Days 0–30 (30 days)
- **CEO:** finalize target ICP list (200), pricing policy by segment, weekly KPI dashboard live.
- **CTO:** Atlas billing integration, usage telemetry, incident budget alerts.
- **Product:** ship “launch hardening” (import templates, failure-safe onboarding, supportability fixes).
- **GTM:** launch campaign (5 outbound sequences), 20–40 high-intent conversations/week.
- **CS:** draft onboarding runbook, customer kickoff template, health score v1.
- **Risk:** create risk register, weekly scoring (P×I), and go/no-go metrics for launch extension.

### Days 31–60 (60 days)
- **CEO:** close first 5 motion-based expansion pilots, tighten ICP + pricing based on close reasons.
- **CTO:** optimize onboarding latency and API reliability; release exporter-first workflow telemetry.
- **Product:** publish partner-ready onboarding scripts, refine ROI pages.
- **GTM:** A/B on demo pitch + follow-up cadence, target 3 wins >$1k ARPA.
- **CS:** convert first 20 customers through 1:1 onboarding, run churn-risk checks.
- **Risk:** enforce contingency plan for delayed payments/verification failures and backup onboarding path.

### Days 61–90 (90 days)
- **CEO:** finalize hiring of 1 dedicated AE + 1 implementation lead if aggressive/base gates met.
- **CTO:** deliver scaling pass and SLA targets.
- **Product:** launch second-wave improvements from top 10 support issues.
- **GTM:** weekly pipeline review, increase conversion efficiency, establish referral loop.
- **CS:** institutionalize QBR-lite, proactive renewal review cadence.
- **Risk:** publish monthly risk report; if blockers persist, switch to conservative demand capture plan.

## 6) Decision recommendation

- **Commit to Base for planning** unless pre-launch pipeline is already >40 warm leads/week.
- **Aggressive target (Month 3)** is feasible only with 2–3 strong growth/partner closes or equivalent velocity.
- **Board-level forecast:** use 3 ranges (Aggressive 3m / Base 6m / Conservative 9m) in KPIs, and review monthly against the weekly funnel table.
