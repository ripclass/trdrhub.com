"""
Document processing API endpoints.
"""

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from ..database import get_db
from app.models import User, ValidationSession, Document, DocumentType, SessionStatus
from ..schemas import DocumentProcessingResponse, ProcessedDocumentInfo
from ..core.security import get_current_user
from ..core.rbac import RBACPolicyEngine, Permission
from ..services import (
    ValidationSessionService, S3Service, DocumentAIService,
    DocumentProcessingService
)
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult
from ..middleware.audit_middleware import get_correlation_id, create_audit_context
from ..config import settings
from ..utils.file_validation import validate_upload_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["document-processing"])


@router.post("/process-document", response_model=DocumentProcessingResponse, status_code=status.HTTP_200_OK)
async def process_document(
    request: Request,
    files: List[UploadFile] = File(..., description="1-6 trade documents (LC + supporting docs)"),
    session_id: Optional[str] = Form(None, description="Optional existing session ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Process document uploads end-to-end:
    1. Upload files to S3
    2. Process with Google Cloud Document AI
    3. Save results to Postgres
    4. Return structured JSON response
    """
    # Check permissions for document upload and validation
    if not RBACPolicyEngine.has_permission(current_user.role, Permission.UPLOAD_OWN_DOCS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to upload documents"
        )

    logger.info(f"Processing {len(files)} documents for user {current_user.id}")

    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    start_time = time.time()

    # Collect file contents for audit hashing
    files_content = []
    file_names = []

    for file in files:
        content = await file.read()
        files_content.append(content)
        file_names.append(file.filename)
        # Reset file position for subsequent reading
        await file.seek(0)

    # Validate file count
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided"
        )

    if len(files) > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 6 files allowed"
        )

    # Validate file types with content-based validation
    allowed_types = {'application/pdf', 'image/jpeg', 'image/png', 'image/tiff'}
    for file in files:
        # Read file header for content validation (first 8 bytes)
        await file.seek(0)
        header_bytes = await file.read(8)
        await file.seek(0)  # Reset for processing
        
        # Content-based validation
        is_valid, error_message = validate_upload_file(
            header_bytes,
            filename=file.filename,
            content_type=file.content_type
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file content for {file.filename}: {error_message}. File content does not match declared type."
            )
        
        # Also check declared content type as secondary validation
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not supported. Use PDF, JPEG, PNG, or TIFF."
            )

    # Initialize services
    session_service = ValidationSessionService(db)
    s3_service = S3Service()
    docai_service = DocumentAIService()

    try:
        # Create or get validation session
        if session_id:
            try:
                session_uuid = UUID(session_id)
                session = session_service.get_session(session_uuid, current_user)
                if not session:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Session not found"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid session ID format"
                )
        else:
            # Create new session
            session = session_service.create_session(current_user)
            logger.info(f"Created new session: {session.id}")

        # Update session status to processing
        session = session_service.update_session_status(session, SessionStatus.PROCESSING)
        session.ocr_provider = "google_documentai"
        db.commit()

        processed_documents = []
        total_confidence = 0.0
        total_entities = 0
        total_pages = 0

        # Process each file
        for idx, file in enumerate(files):
            logger.info(f"Processing file {idx + 1}/{len(files)}: {file.filename}")

            # Determine document type based on filename or order
            document_type = _determine_document_type(file.filename, idx)

            try:
                # Step 1: Upload to S3
                logger.info(f"Uploading {file.filename} to S3...")
                upload_result = await s3_service.upload_file(file, session.id, document_type)

                # Step 2: Process with Document AI
                logger.info(f"Processing {file.filename} with Document AI...")

                # Reset file pointer for processing
                await file.seek(0)
                file_content = await file.read()

                docai_result = await docai_service.process_file(
                    file_content,
                    file.content_type or 'application/pdf'
                )

                if not docai_result['success']:
                    logger.error(f"Document AI processing failed: {docai_result.get('error', 'Unknown error')}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Document AI processing failed: {docai_result.get('error', 'Unknown error')}"
                    )

                # Step 3: Save to database
                logger.info(f"Saving document metadata to database...")
                document = Document(
                    validation_session_id=session.id,
                    document_type=document_type,
                    original_filename=upload_result['original_filename'],
                    s3_key=upload_result['s3_key'],
                    file_size=upload_result['file_size'],
                    content_type=upload_result['content_type'],
                    ocr_text=docai_result['extracted_text'],
                    ocr_confidence=docai_result['overall_confidence'],
                    ocr_processed_at=datetime.now(timezone.utc),
                    extracted_fields=docai_result['extracted_fields']
                )

                db.add(document)
                db.commit()
                db.refresh(document)

                # Prepare response data
                text_preview = docai_result['extracted_text'][:200] if docai_result['extracted_text'] else ""

                processed_doc_info = ProcessedDocumentInfo(
                    document_id=document.id,
                    document_type=document_type,
                    original_filename=upload_result['original_filename'],
                    s3_url=upload_result['s3_url'],
                    s3_key=upload_result['s3_key'],
                    file_size=upload_result['file_size'],
                    extracted_text_preview=text_preview,
                    extracted_fields=docai_result['extracted_fields'],
                    ocr_confidence=docai_result['overall_confidence'],
                    page_count=docai_result['page_count'],
                    entity_count=docai_result['entity_count']
                )

                processed_documents.append(processed_doc_info)

                # Accumulate stats
                total_confidence += docai_result['overall_confidence']
                total_entities += docai_result['entity_count']
                total_pages += docai_result['page_count']

                logger.info(f"Successfully processed {file.filename}")

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process {file.filename}: {str(e)}"
                )

        # Update session status to completed
        session = session_service.update_session_status(session, SessionStatus.COMPLETED)

        # Calculate processing summary
        avg_confidence = total_confidence / len(files) if len(files) > 0 else 0.0
        processing_summary = {
            'total_files_processed': len(files),
            'average_confidence': round(avg_confidence, 3),
            'total_entities_extracted': total_entities,
            'total_pages_processed': total_pages,
            'processor_used': docai_service.processor_id,
            'processing_completed_at': datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Successfully processed all documents for session {session.id}")

        # Log successful upload and processing
        duration_ms = int((time.time() - start_time) * 1000)
        audit_service.log_action(
            action=AuditAction.UPLOAD,
            user=current_user,
            resource_type="documents",
            resource_id=str(session.id),
            lc_number=getattr(session, 'lc_number', None),
            files_content=files_content,
            correlation_id=audit_context['correlation_id'],
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            duration_ms=duration_ms,
            result=AuditResult.SUCCESS,
            audit_metadata={
                "file_names": file_names,
                "total_files": len(files),
                "processing_summary": processing_summary
            }
        )

        # Return response
        return DocumentProcessingResponse(
            session_id=session.id,
            processor_id=docai_service.processor_id,
            processed_documents=processed_documents,
            discrepancies=[],  # Placeholder - would be populated by validation rules
            processing_summary=processing_summary,
            created_at=session.created_at
        )

    except HTTPException as he:
        # Update session status to failed for HTTP errors
        try:
            session_service.update_session_status(session, SessionStatus.FAILED)
        except:
            pass

        # Log failed upload
        duration_ms = int((time.time() - start_time) * 1000)
        audit_service.log_action(
            action=AuditAction.UPLOAD,
            user=current_user,
            resource_type="documents",
            files_content=files_content if files_content else None,
            correlation_id=audit_context['correlation_id'],
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            duration_ms=duration_ms,
            result=AuditResult.FAILURE,
            error_message=str(he.detail),
            audit_metadata={"file_names": file_names, "status_code": he.status_code}
        )
        raise

    except Exception as e:
        # Update session status to failed for unexpected errors
        try:
            session_service.update_session_status(session, SessionStatus.FAILED)
        except:
            pass

        logger.error(f"Unexpected error in document processing: {str(e)}")

        # Log failed upload
        duration_ms = int((time.time() - start_time) * 1000)
        audit_service.log_action(
            action=AuditAction.UPLOAD,
            user=current_user,
            resource_type="documents",
            files_content=files_content if files_content else None,
            correlation_id=audit_context['correlation_id'],
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            duration_ms=duration_ms,
            result=AuditResult.ERROR,
            error_message=str(e),
            audit_metadata={"file_names": file_names}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


def _determine_document_type(filename: Optional[str], index: int) -> str:
    """Determine document type based on filename or position."""
    if not filename:
        # Fallback to position-based mapping
        type_mapping = {
            0: DocumentType.LETTER_OF_CREDIT.value,
            1: DocumentType.COMMERCIAL_INVOICE.value,
            2: DocumentType.BILL_OF_LADING.value,
            3: DocumentType.PACKING_LIST.value,
            4: DocumentType.CERTIFICATE_OF_ORIGIN.value,
            5: DocumentType.INSURANCE_CERTIFICATE.value,
            6: DocumentType.INSPECTION_CERTIFICATE.value,
        }
        return type_mapping.get(index, DocumentType.LETTER_OF_CREDIT.value)

    filename_lower = filename.lower()

    # Check for common patterns in filename
    if any(pattern in filename_lower for pattern in ['lc', 'letter', 'credit']):
        return DocumentType.LETTER_OF_CREDIT.value
    elif any(pattern in filename_lower for pattern in ['invoice', 'inv']):
        return DocumentType.COMMERCIAL_INVOICE.value
    elif any(pattern in filename_lower for pattern in ['bl', 'bill', 'lading', 'shipping']):
        return DocumentType.BILL_OF_LADING.value
    elif 'packing' in filename_lower or 'packlist' in filename_lower:
        return DocumentType.PACKING_LIST.value
    elif any(pattern in filename_lower for pattern in ['certificate_of_origin', 'certificate of origin', 'coo']):
        return DocumentType.CERTIFICATE_OF_ORIGIN.value
    elif any(pattern in filename_lower for pattern in ['insurance', 'policy']):
        return DocumentType.INSURANCE_CERTIFICATE.value
    elif any(pattern in filename_lower for pattern in ['inspection', 'analysis']):
        return DocumentType.INSPECTION_CERTIFICATE.value
    else:
        # Default mapping based on order
        return _determine_document_type(None, index)
