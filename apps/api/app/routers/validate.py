from fastapi import APIRouter, HTTPException
from app.services.validator import validate_document


router = APIRouter(prefix="/api/validate", tags=["validation"])


@router.post("/")
async def validate_doc(payload: dict):
    doc_type = payload.get("document_type")
    if not doc_type:
        raise HTTPException(status_code=400, detail="Missing document_type")
    results = validate_document(payload, doc_type)
    return {"status": "ok", "results": results}


