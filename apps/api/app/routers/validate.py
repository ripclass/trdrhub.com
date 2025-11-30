from decimal import Decimal, InvalidOperation
from uuid import uuid4
from datetime import datetime, timedelta
import json
import copy
import os
import time

import logging
from io import BytesIO
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import UsageAction, User, ValidationSession, SessionStatus, UserRole, Document
from app.models.company import Company, PlanType, CompanyStatus
from app.services.entitlements import EntitlementError, EntitlementService
from app.services.validator import (
    validate_document,
    validate_document_async,
    apply_bank_policy,
    filter_informational_issues,
)
from app.services.crossdoc import (
    build_issue_cards,
    DEFAULT_LABELS,
)
from app.services.ai_issue_rewriter import rewrite_issue
from app.services import ValidationSessionService
from app.services.audit_service import AuditService
from app.middleware.audit_middleware import create_audit_context
from app.models.audit_log import AuditAction, AuditResult
from app.utils.file_validation import validate_upload_file
from app.config import settings
from app.core.lc_types import LCType, VALID_LC_TYPES, normalize_lc_type
from app.services.lc_classifier import detect_lc_type
from fastapi import Header
from typing import Optional, List, Dict, Any, Tuple
import re

from pydantic import BaseModel, Field, ValidationError, model_validator
from app.utils.logger import TRACE_LOG_LEVEL
from app.services.customs.customs_pack import build_customs_manifest_from_option_e
from app.services.customs.customs_pack_full import CustomsPackBuilderFull
from app.services.extraction.lc_extractor import (
    extract_lc_structured,
    extract_lc_structured_with_ai_fallback,
)
from app.services.extraction.ai_first_extractor import (
    extract_lc_ai_first,
    extract_invoice_ai_first,
    extract_bl_ai_first,
    extract_packing_list_ai_first,
    extract_coo_ai_first,
    extract_insurance_ai_first,
    extract_inspection_ai_first,
)
from app.services.extraction.structured_lc_builder import build_unified_structured_result
from app.services.risk.customs_risk import compute_customs_risk_from_option_e

# V2 Validation Pipeline imports
from app.services.validation.pipeline import (
    ValidationPipeline,
    ValidationInput,
    ValidationOutput,
)
from app.services.validation.validation_gate import ValidationGate, GateStatus
from app.services.validation.compliance_scorer import ComplianceScorer
from app.services.extraction.lc_baseline import LCBaseline, FieldResult, FieldPriority, ExtractionStatus

# Hybrid validation pipeline imports
from app.services.validation.llm_requirement_parser import (
    parse_lc_requirements_sync_v2,
    get_cached_requirements,
    infer_document_type,
    RequirementGraph,
)
from app.services.validation.party_matcher import parties_match, PartyMatchResult
from app.services.validation.amendment_generator import (
    generate_amendments_for_issues,
    calculate_total_amendment_cost,
    AmendmentDraft,
)
from app.services.validation.bank_profiles import (
    get_bank_profile,
    detect_bank_from_lc,
    BankProfile,
)
from app.services.validation.confidence_weighting import (
    batch_adjust_issues,
    calculate_overall_extraction_confidence,
)
from app.services.extraction.two_stage_extractor import (
    TwoStageExtractor,
    ExtractedField,
    ExtractionStatus as TwoStageStatus,
)

# Global two-stage extractor instance
_two_stage_extractor: Optional[TwoStageExtractor] = None


def _get_two_stage_extractor() -> TwoStageExtractor:
    """Get or create the two-stage extractor singleton."""
    global _two_stage_extractor
    if _two_stage_extractor is None:
        _two_stage_extractor = TwoStageExtractor()
    return _two_stage_extractor


def _filter_user_facing_fields(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter extracted fields to only include user-facing data.
    
    Removes internal metadata fields that start with underscore (_).
    These are useful for debugging but shouldn't clutter the user interface.
    """
    if not extracted:
        return {}
    
    # Fields to exclude from user display (internal metadata)
    INTERNAL_FIELDS = {
        "_extraction_method", "_extraction_confidence", "_ai_provider",
        "_status", "_field_details", "_status_counts", "_document_type",
        "_two_stage_validation", "_validation_details", "_raw_ai_response",
        "_fallback_used", "_failure_reason", "raw_text",
    }
    
    filtered = {}
    for key, value in extracted.items():
        # Skip underscore-prefixed fields
        if key.startswith("_"):
            continue
        # Skip known internal fields
        if key in INTERNAL_FIELDS:
            continue
        # Skip None values
        if value is None:
            continue
        # Skip empty strings
        if isinstance(value, str) and not value.strip():
            continue
        # Keep this field
        filtered[key] = value
    
    return filtered


def _apply_two_stage_validation(
    extracted_fields: Dict[str, Any],
    document_type: str,
    filename: str = "",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Apply two-stage validation to extracted fields.
    
    Stage 1: AI extraction (already done - passed as extracted_fields)
    Stage 2: Deterministic validation using reference data
    
    Args:
        extracted_fields: Dictionary of field_name -> value or {value, confidence}
        document_type: Type of document (lc, invoice, bl, etc.)
        filename: Original filename for logging
        
    Returns:
        Tuple of:
        - validated_fields: Normalized/validated version of extracted_fields
        - validation_summary: Stats about trusted/review/untrusted fields
    """
    if not extracted_fields:
        return {}, {"total": 0, "trusted": 0, "review": 0, "untrusted": 0}
    
    try:
        extractor = _get_two_stage_extractor()
        
        # Convert extracted_fields to format expected by two-stage extractor
        # If values are already dicts with confidence, use them; otherwise wrap
        ai_extraction: Dict[str, Any] = {}
        for field_name, value in extracted_fields.items():
            if field_name.startswith("_"):  # Skip metadata fields
                continue
            if field_name == "raw_text":  # Skip raw text
                continue
            if isinstance(value, dict) and "value" in value:
                ai_extraction[field_name] = value
            elif isinstance(value, dict) and "confidence" in value:
                ai_extraction[field_name] = value
            else:
                # Wrap raw value with default confidence
                ai_extraction[field_name] = {"value": value, "confidence": 0.7}
        
        if not ai_extraction:
            return extracted_fields, {"total": 0, "trusted": 0, "review": 0, "untrusted": 0}
        
        # Run two-stage validation
        validated = extractor.process(ai_extraction, document_type)
        summary = extractor.get_extraction_summary(validated)
        
        # Build output with normalized values and validation metadata
        validated_fields = dict(extracted_fields)  # Keep original structure
        validation_details: Dict[str, Dict[str, Any]] = {}
        
        for field_name, field_result in validated.items():
            # Use normalized value if available
            if field_result.normalized_value is not None:
                validated_fields[field_name] = field_result.normalized_value
            
            # Add validation metadata
            validation_details[field_name] = {
                "status": field_result.status.value,
                "ai_confidence": field_result.ai_confidence,
                "validation_score": field_result.validation_score,
                "final_confidence": field_result.final_confidence,
                "issues": field_result.issues,
            }
        
        # Add validation metadata to the fields dict
        validated_fields["_two_stage_validation"] = {
            "summary": summary,
            "fields": validation_details,
        }
        
        logger.info(
            "Two-stage validation for %s [%s]: total=%d trusted=%d review=%d untrusted=%d",
            document_type, filename,
            summary.get("total", 0),
            summary.get("trusted", 0),
            summary.get("review", 0),
            summary.get("untrusted", 0),
        )
        
        return validated_fields, summary
        
    except Exception as e:
        logger.warning("Two-stage validation failed for %s [%s]: %s", document_type, filename, e)
        # Return original fields on error
        return extracted_fields, {"total": 0, "trusted": 0, "review": 0, "untrusted": 0, "error": str(e)}


router = APIRouter(prefix="/api/validate", tags=["validation"])
logger = logging.getLogger(__name__)
PROFILE_DB = os.getenv("ENABLE_QUERY_PROFILING", "false").lower() == "true"


@contextmanager
def _profile_section(label: str):
    start = time.perf_counter()
    yield
    if PROFILE_DB:
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("profile[%s]=%.2fms", label, elapsed)


def get_or_create_demo_user(db: Session) -> User:
    """Get or create a demo user for unauthenticated validation requests."""
    demo_email = "demo@trdrhub.com"
    user = db.query(User).filter(User.email == demo_email).first()
    
    if not user:
        # Create demo company first
        # Use raw SQL to avoid schema mismatch issues
        from sqlalchemy import text
        result = db.execute(text("SELECT id FROM companies WHERE name = :name"), {"name": "Demo Company"})
        demo_company_row = result.first()
        
        if not demo_company_row:
            # Insert demo company using raw SQL (matching actual schema)
            company_id = uuid4()
            db.execute(
                text("""
                    INSERT INTO companies (id, name, type, created_at, updated_at)
                    VALUES (:id, :name, :type, NOW(), NOW())
                """),
                {
                    "id": company_id,
                    "name": "Demo Company",
                    "type": "sme"
                }
            )
            db.flush()
            demo_company_id = company_id
        else:
            demo_company_id = demo_company_row[0]
        
        # Create demo user
        # Use pre-computed bcrypt hash to avoid bcrypt backend initialization issues in production
        # This is a bcrypt hash of "demo123" - demo users don't need real password security
        DEMO_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.GQaEJSdVsqVfkG"
        user = User(
            email=demo_email,
            hashed_password=DEMO_PASSWORD_HASH,  # Pre-computed hash for "demo123"
            full_name="Demo User",
            role=UserRole.EXPORTER,
            is_active=True,
            company_id=demo_company_id,
            onboarding_completed=True,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user


async def get_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Get current user if authenticated, otherwise return demo user."""
    if authorization and authorization.startswith("Bearer "):
        try:
            from app.core.security import get_current_user
            from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
            security = HTTPBearer()
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=authorization[7:])
            return await get_current_user(credentials=credentials, db=db)
        except:
            pass
    
    # Return demo user for unauthenticated requests
    return get_or_create_demo_user(db)


@router.post("/")
async def validate_doc(
    request: Request,
    current_user: User = Depends(get_user_optional),
    db: Session = Depends(get_db),
):
    """Validate LC documents."""
    import time
    start_time = time.time()
    
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    document_summaries: List[Dict[str, Any]] = []

    try:
        content_type = request.headers.get("content-type", "")
        payload: dict
        files_list = []  # Collect files for validation
        
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            payload = {}
            for key, value in form.multi_items():
                # Check if this is a file upload (UploadFile instance)
                if hasattr(value, "filename") and hasattr(value, "read"):
                    # This is a file upload - validate it
                    file_obj = value
                    header_bytes = await file_obj.read(8)
                    await file_obj.seek(0)  # Reset for processing
                    
                    # Content-based validation
                    is_valid, error_message = validate_upload_file(
                        header_bytes,
                        filename=file_obj.filename,
                        content_type=file_obj.content_type
                    )
                    
                    if not is_valid:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid file content for {file_obj.filename}: {error_message}. File content does not match declared type."
                        )
                    
                    files_list.append(file_obj)
                    continue
                
                # Safely handle form field values - ensure they're strings
                # Handle potential encoding issues by converting to string safely
                # Skip if this looks like binary data (might be misidentified file)
                if isinstance(value, bytes):
                    # Check if this looks like binary data (PDF, image, etc.)
                    # PDFs start with %PDF, images have magic bytes
                    if len(value) > 4 and (
                        value.startswith(b'%PDF') or 
                        value.startswith(b'\x89PNG') or 
                        value.startswith(b'\xff\xd8\xff') or
                        value.startswith(b'GIF8') or
                        value.startswith(b'PK\x03\x04')  # ZIP
                    ):
                        # This is likely a file that wasn't properly identified
                        # Skip it or log a warning, but don't try to decode as text
                        continue
                    
                    # If value is bytes, try to decode as UTF-8, fallback to latin-1
                    try:
                        payload[key] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        # Fallback to latin-1 which can decode any byte sequence
                        try:
                            payload[key] = value.decode('latin-1')
                        except Exception:
                            # If all decoding fails, skip this field
                            continue
                elif isinstance(value, str):
                    payload[key] = value
                else:
                    # Convert other types to string, but skip if it's a file-like object
                    if hasattr(value, 'read') or hasattr(value, 'filename'):
                        continue
                    try:
                        payload[key] = str(value)
                    except Exception:
                        # Skip if conversion fails
                        continue
        else:
            payload = await request.json()

        # Parse JSON fields safely (document_tags, metadata)
        if "document_tags" in payload and isinstance(payload["document_tags"], str):
            try:
                payload["document_tags"] = json.loads(payload["document_tags"])
            except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
                # If parsing fails, set to empty dict
                payload["document_tags"] = {}
        
        if "metadata" in payload and isinstance(payload["metadata"], str):
            try:
                payload["metadata"] = json.loads(payload["metadata"])
            except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
                # If parsing fails, set to None
                payload["metadata"] = None

        doc_type = (
            payload.get("document_type")
            or payload.get("documentType")
            or "letter_of_credit"
        )
        payload["document_type"] = doc_type
        if not doc_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing document_type")

        # Extract structured data from uploaded files (respecting any document tags)
        document_tags = payload.get("document_tags")
        extracted_context = await _build_document_context(files_list, document_tags)
        if extracted_context:
            logger.info(
                "Extracted context from %d files. Keys: %s",
                len(files_list),
                list(extracted_context.keys()),
            )
            document_details = extracted_context.get("documents") or []
            if document_details:
                status_counts: Dict[str, int] = {}
                for doc in document_details:
                    extraction_stat = doc.get("extraction_status") or "unknown"
                    status_counts[extraction_stat] = status_counts.get(extraction_stat, 0) + 1
                logger.info(
                    "Document extraction status summary: total=%d details=%s",
                    len(document_details),
                    status_counts,
                )
            payload.update(extracted_context)
        else:
            logger.warning("No structured data extracted from %d uploaded files", len(files_list))
        if payload.get("lc"):
            payload["lc"] = _normalize_lc_payload_structures(payload["lc"])
        
        context_contains_structured_data = any(
            key in payload for key in ("lc", "invoice", "bill_of_lading", "documents")
        )
        
        if context_contains_structured_data:
            logger.info(f"Payload contains structured data: {list(payload.keys())}")
        else:
            logger.warning("Payload does not contain structured data - JSON rules will be skipped")

        lc_context = payload.get("lc") or {}
        shipment_context = _resolve_shipment_context(payload)
        
        # First, check if LC type was extracted from the document (from :40A: or AI extraction)
        extracted_lc_type = (
            lc_context.get("lc_type") or 
            lc_context.get("form_of_doc_credit") or
            (lc_context.get("mt700") or {}).get("form_of_doc_credit")
        )
        extracted_lc_type_confidence = lc_context.get("lc_type_confidence", 0)
        extracted_lc_type_reason = lc_context.get("lc_type_reason", "")
        
        # If extracted, use it; otherwise fall back to import/export detection
        override_lc_type = _extract_lc_type_override(payload)
        
        if extracted_lc_type and str(extracted_lc_type).lower() not in ["unknown", "none", ""]:
            # Use extracted LC type from document
            lc_type = str(extracted_lc_type).lower().replace(" ", "_")
            lc_type_reason = extracted_lc_type_reason or f"Extracted from LC document: {extracted_lc_type}"
            lc_type_confidence = extracted_lc_type_confidence if extracted_lc_type_confidence > 0 else 0.85
            lc_type_source = lc_context.get("lc_type_source", "document_extraction")
            lc_type_guess = {"lc_type": lc_type, "reason": lc_type_reason, "confidence": lc_type_confidence}
            logger.info(f"LC type from document extraction: {lc_type} (confidence={lc_type_confidence})")
        else:
            # Fall back to import/export detection based on country relationships
            lc_type_guess = detect_lc_type(lc_context, shipment_context)
            lc_type_source = "auto"
            lc_type = lc_type_guess["lc_type"]
            lc_type_reason = lc_type_guess["reason"]
            lc_type_confidence = lc_type_guess["confidence"]
        
        # Override takes precedence
        if override_lc_type:
            lc_type = override_lc_type
            lc_type_source = "override"
        payload["lc_type"] = lc_type
        payload["lc_type_reason"] = lc_type_reason
        payload["lc_type_confidence"] = lc_type_confidence
        payload["lc_type_source"] = lc_type_source
        payload["lc_detection"] = {
            "auto": lc_type_guess,
            "lc_type": lc_type,
            "source": lc_type_source,
        }
        logger.info(
            "LC type detection: auto=%s override=%s final=%s confidence=%.2f reason=%s",
            lc_type_guess["lc_type"],
            override_lc_type,
            lc_type,
            lc_type_confidence,
            lc_type_reason,
        )
        lc_type_is_unknown = lc_type == LCType.UNKNOWN.value

        # =====================================================================
        # CREATE VALIDATION SESSION EARLY
        # We need a database record BEFORE gating so blocked validations can be retrieved
        # =====================================================================
        user_type = payload.get("userType") or payload.get("user_type")
        metadata = payload.get("metadata")
        validation_session = None
        job_id = None
        
        if user_type in ["bank", "exporter", "importer"] or metadata:
            session_service = ValidationSessionService(db)
            validation_session = session_service.create_session(current_user)
            
            # Set company_id if available
            if current_user.company_id:
                validation_session.company_id = current_user.company_id
            
            # Store metadata based on user type
            if metadata:
                try:
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    org_id = None
                    if hasattr(request, 'state') and hasattr(request.state, 'org_id'):
                        org_id = request.state.org_id
                    validation_session.extracted_data = {
                        "bank_metadata": {
                            "client_name": metadata.get("clientName"),
                            "lc_number": metadata.get("lcNumber"),
                            "date_received": metadata.get("dateReceived"),
                            "org_id": org_id,
                        }
                    }
                except (json.JSONDecodeError, TypeError):
                    pass
            elif user_type in ["exporter", "importer"]:
                lc_number = payload.get("lc_number") or payload.get("lcNumber")
                workflow_type = payload.get("workflow_type") or payload.get("workflowType")
                if lc_number or workflow_type:
                    validation_session.extracted_data = {
                        "lc_number": lc_number,
                        "user_type": user_type,
                        "workflow_type": workflow_type,
                    }
            
            validation_session.status = SessionStatus.PROCESSING.value
            validation_session.processing_started_at = func.now()
            db.commit()
            job_id = str(validation_session.id)
            
            # =====================================================================
            # PERSIST DOCUMENTS TO DATABASE
            # This enables customs pack generation and document retrieval
            # =====================================================================
            try:
                document_list = payload.get("documents") or []
                for idx, doc_info in enumerate(document_list):
                    doc_record = Document(
                        validation_session_id=validation_session.id,
                        document_type=doc_info.get("document_type") or doc_info.get("type") or "unknown",
                        original_filename=doc_info.get("filename") or doc_info.get("name") or f"document_{idx + 1}.pdf",
                        s3_key=f"validation/{validation_session.id}/{doc_info.get('filename', f'doc_{idx}')}",  # Placeholder
                        file_size=doc_info.get("file_size") or doc_info.get("size") or 0,
                        content_type=doc_info.get("content_type") or "application/pdf",
                        ocr_text=doc_info.get("raw_text_preview") or doc_info.get("raw_text") or "",
                        ocr_confidence=doc_info.get("ocr_confidence"),
                        extracted_fields=doc_info.get("extracted_fields") or {},
                    )
                    db.add(doc_record)
                db.commit()
                logger.info("Persisted %d documents to database for session %s", len(document_list), job_id)
            except Exception as doc_persist_error:
                logger.warning("Failed to persist documents to DB: %s", doc_persist_error)
                # Don't fail validation if document persistence fails
        else:
            job_id = payload.get("job_id") or str(uuid4())

        # =====================================================================
        # V2 VALIDATION PIPELINE - PRIMARY FLOW
        # This is the core validation engine. Legacy flow is disabled.
        # If LC extraction fails (missing critical fields), we block validation.
        # =====================================================================
        v2_gate_result = None
        v2_baseline = None
        v2_issues = []
        v2_crossdoc_issues = []
        
        try:
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
                    "telemetry": {"validation_blocked": True, "block_reason": v2_gate_result.block_reason},
                }
            # =====================================================================
            
            # Gate passed - run v2 IssueEngine with DB-backed rules
            from app.services.validation.issue_engine import IssueEngine
            from app.rules.external.rule_executor import RuleExecutor
            from app.rules.external.rule_loader import get_rule_loader
            
            # Create rule loader with database session to load all rules (YAML + DB)
            db_rule_loader = get_rule_loader(db_session=db)
            db_rule_executor = RuleExecutor(rule_loader=db_rule_loader)
            issue_engine = IssueEngine(rule_executor=db_rule_executor)
            
            v2_issues = issue_engine.generate_extraction_issues(v2_baseline)
            logger.info("V2 IssueEngine generated %d extraction issues", len(v2_issues))
            
            # Log database rules loaded
            db_rules_count = len([r for r in db_rule_loader.load_all_rules() if hasattr(r, 'id')])
            logger.info("V2 IssueEngine loaded %d total rules (YAML + Database)", db_rules_count)
            
            # =================================================================
            # EXECUTE DATABASE RULES
            # Run the uploaded rules (UCP600, ISBP745, bank profiles, etc.) 
            # against the validation context
            # =================================================================
            try:
                # Build context for rule execution from all extracted data
                rule_context = {
                    "lc": lc_context,
                    "mt700": lc_context.get("mt700", {}),
                    "invoice": payload.get("invoice", {}),
                    "bill_of_lading": payload.get("bill_of_lading", {}),
                    "packing_list": payload.get("packing_list", {}),
                    "insurance": payload.get("insurance", {}),
                    "certificate_of_origin": payload.get("certificate_of_origin", {}),
                    "documents": payload.get("documents", []),
                    "documents_presence": payload.get("documents_presence", {}),
                }
                
                # Execute rules and get issues
                rule_issues = issue_engine.generate_rule_issues(rule_context)
                if rule_issues:
                    v2_issues.extend(rule_issues)
                    logger.info(
                        "V2 Rule execution generated %d issues from %d database rules",
                        len(rule_issues),
                        db_rules_count
                    )
            except Exception as rule_exec_err:
                logger.warning(
                    "Rule execution failed (non-blocking): %s",
                    str(rule_exec_err),
                    exc_info=True
                )
            
            # Run v2 CrossDocValidator
            from app.services.validation.crossdoc_validator import CrossDocValidator
            crossdoc_validator = CrossDocValidator()
            crossdoc_result = crossdoc_validator.validate_all(
                lc_baseline=v2_baseline,
                invoice=payload.get("invoice"),
                bill_of_lading=payload.get("bill_of_lading"),
                insurance=payload.get("insurance"),
                certificate_of_origin=payload.get("certificate_of_origin"),
                packing_list=payload.get("packing_list"),
            )
            v2_crossdoc_issues = crossdoc_result.issues
            logger.info("V2 CrossDocValidator found %d issues", len(v2_crossdoc_issues))
            
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
            
            # Get documents from both payload and extracted_context
            documents_for_ai = (
                extracted_context.get("documents") or  # Primary: from extraction
                payload.get("documents") or  # Fallback: from payload
                []
            )
            logger.info(f"AI Validation: {len(documents_for_ai)} documents to check")
            
            ai_issues, ai_metadata = await run_ai_validation(
                lc_data=lc_data_for_ai,
                documents=documents_for_ai,
                extracted_context=extracted_context,
            )
            
            logger.info(
                "AI Validation: found %d issues (critical=%d, major=%d)",
                len(ai_issues),
                ai_metadata.get("critical_issues", 0),
                ai_metadata.get("major_issues", 0),
            )
            
            # Convert AI issues to same format as crossdoc issues
            for ai_issue in ai_issues:
                v2_crossdoc_issues.append(ai_issue)
            
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
        
        # Convert v2 issues to legacy format for compatibility
        if v2_issues:
            for issue in v2_issues:
                issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
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
                    "ucp_reference": issue_dict.get("ucp_reference"),
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
                    "ucp_reference": issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or "",
                    "isbp_reference": issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or "",
                    "display_card": True,
                    "ruleset_domain": issue_dict.get("ruleset_domain") or "icc.lcopilot.crossdoc",
                    "auto_generated": issue_dict.get("auto_generated", False),
                })
        
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
            rule_id = issue.get("rule") or issue.get("title") or str(len(deduplicated_results))
            if rule_id not in seen_rules:
                seen_rules.add(rule_id)
                deduplicated_results.append(issue)
            else:
                logger.debug("Removed duplicate issue: %s", rule_id)
        
        if len(failed_results) != len(deduplicated_results):
            logger.warning(
                "Deduplication removed %d duplicate issues",
                len(failed_results) - len(deduplicated_results)
            )
        
        logger.info(
            "V2 Validation: total_issues=%d (extraction=%d crossdoc=%d) after_dedup=%d",
            len(failed_results),
            len(v2_issues) if v2_issues else 0,
            len(v2_crossdoc_issues) if v2_crossdoc_issues else 0,
            len(deduplicated_results),
        )
        
        issue_cards, reference_issues = build_issue_cards(deduplicated_results)

        # Record usage - link to session if created (skip for demo user)
        quota = None
        company_size, tolerance_percent = _determine_company_size(current_user, payload)
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
        
        processing_duration = time.time() - start_time
        processing_summary = _build_processing_summary(document_summaries, processing_duration, len(failed_results))

        if validation_session and current_user.is_bank_user() and current_user.company_id:
            try:
                results = await apply_bank_policy(
                    validation_results=results,
                    bank_id=str(current_user.company_id),
                    document_data=payload,
                    db_session=db,
                    validation_session_id=str(validation_session.id),
                    user_id=str(current_user.id),
                )
            except Exception as e:
                logger.warning("Bank policy application skipped: %s", e)

        # Ensure document_summaries is a list (fallback to empty if malformed)
        final_documents = document_summaries if isinstance(document_summaries, list) else []
        
        # GUARANTEE: Always have non-empty documents for Option-E
        if not final_documents:
            logger.warning("final_documents empty - using files_list fallback")
            final_documents = _build_document_summaries(files_list, results, None)
        
        # Build extractor outputs from payload or extracted context
        extractor_outputs = payload.get("lc_structured_output") if payload else None
        if not extractor_outputs and payload:
            # Fallback: build from LC detection results
            extractor_outputs = {
                "lc_type": payload.get("lc_type", "unknown"),
                "lc_type_reason": payload.get("lc_type_reason", "Auto-detected"),
                "lc_type_confidence": payload.get("lc_type_confidence", 0),
                "lc_type_source": payload.get("lc_type_source", "auto"),
                "mt700": (payload.get("lc") or {}).get("mt700") or {"blocks": {}, "raw_text": None, "version": "mt700_v1"},
                "goods": (payload.get("lc") or {}).get("goods") or (payload.get("lc") or {}).get("goods_items") or [],
                "clauses": (payload.get("lc") or {}).get("clauses") or [],
                "timeline": [],
                "issues": [],
            }
        
        # Build Option-E structured result with proper error handling
        try:
            option_e_payload = build_unified_structured_result(
                session_documents=final_documents,
                extractor_outputs=extractor_outputs,
                legacy_payload=None,
            )
            structured_result = option_e_payload["structured_result"]
        except Exception as e:
            import traceback
            logger.error(
                "Option-E builder failed in /api/validate: %s: %s",
                type(e).__name__,
                str(e),
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "job_id": str(job_id) if job_id else None,
                    "document_count": len(final_documents),
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error_code": "option_e_builder_failed",
                    "message": f"{type(e).__name__}: {str(e)}"
                }
            )

        # Customs risk/pack computation (guarded - skip on error, don't crash endpoint)
        structured_result.setdefault("analytics", {})
        try:
            customs_risk = compute_customs_risk_from_option_e(structured_result)
            structured_result["analytics"]["customs_risk"] = customs_risk
        except Exception as e:
            logger.warning(
                "Customs risk computation skipped: %s: %s",
                type(e).__name__,
                str(e),
                exc_info=True
            )
            structured_result["analytics"]["customs_risk"] = None

        try:
            customs_pack = build_customs_manifest_from_option_e(structured_result)
            structured_result["customs_pack"] = customs_pack
        except Exception as e:
            logger.warning(
                "Customs pack build skipped: %s: %s",
                type(e).__name__,
                str(e),
                exc_info=True
            )
            structured_result["customs_pack"] = None

        lc_structured_docs = (structured_result.get("lc_structured") or {}).get("documents_structured") or []
        if lc_structured_docs and not structured_result.get("documents_structured"):
            structured_result["documents_structured"] = lc_structured_docs

        # Merge actual processing_summary values into structured_result
        # This ensures processing_time_display and other fields are populated
        if structured_result.get("processing_summary") and processing_summary:
            structured_result["processing_summary"].update({
                "processing_time_seconds": processing_summary.get("processing_time_seconds"),
                "processing_time_display": processing_summary.get("processing_time_display"),
                "processing_time_ms": processing_summary.get("processing_time_ms"),
                "extraction_quality": processing_summary.get("extraction_quality"),
                "successful_extractions": processing_summary.get("verified", 0),
                "failed_extractions": processing_summary.get("errors", 0),
            })
        # Also update analytics with processing time
        if structured_result.get("analytics"):
            structured_result["analytics"]["processing_time_display"] = processing_summary.get("processing_time_display")

        # =====================================================================
        # MERGE ISSUE CARDS INTO STRUCTURED RESULT
        # issue_cards were built from failed_results at line 603 but need to be
        # added to structured_result for the frontend to display them
        # =====================================================================
        if issue_cards:
            existing_issues = structured_result.get("issues") or []
            # Convert issue_cards to dict format if they're not already
            formatted_issues = []
            for card in issue_cards:
                if isinstance(card, dict):
                    formatted_issues.append(card)
                elif hasattr(card, 'to_dict'):
                    formatted_issues.append(card.to_dict())
                elif hasattr(card, '__dict__'):
                    formatted_issues.append(card.__dict__)
                else:
                    formatted_issues.append({"title": str(card), "severity": "minor"})
            
            # Merge with any existing issues (from crossdoc, etc.)
            structured_result["issues"] = existing_issues + formatted_issues
            logger.info("Added %d issue cards to structured_result (total issues: %d)", 
                       len(formatted_issues), len(structured_result["issues"]))
        
        # NOTE: v2_crossdoc_issues are already included in issue_cards via failed_results
        # Do NOT add them again here - that was causing DUPLICATE issues!

        # =====================================================================
        # V2 VALIDATION PIPELINE - FINAL SCORING
        # Apply v2 compliance scoring and add structured metadata
        # =====================================================================
        try:
            # Always add v2 fields (gate passed at this point)
            structured_result["validation_blocked"] = False
            structured_result["validation_status"] = "processing"
            
            if v2_gate_result is not None:
                # Add gate result
                structured_result["gate_result"] = v2_gate_result.to_dict()
                
                # Add extraction summary
                structured_result["extraction_summary"] = {
                    "completeness": round(v2_gate_result.completeness * 100, 1),
                    "critical_completeness": round(v2_gate_result.critical_completeness * 100, 1),
                    "missing_critical": v2_gate_result.missing_critical,
                    "missing_required": v2_gate_result.missing_required,
                }
            
            # Add LC baseline to structured result
            if v2_baseline:
                structured_result["lc_baseline"] = {
                    "lc_number": v2_baseline.lc_number.value,
                    "amount": v2_baseline.amount.value,
                    "currency": v2_baseline.currency.value,
                    "applicant": v2_baseline.applicant.value,
                    "beneficiary": v2_baseline.beneficiary.value,
                    "expiry_date": v2_baseline.expiry_date.value,
                    "latest_shipment": v2_baseline.latest_shipment.value,
                    "port_of_loading": v2_baseline.port_of_loading.value,
                    "port_of_discharge": v2_baseline.port_of_discharge.value,
                    "goods_description": v2_baseline.goods_description.value,
                    "incoterm": v2_baseline.incoterm.value,
                    "extraction_completeness": round(v2_baseline.extraction_completeness * 100, 1),
                    "critical_completeness": round(v2_baseline.critical_completeness * 100, 1),
                }
            
            # Calculate v2 compliance score
            v2_scorer = ComplianceScorer()
            all_issues = structured_result.get("issues") or []
            
            # Calculate compliance with v2 scorer
            extraction_completeness = v2_gate_result.completeness if v2_gate_result else 1.0
            v2_score = v2_scorer.calculate_from_issues(
                all_issues,
                extraction_completeness=extraction_completeness,
            )
            
            # Update validation status based on score
            structured_result["validation_status"] = v2_score.level.value
            
            # Override compliance rate with v2 calculation
            if structured_result.get("analytics"):
                compliance_pct = int(round(v2_score.score))
                structured_result["analytics"]["lc_compliance_score"] = compliance_pct
                structured_result["analytics"]["compliance_score"] = compliance_pct  # Frontend alias
                structured_result["analytics"]["compliance_level"] = v2_score.level.value
                structured_result["analytics"]["compliance_cap_reason"] = v2_score.cap_reason
                structured_result["analytics"]["issue_counts"] = {
                    "critical": v2_score.critical_count,
                    "major": v2_score.major_count,
                    "minor": v2_score.minor_count,
                }
            
            if structured_result.get("processing_summary"):
                structured_result["processing_summary"]["compliance_rate"] = int(round(v2_score.score))
                structured_result["processing_summary"]["severity_breakdown"] = {
                    "critical": v2_score.critical_count,
                    "major": v2_score.major_count,
                    "medium": 0,
                    "minor": v2_score.minor_count,
                }
            
            logger.info(
                "V2 compliance scoring: score=%.1f%% level=%s issues=%d (critical=%d major=%d minor=%d)",
                v2_score.score,
                v2_score.level.value,
                len(all_issues),
                v2_score.critical_count,
                v2_score.major_count,
                v2_score.minor_count,
            )
            
            # =====================================================================
            # BANK SUBMISSION VERDICT
            # =====================================================================
            bank_verdict = _build_bank_submission_verdict(
                critical_count=v2_score.critical_count,
                major_count=v2_score.major_count,
                minor_count=v2_score.minor_count,
                compliance_score=v2_score.score,
                all_issues=all_issues,
            )
            structured_result["bank_verdict"] = bank_verdict
            
            if structured_result.get("processing_summary"):
                structured_result["processing_summary"]["bank_verdict"] = bank_verdict.get("verdict")
            
            logger.info(
                "Bank verdict: %s (action_required=%d)",
                bank_verdict.get("verdict"),
                len(bank_verdict.get("action_items", [])),
            )
            
            # =====================================================================
            # AMENDMENT GENERATION (for fixable discrepancies)
            # =====================================================================
            try:
                lc_number = (
                    lc_context.get("lc_number") or
                    mt700.get("20") or
                    extracted_context.get("lc", {}).get("lc_number") or
                    "UNKNOWN"
                )
                lc_amount = lc_context.get("amount") or mt700.get("32B_amount") or 0
                lc_currency = lc_context.get("currency") or mt700.get("32B_currency") or "USD"
                
                amendments = generate_amendments_for_issues(
                    issues=all_issues,
                    lc_data={
                        "lc_number": lc_number,
                        "amount": lc_amount,
                        "currency": lc_currency,
                    }
                )
                
                if amendments:
                    amendment_cost = calculate_total_amendment_cost(amendments)
                    structured_result["amendments_available"] = {
                        "count": len(amendments),
                        "total_estimated_fee_usd": amendment_cost.get("total_estimated_fee_usd", 0),
                        "amendments": [a.to_dict() for a in amendments],
                    }
                    logger.info(f"Generated {len(amendments)} amendment drafts")
            except Exception as e:
                logger.warning(f"Amendment generation failed: {e}")
            
            # =====================================================================
            # CONFIDENCE WEIGHTING (adjust severity based on OCR confidence)
            # =====================================================================
            try:
                if extraction_confidence_summary:
                    structured_result["extraction_confidence"] = extraction_confidence_summary
                    
                    # Add recommendations if low confidence
                    if extraction_confidence_summary.get("average_confidence", 1.0) < 0.6:
                        existing_recommendations = bank_verdict.get("action_items", [])
                        for rec in extraction_confidence_summary.get("recommendations", []):
                            existing_recommendations.append({
                                "priority": "medium",
                                "issue": "Low OCR Confidence",
                                "action": rec,
                            })
            except Exception as e:
                logger.warning(f"Confidence metadata failed: {e}")
            
            # =====================================================================
            # BANK PROFILE METADATA
            # =====================================================================
            if bank_profile:
                structured_result["bank_profile"] = {
                    "bank_code": bank_profile.bank_code,
                    "bank_name": bank_profile.bank_name,
                    "strictness": bank_profile.strictness.value,
                }
            
            # =====================================================================
            # TOLERANCE METADATA (for audit trail)
            # =====================================================================
            if requirement_graph and requirement_graph.tolerances:
                structured_result["tolerances_applied"] = {
                    k: {
                        "tolerance_percent": v.tolerance_percent,
                        "source": v.source.value,
                        "explicit": v.explicit,
                    }
                    for k, v in requirement_graph.tolerances.items()
                }
            
        except Exception as e:
            logger.warning("V2 scoring failed: %s", e, exc_info=True)
        # =====================================================================

        telemetry_payload = {
            "UnifiedStructuredResultBuilt": True,
            "documents": len(structured_result.get("documents_structured", [])),
            "issues": len(structured_result.get("issues", [])),
        }

        if validation_session:
            validation_session.validation_results = {"structured_result": structured_result}
            validation_session.status = SessionStatus.COMPLETED.value
            validation_session.processing_completed_at = func.now()
            db.commit()
            db.refresh(validation_session)
        else:
            db.commit()

        if request_user_type == "bank" and validation_session:
            duration_ms = int((time.time() - start_time) * 1000)
            metadata_dict = payload.get("metadata") or {}
            if isinstance(metadata_dict, str):
                try:
                    metadata_dict = json.loads(metadata_dict)
                except Exception:
                    metadata_dict = {}
            audit_service.log_action(
                action=AuditAction.UPLOAD,
                user=current_user,
                correlation_id=audit_context['correlation_id'],
                resource_type="bank_validation",
                resource_id=str(validation_session.id),
                lc_number=metadata_dict.get("lcNumber") or metadata_dict.get("lc_number"),
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                endpoint=audit_context['endpoint'],
                http_method=audit_context['http_method'],
                result=AuditResult.SUCCESS,
                duration_ms=duration_ms,
                audit_metadata={
                    "client_name": metadata_dict.get("clientName") or metadata_dict.get("client_name"),
                    "date_received": metadata_dict.get("dateReceived") or metadata_dict.get("date_received"),
                    "discrepancy_count": len(failed_results),
                    "document_count": len(payload.get("files", [])) if isinstance(payload.get("files"), list) else 0,
                },
            )

        logger.info(
            "Validation completed",
            extra={
                "job_id": str(job_id),
                "user_type": request_user_type or (current_user.role.value if hasattr(current_user, "role") else "unknown"),
                "rules_evaluated": len(results),
                "failed_rules": len(failed_results),
                "issue_cards": len(issue_cards),
                "json_pipeline": True,
            },
        )

        return {
            "job_id": str(job_id),
            "jobId": str(job_id),
            "structured_result": structured_result,
            "telemetry": telemetry_payload,
        }
    except HTTPException:
        raise
    except UnicodeDecodeError as e:
        # Handle encoding errors specifically
        import logging
        logging.getLogger(__name__).error(f"Encoding error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File encoding error: Unable to process uploaded file. Please ensure files are valid PDFs or images. Error: {str(e)}"
        )
    except Exception as e:
        # Log the full error with stack trace
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(
            f"Validation endpoint exception: {type(e).__name__}: {str(e)}",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "user_id": current_user.id if current_user else None,
                "endpoint": "/api/validate",
                "traceback": error_traceback,
            },
            exc_info=True
        )
        
        # Log failed validation if bank operation
        user_type = payload.get("userType") or payload.get("user_type") if 'payload' in locals() else None
        if user_type == "bank" and 'validation_session' in locals() and validation_session:
            duration_ms = int((time.time() - start_time) * 1000)
            audit_service.log_action(
                action=AuditAction.UPLOAD,
                user=current_user,
                correlation_id=audit_context['correlation_id'],
                resource_type="bank_validation",
                resource_id=str(validation_session.id) if validation_session else "unknown",
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                endpoint=audit_context['endpoint'],
                http_method=audit_context['http_method'],
                result=AuditResult.ERROR,
                duration_ms=duration_ms,
                error_message=str(e),
            )
        raise


def _build_document_summaries(
    files_list: List[Any],
    results: List[Dict[str, Any]],
    document_details: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Create lightweight document summaries for downstream consumers."""
    details = document_details or []
    issue_by_name, issue_by_type, issue_by_id = _collect_document_issue_stats(results)

    def _build_summary_from_detail(detail: Dict[str, Any], index: int) -> Dict[str, Any]:
        filename = detail.get("filename") or detail.get("name")
        doc_type = detail.get("document_type") or _infer_document_type_from_name(filename, index)
        # FIX: Normalize doc_type to canonical form (e.g., "Bill of Lading" -> "bill_of_lading")
        # This ensures it matches the keys in issue_by_type
        normalized_type = _normalize_doc_type_key(doc_type) or doc_type or "supporting_document"
        detail_id = detail.get("id") or str(uuid4())
        stats = _resolve_issue_stats(
            detail_id,
            filename,
            normalized_type,
            issue_by_name,
            issue_by_type,
            issue_by_id,
        )
        status = _severity_to_status(stats.get("max_severity") if stats else None)
        discrepancy_count = stats.get("count", 0) if stats else 0

        return {
            "id": detail_id,
            "name": filename or f"Document {index + 1}",
            "type": _humanize_doc_type(normalized_type),
            "documentType": normalized_type,
            "status": status,
            "discrepancyCount": discrepancy_count,
            "extractedFields": _filter_user_facing_fields(detail.get("extracted_fields") or {}),
            "ocrConfidence": detail.get("ocr_confidence"),
            "extractionStatus": detail.get("extraction_status"),
        }

    if details:
        logger.info(
            "Building document summaries from details: %d documents found",
            len(details),
        )
        return [_build_summary_from_detail(detail, index) for index, detail in enumerate(details)]

    if not files_list:
        # GUARANTEE: Never return empty - create a placeholder document if nothing available
        logger.warning("No document details or files_list available - creating placeholder document")
        return [
            {
                "id": str(uuid4()),
                "name": "No documents uploaded",
                "type": "Supporting Document",
                "documentType": "supporting_document",
                "status": "warning",
                "discrepancyCount": 0,
                "extractedFields": {},
                "ocrConfidence": None,
                "extractionStatus": "unknown",
            }
        ]

    summaries: List[Dict[str, Any]] = []
    for index, file_obj in enumerate(files_list):
        filename = getattr(file_obj, "filename", None)
        inferred_type = _infer_document_type_from_name(filename, index)
        stats = _resolve_issue_stats(
            None,
            filename,
            inferred_type,
            issue_by_name,
            issue_by_type,
            issue_by_id,
        )
        doc_status = _severity_to_status(stats.get("max_severity") if stats else None)
        discrepancy_count = stats.get("count", 0) if stats else 0
        summaries.append(
            {
                "id": str(uuid4()),
                "name": filename or f"Document {index + 1}",
                "type": _humanize_doc_type(inferred_type),
                "documentType": inferred_type,
                "status": doc_status,
                "discrepancyCount": discrepancy_count,
                "extractedFields": {},
                "ocrConfidence": None,
                "extractionStatus": "unknown",
            }
        )

    # GUARANTEE: Never return empty list
    if not summaries:
        logger.warning("Document summaries still empty after processing - adding placeholder")
        summaries.append({
            "id": str(uuid4()),
            "name": "Document",
            "type": "Supporting Document",
            "documentType": "supporting_document",
            "status": "warning",
            "discrepancyCount": 0,
            "extractedFields": {},
            "ocrConfidence": None,
            "extractionStatus": "unknown",
        })

    return summaries


def _infer_document_type_from_name(filename: Optional[str], index: int) -> str:
    """Infer the document type using filename patterns."""
    if filename:
        name = filename.lower()
        if any(token in name for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in name for token in ("bill_of_lading", "bill-of-lading", "bill", "lading", "bl", "shipping", "bol")):
            return "bill_of_lading"
        if any(token in name for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in name for token in ("insurance", "policy")):
            return "insurance_certificate"
        if any(token in name for token in ("certificate_of_origin", "coo", "gsp", "certificate")):
            return "certificate_of_origin"
        if any(token in name for token in ("inspection", "quality", "analysis")):
            return "inspection_certificate"
        if any(token in name for token in ("lc_", "letter_of_credit", "mt700")) or name.endswith("_lc.pdf"):
            return "letter_of_credit"
        if " credit " in name:
            return "letter_of_credit"

    return _fallback_doc_type(index)


def _fallback_doc_type(index: int) -> str:
    """Fallback ordering for document types when hints are unavailable."""
    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
        3: "packing_list",
        4: "certificate_of_origin",
        5: "insurance_certificate",
        6: "inspection_certificate",
    }
    return mapping.get(index, "supporting_document")


def _extract_request_user_type(payload: Dict[str, Any]) -> str:
    value = payload.get("user_type") or payload.get("userType")
    if not value:
        return ""
    return str(value).strip().lower()


def _should_force_json_rules(payload: Dict[str, Any]) -> bool:
    user_type = _extract_request_user_type(payload)
    if user_type in {"exporter", "importer"}:
        return True
    workflow = payload.get("workflow_type") or payload.get("workflowType")
    if workflow:
        normalized = str(workflow).strip().lower()
        if normalized.startswith(("export", "import")):
            return True
    return False


DOCUMENT_TYPE_ALIASES: Dict[str, List[str]] = {
    "letter_of_credit": [
        "letter of credit",
        "lc",
        "l/c",
        "mt700",
        "lc document",
        "lc_document",
    ],
    "commercial_invoice": [
        "invoice",
        "commercial invoice",
        "ci",
        "inv",
    ],
    "bill_of_lading": [
        "bill of lading",
        "bill_of_lading",
        "bill-of-lading",
        "bill",
        "bol",
        "bl",
        "shipping document",
        "awb",
    ],
    "packing_list": [
        "packing list",
        "packlist",
        "packing",
    ],
    "insurance_certificate": [
        "insurance",
        "insurance certificate",
        "policy",
    ],
    "certificate_of_origin": [
        "certificate of origin",
        "coo",
        "gsp",
    ],
    "inspection_certificate": [
        "inspection",
        "analysis",
        "quality certificate",
    ],
    "supporting_document": [
        "supporting",
        "misc",
        "other",
    ],
}


def _canonical_document_tag(raw_value: Any) -> Optional[str]:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip().lower()
    if not normalized:
        return None
    normalized = normalized.replace("-", " ").replace("_", " ")
    for canonical, aliases in DOCUMENT_TYPE_ALIASES.items():
        if normalized == canonical.replace("_", " "):
            return canonical
        if normalized in aliases:
            return canonical
    for canonical, aliases in DOCUMENT_TYPE_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return canonical
    return normalized.replace(" ", "_")


def _resolve_document_type(
    filename: Optional[str],
    index: int,
    document_tags: Optional[Dict[str, str]] = None,
) -> str:
    if filename and document_tags:
        lower_name = filename.lower()
        base_name = lower_name.rsplit(".", 1)[0]
        tag_value = document_tags.get(lower_name) or document_tags.get(base_name)
        if tag_value:
            return tag_value
    return _infer_document_type(filename, index)


async def _build_document_context(
    files_list: List[Any],
    document_tags: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Attempt to extract basic structured fields from uploaded documents.

    Returns a dictionary that can be merged into the validation payload (e.g. {"lc": {...}}).
    Also stores raw_text and sets extraction_status.
    """
    if not files_list:
        logger.debug("No files provided for extraction")
        return {"extraction_status": "empty"}

    try:
        from app.rules.extractors import DocumentFieldExtractor, ISO20022ParseError, extract_iso20022_lc
        from app.rules.models import DocumentType
        from app.services.extraction.lc_extractor import extract_lc_structured as extract_lc
    except ImportError as e:
        logger.warning(f"DocumentFieldExtractor not available; skipping text extraction: {e}")
        return {"extraction_status": "error", "extraction_error": str(e)}

    extractor = DocumentFieldExtractor()
    normalized_tags: Dict[str, str] = {}
    if isinstance(document_tags, dict):
        for raw_name, raw_value in document_tags.items():
            if not raw_name:
                continue
            canonical = _canonical_document_tag(str(raw_value)) if raw_value else None
            if canonical:
                normalized_tags[raw_name.lower()] = canonical
                # Also index by filename without extension for convenience
                base_name = raw_name.rsplit(".", 1)[0].lower()
                normalized_tags.setdefault(base_name, canonical)

    context: Dict[str, Any] = {}
    document_details: List[Dict[str, Any]] = []
    has_structured_data = False
    known_doc_types = {
        "letter_of_credit",
        "commercial_invoice",
        "bill_of_lading",
        "packing_list",
        "insurance_certificate",
        "certificate_of_origin",
        "inspection_certificate",
        "supporting_document",
    }
    documents_presence: Dict[str, Dict[str, Any]] = {
        doc_type: {"present": False, "count": 0} for doc_type in known_doc_types
    }

    for idx, upload_file in enumerate(files_list):
        filename = getattr(upload_file, "filename", f"document_{idx+1}")
        content_type = getattr(upload_file, "content_type", "unknown")
        document_type = _resolve_document_type(filename, idx, normalized_tags)
        document_id = str(uuid4())
        doc_info: Dict[str, Any] = {
            "id": document_id,
            "filename": filename,
            "document_type": document_type,
            "extracted_fields": {},
            "extraction_status": "empty",
        }
        if normalized_tags and filename:
            lower_name = filename.lower()
            doc_info["tag"] = normalized_tags.get(lower_name) or normalized_tags.get(lower_name.rsplit(".", 1)[0])
        
        logger.info(f"Processing file {idx+1}/{len(files_list)}: {filename} (type: {document_type}, content-type: {content_type})")
        
        extracted_text = await _extract_text_from_upload(upload_file)
        if not extracted_text:
            logger.warning(f"⚠ No text extracted from {filename} - skipping field extraction")
            doc_info["extraction_status"] = "empty"
            document_details.append(doc_info)
            continue
        
        logger.info(f"✓ Extracted {len(extracted_text)} characters from {filename}")

        try:
            if document_type == "letter_of_credit":
                lc_payload = context.setdefault("lc", {})
                if "raw_text" not in lc_payload:
                    lc_payload["raw_text"] = extracted_text
                    context["lc_text"] = extracted_text

                lc_format = detect_lc_format(extracted_text)
                lc_payload["format"] = lc_format

                if lc_format == "iso20022":
                    # Use enhanced ISO 20022 extractor with AI fallback
                    try:
                        from app.services.extraction.iso20022_lc_extractor import (
                            extract_iso20022_with_ai_fallback,
                            ISO20022ParseError as ISO20022Error,
                        )
                        
                        iso_context = await extract_iso20022_with_ai_fallback(
                            extracted_text,
                            ai_threshold=0.5,
                        )
                        
                        extraction_method = iso_context.get("_extraction_method", "iso20022")
                        extraction_confidence = iso_context.get("_extraction_confidence", 0.0)
                        
                        logger.info(
                            f"ISO 20022 extraction from {filename}: method={extraction_method} "
                            f"confidence={extraction_confidence:.2f}"
                        )
                        
                        lc_payload.update(iso_context)
                        has_structured_data = True
                        doc_info["extracted_fields"] = iso_context
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        
                        logger.info(f"ISO20022 LC context keys: {list(lc_payload.keys())}")
                        if not context.get("lc_number") and iso_context.get("number"):
                            context["lc_number"] = iso_context["number"]
                            
                    except Exception as exc:
                        logger.warning(f"ISO20022 LC extraction failed for {filename}: {exc}", exc_info=True)
                        doc_info["extraction_status"] = "failed"
                        doc_info["extraction_error"] = str(exc)
                else:
                    # Use AI-FIRST extraction for OCR/plaintext LC documents
                    # This runs AI as PRIMARY, then validates with regex
                    try:
                        # AI-first extraction (PRIMARY)
                        lc_struct = await extract_lc_ai_first(extracted_text)
                        extraction_method = lc_struct.get("_extraction_method", "unknown")
                        extraction_confidence = lc_struct.get("_extraction_confidence", 0.0)
                        extraction_status = lc_struct.get("_status", "unknown")
                        
                        logger.info(
                            f"AI-first extraction from {filename}: method={extraction_method} "
                            f"confidence={extraction_confidence:.2f} status={extraction_status} "
                            f"keys={list(lc_struct.keys())}"
                        )
                        
                        if lc_struct and extraction_status != "failed":
                            # AI-first already includes validation, but apply two-stage for normalization
                            validated_lc, validation_summary = _apply_two_stage_validation(
                                lc_struct, "lc", filename
                            )
                            
                            lc_payload.update(validated_lc)
                            context["lc_structured_output"] = validated_lc
                            has_structured_data = True
                            logger.info(f"LC context keys: {list(lc_payload.keys())}")
                            
                            # Get LC number from various possible keys
                            lc_number = (
                                validated_lc.get("number") or 
                                validated_lc.get("lc_number") or
                                validated_lc.get("reference")
                            )
                            if not context.get("lc_number") and lc_number:
                                context["lc_number"] = lc_number
                            
                            doc_info["extracted_fields"] = validated_lc
                            doc_info["extraction_status"] = "success"
                            doc_info["extraction_method"] = extraction_method
                            doc_info["extraction_confidence"] = extraction_confidence
                            doc_info["validation_summary"] = validation_summary
                            doc_info["ai_first_status"] = extraction_status
                            
                            # Include field-level details if available
                            if "_field_details" in lc_struct:
                                doc_info["field_details"] = lc_struct["_field_details"]
                            if "_status_counts" in lc_struct:
                                doc_info["status_counts"] = lc_struct["_status_counts"]
                        else:
                            logger.warning(f"AI-first extraction failed for {filename}, status={extraction_status}")
                    except Exception as extract_error:
                        logger.warning(f"LC extraction (with AI) failed for {filename}: {extract_error}", exc_info=True)
                        # Ultimate fallback to basic field extractor
                        try:
                            lc_fields = extractor.extract_fields(extracted_text, DocumentType.LETTER_OF_CREDIT)
                            logger.info(f"Fallback: Extracted {len(lc_fields)} fields from LC document {filename}")
                            lc_context = _fields_to_lc_context(lc_fields)
                            if lc_context:
                                # Apply two-stage validation to fallback extraction
                                validated_lc, validation_summary = _apply_two_stage_validation(
                                    lc_context, "lc", filename
                                )
                                
                                lc_payload.update(validated_lc)
                                has_structured_data = True
                                logger.info(f"LC context keys: {list(lc_payload.keys())}")
                                if not context.get("lc_number") and validated_lc.get("number"):
                                    context["lc_number"] = validated_lc["number"]
                                doc_info["extracted_fields"] = validated_lc
                                doc_info["extraction_status"] = "success"
                                doc_info["validation_summary"] = validation_summary
                            else:
                                logger.warning(f"No LC context created from {len(lc_fields)} extracted fields")
                        except Exception as fallback_error:
                            logger.error(f"Both LC extraction methods failed for {filename}: {fallback_error}", exc_info=True)
                            doc_info["extraction_status"] = "failed"
                            doc_info["extraction_error"] = str(fallback_error)
            elif document_type == "commercial_invoice":
                # Use AI-FIRST extraction for invoices
                try:
                    invoice_struct = await extract_invoice_ai_first(extracted_text)
                    extraction_method = invoice_struct.get("_extraction_method", "unknown")
                    extraction_confidence = invoice_struct.get("_extraction_confidence", 0.0)
                    extraction_status = invoice_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first invoice extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if invoice_struct and extraction_status != "failed":
                        # Apply two-stage validation for normalization
                        validated_invoice, validation_summary = _apply_two_stage_validation(
                            invoice_struct, "invoice", filename
                        )
                        
                        if "invoice" not in context:
                            context["invoice"] = {}
                        context["invoice"]["raw_text"] = extracted_text
                        context["invoice"].update(validated_invoice)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_invoice
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in invoice_struct:
                            doc_info["field_details"] = invoice_struct["_field_details"]
                        if "_status_counts" in invoice_struct:
                            doc_info["status_counts"] = invoice_struct["_status_counts"]
                        
                        logger.info(f"Invoice context keys: {list(context['invoice'].keys())}")
                    else:
                        logger.warning(f"AI-first invoice extraction failed for {filename}")
                except Exception as inv_err:
                    logger.warning(f"Invoice AI extraction failed for {filename}: {inv_err}", exc_info=True)
                    # Fallback to regex
                    invoice_fields = extractor.extract_fields(extracted_text, DocumentType.COMMERCIAL_INVOICE)
                    invoice_context = _fields_to_flat_context(invoice_fields)
                    if invoice_context:
                        validated_invoice, validation_summary = _apply_two_stage_validation(
                            invoice_context, "invoice", filename
                        )
                        if "invoice" not in context:
                            context["invoice"] = {}
                        context["invoice"]["raw_text"] = extracted_text
                        context["invoice"].update(validated_invoice)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_invoice
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
            elif document_type == "bill_of_lading":
                # Use AI-FIRST extraction for Bill of Lading
                try:
                    bl_struct = await extract_bl_ai_first(extracted_text)
                    extraction_method = bl_struct.get("_extraction_method", "unknown")
                    extraction_confidence = bl_struct.get("_extraction_confidence", 0.0)
                    extraction_status = bl_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first B/L extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if bl_struct and extraction_status != "failed":
                        # Apply two-stage validation for normalization
                        validated_bl, validation_summary = _apply_two_stage_validation(
                            bl_struct, "bl", filename
                        )
                        
                        if "bill_of_lading" not in context:
                            context["bill_of_lading"] = {}
                        context["bill_of_lading"]["raw_text"] = extracted_text
                        context["bill_of_lading"].update(validated_bl)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_bl
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in bl_struct:
                            doc_info["field_details"] = bl_struct["_field_details"]
                        if "_status_counts" in bl_struct:
                            doc_info["status_counts"] = bl_struct["_status_counts"]
                        
                        logger.info(f"B/L context keys: {list(context['bill_of_lading'].keys())}")
                    else:
                        logger.warning(f"AI-first B/L extraction failed for {filename}")
                except Exception as bl_err:
                    logger.warning(f"B/L AI extraction failed for {filename}: {bl_err}", exc_info=True)
                    # Fallback to regex
                    bl_fields = extractor.extract_fields(extracted_text, DocumentType.BILL_OF_LADING)
                    bl_context = _fields_to_flat_context(bl_fields)
                    if bl_context:
                        validated_bl, validation_summary = _apply_two_stage_validation(
                            bl_context, "bl", filename
                        )
                        if "bill_of_lading" not in context:
                            context["bill_of_lading"] = {}
                        context["bill_of_lading"]["raw_text"] = extracted_text
                        context["bill_of_lading"].update(validated_bl)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_bl
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
            elif document_type == "packing_list":
                # Use AI-FIRST extraction for packing list
                try:
                    packing_struct = await extract_packing_list_ai_first(extracted_text)
                    extraction_method = packing_struct.get("_extraction_method", "unknown")
                    extraction_confidence = packing_struct.get("_extraction_confidence", 0.0)
                    extraction_status = packing_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first packing list extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if packing_struct and extraction_status != "failed":
                        validated_packing, validation_summary = _apply_two_stage_validation(
                            packing_struct, "packing_list", filename
                        )
                        
                        pkg_ctx = context.setdefault("packing_list", {})
                        pkg_ctx["raw_text"] = extracted_text
                        pkg_ctx.update(validated_packing)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_packing
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in packing_struct:
                            doc_info["field_details"] = packing_struct["_field_details"]
                        
                        logger.info(f"Packing list context keys: {list(pkg_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first packing list extraction failed for {filename}")
                except Exception as packing_err:
                    logger.warning(f"Packing list AI extraction failed for {filename}: {packing_err}", exc_info=True)
                    packing_fields = extractor.extract_fields(extracted_text, DocumentType.PACKING_LIST)
                    packing_context = _fields_to_flat_context(packing_fields)
                    if packing_context:
                        validated_packing, validation_summary = _apply_two_stage_validation(
                            packing_context, "packing_list", filename
                        )
                        pkg_ctx = context.setdefault("packing_list", {})
                        pkg_ctx["raw_text"] = extracted_text
                        pkg_ctx.update(validated_packing)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_packing
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
            elif document_type == "certificate_of_origin":
                # Use AI-FIRST extraction for certificate of origin
                try:
                    coo_struct = await extract_coo_ai_first(extracted_text)
                    extraction_method = coo_struct.get("_extraction_method", "unknown")
                    extraction_confidence = coo_struct.get("_extraction_confidence", 0.0)
                    extraction_status = coo_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first CoO extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if coo_struct and extraction_status != "failed":
                        validated_coo, validation_summary = _apply_two_stage_validation(
                            coo_struct, "certificate_of_origin", filename
                        )
                        
                        coo_ctx = context.setdefault("certificate_of_origin", {})
                        coo_ctx["raw_text"] = extracted_text
                        coo_ctx.update(validated_coo)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_coo
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in coo_struct:
                            doc_info["field_details"] = coo_struct["_field_details"]
                        
                        logger.info(f"Certificate of origin context keys: {list(coo_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first CoO extraction failed for {filename}")
                except Exception as coo_err:
                    logger.warning(f"CoO AI extraction failed for {filename}: {coo_err}", exc_info=True)
                    coo_fields = extractor.extract_fields(extracted_text, DocumentType.CERTIFICATE_OF_ORIGIN)
                    coo_context = _fields_to_flat_context(coo_fields)
                    if coo_context:
                        validated_coo, validation_summary = _apply_two_stage_validation(
                            coo_context, "certificate_of_origin", filename
                        )
                        coo_ctx = context.setdefault("certificate_of_origin", {})
                        coo_ctx["raw_text"] = extracted_text
                        coo_ctx.update(validated_coo)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_coo
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
            elif document_type == "insurance_certificate":
                # Use AI-FIRST extraction for insurance certificate
                try:
                    insurance_struct = await extract_insurance_ai_first(extracted_text)
                    extraction_method = insurance_struct.get("_extraction_method", "unknown")
                    extraction_confidence = insurance_struct.get("_extraction_confidence", 0.0)
                    extraction_status = insurance_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first insurance extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if insurance_struct and extraction_status != "failed":
                        validated_insurance, validation_summary = _apply_two_stage_validation(
                            insurance_struct, "insurance", filename
                        )
                        
                        insurance_ctx = context.setdefault("insurance_certificate", {})
                        insurance_ctx["raw_text"] = extracted_text
                        insurance_ctx.update(validated_insurance)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_insurance
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in insurance_struct:
                            doc_info["field_details"] = insurance_struct["_field_details"]
                        
                        logger.info(f"Insurance context keys: {list(insurance_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first insurance extraction failed for {filename}")
                except Exception as ins_err:
                    logger.warning(f"Insurance AI extraction failed for {filename}: {ins_err}", exc_info=True)
                    insurance_fields = extractor.extract_fields(extracted_text, DocumentType.INSURANCE_CERTIFICATE)
                    insurance_context = _fields_to_flat_context(insurance_fields)
                    if insurance_context:
                        validated_insurance, validation_summary = _apply_two_stage_validation(
                            insurance_context, "insurance", filename
                        )
                        insurance_ctx = context.setdefault("insurance_certificate", {})
                        insurance_ctx["raw_text"] = extracted_text
                        insurance_ctx.update(validated_insurance)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_insurance
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
            elif document_type == "inspection_certificate":
                # Use AI-FIRST extraction for inspection certificate
                try:
                    inspection_struct = await extract_inspection_ai_first(extracted_text)
                    extraction_method = inspection_struct.get("_extraction_method", "unknown")
                    extraction_confidence = inspection_struct.get("_extraction_confidence", 0.0)
                    extraction_status = inspection_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first inspection extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if inspection_struct and extraction_status != "failed":
                        validated_inspection, validation_summary = _apply_two_stage_validation(
                            inspection_struct, "inspection", filename
                        )
                        
                        inspection_ctx = context.setdefault("inspection_certificate", {})
                        inspection_ctx["raw_text"] = extracted_text
                        inspection_ctx.update(validated_inspection)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_inspection
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in inspection_struct:
                            doc_info["field_details"] = inspection_struct["_field_details"]
                        
                        logger.info(f"Inspection context keys: {list(inspection_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first inspection extraction failed for {filename}")
                except Exception as insp_err:
                    logger.warning(f"Inspection AI extraction failed for {filename}: {insp_err}", exc_info=True)
                    inspection_fields = extractor.extract_fields(extracted_text, DocumentType.INSPECTION_CERTIFICATE)
                    inspection_context = _fields_to_flat_context(inspection_fields)
                    if inspection_context:
                        validated_inspection, validation_summary = _apply_two_stage_validation(
                            inspection_context, "inspection", filename
                        )
                        inspection_ctx = context.setdefault("inspection_certificate", {})
                        inspection_ctx["raw_text"] = extracted_text
                        inspection_ctx.update(validated_inspection)
                        has_structured_data = True
                        doc_info["extracted_fields"] = validated_inspection
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
            else:
                # For other document types, retain raw text for downstream use
                doc_info["raw_text_preview"] = extracted_text[:500]
                doc_info["extraction_status"] = "text_only"
                extra_context = context.setdefault(document_type, {})
                extra_context["raw_text"] = extracted_text
        except Exception as e:
            logger.error(f"Error extracting fields from {filename}: {e}", exc_info=True)
            document_details.append(doc_info)
            continue

        if doc_info.get("extracted_fields"):
            doc_info["raw_text_preview"] = extracted_text[:500]
        elif doc_info.get("extraction_status") in {"empty", "text_only"} and extracted_text:
            # Ensure at least a preview is available for OCR overview
            doc_info["raw_text_preview"] = extracted_text[:500]
            if doc_info.get("extraction_status") == "empty":
                doc_info["extraction_status"] = "text_only"

        document_details.append(doc_info)
        entry = documents_presence.setdefault(
            document_type,
            {"present": False, "count": 0},
        )
        entry["present"] = True
        entry["count"] += 1

    # Set extraction status
    if has_structured_data:
        context["extraction_status"] = "success"
        logger.info(f"Final extracted context structure: {list(context.keys())}")
    elif any(key in context for key in ("lc", "invoice", "bill_of_lading")):
        # We have raw_text but no structured fields
        context["extraction_status"] = "partial"
        logger.warning("Extracted raw text but no structured fields could be parsed")
    else:
        context["extraction_status"] = "empty"
        logger.warning("No context extracted from any files")
    
    if document_details:
        context["documents"] = document_details

    context["documents_presence"] = documents_presence
    context["documents_summary"] = documents_presence
    if context.get("lc"):
        context["lc"] = _normalize_lc_payload_structures(context["lc"])

    # GUARANTEE: Always provide lc_structured_output for Option-E builder
    # Even if extraction failed, provide a minimal structure
    if "lc_structured_output" not in context:
        lc_data = context.get("lc") or {}
        context["lc_structured_output"] = {
            "lc_type": lc_data.get("type") or "unknown",
            "lc_type_reason": "Extracted from uploaded documents" if lc_data else "No LC data extracted",
            "lc_type_confidence": 50 if lc_data else 0,
            "lc_type_source": "auto",
            "mt700": lc_data.get("mt700") or {"blocks": {}, "raw_text": lc_data.get("raw_text"), "version": "mt700_v1"},
            "goods": lc_data.get("goods") or lc_data.get("goods_items") or [],
            "clauses": lc_data.get("clauses") or lc_data.get("additional_conditions") or [],
            "timeline": [],
            "issues": [],
        }

    return context


def detect_lc_format(raw_lc_text: Optional[str]) -> str:
    """
    Detect whether an LC payload is ISO 20022 XML or MT700 text.
    Defaults to MT700 when no XML signature is present.
    """

    if not raw_lc_text:
        return "mt700"

    snippet = raw_lc_text.strip()
    lowered = snippet.lower()
    if "<document" in lowered and "xmlns" in lowered:
        return "iso20022"
    if snippet.startswith("<?xml") and "<Document" in snippet:
        return "iso20022"
    return "mt700"


def _resolve_shipment_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    for key in (
        "bill_of_lading",
        "billOfLading",
        "awb",
        "air_waybill",
        "airway_bill",
        "shipment",
    ):
        ctx = payload.get(key)
        if isinstance(ctx, dict):
            return ctx
    lc_ports = (payload.get("lc") or {}).get("ports")
    if isinstance(lc_ports, dict):
        shipment: Dict[str, Any] = {}
        loading_value = lc_ports.get("port_of_loading") or lc_ports.get("loading")
        discharge_value = lc_ports.get("port_of_discharge") or lc_ports.get("discharge")
        if loading_value:
            shipment["port_of_loading"] = loading_value
        if discharge_value:
            shipment["port_of_discharge"] = discharge_value
        if shipment:
            return shipment
        return lc_ports
    return {}


def _extract_lc_type_override(payload: Dict[str, Any]) -> Optional[str]:
    options = payload.get("options") or {}
    candidates = [
        payload.get("lc_type_override"),
        payload.get("lcTypeOverride"),
        options.get("lc_type_override"),
        options.get("lc_type"),
        payload.get("lcType"),
        payload.get("lc_type_selection"),
        payload.get("requested_lc_type"),
    ]
    for candidate in candidates:
        normalized = normalize_lc_type(candidate)
        if normalized in VALID_LC_TYPES:
            if normalized == LCType.UNKNOWN.value:
                return LCType.UNKNOWN.value
            return normalized
        if candidate and str(candidate).strip().lower() == "auto":
            return None
    return None


def _build_issue_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a context snapshot from the validation payload for AI issue rewriting.
    Extracts key document data that helps the AI produce accurate issue descriptions.
    """
    lc = payload.get("lc") or payload.get("lc_data") or {}
    invoice = payload.get("invoice") or {}
    bill_of_lading = payload.get("bill_of_lading") or payload.get("billOfLading") or {}
    certificate_of_origin = payload.get("certificate_of_origin") or payload.get("certificateOfOrigin") or {}
    insurance = payload.get("insurance") or payload.get("insurance_certificate") or {}
    packing_list = payload.get("packing_list") or payload.get("packingList") or {}
    
    return {
        "lc": {
            "goods_description": lc.get("goods_description"),
            "goods_items": lc.get("goods_items"),
            "incoterm": lc.get("incoterm"),
            "ports": lc.get("ports"),
            "dates": lc.get("dates"),
            "applicant": lc.get("applicant"),
            "beneficiary": lc.get("beneficiary"),
            "amount": lc.get("amount") or lc.get("lc_amount"),
            "currency": lc.get("currency"),
        },
        "invoice": {
            "goods_description": invoice.get("goods_description") or invoice.get("product_description"),
            "amount": invoice.get("invoice_amount") or invoice.get("amount"),
            "currency": invoice.get("currency"),
            "hs_code": invoice.get("hs_code"),
            "consignee": invoice.get("consignee"),
            "shipper": invoice.get("shipper"),
        },
        "bill_of_lading": {
            "goods_description": bill_of_lading.get("goods_description"),
            "port_of_loading": bill_of_lading.get("port_of_loading"),
            "port_of_discharge": bill_of_lading.get("port_of_discharge"),
            "vessel": bill_of_lading.get("vessel"),
            "on_board_date": bill_of_lading.get("on_board_date"),
            "consignee": bill_of_lading.get("consignee"),
            "shipper": bill_of_lading.get("shipper"),
        },
        "certificate_of_origin": {
            "origin_country": certificate_of_origin.get("origin_country") or certificate_of_origin.get("country_of_origin"),
            "goods_description": certificate_of_origin.get("goods_description"),
        },
        "insurance": {
            "coverage_amount": insurance.get("coverage_amount") or insurance.get("amount"),
            "currency": insurance.get("currency"),
            "risks_covered": insurance.get("risks_covered"),
        },
        "packing_list": {
            "total_packages": packing_list.get("total_packages"),
            "gross_weight": packing_list.get("gross_weight"),
            "net_weight": packing_list.get("net_weight"),
        },
        "metadata": {
            "lc_number": payload.get("lc_number") or payload.get("lcNumber"),
            "user_type": payload.get("user_type") or payload.get("userType"),
            "workflow_type": payload.get("workflow_type") or payload.get("workflowType"),
        },
    }


def _determine_company_size(current_user: User, payload: Dict[str, Any]) -> Tuple[str, Decimal]:
    """Infer company size from user/company metadata."""
    size = str(payload.get("company_size") or "").strip().lower()
    onboarding_company = ((current_user.onboarding_data or {}).get("company") or {}) if current_user else {}
    if onboarding_company:
        size = (onboarding_company.get("size") or size).strip().lower()
    if not size and getattr(current_user, "company", None):
        company = current_user.company
        if isinstance(company.event_metadata, dict):
            meta_size = company.event_metadata.get("company_size")
            if meta_size:
                size = str(meta_size).strip().lower()
    if size not in {"sme", "medium", "large"}:
        size = "sme"
    tolerance_map = {
        "sme": Decimal("10.0"),
        "medium": Decimal("5.0"),
        "large": Decimal("2.0"),
    }
    tolerance_percent = tolerance_map.get(size, Decimal("7.5"))
    return size, tolerance_percent


def _compute_invoice_amount_bounds(payload: Dict[str, Any], tolerance_percent: Decimal) -> Tuple[Optional[float], Optional[float]]:
    """Compute absolute tolerance amount and allowed invoice limit."""
    # Handle both formats: {"value": 125000} (legacy) and 125000 (AI-first)
    lc_data = payload.get("lc") or {}
    amount_raw = lc_data.get("amount")
    
    if isinstance(amount_raw, dict):
        # Legacy format: {"value": 125000}
        lc_amount_value = amount_raw.get("value")
    else:
        # AI-first format: direct number
        lc_amount_value = amount_raw
    
    lc_amount_decimal = _coerce_decimal(lc_amount_value)
    if lc_amount_decimal is None:
        return None, None
    tolerance_value = lc_amount_decimal * tolerance_percent / Decimal("100")
    limit = lc_amount_decimal + tolerance_value
    return float(tolerance_value), float(limit)


def _coerce_decimal(value: Any) -> Optional[Decimal]:
    """Lightweight decimal coercion used for tolerance math."""
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            normalized = value.replace(",", "").strip()
            if not normalized:
                return None
            return Decimal(normalized)
    except InvalidOperation:
        return None
    return None


async def _extract_text_from_upload(upload_file: Any) -> str:
    """
    Extract textual content from an uploaded PDF/image.
    
    Tries pdfminer/PyPDF2 first, then falls back to OCR (Google Document AI/AWS Textract)
    if enabled and text extraction returns empty.
    """
    filename = getattr(upload_file, "filename", "unknown")
    content_type = getattr(upload_file, "content_type", "unknown")
    
    logger.log(TRACE_LOG_LEVEL, "Starting text extraction for %s (type=%s)", filename, content_type)
    
    try:
        file_bytes = await upload_file.read()
        await upload_file.seek(0)
        logger.info(f"✓ Read {len(file_bytes)} bytes from {filename}")
    except Exception as e:
        logger.error(f"✗ Failed to read file {filename}: {e}", exc_info=True)
        return ""

    if not file_bytes:
        logger.warning(f"⚠ Empty file content for {filename}")
        return ""
    
    # Check file size limit for OCR
    if len(file_bytes) > settings.OCR_MAX_BYTES:
        logger.warning(
            f"File {filename} exceeds OCR size limit ({len(file_bytes)} > {settings.OCR_MAX_BYTES} bytes). "
            f"Skipping OCR fallback."
        )

    text_output = ""

    # Try pdfminer first (better for complex layouts)
    logger.log(TRACE_LOG_LEVEL, "Trying pdfminer extraction for %s", filename)
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        text_output = extract_text(BytesIO(file_bytes))
        if text_output.strip():
            logger.log(TRACE_LOG_LEVEL, "pdfminer extracted %s characters from %s", len(text_output), filename)
            return text_output
        else:
            logger.log(TRACE_LOG_LEVEL, "pdfminer returned empty text for %s", filename)
    except Exception as pdfminer_error:
        logger.log(TRACE_LOG_LEVEL, "pdfminer extraction failed for %s: %s", filename, pdfminer_error)

    # Fallback to PyPDF2
    logger.log(TRACE_LOG_LEVEL, "Trying PyPDF2 extraction for %s", filename)
    try:
        from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]
        reader = PdfReader(BytesIO(file_bytes))
        pieces = []
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                pieces.append(page_text)
            except Exception as e:
                logger.debug(f"Failed to extract text from page {page_num+1} of {filename}: {e}")
                continue
        text_output = "\n".join(pieces)
        if text_output.strip():
            logger.log(TRACE_LOG_LEVEL, "PyPDF2 extracted %s characters from %s (%s pages)", len(text_output), filename, len(reader.pages))
            return text_output
        else:
            logger.log(TRACE_LOG_LEVEL, "PyPDF2 returned empty text for %s (%s pages)", filename, len(reader.pages))
    except Exception as pypdf_error:
        logger.warning(f"  ✗ PyPDF2 extraction failed for {filename}: {pypdf_error}")

    # If pdfminer/PyPDF2 returned empty and OCR is enabled, try OCR providers
    if not text_output.strip() and settings.OCR_ENABLED:
        logger.log(TRACE_LOG_LEVEL, "Text extraction empty for %s, attempting OCR fallback (enabled=%s)", filename, settings.OCR_ENABLED)
        logger.log(TRACE_LOG_LEVEL, "OCR provider order: %s", settings.OCR_PROVIDER_ORDER)
        
        # Check file size and page count before attempting OCR
        page_count = 0
        try:
            from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]
            reader = PdfReader(BytesIO(file_bytes))
            page_count = len(reader.pages)
            logger.log(TRACE_LOG_LEVEL, "Page count for %s: %s", filename, page_count)
        except:
            # If we can't count pages, assume it's a single-page image
            page_count = 1 if content_type.startswith('image/') else 0
            logger.log(TRACE_LOG_LEVEL, "Could not determine page count for %s, assuming %s", filename, page_count)
        
        if page_count > settings.OCR_MAX_PAGES:
            logger.warning(
                f"  ⚠ File {filename} exceeds OCR page limit ({page_count} > {settings.OCR_MAX_PAGES} pages). "
                f"Skipping OCR."
            )
        elif len(file_bytes) > settings.OCR_MAX_BYTES:
            logger.warning(
                f"File {filename} exceeds OCR size limit ({len(file_bytes)} > {settings.OCR_MAX_BYTES} bytes). "
                f"Skipping OCR."
            )
        else:
            # Try OCR providers in configured order
            logger.log(TRACE_LOG_LEVEL, "Attempting OCR with providers %s for %s", settings.OCR_PROVIDER_ORDER, filename)
            text_output = await _try_ocr_providers(file_bytes, filename, content_type)
            if text_output.strip():
                logger.log(TRACE_LOG_LEVEL, "OCR extraction successful for %s (%s characters)", filename, len(text_output))
                return text_output
            else:
                logger.warning(f"  ✗ OCR extraction returned empty")
    elif not settings.OCR_ENABLED:
        logger.log(TRACE_LOG_LEVEL, "OCR disabled, bypassing fallback for %s", filename)

    if not text_output.strip():
        logger.error(f"❌ ALL extraction methods failed for {filename}")
        logger.error(f"   Summary: pdfminer=empty, PyPDF2=empty, OCR={'attempted' if settings.OCR_ENABLED else 'disabled'}")
        logger.error(f"   File details: content-type={content_type}, size={len(file_bytes)} bytes")
    else:
        logger.log(TRACE_LOG_LEVEL, "Extraction complete for %s (%s characters)", filename, len(text_output))
    
    return text_output


async def _try_ocr_providers(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Try OCR providers in configured order until one succeeds.
    
    Returns extracted text or empty string if all providers fail.
    """
    from uuid import uuid4
    from app.ocr.factory import get_ocr_factory
    
    # Map provider order names to adapter classes
    provider_map = {
        "gdocai": "google_documentai",
        "textract": "aws_textract",
    }
    
    # Get configured provider order
    provider_order = settings.OCR_PROVIDER_ORDER or ["gdocai", "textract"]
    
    try:
        factory = get_ocr_factory()
        all_adapters = factory.get_all_adapters()
        
        # Create a map of provider names to adapters
        adapter_map = {adapter.provider_name: adapter for adapter in all_adapters}
        
        # Try providers in configured order
        for provider_name in provider_order:
            # Map short name to full provider name
            full_provider_name = provider_map.get(provider_name, provider_name)
            
            if full_provider_name not in adapter_map:
                logger.debug(f"OCR provider {provider_name} ({full_provider_name}) not available")
                continue
            
            adapter = adapter_map[full_provider_name]
            
            try:
                # Check health before attempting
                if not await adapter.health_check():
                    logger.debug(f"OCR provider {full_provider_name} health check failed")
                    continue
                
                # Try OCR with timeout
                import asyncio
                doc_id = uuid4()
                
                result = await asyncio.wait_for(
                    adapter.process_file_bytes(file_bytes, filename, content_type, doc_id),
                    timeout=settings.OCR_TIMEOUT_SEC
                )
                
                if result and result.full_text and not result.error:
                    logger.info(
                        f"OCR provider {full_provider_name} extracted {len(result.full_text)} characters "
                        f"from {filename} (confidence: {result.overall_confidence:.2f}, "
                        f"time: {result.processing_time_ms}ms)"
                    )
                    return result.full_text
                elif result and result.error:
                    logger.warning(f"OCR provider {full_provider_name} returned error: {result.error}")
                else:
                    logger.debug(f"OCR provider {full_provider_name} returned empty result")
                    
            except asyncio.TimeoutError:
                logger.warning(f"OCR provider {full_provider_name} timed out after {settings.OCR_TIMEOUT_SEC}s")
                continue
            except Exception as e:
                logger.warning(f"OCR provider {full_provider_name} failed: {e}", exc_info=True)
                continue
        
        logger.warning(f"All OCR providers failed for {filename}")
        return ""
        
    except Exception as e:
        logger.error(f"Failed to initialize OCR factory: {e}", exc_info=True)
        return ""


def _infer_document_type(filename: Optional[str], index: int) -> str:
    """Guess document type using filename hints or position."""
    if filename:
        lower = filename.lower()
        if any(token in lower for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in lower for token in ("bill of lading", "bill_of_lading", "bill-of-lading", "bill", "lading", "bl", "shipping", "bol")):
            return "bill_of_lading"
        if any(token in lower for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in lower for token in ("insurance", "policy")):
            return "insurance_certificate"
        if any(token in lower for token in ("certificate_of_origin", "coo", "gsp", "certificate")):
            return "certificate_of_origin"
        if any(token in lower for token in ("inspection", "analysis", "quality")):
            return "inspection_certificate"
        if any(token in lower for token in ("lc_", "letter_of_credit", "mt700")) or lower.endswith("_lc.pdf"):
            return "letter_of_credit"
        if " credit " in lower:
            return "letter_of_credit"

    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
    }
    return mapping.get(index, "letter_of_credit")


def _resolve_issue_stats(
    detail_id: Optional[str],
    filename: Optional[str],
    doc_type: Optional[str],
    issue_by_name: Dict[str, Dict[str, Any]],
    issue_by_type: Dict[str, Dict[str, Any]],
    issue_by_id: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if detail_id and detail_id in issue_by_id:
        return issue_by_id[detail_id]

    if filename:
        name_key = filename.strip().lower()
        if name_key in issue_by_name:
            return issue_by_name[name_key]
        inferred_type = _label_to_doc_type(name_key)
        if inferred_type and inferred_type in issue_by_type:
            return issue_by_type[inferred_type]

    if doc_type and doc_type in issue_by_type:
        return issue_by_type[doc_type]

    return None


def _collect_document_issue_stats(
    results: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    issue_by_name: Dict[str, Dict[str, Any]] = {}
    issue_by_type: Dict[str, Dict[str, Any]] = {}
    issue_by_id: Dict[str, Dict[str, Any]] = {}

    for result in results:
        if result.get("passed", False) or result.get("not_applicable", False):
            continue

        severity = (result.get("severity") or "minor").lower()
        doc_names = _extract_document_names(result)
        doc_types = _extract_document_types(result)
        doc_ids = _extract_document_ids(result)

        for doc_id in doc_ids:
            _bump_issue_entry(issue_by_id, doc_id, severity)

        for name in doc_names:
            name_key = name.strip().lower()
            entry = _bump_issue_entry(issue_by_name, name_key, severity)
            inferred_type = _label_to_doc_type(name)
            if inferred_type:
                _bump_issue_entry(issue_by_type, inferred_type, severity)

        for doc_type in doc_types:
            canonical = _normalize_doc_type_key(doc_type)
            if canonical:
                _bump_issue_entry(issue_by_type, canonical, severity)

    return issue_by_name, issue_by_type, issue_by_id


def _extract_document_names(discrepancy: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for key in ("documents", "document_names"):
        value = discrepancy.get(key)
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, list):
            names.extend([str(item) for item in value if isinstance(item, str)])
    for key in ("document", "document_name"):
        if discrepancy.get(key):
            names.append(str(discrepancy[key]))
    return names


def _extract_document_types(discrepancy: Dict[str, Any]) -> List[str]:
    types: List[str] = []
    value = discrepancy.get("document_types")
    if isinstance(value, str):
        types.append(value)
    elif isinstance(value, list):
        types.extend([str(item) for item in value if item])
    elif value:
        types.append(str(value))
    if discrepancy.get("document_type"):
        types.append(str(discrepancy["document_type"]))
    return types


def _extract_document_ids(discrepancy: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    value = discrepancy.get("document_ids")
    if isinstance(value, str):
        ids.append(value)
    elif isinstance(value, list):
        ids.extend([str(item) for item in value if item])
    elif value:
        ids.append(str(value))
    if discrepancy.get("document_id"):
        ids.append(str(discrepancy["document_id"]))
    return ids


def _bump_issue_entry(bucket: Dict[str, Dict[str, Any]], key: str, severity: str) -> Dict[str, Any]:
    if not key:
        return {}
    entry = bucket.setdefault(key, {"count": 0, "max_severity": "minor"})
    entry["count"] += 1
    if _severity_rank(severity) > _severity_rank(entry["max_severity"]):
        entry["max_severity"] = severity
    return entry


def _severity_rank(severity: Optional[str]) -> int:
    order = {
        "critical": 3,
        "error": 3,
        "major": 2,
        "warning": 2,
        "warn": 2,
        "minor": 1,
    }
    if not severity:
        return 0
    return order.get(severity.lower(), 1)


def _severity_to_status(severity: Optional[str]) -> str:
    if not severity:
        return "success"
    normalized = severity.lower()
    if normalized in {"critical", "error"}:
        return "error"
    if normalized in {"major", "warning", "warn", "minor"}:
        return "warning"
    return "success"


def _label_to_doc_type(label: Optional[str]) -> Optional[str]:
    if not label:
        return None
    normalized = str(label).strip().lower()
    for canonical, friendly in DEFAULT_LABELS.items():
        if normalized == friendly.lower():
            return canonical
        if normalized.replace(" ", "_") == canonical:
            return canonical
    return None


def _normalize_doc_type_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip().lower()
    normalized_snake = normalized.replace(" ", "_")
    if normalized_snake in DEFAULT_LABELS:
        return normalized_snake
    if normalized in DEFAULT_LABELS:
        return normalized
    return normalized_snake


def _humanize_doc_type(doc_type: Optional[str]) -> str:
    if not doc_type:
        return "Supporting Document"
    return DEFAULT_LABELS.get(doc_type, doc_type.replace("_", " ").title())


def _build_blocked_structured_result(
    v2_gate_result,
    v2_baseline: LCBaseline,
    lc_type: str,
    processing_duration: float,
    documents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a structured_result for blocked validation.
    
    This is returned when the validation gate blocks (missing LC, critical fields missing).
    The response is HTTP 200 with validation_blocked=true.
    """
    # Build blocking issues
    blocking_issues = []
    for issue in v2_gate_result.blocking_issues:
        if isinstance(issue, dict):
            blocking_issues.append(issue)
        elif hasattr(issue, 'to_dict'):
            blocking_issues.append(issue.to_dict())
    
    # Build document list - PRESERVE extraction data even when validation is blocked
    # The extraction succeeded, we're blocking validation due to missing LC fields
    # Don't throw away the extraction work!
    docs_structured = []
    for i, doc in enumerate(documents):
        # Preserve actual extraction status and fields
        actual_extraction_status = doc.get("extraction_status") or "unknown"
        actual_extracted_fields = doc.get("extracted_fields") or {}
        
        docs_structured.append({
            "document_id": doc.get("id") or str(uuid4()),
            "filename": doc.get("filename") or doc.get("name") or f"Document {i+1}",
            "document_type": doc.get("document_type") or "supporting_document",
            "extraction_status": actual_extraction_status,  # Keep real status
            "extracted_fields": actual_extracted_fields,    # Keep real data
            "issues_count": 0,
            "raw_text_preview": doc.get("raw_text_preview"),  # Keep preview text
            "ocr_confidence": doc.get("ocr_confidence"),
        })
    
    # Processing time display
    if processing_duration < 1:
        time_display = f"{int(processing_duration * 1000)}ms"
    else:
        time_display = f"{processing_duration:.1f}s"
    
    return {
        "version": "structured_result_v1",
        
        # V2 blocked status
        "validation_blocked": True,
        "validation_status": "blocked",
        
        # Gate result
        "gate_result": v2_gate_result.to_dict(),
        
        # Extraction summary
        "extraction_summary": {
            "completeness": round(v2_gate_result.completeness * 100, 1),
            "critical_completeness": round(v2_gate_result.critical_completeness * 100, 1),
            "missing_critical": v2_gate_result.missing_critical,
            "missing_required": v2_gate_result.missing_required,
        },
        
        # LC baseline (partial data)
        "lc_baseline": {
            "lc_number": v2_baseline.lc_number.value if v2_baseline else None,
            "amount": v2_baseline.amount.value if v2_baseline else None,
            "currency": v2_baseline.currency.value if v2_baseline else None,
            "applicant": v2_baseline.applicant.value if v2_baseline else None,
            "beneficiary": v2_baseline.beneficiary.value if v2_baseline else None,
            "extraction_completeness": round(v2_baseline.extraction_completeness * 100, 1) if v2_baseline else 0,
            "critical_completeness": round(v2_baseline.critical_completeness * 100, 1) if v2_baseline else 0,
        },
        
        # Issues (blocking issues)
        "issues": blocking_issues,
        
        # Documents
        "documents_structured": docs_structured,
        
        # Processing summary - count ACTUAL extraction results
        "processing_summary": {
            "total_documents": len(documents),
            "successful_extractions": sum(1 for d in documents if d.get("extraction_status") == "success"),
            "failed_extractions": sum(1 for d in documents if d.get("extraction_status") in ("failed", "error", "empty")),
            "partial_extractions": sum(1 for d in documents if d.get("extraction_status") in ("text_only", "partial")),
            "total_issues": len(blocking_issues),
            "compliance_rate": 0,  # 0 because validation is blocked
            "processing_time_seconds": round(processing_duration, 2),
            "processing_time_display": time_display,
            "severity_breakdown": {
                "critical": len(blocking_issues),
                "major": 0,
                "medium": 0,
                "minor": 0,
            },
        },
        
        # Analytics
        "analytics": {
            "extraction_accuracy": round(v2_gate_result.completeness * 100) if v2_gate_result else 0,
            "lc_compliance_score": 0,
            "compliance_level": "blocked",
            "compliance_cap_reason": v2_gate_result.block_reason,
            "customs_ready_score": 0,
            "documents_processed": len(documents),
            "issue_counts": {
                "critical": len(blocking_issues),
                "major": 0,
                "medium": 0,
                "minor": 0,
            },
            "document_risk": [],
        },
        
        # Timeline
        "timeline": [
            {
                "title": "Documents Uploaded",
                "status": "completed",
                "description": f"{len(documents)} documents received",
            },
            {
                "title": "LC Extraction",
                "status": "error",
                "description": v2_gate_result.block_reason or "Extraction failed",
            },
            {
                "title": "Validation",
                "status": "blocked",
                "description": "Validation blocked due to missing LC data",
            },
        ],
        
        # LC structured (minimal)
        "lc_structured": {
            "mt700": {"blocks": {}, "raw_text": None, "version": "mt700_v1"},
            "goods": [],
            "clauses": [],
            "timeline": [],
        },
        
        # Type info
        "lc_type": lc_type,
        "lc_type_reason": "Blocked - LC extraction incomplete",
        "lc_type_confidence": 0,
        
        # Customs (empty)
        "customs_pack": None,
        "ai_enrichment": None,
    }


def _build_lc_baseline_from_context(lc_context: Dict[str, Any]) -> LCBaseline:
    """
    Build LCBaseline from extracted LC context.
    
    This is the bridge between the legacy extraction and the v2 validation pipeline.
    Supports both flat lc_context fields and nested mt700 blocks.
    """
    from app.services.extraction.lc_baseline import (
        LCBaseline, FieldResult, FieldPriority, ExtractionStatus,
        PartyInfo, AmountInfo, PortInfo,
    )
    
    baseline = LCBaseline()
    
    # Extract MT700 blocks if present
    mt700 = lc_context.get("mt700", {})
    blocks = mt700.get("blocks", {}) if isinstance(mt700, dict) else {}
    
    # Helper to set field with proper status
    def set_field(field_result: FieldResult, value: Any, confidence: float = 0.8, source: str = "context"):
        if value is not None and value != "" and value != {}:
            field_result.value = value
            field_result.status = ExtractionStatus.EXTRACTED
            field_result.confidence = confidence
            field_result.source = source
        else:
            field_result.status = ExtractionStatus.MISSING
            field_result.confidence = 0.0
    
    # Helper to get value from multiple keys
    def get_value(*keys, from_blocks=False):
        for key in keys:
            if from_blocks and key in blocks:
                return blocks[key]
            if key in lc_context:
                val = lc_context[key]
                if val is not None and val != "":
                    return val
        return None
    
    # =====================================================================
    # LC Number (MT700 Field 20)
    # =====================================================================
    lc_number = get_value("number", "lc_number", "documentaryCredit", "doc_credit_number")
    if not lc_number:
        lc_number = blocks.get("20")  # MT700 field 20
    set_field(baseline.lc_number, lc_number)
    
    # =====================================================================
    # LC Type
    # =====================================================================
    lc_type = get_value("lc_type", "form_of_doc_credit", "type")
    if not lc_type:
        lc_type = blocks.get("40A")  # MT700 field 40A - Form of Documentary Credit
    set_field(baseline.lc_type, lc_type)
    
    # =====================================================================
    # Amount (MT700 Field 32B)
    # =====================================================================
    amount_raw = get_value("amount", "credit_amount", "value")
    currency = get_value("currency", "ccy")
    
    if not amount_raw and blocks.get("32B"):
        # Parse MT700 32B: "USD100000.00"
        field_32b = blocks["32B"]
        if isinstance(field_32b, str) and len(field_32b) >= 3:
            currency = field_32b[:3]
            try:
                amount_raw = float(field_32b[3:].replace(",", ""))
            except ValueError:
                amount_raw = field_32b[3:]
    
    # Parse amount value
    amount_value = None
    if amount_raw:
        if isinstance(amount_raw, dict):
            amount_value = amount_raw.get("value")
            if not currency:
                currency = amount_raw.get("currency")
        elif isinstance(amount_raw, (int, float)):
            amount_value = float(amount_raw)
        elif isinstance(amount_raw, str):
            try:
                amount_value = float(amount_raw.replace(",", ""))
            except ValueError:
                pass
    
    set_field(baseline.amount, amount_value)
    
    # Currency field
    set_field(baseline.currency, currency)
    
    # Store structured amount info
    if amount_value is not None or currency:
        baseline._amount_info = AmountInfo(value=amount_value, currency=currency)
    
    # =====================================================================
    # Applicant (MT700 Field 50)
    # =====================================================================
    applicant = get_value("applicant", "applicant_name", "buyer")
    if not applicant:
        applicant = blocks.get("50")  # MT700 field 50
    
    if applicant:
        if isinstance(applicant, dict):
            baseline._applicant_info = PartyInfo(
                name=applicant.get("name"),
                address=applicant.get("address"),
                country=applicant.get("country"),
            )
            applicant = applicant.get("name")
        elif isinstance(applicant, str):
            baseline._applicant_info = PartyInfo(name=applicant)
    set_field(baseline.applicant, applicant)
    
    # =====================================================================
    # Beneficiary (MT700 Field 59)
    # =====================================================================
    beneficiary = get_value("beneficiary", "beneficiary_name", "seller")
    if not beneficiary:
        beneficiary = blocks.get("59")  # MT700 field 59
    
    if beneficiary:
        if isinstance(beneficiary, dict):
            baseline._beneficiary_info = PartyInfo(
                name=beneficiary.get("name"),
                address=beneficiary.get("address"),
                country=beneficiary.get("country"),
            )
            beneficiary = beneficiary.get("name")
        elif isinstance(beneficiary, str):
            baseline._beneficiary_info = PartyInfo(name=beneficiary)
    set_field(baseline.beneficiary, beneficiary)
    
    # =====================================================================
    # Banks
    # =====================================================================
    issuing_bank = get_value("issuing_bank", "issuer", "issuing_bank_name")
    if not issuing_bank:
        issuing_bank = blocks.get("52A") or blocks.get("52D")  # MT700 field 52
    set_field(baseline.issuing_bank, issuing_bank)
    
    advising_bank = get_value("advising_bank", "advising_bank_name")
    if not advising_bank:
        advising_bank = blocks.get("57A") or blocks.get("57D")  # MT700 field 57
    set_field(baseline.advising_bank, advising_bank)
    
    # =====================================================================
    # Dates (MT700 Fields 31C, 31D, 44C)
    # =====================================================================
    issue_date = get_value("issue_date", "date_of_issue")
    if not issue_date:
        issue_date = blocks.get("31C")  # MT700 field 31C - Date of Issue
    set_field(baseline.issue_date, issue_date)
    
    expiry_date = get_value("expiry_date", "expiry", "validity_date")
    if not expiry_date:
        expiry_date = blocks.get("31D")  # MT700 field 31D - Date and Place of Expiry
    set_field(baseline.expiry_date, expiry_date)
    
    latest_shipment = get_value("latest_shipment", "latest_shipment_date", "shipment_date")
    if not latest_shipment:
        latest_shipment = blocks.get("44C")  # MT700 field 44C - Latest Date of Shipment
    set_field(baseline.latest_shipment, latest_shipment)
    
    # =====================================================================
    # Ports (MT700 Fields 44E, 44F)
    # =====================================================================
    port_of_loading = get_value("port_of_loading", "loading_port", "pol")
    if not port_of_loading:
        port_of_loading = blocks.get("44E")  # MT700 field 44E - Port of Loading
    
    if port_of_loading:
        if isinstance(port_of_loading, dict):
            baseline._port_of_loading_info = PortInfo(
                name=port_of_loading.get("name") or port_of_loading.get("port"),
                country=port_of_loading.get("country"),
            )
            port_of_loading = baseline._port_of_loading_info.name
        elif isinstance(port_of_loading, str):
            baseline._port_of_loading_info = PortInfo(name=port_of_loading)
    set_field(baseline.port_of_loading, port_of_loading)
    
    port_of_discharge = get_value("port_of_discharge", "discharge_port", "pod")
    if not port_of_discharge:
        port_of_discharge = blocks.get("44F")  # MT700 field 44F - Port of Discharge
    
    if port_of_discharge:
        if isinstance(port_of_discharge, dict):
            baseline._port_of_discharge_info = PortInfo(
                name=port_of_discharge.get("name") or port_of_discharge.get("port"),
                country=port_of_discharge.get("country"),
            )
            port_of_discharge = baseline._port_of_discharge_info.name
        elif isinstance(port_of_discharge, str):
            baseline._port_of_discharge_info = PortInfo(name=port_of_discharge)
    set_field(baseline.port_of_discharge, port_of_discharge)
    
    # =====================================================================
    # Goods Description (MT700 Field 45A)
    # =====================================================================
    goods_description = get_value("goods_description", "description", "goods", "merchandise")
    if not goods_description:
        goods_description = blocks.get("45A")  # MT700 field 45A - Description of Goods
    
    # Handle goods as list of dicts or strings
    if isinstance(goods_description, list):
        desc_parts = []
        for g in goods_description:
            if isinstance(g, dict):
                # Extract description from goods item dict
                desc = g.get("description") or g.get("line") or g.get("text") or ""
                hs = g.get("hs_code", "")
                qty = g.get("quantity", {})
                qty_str = ""
                if isinstance(qty, dict) and qty.get("value"):
                    qty_str = f", QTY: {qty.get('value')} {qty.get('unit', 'PCS')}"
                elif qty:
                    qty_str = f", QTY: {qty}"
                if desc:
                    item_desc = f"{desc}{' HS: ' + hs if hs else ''}{qty_str}"
                    desc_parts.append(item_desc)
            elif isinstance(g, str) and g.strip():
                desc_parts.append(g.strip())
        goods_description = "\n".join(desc_parts) if desc_parts else None
    set_field(baseline.goods_description, goods_description)
    
    # =====================================================================
    # Incoterm (often in goods or separate field)
    # =====================================================================
    incoterm = get_value("incoterm", "trade_terms", "delivery_terms")
    set_field(baseline.incoterm, incoterm, confidence=0.6)
    
    # =====================================================================
    # Documents Required (MT700 Field 46A)
    # =====================================================================
    documents_required = get_value("documents_required", "required_documents")
    if not documents_required:
        documents_required = blocks.get("46A")  # MT700 field 46A - Documents Required
    
    if documents_required:
        if isinstance(documents_required, list):
            baseline._documents_list = documents_required
        elif isinstance(documents_required, str):
            baseline._documents_list = [documents_required]
    set_field(baseline.documents_required, documents_required)
    
    # =====================================================================
    # Additional Conditions (MT700 Field 47A)
    # =====================================================================
    additional_conditions = get_value("additional_conditions", "conditions")
    if not additional_conditions:
        additional_conditions = blocks.get("47A")  # MT700 field 47A - Additional Conditions
    
    if additional_conditions:
        if isinstance(additional_conditions, list):
            baseline._conditions_list = additional_conditions
        elif isinstance(additional_conditions, str):
            baseline._conditions_list = [additional_conditions]
    set_field(baseline.additional_conditions, additional_conditions)
    
    # =====================================================================
    # UCP Reference
    # =====================================================================
    ucp_reference = get_value("ucp_reference", "applicable_rules")
    if not ucp_reference:
        ucp_reference = blocks.get("40E")  # MT700 field 40E - Applicable Rules
    set_field(baseline.ucp_reference, ucp_reference)
    
    # Log extraction summary
    logger.info(
        "LCBaseline from context: completeness=%.1f%% critical=%.1f%% missing_critical=%s",
        baseline.extraction_completeness * 100,
        baseline.critical_completeness * 100,
        [f.field_name for f in baseline.get_missing_critical()],
    )
    
    return baseline


def _summarize_document_statuses(documents: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"success": 0, "warning": 0, "error": 0}
    for doc in documents:
        status = (doc.get("status") or "success").lower()
        if status not in counts:
            counts[status] = 0
        counts[status] += 1
    return counts


def _build_processing_summary(
    document_summaries: List[Dict[str, Any]],
    processing_seconds: float,
    total_discrepancies: int,
) -> Dict[str, Any]:
    status_counts = _summarize_document_statuses(document_summaries)
    total_docs = len(document_summaries)
    verified = status_counts.get("success", 0)
    warnings = status_counts.get("warning", 0)
    errors = status_counts.get("error", 0)
    compliance_rate = 0
    if total_docs:
        compliance_rate = max(0, round((verified / total_docs) * 100))

    # Calculate extraction quality from OCR confidence
    confidences = [
        doc.get("ocrConfidence") 
        for doc in document_summaries 
        if isinstance(doc.get("ocrConfidence"), (int, float))
    ]
    if confidences:
        extraction_quality = round(sum(confidences) / len(confidences) * 100)
    else:
        # Fallback: estimate quality based on status distribution
        extraction_quality = max(
            80, 
            100 - warnings * 5 - errors * 10
        )

    # Convert processing time to milliseconds
    processing_time_ms = round(processing_seconds * 1000)

    return {
        # --- Document counts ---
        "documents": total_docs,  # backward compatibility
        "documents_found": total_docs,  # Frontend expects this field
        "total_documents": total_docs,  # Explicit field for frontend
        
        # --- Validation/Extraction ---
        "verified": verified,
        "warnings": warnings,
        "errors": errors,
        "successful_extractions": verified,  # Frontend checks this field
        "failed_extractions": errors,  # Frontend checks this field
        "compliance_rate": compliance_rate,
        "processing_time_seconds": round(processing_seconds, 2),
        "processing_time_display": _format_duration(processing_seconds),
        "processing_time_ms": processing_time_ms,  # NEW — milliseconds version
        "extraction_quality": extraction_quality,  # NEW — OCR quality score (0-100)
        "discrepancies": total_discrepancies,
        "status_counts": status_counts,
    }


def _build_bank_submission_verdict(
    critical_count: int,
    major_count: int,
    minor_count: int,
    compliance_score: float,
    all_issues: List[Any],
) -> Dict[str, Any]:
    """
    Build a bank submission verdict with GO/NO-GO recommendation.
    
    This helps exporters understand if their documents are ready
    for bank submission or what actions are required first.
    """
    # Determine verdict
    if critical_count > 0:
        verdict = "REJECT"
        verdict_color = "red"
        verdict_message = "Documents will be REJECTED by bank"
        recommendation = "Do NOT submit to bank until critical issues are resolved."
    elif major_count > 2:
        verdict = "HOLD"
        verdict_color = "orange"
        verdict_message = "High risk of discrepancy notice"
        recommendation = "Consider resolving major issues before submission to avoid discrepancy fees."
    elif major_count > 0:
        verdict = "CAUTION"
        verdict_color = "yellow"
        verdict_message = "Minor corrections recommended"
        recommendation = "Documents may be accepted with discrepancy notice. Consider corrections."
    else:
        verdict = "SUBMIT"
        verdict_color = "green"
        verdict_message = "Documents appear compliant"
        recommendation = "Documents are ready for bank submission."
    
    # Build action items from critical and major issues
    action_items = []
    for issue in all_issues:
        if hasattr(issue, 'severity'):
            severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
        elif isinstance(issue, dict):
            severity = issue.get("severity", "")
        else:
            continue
        
        if severity in ["critical", "major"]:
            if hasattr(issue, 'title'):
                title = issue.title
            elif isinstance(issue, dict):
                title = issue.get("title", issue.get("message", "Unknown issue"))
            else:
                continue
            
            if hasattr(issue, 'suggestion'):
                action = issue.suggestion
            elif isinstance(issue, dict):
                action = issue.get("suggestion", issue.get("suggested_fix", "Review and correct"))
            else:
                action = "Review and correct"
            
            action_items.append({
                "priority": "critical" if severity == "critical" else "high",
                "issue": title,
                "action": action,
            })
    
    # Calculate estimated fee if discrepant
    discrepancy_fee = 75.00 if (critical_count + major_count) > 0 else 0.00
    
    return {
        "verdict": verdict,
        "verdict_color": verdict_color,
        "verdict_message": verdict_message,
        "recommendation": recommendation,
        "can_submit": verdict in ["SUBMIT", "CAUTION"],
        "will_be_rejected": verdict == "REJECT",
        "estimated_discrepancy_fee": discrepancy_fee,
        "issue_summary": {
            "critical": critical_count,
            "major": major_count,
            "minor": minor_count,
            "total": critical_count + major_count + minor_count,
        },
        "action_items": action_items[:5],  # Top 5 action items
        "action_items_count": len(action_items),
    }


def _build_processing_timeline(
    document_summaries: List[Dict[str, Any]],
    processing_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    doc_count = len(document_summaries)
    now = datetime.utcnow()
    stages = [
        ("Documents Uploaded", "success", f"{doc_count} document(s) received"),
        ("LC Terms Extracted", "success", "Structured LC context generated"),
        ("Document Cross-Check", "success", "Validated trade docs against LC terms"),
        (
            "Customs Pack Generated",
            "warning" if processing_summary.get("warnings") else "success",
            "Bundle prepared for customs clearance",
        ),
    ]

    for index, (title, status, description) in enumerate(stages):
        events.append(
            {
                "title": title,
                "status": status,
                "description": description,
                "timestamp": (now - timedelta(seconds=max(5, (len(stages) - index) * 5))).isoformat() + "Z",
            }
        )
    return events


async def _rewrite_failed_results(
    issues: List[Dict[str, Any]],
    context_snapshot: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not issues:
        return issues

    rewritten: List[Dict[str, Any]] = []
    for issue in issues:
        try:
            rewrite_payload = await rewrite_issue(issue, context_snapshot)
            if rewrite_payload:
                _apply_issue_rewrite(issue, rewrite_payload)
        except Exception as exc:
            logger.warning("Issue rewrite failed for %s: %s", issue.get("rule"), exc)
        rewritten.append(issue)
    return rewritten


def _apply_issue_rewrite(issue: Dict[str, Any], rewrite_payload: Dict[str, Any]) -> None:
    title = rewrite_payload.get("title")
    if title:
        issue["title"] = title

    description = rewrite_payload.get("description")
    if description:
        issue["description"] = description
        issue["message"] = description

    expected = rewrite_payload.get("expected")
    if expected is not None:
        issue["expected"] = expected

    found = rewrite_payload.get("found")
    if found is not None:
        issue["found"] = found
        issue["actual"] = found

    suggestion = rewrite_payload.get("suggested_fix") or rewrite_payload.get("suggestion")
    if suggestion is not None:
        issue["suggested_fix"] = suggestion
        issue["suggestion"] = suggestion

    documents = rewrite_payload.get("documents")
    if documents:
        issue["documents"] = documents
        issue["document_names"] = documents

    priority = rewrite_payload.get("priority")
    severity = _priority_to_severity(priority, issue.get("severity"))
    issue["severity"] = severity
    if priority:
        issue["priority"] = priority


def _priority_to_severity(priority: Optional[str], fallback: Optional[str]) -> str:
    candidate = (priority or fallback or "minor").lower()
    if candidate in {"critical", "high"}:
        return "critical"
    if candidate in {"major", "medium", "warn", "warning"}:
        return "major"
    return "minor"


def _normalize_issue_severity(value: Optional[str]) -> str:
    """Normalize issue severity to standard values: critical, major, minor."""
    if not value:
        return "minor"
    normalized = value.lower()
    if normalized in {"critical", "high"}:
        return "critical"
    if normalized in {"major", "medium", "warn", "warning"}:
        return "major"
    return "minor"


def _format_deterministic_issue(result: Dict[str, Any]) -> Dict[str, Any]:
    issue_id = str(result.get("rule") or result.get("rule_id") or uuid4())
    severity = _normalize_issue_severity(result.get("severity"))
    priority = result.get("priority") or severity
    documents = _extract_document_names(result)
    expected = result.get("expected") or result.get("expected_value")
    found = result.get("found") or result.get("actual_value")
    suggestion = result.get("suggestion")
    expected_outcome = result.get("expected_outcome") or {}
    if not suggestion:
        suggestion = expected_outcome.get("invalid") or expected_outcome.get("message")

    return {
        "id": issue_id,
        "title": result.get("title") or result.get("rule") or "Rule Breach",
        "severity": severity,
        "priority": priority,
        "documents": documents,
        "description": result.get("message") or "",
        "expected": _coerce_issue_value(expected),
        "found": _coerce_issue_value(found),
        "suggested_fix": _coerce_issue_value(suggestion),
        "ucp_reference": _coerce_issue_value(result.get("rule")),
    }


def _coerce_issue_value(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return str(value)


def _build_document_lookup(
    documents: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]]]:
    meta: Dict[str, Dict[str, Any]] = {}
    key_map: Dict[str, List[str]] = {}

    for doc in documents:
        doc_id = doc.get("id")
        if not doc_id:
            continue
        display_name = doc.get("name") or doc.get("type") or doc.get("documentType") or doc_id
        meta[doc_id] = {
            "document_id": doc_id,
            "name": doc.get("name"),
            "display": display_name,
            "type": doc.get("documentType") or doc.get("type"),
        }
        candidate_keys = {
            _normalize_doc_match_key(display_name),
            _normalize_doc_match_key(doc.get("name")),
            _normalize_doc_match_key(_strip_extension(doc.get("name"))),
            _normalize_doc_match_key(doc.get("documentType")),
            _normalize_doc_match_key(doc.get("type")),
        }
        for key in filter(None, candidate_keys):
            key_map.setdefault(key, []).append(doc_id)

    return meta, key_map


def _match_issue_documents(
    issue: Dict[str, Any],
    doc_meta: Dict[str, Dict[str, Any]],
    key_map: Dict[str, List[str]],
) -> Tuple[List[str], List[str]]:
    matched: List[str] = []
    matched_ids: List[str] = []

    requested = issue.get("documents") or []
    if isinstance(requested, str):
        requested = [requested]

    for raw in requested:
        key = _normalize_doc_match_key(raw)
        if not key:
            continue
        for doc_id in key_map.get(key, []):
            if doc_id in matched_ids:
                continue
            meta = doc_meta.get(doc_id)
            if not meta:
                continue
            matched.append(meta.get("name") or meta.get("display") or meta.get("type") or doc_id)
            matched_ids.append(doc_id)

    return matched, matched_ids


def _normalize_doc_match_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]", "", str(value).lower())
    return normalized or None


def _strip_extension(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if "." not in value:
        return value
    return value.rsplit(".", 1)[0]


def _build_documents_section(
    documents: List[Dict[str, Any]],
    issue_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    section: List[Dict[str, Any]] = []
    for doc in documents:
        doc_id = doc.get("id") or str(uuid4())
        extraction_status = (
            doc.get("extractionStatus")
            or doc.get("extraction_status")
            or doc.get("status")
            or "unknown"
        )
        section.append(
            {
                "document_id": doc_id,
                "document_type": _humanize_doc_type(doc.get("documentType") or doc.get("type")),
                "filename": doc.get("name"),
                "extraction_status": extraction_status,
                "extracted_fields": _filter_user_facing_fields(doc.get("extractedFields") or doc.get("extracted_fields") or {}),
                "issues_count": issue_counts.get(doc_id, 0),
            }
        )
    return section


def _compose_processing_summary(
    documents: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    severity_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    total_docs = len(documents)
    successful = sum(
        1 for doc in documents if (doc.get("extraction_status") or "").lower() == "success"
    )
    failed = total_docs - successful
    severity_breakdown = severity_counts or _count_issue_severity(issues)

    return {
        "total_documents": total_docs,
        "successful_extractions": successful,
        "failed_extractions": failed,
        "total_issues": len(issues),
        "severity_breakdown": severity_breakdown,
    }


def _count_issue_severity(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = _normalize_issue_severity(issue.get("severity"))
        if severity in counts:
            counts[severity] += 1
        else:
            counts["minor"] += 1
    return counts


def _build_analytics_section(
    summary: Dict[str, Any],
    documents: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    severity = summary.get("severity_breakdown") or {}
    compliance_score = max(
        0,
        100 - severity.get("critical", 0) * 30 - severity.get("major", 0) * 20 - severity.get("minor", 0) * 5,
    )

    document_risk = []
    for doc in documents:
        count = doc.get("issues_count", 0)
        if count >= 3:
            risk = "high"
        elif count >= 1:
            risk = "medium"
        else:
            risk = "low"
        document_risk.append(
            {
                "document_id": doc.get("document_id"),
                "filename": doc.get("filename"),
                "risk": risk,
            }
        )

    return {
        "compliance_score": compliance_score,
        "issue_counts": severity,
        "document_risk": document_risk,
    }


def _build_timeline_entries() -> List[Dict[str, str]]:
    return [
        {"label": "Upload Received", "status": "complete"},
        {"label": "OCR Complete", "status": "complete"},
        {"label": "Deterministic Rules", "status": "complete"},
        {"label": "Issue Review Ready", "status": "complete"},
    ]

def _build_document_processing_analytics(
    document_summaries: List[Dict[str, Any]],
    processing_summary: Dict[str, Any],
) -> Dict[str, Any]:
    status_counts = processing_summary.get("status_counts", {})
    confidences = [doc.get("ocrConfidence") for doc in document_summaries if isinstance(doc.get("ocrConfidence"), (int, float))]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        extraction_accuracy = round(avg_confidence * 100)
    else:
        extraction_accuracy = max(80, 100 - status_counts.get("warning", 0) * 5 - status_counts.get("error", 0) * 10)

    document_processing = []
    for index, doc in enumerate(document_summaries):
        extracted_fields = doc.get("extractedFields") or {}
        processing_time = 0.2 + max(0, len(extracted_fields)) * 0.05 + index * 0.02
        ocr_confidence = doc.get("ocrConfidence")
        if isinstance(ocr_confidence, (int, float)):
            accuracy_score = round(ocr_confidence * 100)
        else:
            accuracy_score = 98 if doc.get("status") == "success" else 90

        # Get issue count from document summary (populated by _build_document_summaries)
        issue_count = doc.get("discrepancyCount", 0) or 0
        
        # Derive risk label from issue count for better accuracy
        if issue_count >= 3:
            risk_label = "high"
        elif issue_count >= 1:
            risk_label = "medium"
        else:
            risk_label = "low"
        
        compliance_label = "High" if doc.get("status") == "success" else "Medium" if doc.get("status") == "warning" else "Low"

        document_processing.append(
            {
                "name": doc.get("name"),
                "type": doc.get("type"),
                "status": doc.get("status"),
                "processing_time_seconds": round(processing_time, 2),
                "accuracy_score": accuracy_score,
                "compliance_level": compliance_label,
                "risk_level": risk_label,
                "issues": issue_count,  # FIX: Include issue count for frontend
            }
        )

    # Count total issues from documents and discrepancies
    total_doc_issues = sum(doc.get("discrepancyCount", 0) or 0 for doc in document_summaries)
    total_discrepancies = processing_summary.get("discrepancies", 0)
    total_issues = max(total_doc_issues, total_discrepancies)
    
    performance_insights = [
        f"{len(document_summaries)}/{processing_summary.get('documents', 0)} documents extracted successfully",
        f"{total_issues} issues detected",
        f"Compliance score {processing_summary.get('compliance_rate', 0)}%",
    ]

    return {
        "extraction_accuracy": extraction_accuracy,
        "lc_compliance_score": processing_summary.get("compliance_rate", 0),
        "customs_ready_score": max(
            0,
            processing_summary.get("compliance_rate", 0) - status_counts.get("warning", 0) * 2 - status_counts.get("error", 0) * 5,
        ),
        "documents_processed": processing_summary.get("documents", 0),
        "document_status_distribution": status_counts,
        "document_processing": document_processing,
        "performance_insights": performance_insights,
        "processing_time_display": processing_summary.get("processing_time_display"),
    }


def _format_duration(duration_seconds: float) -> str:
    if not duration_seconds:
        return "0s"
    minutes = duration_seconds / 60
    if minutes >= 1:
        return f"{minutes:.1f} minutes"
    return f"{duration_seconds:.1f} seconds"


def _fields_to_lc_context(fields: List[Any]) -> Dict[str, Any]:
    """Convert extracted LC fields into nested context for rule evaluation."""
    lc_context: Dict[str, Any] = {}

    for field in fields:
        value = (field.value or "").strip()
        if not value:
            continue

        name = field.field_name
        if name == "lc_number":
            lc_context["number"] = value
        elif name == "issue_date":
            _set_nested_value(lc_context, ("dates", "issue"), value)
        elif name == "expiry_date":
            _set_nested_value(lc_context, ("dates", "expiry"), value)
        elif name == "latest_shipment_date":
            _set_nested_value(lc_context, ("dates", "latest_shipment"), value)
        elif name == "lc_amount":
            _set_nested_value(lc_context, ("amount", "value"), value)
        elif name == "applicant":
            _set_nested_value(lc_context, ("applicant", "name"), value)
        elif name == "applicant_address":
            _set_nested_value(lc_context, ("applicant", "address"), value)
        elif name == "applicant_country":
            _set_nested_value(lc_context, ("applicant", "country"), value)
        elif name == "beneficiary":
            _set_nested_value(lc_context, ("beneficiary", "name"), value)
        elif name == "beneficiary_address":
            _set_nested_value(lc_context, ("beneficiary", "address"), value)
        elif name == "beneficiary_country":
            _set_nested_value(lc_context, ("beneficiary", "country"), value)
        elif name == "port_of_loading":
            _set_nested_value(lc_context, ("ports", "loading"), value)
        elif name == "port_of_discharge":
            _set_nested_value(lc_context, ("ports", "discharge"), value)
        elif name == "goods_description":
            lc_context["goods_description"] = value
        elif name == "goods_items":
            try:
                lc_context["goods_items"] = json.loads(value)
            except (TypeError, ValueError):
                lc_context["goods_items"] = value
        elif name == "incoterm":
            lc_context["incoterm"] = value
        elif name == "ucp_reference":
            lc_context["ucp_reference"] = value
        elif name == "additional_conditions":
            lc_context["additional_conditions"] = value
        else:
            lc_context[name] = value

    return lc_context


def _fields_to_flat_context(fields: List[Any]) -> Dict[str, Any]:
    """Convert generic extracted fields to a flat dictionary."""
    context: Dict[str, Any] = {}
    for field in fields:
        value = (field.value or "").strip()
        if not value:
            continue
        context[field.field_name] = value
    return context


def _parse_json_if_possible(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON string in LC payload; leaving raw text")
                return value
    return value


def _coerce_goods_items(value: Any) -> List[Dict[str, Any]]:
    parsed = _parse_json_if_possible(value)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _normalize_lc_payload_structures(lc_payload: Any) -> Dict[str, Any]:
    parsed = _parse_json_if_possible(lc_payload)
    if not isinstance(parsed, dict):
        return {}

    nested_keys = (
        "applicant",
        "beneficiary",
        "ports",
        "dates",
        "amount",
        "issuing_bank",
        "advising_bank",
    )
    for key in nested_keys:
        if key in parsed:
            nested = _parse_json_if_possible(parsed[key])
            if isinstance(nested, dict):
                parsed[key] = nested

    if "goods_items" in parsed:
        parsed["goods_items"] = _coerce_goods_items(parsed.get("goods_items"))

    return parsed


def _set_nested_value(container: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    current = container
    for segment in path[:-1]:
        current = current.setdefault(segment, {})
    current[path[-1]] = value


@router.get("/customs-pack/{session_id}")
async def generate_customs_pack(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Build the customs pack ZIP, upload to S3, and return a signed URL.
    The FE should read .customs_pack.download_url and redirect the browser to it.
    """
    from uuid import UUID
    
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    session = (
        db.query(ValidationSession)
        .filter(
            ValidationSession.id == session_uuid,
            ValidationSession.deleted_at.is_(None)
        )
        .first()
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation session not found"
        )
    
    # Check access - user must own the session or be admin
    if session.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Validate session has been processed
    validation_results = session.validation_results or {}
    if not validation_results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Session has no validation_results yet. Please run validation first."
        )
    
    # Build the customs pack
    try:
        builder = CustomsPackBuilderFull()
        result = builder.build_and_upload(db=db, session_id=session_id)
    except ValueError as e:
        # Session not found or invalid
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to build customs pack for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate customs pack: {str(e)}"
        )
    
    return {"customs_pack": result}
