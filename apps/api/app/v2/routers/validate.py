"""
V2 Validation API Router

Parallel to V1 - activated via feature flag.

Target: <30 seconds, 99% accuracy
"""

import asyncio
import logging
import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from pydantic import BaseModel

from app.core.security import get_current_user, get_optional_user
from app.models.user import User

from ..core.types import (
    LCopilotV2Response, DocumentResult, Issue, Amendment,
    Verdict, ComplianceInfo, QualityMetrics, AuditInfo,
    DocumentQualityInfo, DocumentRegions, SanctionsStatus,
    IssueSummary, DocumentType, DocumentQuality
)
from ..core.config import get_v2_config
from ..extraction.intake import DocumentIntake, UploadedDocument
from ..preprocessing.pipeline import PreprocessingPipeline
from ..extraction.smart_extractor import SmartExtractor
from ..validation.engine import ValidationEngineV2
from ..validation.verdict import VerdictCalculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["v2-validation"])


class V2ValidationRequest(BaseModel):
    """Request options for V2 validation."""
    lc_number: Optional[str] = None
    user_type: Optional[str] = "exporter"
    strict_mode: Optional[bool] = False
    include_amendments: Optional[bool] = True
    bank_profile: Optional[str] = None


class V2ValidationResponse(BaseModel):
    """V2 validation response schema."""
    session_id: str
    version: str = "v2"
    processing_time_seconds: float
    
    # Main verdict
    verdict: dict
    
    # Documents
    documents: List[dict]
    
    # Issues with citations
    issues: List[dict]
    
    # Amendments
    amendments: List[dict]
    
    # Extracted data
    extracted_data: dict
    
    # Compliance
    compliance: dict
    
    # Quality metrics
    quality: dict
    
    # Audit info
    audit: dict


@router.post("/validate", response_model=V2ValidationResponse)
async def validate_v2(
    files: List[UploadFile] = File(...),
    lc_number: Optional[str] = Form(None),
    user_type: Optional[str] = Form("exporter"),
    strict_mode: Optional[bool] = Form(False),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    V2 Validation Endpoint
    
    Features:
    - Up to 10 documents
    - <30 second processing
    - 99% accuracy target
    - Every issue has UCP600/ISBP745 citations
    - Smart AI routing based on document quality
    - Handwriting and stamp detection
    
    Returns:
        LCopilotV2Response with verdict, issues, and extracted data
    """
    session_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    config = get_v2_config()
    
    logger.info(f"V2 Validation started: session={session_id}, files={len(files)}")
    
    try:
        # =====================================================================
        # STAGE 1: INTAKE (0-2 seconds)
        # =====================================================================
        stage_start = time.perf_counter()
        
        # Convert files to UploadedDocument
        uploaded = []
        for f in files:
            content = await f.read()
            uploaded.append(UploadedDocument(
                file_data=content,
                filename=f.filename or "unknown",
                content_type=f.content_type or "application/octet-stream",
                size=len(content),
            ))
        
        # Classify documents
        intake = DocumentIntake()
        classified = await intake.intake(uploaded)
        
        intake_time = time.perf_counter() - stage_start
        logger.info(f"Stage 1 (Intake): {len(classified)} docs in {intake_time:.2f}s")
        
        # =====================================================================
        # STAGE 2: PREPROCESSING (2-8 seconds)
        # =====================================================================
        stage_start = time.perf_counter()
        
        pipeline = PreprocessingPipeline()
        preprocessed = await pipeline.process_all(classified)
        
        preprocess_time = time.perf_counter() - stage_start
        logger.info(f"Stage 2 (Preprocess): {preprocess_time:.2f}s")
        
        # =====================================================================
        # STAGE 3: AI EXTRACTION (8-18 seconds)
        # =====================================================================
        stage_start = time.perf_counter()
        
        # Prepare extraction inputs
        extraction_inputs = [
            (
                doc.id,
                doc.document_type,
                doc.full_text,
                doc.quality_score,
                doc.has_handwriting,
            )
            for doc in preprocessed
        ]
        
        extractor = SmartExtractor()
        extractions = await extractor.extract_all(extraction_inputs)
        
        extraction_time = time.perf_counter() - stage_start
        logger.info(f"Stage 3 (Extraction): {extraction_time:.2f}s")
        
        # =====================================================================
        # STAGE 4: VALIDATION (18-25 seconds)
        # =====================================================================
        stage_start = time.perf_counter()
        
        engine = ValidationEngineV2()
        issues, sanctions_status, audit_info = await engine.validate(extractions)
        
        # Calculate verdict
        verdict_calc = VerdictCalculator()
        overall_confidence = (
            sum(e.overall_confidence for e in extractions.values()) / len(extractions)
            if extractions else 0.0
        )
        verdict = verdict_calc.calculate(issues, sanctions_status, overall_confidence)
        
        validation_time = time.perf_counter() - stage_start
        logger.info(f"Stage 4 (Validation): {validation_time:.2f}s")
        
        # =====================================================================
        # STAGE 5: RESPONSE (25-30 seconds)
        # =====================================================================
        stage_start = time.perf_counter()
        
        # Build document results
        doc_results = []
        for doc in preprocessed:
            extraction = extractions.get(doc.id)
            
            doc_results.append({
                "id": doc.id,
                "filename": doc.filename,
                "documentType": doc.document_type.value,
                "quality": {
                    "overall": doc.quality_score,
                    "ocrConfidence": doc.average_ocr_confidence,
                    "category": doc.quality_category.value,
                },
                "regions": {
                    "hasHandwriting": doc.has_handwriting,
                    "hasSignatures": doc.has_signatures,
                    "hasStamps": doc.has_stamps,
                    "handwritingCount": len(doc.handwriting_regions),
                    "signatureCount": len(doc.signature_regions),
                    "stampCount": len(doc.stamp_regions),
                },
                "extracted": {
                    k: {
                        "value": v.value,
                        "confidence": v.confidence,
                        "source": v.source,
                        "providerAgreement": v.provider_agreement,
                        "needsReview": v.needs_review,
                    }
                    for k, v in (extraction.fields if extraction else {}).items()
                },
                "processingTimeMs": doc.total_processing_time_ms,
                "pagesProcessed": len(doc.pages),
                "status": "success" if extraction and extraction.overall_confidence > 0.5 else "partial",
            })
        
        # Build extracted data by type
        extracted_data = {}
        for doc_id, extraction in extractions.items():
            doc_type = extraction.document_type.value
            if doc_type not in extracted_data:
                extracted_data[doc_type] = {}
            
            for field_name, field_conf in extraction.fields.items():
                extracted_data[doc_type][field_name] = {
                    "value": field_conf.value,
                    "confidence": field_conf.confidence,
                    "source": field_conf.source,
                    "providerAgreement": field_conf.provider_agreement,
                    "needsReview": field_conf.needs_review,
                }
        
        # Build compliance info
        compliance_score = 100 - (
            verdict.issue_summary.critical * 25 +
            verdict.issue_summary.major * 10 +
            verdict.issue_summary.minor * 2
        )
        compliance_score = max(0, min(100, compliance_score))
        
        compliance = {
            "sanctionsStatus": sanctions_status.to_dict(),
            "ucpCompliance": compliance_score,
            "isbpCompliance": compliance_score,
            "overallScore": compliance_score,
        }
        
        # Build quality metrics
        fields_needing_review = []
        for extraction in extractions.values():
            for field_name, field in extraction.fields.items():
                if field.needs_review:
                    fields_needing_review.append(field_name)
        
        poor_docs = [
            doc.filename for doc in preprocessed
            if doc.quality_category in [DocumentQuality.POOR, DocumentQuality.VERY_POOR]
        ]
        
        providers_used = set()
        for extraction in extractions.values():
            providers_used.update(extraction.providers_used)
        
        quality = {
            "overallConfidence": overall_confidence,
            "fieldsNeedingReview": list(set(fields_needing_review)),
            "poorQualityDocuments": poor_docs,
            "handwritingDetected": any(doc.has_handwriting for doc in preprocessed),
            "providersUsed": list(providers_used),
        }
        
        # Build audit
        audit = {
            "rulesEvaluated": audit_info.get("rules_evaluated", 0),
            "rulesPassed": audit_info.get("rules_passed", 0),
            "rulesFailed": len(issues),
            "crossDocChecks": audit_info.get("cross_doc_checks", 0),
            "aiProvidersUsed": list(providers_used),
        }
        
        # Generate amendments for critical/major issues
        amendments = []
        if issues:
            from app.services.amendment_generator import generate_amendment_for_issue
            
            for issue in issues[:5]:  # Top 5 issues
                if issue.can_amend:
                    try:
                        # Get LC data for amendment
                        lc_data = extracted_data.get("letter_of_credit", {})
                        amendment = await generate_amendment_for_issue(issue, lc_data)
                        if amendment:
                            amendments.append(amendment)
                    except Exception as e:
                        logger.warning(f"Amendment generation failed: {e}")
        
        total_time = time.perf_counter() - start_time
        
        response = V2ValidationResponse(
            session_id=session_id,
            version="v2",
            processing_time_seconds=round(total_time, 2),
            verdict=verdict.to_dict(),
            documents=doc_results,
            issues=[i.to_dict() for i in issues],
            amendments=amendments,
            extracted_data=extracted_data,
            compliance=compliance,
            quality=quality,
            audit=audit,
        )
        
        logger.info(
            f"V2 Validation complete: session={session_id}, "
            f"time={total_time:.2f}s, issues={len(issues)}, "
            f"verdict={verdict.status.value}"
        )
        
        # Log stage timing breakdown
        logger.info(
            f"Stage timing: intake={intake_time:.2f}s, preprocess={preprocess_time:.2f}s, "
            f"extraction={extraction_time:.2f}s, validation={validation_time:.2f}s"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"V2 Validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/health")
async def v2_health():
    """V2 pipeline health check."""
    config = get_v2_config()
    
    return {
        "status": "healthy",
        "version": "v2",
        "features": {
            "smart_routing": config.enable_smart_routing,
            "image_enhancement": config.enable_image_enhancement,
            "handwriting_ocr": config.enable_handwriting_ocr,
            "parallel_processing": config.enable_parallel_processing,
        },
        "ai_providers": config.ai.available_providers(),
        "can_ensemble": config.ai.can_ensemble(),
        "performance_targets": {
            "max_processing_seconds": config.performance.max_processing_seconds,
            "target_accuracy": config.performance.target_accuracy,
            "max_documents": config.performance.max_documents,
        },
    }


@router.get("/providers")
async def v2_providers():
    """List available AI providers."""
    config = get_v2_config()
    
    providers = []
    
    if config.ai.openai_api_key:
        providers.append({
            "name": "OpenAI",
            "id": "openai",
            "model": config.ai.openai_model,
            "available": True,
            "best_for": ["structured_data", "json_output"],
        })
    
    if config.ai.anthropic_api_key:
        providers.append({
            "name": "Anthropic Claude",
            "id": "anthropic",
            "model": config.ai.anthropic_model,
            "available": True,
            "best_for": ["accuracy", "reasoning"],
        })
    
    if config.ai.gemini_api_key:
        providers.append({
            "name": "Google Gemini",
            "id": "gemini",
            "model": config.ai.gemini_model,
            "available": True,
            "best_for": ["poor_quality", "handwriting", "multilingual"],
        })
    
    return {
        "providers": providers,
        "ensemble_available": len(providers) >= 2,
    }

