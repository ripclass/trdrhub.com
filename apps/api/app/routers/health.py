"""
Health and stub monitoring endpoints.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..ocr.factory import get_ocr_factory
from ..stubs.models import StubScenarioModel

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/stub-status")
async def get_stub_status() -> Dict:
    """Get current stub mode status and configuration."""
    
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


