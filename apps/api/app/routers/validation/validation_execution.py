"""Validation execution stage extracted from pipeline_runner.py."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from uuid import uuid4

from app.services.facts import (
    apply_bl_fact_graph_to_validation_inputs,
    apply_coo_fact_graph_to_validation_inputs,
    apply_insurance_fact_graph_to_validation_inputs,
    apply_inspection_fact_graph_to_validation_inputs,
    apply_invoice_fact_graph_to_validation_inputs,
    apply_lc_fact_graph_to_validation_inputs,
    apply_packing_list_fact_graph_to_validation_inputs,
)


_SHARED_NAMES = [
    'Any',
    'Company',
    'CompanyStatus',
    'Decimal',
    'EntitlementError',
    'EntitlementService',
    'HTTPException',
    'PlanType',
    'SessionStatus',
    'UsageAction',
    'ValidationGate',
    '_build_blocked_structured_result',
    '_build_document_summaries',
    '_build_issue_dedup_key',
    '_build_lc_baseline_from_context',
    '_build_processing_summary',
    '_compute_invoice_amount_bounds',
    '_determine_company_size',
    '_extract_request_user_type',
    '_resolve_invoice_amount_tolerance_percent',
    '_response_shaping',
    'apply_bank_policy',
    'build_issue_cards',
    'build_lc_classification',
    'calculate_overall_extraction_confidence',
    'detect_bank_from_lc',
    'func',
    'get_bank_profile',
    'json',
    'logger',
    'parse_lc_requirements_sync_v2',
    'status',
    'time',
    'validate_document_async',
]

DB_RULE_TIMEOUT_SECONDS = 60.0
PRICE_VERIFICATION_TIMEOUT_SECONDS = 25.0
AI_VALIDATION_TIMEOUT_SECONDS = 45.0
BANK_POLICY_TIMEOUT_SECONDS = 20.0


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def bind_shared(shared: Any) -> None:
    namespace = globals()
    missing_bindings: list[str] = []
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            missing_bindings.append(name)
    if missing_bindings:
        raise RuntimeError(
            "Missing shared bindings for validation.validation_execution: "
            + ", ".join(sorted(missing_bindings))
        )


class _DeferredValidationFlow(Exception):
    """Short-circuit final validation stages while extraction resolution remains open."""


async def _await_with_timeout(stage_label: str, coro, timeout_seconds: float, default: Any):
    try:
        return await asyncio.wait_for(coro, timeout_seconds), False
    except asyncio.TimeoutError:
        logger.warning(
            "%s timed out after %.1fs; continuing with degraded fallback",
            stage_label,
            timeout_seconds,
        )
        return default, True


def _should_defer_final_validation(documents: Any) -> Dict[str, Any]:
    workflow_stage = _response_shaping.build_workflow_stage(
        documents if isinstance(documents, list) else [],
        validation_status="review",
    )
    return {
        "defer": str(workflow_stage.get("stage") or "").strip().lower()
        == "extraction_resolution",
        "workflow_stage": workflow_stage,
    }


def _filter_price_issues_for_documentary_context(
    existing_issues: list[dict[str, Any]],
    price_issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Keep documentary findings primary when the goods baseline itself is already
    inconsistent. In that state, price verification is advisory and should not
    add duplicate noise to the SME-facing LC findings path.
    """
    if not price_issues:
        return []

    existing_rules = set()
    for issue in existing_issues:
        if isinstance(issue, dict):
            rule_token = issue.get("rule") or issue.get("rule_id")
        else:
            rule_token = getattr(issue, "rule", None) or getattr(issue, "rule_id", None)
        rule_token = str(rule_token or "").strip().upper()
        if rule_token:
            existing_rules.add(rule_token)
    if existing_rules.intersection({"CROSSDOC-INV-003", "CROSSDOC-GOODS-1"}):
        return []

    return price_issues


async def execute_validation_pipeline(
    *,
    request,
    current_user,
    db,
    payload,
    files_list,
    doc_type,
    checkpoint,
    start_time,
    setup_state,
):
    validation_session = setup_state["validation_session"]
    job_id = setup_state["job_id"]
    extracted_context = setup_state["extracted_context"]
    lc_context = setup_state["lc_context"]
    lc_type = setup_state["lc_type"]
    lc_type_is_unknown = setup_state["lc_type_is_unknown"]

    # V2 VALIDATION PIPELINE - PRIMARY FLOW
    # This is the core validation engine. Legacy flow is disabled.
    # If LC extraction fails (missing critical fields), we block validation.
    # =====================================================================
    v2_gate_result = None
    v2_baseline = None
    v2_issues = []
    v2_crossdoc_issues = []
    ai_validation_summary = None
    defer_final_validation = False
    workflow_stage_hint = None

    try:
        lc_context = apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)
        setup_state["lc_context"] = lc_context
        apply_invoice_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_bl_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_packing_list_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_coo_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_insurance_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_inspection_fact_graph_to_validation_inputs(payload, extracted_context)

        # Build LCBaseline from extracted context
        v2_baseline = _build_lc_baseline_from_context(lc_context)

        # Run validation gate
        v2_gate = ValidationGate()
        v2_gate_result = v2_gate.check_from_baseline(v2_baseline)

        logger.info(
            "V2 Validation Gate: status=%s can_proceed=%s completeness=%.1f%% critical=%.1f%%",
            v2_gate_result.status.value,
            v2_gate_result.can_proceed,
            v2_gate_result.completeness * 100,
            v2_gate_result.critical_completeness * 100,
        )
        checkpoint("validation_gate_complete")

        # =====================================================================
        # BLOCKED RESPONSE - Return immediately if gate blocks
        # This is the key fix: NO more "100% compliant with N/A fields"
        # =====================================================================
        if not v2_gate_result.can_proceed:
            logger.warning(
                "V2 Gate BLOCKED: %s. Missing critical: %s",
                v2_gate_result.block_reason,
                v2_gate_result.missing_critical,
            )

            # Build blocked response
            processing_duration = time.time() - start_time
            blocked_result = _build_blocked_structured_result(
                v2_gate_result=v2_gate_result,
                v2_baseline=v2_baseline,
                lc_type=lc_type,
                processing_duration=processing_duration,
                documents=payload.get("documents") or [],
            )

            # Store blocked result in validation session so it can be retrieved later
            if validation_session:
                validation_session.status = SessionStatus.COMPLETED.value
                validation_session.processing_completed_at = func.now()
                validation_session.validation_results = {
                    "structured_result": blocked_result,
                    "validation_blocked": True,
                    "block_reason": v2_gate_result.block_reason,
                }
                db.commit()

            return {
                "job_id": str(job_id),
                "jobId": str(job_id),
                "structured_result": blocked_result,
                "telemetry": {
                    "validation_blocked": True,
                    "block_reason": v2_gate_result.block_reason,
                    "timings": {},
                    "total_time_seconds": round(time.time() - start_time, 3),
                },
            }
        # =====================================================================

        # Gate passed - run v2 IssueEngine (without full rule execution)
        from app.services.validation.issue_engine import IssueEngine

        # Create IssueEngine without RuleExecutor to avoid running all 2,159 rules
        # Full rule execution is DISABLED due to false positives from country-specific rules
        issue_engine = IssueEngine()

        v2_issues = issue_engine.generate_extraction_issues(v2_baseline)
        logger.info("V2 IssueEngine generated %d extraction issues", len(v2_issues))
        workflow_stage_hint = _should_defer_final_validation(
            payload.get("documents") or extracted_context.get("documents") or []
        )
        defer_final_validation = bool(workflow_stage_hint.get("defer"))
        if defer_final_validation:
            db_rule_issues = []
            db_rules_debug = {
                "enabled": False,
                "status": "deferred",
                "reason": "extraction_resolution",
                "workflow_stage": workflow_stage_hint.get("workflow_stage"),
            }
            bank_profile = None
            requirement_graph = None
            extraction_confidence_summary = None
            ai_validation_summary = {
                "issue_count": 0,
                "critical_issues": 0,
                "major_issues": 0,
                "minor_issues": 0,
                "documents_checked": len(payload.get("documents") or extracted_context.get("documents") or []),
                "derived_ai_verdict": "review",
                "metadata": {"deferred": True, "reason": "extraction_resolution"},
                "timed_out": False,
                "deferred": True,
                "reason": "extraction_resolution",
            }
            logger.info(
                "Deferring final validation stages while extraction remains unresolved: %s",
                (workflow_stage_hint.get("workflow_stage") or {}).get("summary"),
            )
            raise _DeferredValidationFlow()

        # =================================================================
        # EXECUTE DATABASE RULES (2500+ rules from DB)
        # Filters by jurisdiction, document_type, and domain
        # =================================================================
        db_rule_issues = []
        db_rules_debug = {"enabled": False, "status": "not_started"}
        lc_ctx = extracted_context.get("lc") or payload.get("lc") or {}
        requirements_graph_v1 = payload.get("requirements_graph_v1")
        try:
            # =============================================================
            # DYNAMIC JURISDICTION & DOMAIN DETECTION
            # Detects relevant rulesets based on LC and document content
            # =============================================================
            if not isinstance(requirements_graph_v1, dict):
                requirements_graph_v1 = _response_shaping.build_requirements_graph_v1(
                    payload.get("documents") or extracted_context.get("documents") or []
                )
            if isinstance(lc_ctx, dict) and isinstance(requirements_graph_v1, dict):
                lc_ctx.setdefault("requirements_graph_v1", requirements_graph_v1)
                lc_ctx.setdefault("requirementsGraphV1", requirements_graph_v1)
            if isinstance(lc_ctx, dict) and not isinstance(lc_ctx.get("lc_classification"), dict):
                lc_ctx["lc_classification"] = build_lc_classification(lc_ctx, payload)
            mt700 = lc_ctx.get("mt700") or {}
            coo = payload.get("certificate_of_origin") or {}
            invoice = payload.get("invoice") or {}
            bl = payload.get("bill_of_lading") or {}

            # Country code mapping (common variations)
            COUNTRY_CODE_MAP = {
                "bangladesh": "bd", "peoples republic of bangladesh": "bd",
                "india": "in", "republic of india": "in",
                "china": "cn", "peoples republic of china": "cn", "prc": "cn",
                "united states": "us", "usa": "us", "united states of america": "us",
                "united arab emirates": "ae", "uae": "ae",
                "saudi arabia": "sa", "kingdom of saudi arabia": "sa",
                "singapore": "sg", "republic of singapore": "sg",
                "hong kong": "hk", "hong kong sar": "hk",
                "germany": "de", "federal republic of germany": "de",
                "united kingdom": "uk", "great britain": "uk", "gb": "uk",
                "japan": "jp", "turkey": "tr", "pakistan": "pk",
                "indonesia": "id", "malaysia": "my", "thailand": "th",
                "vietnam": "vn", "philippines": "ph", "south korea": "kr",
                "brazil": "br", "mexico": "mx", "egypt": "eg",
            }

            def normalize_country(country_str: str) -> str:
                """Convert country name/code to 2-letter ISO code."""
                if not country_str:
                    return ""
                country_lower = country_str.lower().strip()
                # Already a 2-letter code?
                if len(country_lower) == 2:
                    return country_lower
                return COUNTRY_CODE_MAP.get(country_lower, "")

            # Detect jurisdictions from multiple sources
            detected_jurisdictions = set()

            # From LC
            for field in ["jurisdiction", "country", "issuing_bank_country", "advising_bank_country"]:
                val = normalize_country(lc_ctx.get(field, "") or mt700.get(field, ""))
                if val:
                    detected_jurisdictions.add(val)

            # From beneficiary (exporter) - usually the exporter's country matters most
            beneficiary = lc_ctx.get("beneficiary") or mt700.get("beneficiary") or {}
            if isinstance(beneficiary, dict):
                val = normalize_country(beneficiary.get("country", ""))
                if val:
                    detected_jurisdictions.add(val)
            elif isinstance(beneficiary, str):
                # Try to extract country from address string
                for country, code in COUNTRY_CODE_MAP.items():
                    if country in beneficiary.lower():
                        detected_jurisdictions.add(code)
                        break

            # From Certificate of Origin
            origin_country = normalize_country(
                coo.get("country_of_origin") or 
                coo.get("origin_country") or 
                coo.get("country") or ""
            )
            if origin_country:
                detected_jurisdictions.add(origin_country)

            # From Invoice seller address
            seller_country = normalize_country(
                invoice.get("seller_country") or
                invoice.get("exporter_country") or ""
            )
            if seller_country:
                detected_jurisdictions.add(seller_country)

            # From B/L port of loading (often indicates export country)
            port_of_loading = (bl.get("port_of_loading") or "").lower()
            if "chittagong" in port_of_loading or "dhaka" in port_of_loading or "mongla" in port_of_loading:
                detected_jurisdictions.add("bd")
            elif "shanghai" in port_of_loading or "shenzhen" in port_of_loading or "ningbo" in port_of_loading:
                detected_jurisdictions.add("cn")
            elif "mumbai" in port_of_loading or "chennai" in port_of_loading or "nhava sheva" in port_of_loading:
                detected_jurisdictions.add("in")

            # Build supplement domains dynamically
            supplement_domains = ["icc.isbp745", "icc.lcopilot.crossdoc"]

            # Add jurisdiction-specific regulations
            for jur in detected_jurisdictions:
                if jur and jur != "global":
                    supplement_domains.append(f"regulations.{jur}")

            # Add sanctions screening
            supplement_domains.append("sanctions.screening")

            # Primary jurisdiction (prefer exporter's country)
            primary_jurisdiction = "global"
            if origin_country:
                primary_jurisdiction = origin_country
            elif seller_country:
                primary_jurisdiction = seller_country
            elif detected_jurisdictions:
                primary_jurisdiction = list(detected_jurisdictions)[0]

            logger.info(
                "Dynamic jurisdiction detection: primary=%s, all=%s, supplements=%s",
                primary_jurisdiction, list(detected_jurisdictions), supplement_domains
            )

            # Build document data for rule engine
            db_rule_payload = {
                "jurisdiction": primary_jurisdiction,
                "domain": "icc.ucp600",
                "supplement_domains": supplement_domains,
                # LC data
                "lc": lc_ctx,
                "lc_number": v2_baseline.lc_number if v2_baseline else None,
                "amount": v2_baseline.amount if v2_baseline else None,
                "currency": v2_baseline.currency if v2_baseline else None,
                "expiry_date": v2_baseline.expiry_date if v2_baseline else None,
                # Documents
                "invoice": payload.get("invoice"),
                "bill_of_lading": payload.get("bill_of_lading"),
                "insurance": payload.get("insurance"),
                "certificate_of_origin": payload.get("certificate_of_origin"),
                "packing_list": payload.get("packing_list"),
                # Extracted context
                "extracted_context": extracted_context,
                "requirements_graph_v1": requirements_graph_v1 if isinstance(requirements_graph_v1, dict) else None,
            }

            # Determine primary document type for filtering
            primary_doc_type = "letter_of_credit"
            if payload.get("invoice"):
                primary_doc_type = "commercial_invoice"

            logger.info(
                "Executing DB rules: jurisdiction=%s, domain=icc.ucp600, supplements=%s, doc_type=%s",
                primary_jurisdiction, supplement_domains, primary_doc_type
            )

            db_rule_issues, db_rules_timed_out = await _await_with_timeout(
                "DB rules execution",
                validate_document_async(
                    document_data=db_rule_payload,
                    document_type=primary_doc_type,
                ),
                DB_RULE_TIMEOUT_SECONDS,
                [],
            )

            # Filter out N/A and passed rules, keep only failures
            db_rule_issues = [
                issue for issue in db_rule_issues
                if not issue.get("passed", False) and not issue.get("not_applicable", False)
            ]

            logger.info("DB rules executed: %d issues found (after filtering)", len(db_rule_issues))

            # Store debug info for response
            db_rules_debug = {
                "enabled": True,
                "domain": "icc.ucp600",
                "supplements": supplement_domains,
                "primary_jurisdiction": primary_jurisdiction,
                "detected_jurisdictions": list(detected_jurisdictions),
                "issues_found": len(db_rule_issues),
                "timed_out": db_rules_timed_out,
            }

        except Exception as db_rule_err:
            logger.warning("DB rule execution failed (continuing with other validators): %s", str(db_rule_err))
            db_rules_debug = {
                "enabled": False,
                "error": str(db_rule_err),
            }

        # Run v2 CrossDocValidator
        from app.services.validation.crossdoc_validator import CrossDocValidator
        crossdoc_validator = CrossDocValidator()
        crossdoc_lc_context = dict(lc_ctx) if isinstance(lc_ctx, dict) else {}
        metadata_dict = payload.get("metadata") or {}
        if isinstance(metadata_dict, str):
            try:
                metadata_dict = json.loads(metadata_dict)
            except Exception:
                metadata_dict = {}
        if isinstance(metadata_dict, dict):
            date_received = metadata_dict.get("dateReceived") or metadata_dict.get("date_received")
            if date_received and not crossdoc_lc_context.get("date_received"):
                crossdoc_lc_context["date_received"] = date_received
                bank_metadata = crossdoc_lc_context.get("bank_metadata")
                if isinstance(bank_metadata, dict):
                    bank_metadata.setdefault("date_received", date_received)
                else:
                    crossdoc_lc_context["bank_metadata"] = {"date_received": date_received}
        crossdoc_result = crossdoc_validator.validate_all(
            lc_baseline=v2_baseline,
            invoice=payload.get("invoice"),
            bill_of_lading=payload.get("bill_of_lading"),
            insurance=payload.get("insurance") or payload.get("insurance_certificate"),
            certificate_of_origin=payload.get("certificate_of_origin"),
            packing_list=payload.get("packing_list"),
            inspection_certificate=payload.get("inspection_certificate"),
            beneficiary_certificate=payload.get("beneficiary_certificate"),
            context={
                "lc": crossdoc_lc_context,
                "requirements_graph_v1": requirements_graph_v1 if isinstance(requirements_graph_v1, dict) else None,
            },
        )
        v2_crossdoc_issues = crossdoc_result.issues
        logger.info("V2 CrossDocValidator found %d issues", len(v2_crossdoc_issues))
        checkpoint("crossdoc_validation_complete")

        # =================================================================
        # PRICE VERIFICATION (LCopilot Integration)
        # =================================================================
        try:
            from app.services.crossdoc import run_price_verification_checks

            price_verify_payload = {
                "invoice": payload.get("invoice") or {},
                "lc": payload.get("lc") or extracted_context.get("lc") or {},
                "documents": payload.get("documents") or extracted_context.get("documents") or [],
            }

            price_issues, price_checks_timed_out = await _await_with_timeout(
                "Price verification",
                run_price_verification_checks(
                    payload=price_verify_payload,
                    include_tbml_checks=True,
                ),
                PRICE_VERIFICATION_TIMEOUT_SECONDS,
                [],
            )

            price_issues = _filter_price_issues_for_documentary_context(
                v2_crossdoc_issues,
                price_issues,
            )

            if price_issues:
                logger.info("Price verification found %d issues", len(price_issues))
                v2_crossdoc_issues.extend(price_issues)
            if price_checks_timed_out:
                logger.warning("Price verification timed out and was skipped for this run")
        except Exception as e:
            logger.warning(f"Price verification skipped: {e}")

        # =================================================================
        # AI VALIDATION ENGINE
        # =================================================================
        from app.services.validation.ai_validator import run_ai_validation, AIValidationIssue

        # Build LC data for AI from multiple potential sources
        lc_data_for_ai = {}

        # Get raw text from extracted_context (built from uploaded files)
        # The LC raw text is stored in context["lc"]["raw_text"] or context["lc_text"]
        lc_context = extracted_context.get("lc") or {}
        lc_raw_text = (
            lc_context.get("raw_text") or  # Primary: from lc object in extracted_context
            extracted_context.get("lc_text") or  # Alternative: direct lc_text
            (payload.get("lc") or {}).get("raw_text") or  # Fallback: from payload
            ""
        )
        lc_data_for_ai["raw_text"] = lc_raw_text
        logger.info(f"AI Validation: LC raw_text length = {len(lc_raw_text)} chars")

        # Get goods description from various locations
        mt700 = lc_context.get("mt700") or {}
        lc_data_for_ai["goods_description"] = (
            lc_context.get("goods_description") or
            mt700.get("goods_description") or 
            mt700.get("45A") or
            ""
        )
        logger.info(f"AI Validation: goods_description length = {len(lc_data_for_ai['goods_description'])} chars")

        # Get goods list
        lc_data_for_ai["goods"] = (
            lc_context.get("goods") or 
            lc_context.get("goods_items") or 
            mt700.get("goods") or
            []
        )
        lc_data_for_ai["requirements_graph_v1"] = (
            lc_context.get("requirements_graph_v1")
            or lc_context.get("requirementsGraphV1")
            or payload.get("requirements_graph_v1")
            or extracted_context.get("requirements_graph_v1")
        )

        # Get documents from both payload and extracted_context
        documents_for_ai = (
            extracted_context.get("documents") or  # Primary: from extraction
            payload.get("documents") or  # Fallback: from payload
            []
        )
        logger.info(f"AI Validation: {len(documents_for_ai)} documents to check")

        (ai_issues, ai_metadata), ai_validation_timed_out = await _await_with_timeout(
            "AI validation",
            run_ai_validation(
                lc_data=lc_data_for_ai,
                documents=documents_for_ai,
                extracted_context=extracted_context,
            ),
            AI_VALIDATION_TIMEOUT_SECONDS,
            ([], {"timed_out": True}),
        )
        if not isinstance(ai_metadata, dict):
            ai_metadata = {}

        logger.info(
            "AI Validation: found %d issues (critical=%d, major=%d)",
            len(ai_issues),
            ai_metadata.get("critical_issues", 0),
            ai_metadata.get("major_issues", 0),
        )
        ai_validation_summary = {
            "issue_count": len(ai_issues),
            "critical_issues": int(ai_metadata.get("critical_issues", 0) or 0),
            "major_issues": int(ai_metadata.get("major_issues", 0) or 0),
            "minor_issues": int(ai_metadata.get("minor_issues", 0) or 0),
            "documents_checked": len(documents_for_ai) if isinstance(documents_for_ai, list) else 0,
            "derived_ai_verdict": (
                "reject" if int(ai_metadata.get("critical_issues", 0) or 0) > 0 else (
                "warn" if int(ai_metadata.get("major_issues", 0) or 0) > 0 else "pass"
                )
            ),
            "metadata": ai_metadata or {},
            "timed_out": ai_validation_timed_out,
        }

        # Convert AI issues to same format as crossdoc issues
        for ai_issue in ai_issues:
            v2_crossdoc_issues.append(ai_issue)
        checkpoint("ai_validation_complete")

        # =================================================================
        # HYBRID VALIDATION ENHANCEMENTS
        # =================================================================

        # 1. Bank Profile Detection
        bank_profile = None
        try:
            bank_profile = detect_bank_from_lc({
                "issuing_bank": lc_context.get("issuing_bank") or mt700.get("issuing_bank") or "",
                "advising_bank": lc_context.get("advising_bank") or mt700.get("advising_bank") or "",
                "raw_text": lc_raw_text,
            })
            logger.info(f"Bank profile detected: {bank_profile.bank_code} ({bank_profile.strictness.value})")
        except Exception as e:
            logger.warning(f"Bank profile detection failed: {e}")
            bank_profile = get_bank_profile()  # Default profile

        # 2. Enhanced Requirement Parsing (v2 with caching)
        requirement_graph = None
        try:
            requirement_graph = parse_lc_requirements_sync_v2(lc_raw_text)
            if requirement_graph:
                logger.info(
                    f"RequirementGraph: {len(requirement_graph.required_documents)} docs, "
                    f"{len(requirement_graph.tolerances)} tolerances, "
                    f"{len(requirement_graph.contradictions)} contradictions"
                )
                # Store tolerances in metadata for downstream use
                ai_metadata["tolerances"] = {
                    k: v.to_dict() if hasattr(v, 'to_dict') else {
                        "field": v.field,
                        "tolerance_percent": v.tolerance_percent,
                        "source": v.source.value,
                    }
                    for k, v in requirement_graph.tolerances.items()
                }
                ai_metadata["contradictions"] = [
                    {"clause_1": c.clause_1, "clause_2": c.clause_2, "resolution": c.resolution}
                    for c in requirement_graph.contradictions
                ]
        except Exception as e:
            logger.warning(f"RequirementGraph parsing failed: {e}")

        # 3. Calculate overall extraction confidence
        extraction_confidence_summary = None
        try:
            extraction_confidence_summary = calculate_overall_extraction_confidence(extracted_context)
            logger.info(
                f"Extraction confidence: avg={extraction_confidence_summary.get('average_confidence', 0):.2f}, "
                f"lowest={extraction_confidence_summary.get('lowest_confidence_document', 'N/A')}"
            )
        except Exception as e:
            logger.warning(f"Extraction confidence calculation failed: {e}")

    except _DeferredValidationFlow:
        logger.info("Validation stage execution deferred until extraction resolution is complete")
    except Exception as e:
        logger.error("V2 pipeline error: %s", e, exc_info=True)
        # Don't fall back to legacy - just log the error
        # v2_gate_result remains None, issues remain empty
    # =====================================================================

    # Ensure user has a company (demo user will have one)
    if not current_user.company:
        # Try to get or create company for user
        demo_company = db.query(Company).filter(Company.name == "Demo Company").first()
        if not demo_company:
            demo_company = Company(
                name="Demo Company",
                contact_email=current_user.email or "demo@trdrhub.com",
                plan=PlanType.FREE,
                status=CompanyStatus.ACTIVE,
            )
            db.add(demo_company)
            db.flush()
        current_user.company_id = demo_company.id
        db.commit()
        db.refresh(current_user)

    # Skip quota checks for demo user (allows validation to work without billing)
    if current_user.email != "demo@trdrhub.com":
        entitlements = EntitlementService(db)
        try:
            entitlements.enforce_quota(current_user.company, UsageAction.VALIDATE)
        except EntitlementError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "quota_exceeded",
                    "message": exc.message,
                    "quota": exc.result.to_dict(),
                    "next_action_url": exc.next_action_url,
                },
            ) from exc

    # =====================================================================
    # V2 VALIDATION - PRIMARY PATH (Legacy disabled)
    # Note: Session was already created above, before gating check
    # =====================================================================
    request_user_type = _extract_request_user_type(payload)

    # Build unified issues list from v2 components
    results = []  # Legacy results - empty
    failed_results = []

    checkpoint("pre_issue_conversion")

    # =================================================================
    # BATCH LOOKUP: Collect all UCP/ISBP refs FIRST, then ONE query each
    # This replaces N individual DB queries with just 2 batch queries
    # =================================================================
    from app.services.rules_service import batch_lookup_descriptions

    all_ucp_refs = []
    all_isbp_refs = []

    # Collect refs from v2_issues
    if v2_issues:
        for issue in v2_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
            ucp_ref = issue_dict.get("ucp_reference")
            isbp_ref = issue_dict.get("isbp_reference")
            if ucp_ref and not issue_dict.get("ucp_description"):
                all_ucp_refs.append(ucp_ref)
            if isbp_ref and not issue_dict.get("isbp_description"):
                all_isbp_refs.append(isbp_ref)

    # Collect refs from crossdoc issues
    if v2_crossdoc_issues:
        for issue in v2_crossdoc_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            if ucp_ref and not issue_dict.get("ucp_description"):
                all_ucp_refs.append(ucp_ref)
            if isbp_ref and not issue_dict.get("isbp_description"):
                all_isbp_refs.append(isbp_ref)

    # Collect refs from DB rule issues
    if db_rule_issues:
        for issue in db_rule_issues:
            issue_dict = issue if isinstance(issue, dict) else issue.to_dict() if hasattr(issue, 'to_dict') else {}
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            if ucp_ref and not issue_dict.get("ucp_description"):
                all_ucp_refs.append(ucp_ref)
            if isbp_ref and not issue_dict.get("isbp_description"):
                all_isbp_refs.append(isbp_ref)

    # BATCH LOOKUP: 2 queries instead of N
    ucp_desc_cache, isbp_desc_cache = batch_lookup_descriptions(all_ucp_refs, all_isbp_refs)
    logger.info(f"Batch lookup: {len(ucp_desc_cache)} UCP refs, {len(isbp_desc_cache)} ISBP refs")

    # Helper to get description from cache
    def _get_ucp_desc(ref: str) -> Optional[str]:
        if not ref:
            return None
        # Try cache first, no fallback to individual query
        return ucp_desc_cache.get(ref) or ucp_desc_cache.get(ref.replace("Article ", "").replace("UCP600 ", ""))

    def _get_isbp_desc(ref: str) -> Optional[str]:
        if not ref:
            return None
        return isbp_desc_cache.get(ref) or isbp_desc_cache.get(ref.replace("ISBP745 ", "").replace("?", ""))

    # Convert v2 issues to legacy format for compatibility
    if v2_issues:
        for issue in v2_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
            ucp_ref = issue_dict.get("ucp_reference")
            isbp_ref = issue_dict.get("isbp_reference")
            failed_results.append({
                "rule": issue_dict.get("rule", "V2-ISSUE"),
                "title": issue_dict.get("title", "Validation Issue"),
                "passed": False,
                "severity": issue_dict.get("severity", "major"),
                "message": issue_dict.get("message", ""),
                "expected": issue_dict.get("expected", ""),
                "found": issue_dict.get("found", issue_dict.get("actual", "")),
                "suggested_fix": issue_dict.get("suggested_fix", issue_dict.get("suggestion", "")),
                "documents": issue_dict.get("documents", []),
                "ucp_reference": ucp_ref,
                "isbp_reference": isbp_ref,
                "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                "display_card": True,
                "ruleset_domain": "icc.lcopilot.extraction",
            })

    # Add cross-doc issues (including AI validator issues)
    if v2_crossdoc_issues:
        for issue in v2_crossdoc_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue

            # Handle both CrossDocIssue and AIValidationIssue formats
            # CrossDocIssue uses: "rule", "ucp_article", "actual"
            # AIValidationIssue uses: "rule", "ucp_reference", "actual"
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            failed_results.append({
                "rule": issue_dict.get("rule") or issue_dict.get("rule_id") or "CROSSDOC-ISSUE",
                "title": issue_dict.get("title", "Cross-Document Issue"),
                "passed": False,
                "severity": issue_dict.get("severity", "major"),
                "message": issue_dict.get("message", ""),
                "expected": issue_dict.get("expected", ""),
                "found": issue_dict.get("actual") or issue_dict.get("found") or "",
                "suggested_fix": issue_dict.get("suggestion") or issue_dict.get("suggested_fix") or "",
                "documents": issue_dict.get("documents") or issue_dict.get("document_names") or [issue_dict.get("source_doc", ""), issue_dict.get("target_doc", "")],
                "ucp_reference": ucp_ref,
                "isbp_reference": isbp_ref,
                "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                "display_card": True,
                "ruleset_domain": issue_dict.get("ruleset_domain") or "icc.lcopilot.crossdoc",
                "auto_generated": issue_dict.get("auto_generated", False),
            })

    # Add DB rule issues (2500+ rules from database)
    if db_rule_issues:
        for issue in db_rule_issues:
            issue_dict = issue if isinstance(issue, dict) else issue.to_dict() if hasattr(issue, 'to_dict') else {}
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            failed_results.append({
                "rule": issue_dict.get("rule") or issue_dict.get("rule_id") or "DB-RULE",
                "title": issue_dict.get("title", "Validation Rule"),
                "passed": False,
                "severity": issue_dict.get("severity", "major"),
                "message": issue_dict.get("message", ""),
                "expected": issue_dict.get("expected", ""),
                "found": issue_dict.get("actual") or issue_dict.get("found") or "",
                "suggested_fix": issue_dict.get("suggestion") or issue_dict.get("suggested_fix") or "",
                "documents": issue_dict.get("documents") or [],
                "ucp_reference": ucp_ref,
                "isbp_reference": isbp_ref,
                "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                "display_card": True,
                "ruleset_domain": issue_dict.get("ruleset_domain") or "icc.ucp600",
            })
        logger.info("Added %d DB rule issues to failed_results", len(db_rule_issues))

    # Add LC type unknown warning if applicable
    if lc_type_is_unknown:
        failed_results.append(
            {
                "rule": "LC-TYPE-UNKNOWN",
                "title": "LC Type Not Determined",
                "passed": False,
                "severity": "warning",
                "message": (
                    "We could not determine whether this LC is an import or export workflow. "
                    "Advanced trade-specific checks were disabled for safety."
                ),
                "documents": ["Letter of Credit"],
                "document_names": ["Letter of Credit"],
                "display_card": True,
                "ruleset_domain": "system.lc_type",
                "not_applicable": False,
            }
        )

    # =====================================================================
    # DEDUPLICATION - Remove duplicate issues by rule ID
    # =====================================================================
    seen_rules = set()
    deduplicated_results = []
    for issue in failed_results:
        dedup_key = _build_issue_dedup_key(issue)
        if dedup_key not in seen_rules:
            seen_rules.add(dedup_key)
            deduplicated_results.append(issue)
        else:
            logger.debug(
                "Removed duplicate issue: %s",
                issue.get("rule") or issue.get("title") or dedup_key,
            )

    if len(failed_results) != len(deduplicated_results):
        logger.warning(
            "Deduplication removed %d duplicate issues",
            len(failed_results) - len(deduplicated_results)
        )

    if validation_session and current_user.is_bank_user() and current_user.company_id:
        try:
            policy_results, bank_policy_timed_out = await _await_with_timeout(
                "Bank policy application",
                apply_bank_policy(
                    validation_results=deduplicated_results,
                    bank_id=str(current_user.company_id),
                    document_data=payload,
                    db_session=db,
                    validation_session_id=str(validation_session.id),
                    user_id=str(current_user.id),
                ),
                BANK_POLICY_TIMEOUT_SECONDS,
                None,
            )
            if policy_results is not None:
                deduplicated_results = [
                    issue for issue in policy_results if not issue.get("passed", False)
                ]
            if bank_policy_timed_out:
                logger.warning("Bank policy application timed out; using pre-policy issue set")
        except Exception as e:
            logger.warning("Bank policy application skipped: %s", e)

    results = list(deduplicated_results)

    logger.info(
        "V2 Validation: total_issues=%d (extraction=%d crossdoc=%d db_rules=%d) after_dedup=%d",
        len(failed_results),
        len(v2_issues) if v2_issues else 0,
        len(v2_crossdoc_issues) if v2_crossdoc_issues else 0,
        len(db_rule_issues) if db_rule_issues else 0,
        len(deduplicated_results),
    )

    issue_cards, reference_issues = build_issue_cards(deduplicated_results)
    checkpoint("issue_cards_built")

    # Record usage - link to session if created (skip for demo user)
    quota = None
    company_size, _company_size_tolerance_percent = _determine_company_size(current_user, payload)
    tolerance_percent = _resolve_invoice_amount_tolerance_percent(payload)
    payload["company_profile"] = {
        "size": company_size,
        "invoice_amount_tolerance_percent": float(tolerance_percent),
    }
    tolerance_value, amount_limit = _compute_invoice_amount_bounds(payload, tolerance_percent)
    if tolerance_value is not None:
        payload["invoice_amount_tolerance_value"] = tolerance_value
    if amount_limit is not None:
        payload["invoice_amount_limit"] = amount_limit

    if current_user.email != "demo@trdrhub.com":
        entitlements = EntitlementService(db)
        quota = entitlements.record_usage(
            current_user.company,
            UsageAction.VALIDATE,
            user_id=current_user.id,
            cost=Decimal("0.00"),
            description=f"Validation request for document type {doc_type}",
            session_id=validation_session.id if validation_session else None,
        )

    document_details_for_summaries = payload.get("documents")
    logger.info(
        "Building document summaries: files_list=%d details=%d issues=%d",
        len(files_list) if files_list else 0,
        len(document_details_for_summaries) if document_details_for_summaries else 0,
        len(deduplicated_results) if deduplicated_results else 0,
    )
    # FIX: Use deduplicated_results (actual issues) instead of empty results list
    # This ensures document issue counts are correctly linked to each document
    document_summaries = _build_document_summaries(
        files_list,
        deduplicated_results,  # Was 'results' which was always empty!
        document_details_for_summaries,
    )
    if document_summaries:
        doc_status_counts: Dict[str, int] = {}
        for summary in document_summaries:
            doc_status_val = summary.get("status") or "unknown"
            doc_status_counts[doc_status_val] = doc_status_counts.get(doc_status_val, 0) + 1
        logger.info(
            "Document summaries built: total=%d status_breakdown=%s",
            len(document_summaries),
            doc_status_counts,
        )
    else:
        logger.warning(
            "Document summaries are empty: no documents captured for job %s", job_id
        )

    checkpoint("document_summaries_built")

    processing_duration = time.time() - start_time
    processing_summary = _build_processing_summary(
        document_summaries,
        processing_duration,
        len(deduplicated_results),
    )

    return {
        "validation_session": validation_session,
        "job_id": job_id,
        "extracted_context": extracted_context,
        "lc_context": lc_context,
        "lc_type": lc_type,
        "lc_type_is_unknown": lc_type_is_unknown,
        "v2_gate_result": v2_gate_result,
        "v2_baseline": v2_baseline,
        "v2_issues": v2_issues,
        "v2_crossdoc_issues": v2_crossdoc_issues,
        "db_rule_issues": db_rule_issues if 'db_rule_issues' in locals() else [],
        "db_rules_debug": db_rules_debug if 'db_rules_debug' in locals() else {"enabled": False, "status": "not_started"},
        "bank_profile": bank_profile if 'bank_profile' in locals() else None,
        "requirement_graph": requirement_graph if 'requirement_graph' in locals() else None,
        "extraction_confidence_summary": extraction_confidence_summary if 'extraction_confidence_summary' in locals() else None,
        "ai_validation_summary": ai_validation_summary,
        "validation_deferred": defer_final_validation,
        "workflow_stage_hint": workflow_stage_hint,
        "request_user_type": request_user_type,
        "results": results,
        "failed_results": failed_results,
        "deduplicated_results": deduplicated_results,
        "issue_cards": issue_cards,
        "reference_issues": reference_issues,
        "document_summaries": document_summaries,
        "processing_duration": processing_duration,
        "processing_summary": processing_summary,
    }


__all__ = ["bind_shared", "execute_validation_pipeline"]
