"""
Fake S3 endpoints for stub mode file operations.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pathlib import Path

from ..config import settings

# Only create router if stub mode is enabled
if settings.USE_STUBS:
    router = APIRouter(tags=["fake-s3"])

    def _ensure_stub_access(request: Request) -> None:
        if not settings.USE_STUBS:
            raise HTTPException(status_code=404, detail="Stub mode disabled")

        if settings.STUB_STATUS_TOKEN:
            token = request.headers.get("X-Stub-Auth") or request.query_params.get("token")
            if token != settings.STUB_STATUS_TOKEN:
                raise HTTPException(status_code=403, detail="Stub access token required")
        else:
            client_host = getattr(request.client, "host", "")
            if client_host not in {"127.0.0.1", "::1", "localhost"}:
                raise HTTPException(status_code=403, detail="Stub storage limited to local access")
    
    @router.put("/fake-s3/{session_id}/{document_type}/{file_id}")
    async def fake_s3_upload(
        session_id: str,
        document_type: str, 
        file_id: str,
        request: Request
    ):
        """Handle fake S3 upload for stub mode."""
        _ensure_stub_access(request)
        from ..stubs.storage_stub import StubS3Service
        from ..services import DocumentProcessingService
        from app.models import DocumentType, ValidationSession
        from ..database import SessionLocal
        from uuid import UUID
        
        # Read file content
        file_content = await request.body()
        content_type = request.headers.get('content-type', 'application/pdf')
        
        # Store the file
        stub_storage = StubS3Service()
        result = stub_storage.store_uploaded_file(
            session_id, document_type, file_id, file_content, content_type
        )
        
        # Create Document record in database
        print(f"Attempting to create document record for session {session_id}, type: {document_type}")
        db = SessionLocal()
        try:
            # Get the session
            session = db.query(ValidationSession).filter(
                ValidationSession.id == UUID(session_id)
            ).first()
            
            if session:
                print(f"Found validation session: {session.id}")
                processing_service = DocumentProcessingService(db)
                s3_key = f"uploads/{session_id}/{document_type}/{file_id}"
                
                # Map document type string to enum
                doc_type_map = {
                    'letter_of_credit': DocumentType.LETTER_OF_CREDIT,
                    'commercial_invoice': DocumentType.COMMERCIAL_INVOICE,
                    'bill_of_lading': DocumentType.BILL_OF_LADING
                }
                
                doc_type_enum = doc_type_map.get(document_type)
                if doc_type_enum:
                    print(f"Creating document record with type: {doc_type_enum}")
                    # Create document record
                    document = processing_service.create_document_record(
                        session=session,
                        document_type=doc_type_enum,
                        original_filename=f"{document_type}.pdf",  # We don't have the original filename
                        s3_key=s3_key,
                        file_size=result["file_size"],
                        content_type=content_type
                    )
                    print(f"✅ Created document record for {document_type} (ID: {document.id})")
                else:
                    print(f"❌ Unknown document type: {document_type}")
            else:
                print(f"❌ Session not found: {session_id}")
        except Exception as e:
            print(f"❌ Error creating document record: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
        
        return {
            "message": "File uploaded successfully",
            "file_size": result["file_size"],
            "stored_at": result["stored_at"]
        }
    
    @router.get("/fake-s3-download/{s3_key:path}")
    async def fake_s3_download(s3_key: str, request: Request):
        """Serve files for fake S3 download URLs."""
        _ensure_stub_access(request)
        from ..stubs.storage_stub import StubS3Service
        
        stub_storage = StubS3Service()
        file_path = stub_storage.get_file_path(s3_key)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get file info for proper headers
        file_info = stub_storage.get_file_info(s3_key)
        
        return FileResponse(
            path=str(file_path),
            media_type=file_info["content_type"],
            filename=file_path.name
        )

else:
    # Create empty router if stubs not enabled
    router = APIRouter(tags=["fake-s3-disabled"])