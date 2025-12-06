"""
Health and stub monitoring endpoints.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..config import settings
from ..ocr.factory import get_ocr_factory
from ..stubs.models import StubScenarioModel

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/stub-status")
async def get_stub_status(request: Request) -> Dict:
    """Get current stub mode status and configuration."""

    if not settings.USE_STUBS:
        raise HTTPException(status_code=404, detail="Stub mode disabled")

    if settings.STUB_STATUS_TOKEN:
        provided_token = request.headers.get("X-Stub-Auth") or request.query_params.get("token")
        if provided_token != settings.STUB_STATUS_TOKEN:
            raise HTTPException(status_code=403, detail="Stub access token required")
    else:
        client_host = getattr(request.client, "host", "")
        if client_host not in {"127.0.0.1", "::1", "localhost"}:
            raise HTTPException(status_code=403, detail="Stub diagnostics limited to local access")

    status = {
        "stub_mode_enabled": settings.USE_STUBS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "ocr": "stub" if settings.USE_STUBS else "real",
            "storage": "stub" if settings.USE_STUBS else "real"
        }
    }
    
    if settings.USE_STUBS:
        # Get OCR factory info
        try:
            ocr_factory = get_ocr_factory()
            adapter = await ocr_factory.get_adapter()
            
            if hasattr(adapter, 'get_scenario_info'):
                scenario_info = adapter.get_scenario_info(settings.STUB_SCENARIO)
                status.update({
                    "current_scenario": settings.STUB_SCENARIO,
                    "scenario_info": scenario_info,
                    "error_simulation": {
                        "ocr_failure": settings.STUB_FAIL_OCR,
                        "storage_failure": settings.STUB_FAIL_STORAGE
                    }
                })
        except Exception as e:
            status["ocr_error"] = str(e)
        
        # Get stub storage stats if available
        try:
            from ..stubs.storage_stub import StubS3Service
            stub_storage = StubS3Service()
            storage_stats = stub_storage.get_storage_stats()
            status["storage_stats"] = storage_stats
        except Exception as e:
            status["storage_error"] = str(e)
    
    return status


@router.get("/stub-scenarios")
async def get_available_scenarios() -> Dict:
    """Get list of available stub scenarios."""
    
    if not settings.USE_STUBS:
        raise HTTPException(
            status_code=400,
            detail="Stub mode not enabled"
        )
    
    scenarios = []
    stub_dir = Path(settings.STUB_DATA_DIR)
    
    if not stub_dir.exists():
        return {
            "scenarios": [],
            "error": f"Stub directory {stub_dir} does not exist"
        }
    
    for scenario_file in stub_dir.glob("*.json"):
        try:
            import json
            with open(scenario_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            scenario = StubScenarioModel.parse_obj(data)
            
            scenarios.append({
                "filename": scenario_file.name,
                "name": scenario.scenario_name,
                "description": scenario.description,
                "document_types": [doc.document_type for doc in scenario.documents],
                "expected_discrepancies": scenario.expected_discrepancies,
                "tags": scenario.tags,
                "current": scenario_file.name == settings.STUB_SCENARIO
            })
            
        except Exception as e:
            scenarios.append({
                "filename": scenario_file.name,
                "error": f"Failed to parse: {str(e)}"
            })
    
    return {
        "scenarios": scenarios,
        "current_scenario": settings.STUB_SCENARIO,
        "total_count": len(scenarios)
    }


@router.get("/ensemble-status")
async def get_ensemble_status() -> Dict:
    """
    Get status of AI ensemble extraction providers.
    
    Returns information about which LLM providers are available for
    ensemble extraction and the recommended extraction mode.
    """
    try:
        from ..services.extraction.ensemble_extractor import get_ensemble_status as _get_status
        
        status = _get_status()
        
        # Add configuration info
        status["configuration"] = {
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
            "gemini_configured": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
        }
        
        # Add extraction mode info
        if status["providers_available"] >= 3:
            status["extraction_mode"] = "full_ensemble"
            status["expected_accuracy_boost"] = "+15%"
        elif status["providers_available"] == 2:
            status["extraction_mode"] = "partial_ensemble"
            status["expected_accuracy_boost"] = "+10%"
        else:
            status["extraction_mode"] = "single_provider"
            status["expected_accuracy_boost"] = "baseline"
        
        return status
        
    except ImportError as e:
        return {
            "ensemble_available": False,
            "error": f"Ensemble module not available: {e}",
            "providers_available": 0,
            "providers": [],
            "recommendation": "Install ensemble dependencies",
        }
    except Exception as e:
        return {
            "ensemble_available": False,
            "error": str(e),
            "providers_available": 0,
            "providers": [],
        }


@router.get("/ai-providers")
async def get_ai_providers() -> Dict:
    """
    Get detailed status of all AI providers.
    
    Returns:
        Detailed status for each configured AI provider.
    """
    from ..services.llm_provider import LLMProviderFactory
    
    providers_status = []
    
    # Check OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    providers_status.append({
        "name": "openai",
        "model": os.getenv("LLM_MODEL_VERSION", "gpt-4o-mini"),
        "configured": bool(openai_key),
        "key_prefix": openai_key[:8] + "..." if openai_key else None,
        "cost_per_1m_tokens": {"input": 0.15, "output": 0.60},
    })
    
    # Check Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    providers_status.append({
        "name": "anthropic",
        "model": os.getenv("ANTHROPIC_MODEL_VERSION", "claude-3-haiku-20240307"),
        "configured": bool(anthropic_key),
        "key_prefix": anthropic_key[:8] + "..." if anthropic_key else None,
        "cost_per_1m_tokens": {"input": 0.25, "output": 1.25},
    })
    
    # Check Gemini
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    providers_status.append({
        "name": "gemini",
        "model": os.getenv("GEMINI_MODEL_VERSION", "gemini-1.5-flash"),
        "configured": bool(gemini_key),
        "key_prefix": gemini_key[:8] + "..." if gemini_key else None,
        "cost_per_1m_tokens": {"input": 0.075, "output": 0.30},
    })
    
    configured_count = sum(1 for p in providers_status if p["configured"])
    
    return {
        "providers": providers_status,
        "configured_count": configured_count,
        "ensemble_ready": configured_count >= 2,
        "full_ensemble_ready": configured_count >= 3,
        "primary_provider": os.getenv("LLM_PROVIDER", "openai"),
        "recommendation": (
            "Full ensemble available - maximum accuracy" if configured_count >= 3
            else "Partial ensemble - add more API keys for better accuracy" if configured_count == 2
            else "Single provider only - add API keys for ensemble extraction" if configured_count == 1
            else "No AI providers configured - add at least one API key"
        ),
    }


