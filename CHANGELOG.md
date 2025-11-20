# Changelog

All notable changes to TRDR Hub LCopilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2025-11-20] - Rules Table Integration

### Added
- Governance columns and indexes on `rules`, plus the new `rules_audit` table with logging hooks.
- `RulesImporter`, bulk sync endpoints, Supabase storage helpers, and CLI entrypoints (`scripts/import_rules.py`, `scripts/sync_rulesets.py`).
- Admin UI updates: Rules Governance view, upload import summary, navigation refresh, and Prometheus counters.
- Vitest/pytest coverage for importer + UI, runbook (`docs/runbooks/rules-sync-runbook.md`), and Supabase RLS SQL (`infra/sql/rules_rls.sql`).

### Changed
- Cache invalidation, audit logging, and metrics now execute on publish/rollback/update/delete/bulk-sync.
- Docs (`docs/rules-feature-completion-plan.md`, `CHANGELOG.md`) now reflect the new flow and operations handoff.

### Known Issues
- Automated validation regression tests could not be executed locally because a Python interpreter entrypoint (pytest) is not exposed on this workstation. Re-run the backend suite once the env provides a CLI.

## [5.0.0] - 2025-09-18 - BMAD Retrofit v5

### Added - BMAD Framework Integration
- **BMAD Method Retrofit:** Complete retrofit of documentation to reflect bank-grade platform reality
- **PRD v5:** Comprehensive Product Requirements Document with bank-grade scope
  - Background & Market Context documentation
  - Problem Definition & User Jobs analysis
  - Scope & Non-Functional Requirements specification
  - Epics & Milestones roadmap (4 major epics)
  - Feature Specifications with implementation status
  - Acceptance Criteria & KPIs with measurable targets
- **Architecture v5:** Complete system architecture documentation
  - Context & Constraints analysis
  - Components & Data Flow specification
  - Infrastructure & Deployment strategy
  - Security & Compliance framework
  - Observability & Disaster Recovery procedures
- **BMAD Stories:** Structured user stories with full traceability
  - Retroactive DONE stories for implemented features
  - Forward TODO stories for planned development
  - BMAD framework (Background, Motivation, Approach, Details)
  - Complete acceptance criteria with testable scenarios
  - SM/Dev/QA checklists and test plans

### Added - Process & Tooling
- **Gap Closure Tracker:** Comprehensive tracking of remaining work
  - External gaps (13%): AI integration, bank connectors, eUCP 2.1
  - Internal gaps (9%): infrastructure hardening, testing, compliance
  - Priority matrix and dependency mapping
- **Bank Pilot Readiness Assessment:** Current 78% readiness score
  - Detailed scoring model across 6 categories
  - Gating criteria for pilot launch
  - Green path to 90% readiness
  - Risk assessment and mitigation strategies
- **Document Drift Check Script:** Automated documentation quality assurance
  - Detects implemented components vs. documentation gaps
  - Validates PRD, Architecture, and Story coverage
  - Generates weekly drift reports
  - CI integration for continuous monitoring
- **GitHub Actions Workflow:** Automated documentation quality checks
  - Story frontmatter schema validation
  - Markdown linting and link checking
  - Weekly drift monitoring with issue creation
  - PR comments with drift analysis

### Added - Configuration Updates
- **BMAD Core Config v5:** Updated configuration for retrofit
  - Version tracking and scope evolution documentation
  - Story template schema enforcement
  - SM→Dev→QA gate definitions
  - Drift check configuration
  - Component tracking for quality assurance

### Changed - Documentation Structure
- **Version Upgrade:** All documents upgraded from v4 to v5
- **Scope Recognition:** Documentation now reflects bank-grade platform reality
- **Cross-Linking:** Comprehensive linking between PRD, Architecture, and Stories
- **Traceability:** Complete traceability from epics to stories to code

### Technical Debt Documented
- **Infrastructure Gaps:** Database pooling, object storage, queue systems
- **AI Integration:** LLM assistance for discrepancy analysis and multilingual support
- **Bank Connectivity:** SWIFT message integration and real-time API connectors
- **Compliance:** Full UCP600 coverage and eUCP 2.1 support

### Process Improvements
- **BMAD Workflow:** Established SM→Dev→QA cycle for future development
- **Quality Gates:** Defined acceptance criteria for story progression
- **Documentation First:** All new features require corresponding documentation
- **Continuous Monitoring:** Weekly drift checks prevent documentation decay

## Previous Versions

### [4.x] - 2025-09-11 to 2025-09-17
- Core platform development
- OCR pipeline implementation
- Rules engine development
- Audit trail system
- Multi-tenant security
- Disaster recovery automation
- PWA frontend development

### [1.0] - 2025-09-11
- Initial PRD draft
- MVP concept definition
- Basic project scaffolding

---

## BMAD Retrofit Impact Summary

### Scope Evolution
- **From:** Simple MVP LC validation tool for Bangladeshi SMEs
- **To:** Bank-grade Letter of Credit compliance platform for SMEs and financial institutions
- **Recognition:** Documentation now accurately reflects implemented capabilities

### Documentation Completeness
- **PRD Coverage:** Complete feature specifications with bank-grade requirements
- **Architecture:** Detailed technical implementation matching current codebase
- **Stories:** Structured development workflow with retrospective and prospective stories
- **Process:** BMAD methodology integrated for future development

### Quality Assurance
- **Automated Monitoring:** CI/CD integration prevents documentation drift
- **Traceability:** Complete links between business requirements and technical implementation
- **Pilot Readiness:** Clear path from 78% to 90% bank pilot readiness
- **Risk Management:** Identified and documented all critical gaps

### Next Steps
1. Execute gap closure plan to reach 90% pilot readiness
2. Implement AI validation layer for competitive advantage
3. Establish bank partnerships for pilot program
4. Follow BMAD SM→Dev→QA workflow for all new development

**Impact:** This retrofit establishes TRDR Hub LCopilot as a properly documented, bank-grade platform ready for enterprise adoption and systematic development using BMAD methodology.