"""
Digital Signature Service

Integrates with DocuSign and Adobe Sign for legally binding signatures.
Also supports local signature images and stamps.
"""

import os
import io
import uuid
import base64
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

# Environment variables
DOCUSIGN_API_KEY = os.getenv("DOCUSIGN_API_KEY")
DOCUSIGN_ACCOUNT_ID = os.getenv("DOCUSIGN_ACCOUNT_ID")
DOCUSIGN_BASE_URL = os.getenv("DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi")

ADOBE_SIGN_CLIENT_ID = os.getenv("ADOBE_SIGN_CLIENT_ID")
ADOBE_SIGN_CLIENT_SECRET = os.getenv("ADOBE_SIGN_CLIENT_SECRET")
ADOBE_SIGN_BASE_URL = os.getenv("ADOBE_SIGN_BASE_URL", "https://api.na1.adobesign.com")


class SignatureProvider(str, Enum):
    """Supported signature providers"""
    LOCAL = "local"           # Local signature image
    DOCUSIGN = "docusign"     # DocuSign e-signature
    ADOBE_SIGN = "adobe_sign"  # Adobe Sign


class SignatureStatus(str, Enum):
    """Status of signature request"""
    PENDING = "pending"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignatureRequest:
    """Represents a signature request"""
    def __init__(
        self,
        document_set_id: str,
        document_bytes: bytes,
        document_name: str,
        signers: List[Dict[str, str]],
        provider: SignatureProvider = SignatureProvider.LOCAL,
    ):
        self.id = str(uuid.uuid4())
        self.document_set_id = document_set_id
        self.document_bytes = document_bytes
        self.document_name = document_name
        self.signers = signers  # [{"name": "...", "email": "...", "role": "beneficiary"}]
        self.provider = provider
        self.status = SignatureStatus.PENDING
        self.created_at = datetime.utcnow()
        self.external_id = None  # ID from external provider


class DigitalSignatureService:
    """
    Service for handling digital signatures.
    
    Supports:
    - Local signature images (uploaded)
    - DocuSign integration
    - Adobe Sign integration
    """
    
    def __init__(self):
        self._docusign_client = None
        self._adobe_client = None
    
    # ============== Local Signatures ==============
    
    async def apply_local_signature(
        self,
        pdf_bytes: bytes,
        signature_image: bytes,
        position: Dict[str, int],  # {"page": 1, "x": 100, "y": 100, "width": 150, "height": 50}
        stamp_image: Optional[bytes] = None,
        stamp_position: Optional[Dict[str, int]] = None,
    ) -> bytes:
        """
        Apply a local signature image to a PDF.
        
        This embeds the signature image directly without external verification.
        Suitable for internal documents or where e-signature isn't required.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from PyPDF2 import PdfReader, PdfWriter
        from PIL import Image
        
        # Read original PDF
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        
        # Process each page
        for page_num, page in enumerate(reader.pages):
            if page_num == position.get("page", 0):
                # Create overlay with signature
                overlay_buffer = io.BytesIO()
                overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=A4)
                
                # Add signature image
                sig_img_buffer = io.BytesIO(signature_image)
                overlay_canvas.drawImage(
                    sig_img_buffer,
                    position.get("x", 100),
                    position.get("y", 100),
                    width=position.get("width", 150),
                    height=position.get("height", 50),
                    mask='auto'
                )
                
                # Add stamp if provided
                if stamp_image and stamp_position:
                    stamp_buffer = io.BytesIO(stamp_image)
                    overlay_canvas.drawImage(
                        stamp_buffer,
                        stamp_position.get("x", 400),
                        stamp_position.get("y", 100),
                        width=stamp_position.get("width", 80),
                        height=stamp_position.get("height", 80),
                        mask='auto'
                    )
                
                overlay_canvas.save()
                
                # Merge overlay with page
                overlay_pdf = PdfReader(io.BytesIO(overlay_buffer.getvalue()))
                page.merge_page(overlay_pdf.pages[0])
            
            writer.add_page(page)
        
        # Write output
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    
    # ============== DocuSign Integration ==============
    
    async def create_docusign_envelope(
        self,
        request: SignatureRequest,
        subject: str = "Document for Signature",
        message: str = "Please review and sign this document.",
    ) -> Dict[str, Any]:
        """
        Create a DocuSign envelope for signing.
        
        Returns envelope ID and signing URLs.
        """
        if not DOCUSIGN_API_KEY or not DOCUSIGN_ACCOUNT_ID:
            raise ValueError("DocuSign credentials not configured")
        
        # Prepare document
        doc_base64 = base64.b64encode(request.document_bytes).decode('utf-8')
        
        # Build signers
        signers = []
        for i, signer in enumerate(request.signers):
            signers.append({
                "email": signer["email"],
                "name": signer["name"],
                "recipientId": str(i + 1),
                "routingOrder": str(i + 1),
                "tabs": {
                    "signHereTabs": [{
                        "documentId": "1",
                        "pageNumber": "1",
                        "xPosition": "400",
                        "yPosition": "200"
                    }],
                    "dateSignedTabs": [{
                        "documentId": "1",
                        "pageNumber": "1",
                        "xPosition": "400",
                        "yPosition": "250"
                    }]
                }
            })
        
        # Create envelope
        envelope_data = {
            "emailSubject": subject,
            "emailBlurb": message,
            "documents": [{
                "documentId": "1",
                "name": request.document_name,
                "fileExtension": "pdf",
                "documentBase64": doc_base64
            }],
            "recipients": {
                "signers": signers
            },
            "status": "sent"  # Send immediately
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes",
                json=envelope_data,
                headers={
                    "Authorization": f"Bearer {DOCUSIGN_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 201:
                logger.error(f"DocuSign error: {response.text}")
                raise Exception(f"Failed to create DocuSign envelope: {response.text}")
            
            result = response.json()
            
            request.external_id = result.get("envelopeId")
            request.status = SignatureStatus.SENT
            
            return {
                "envelope_id": result.get("envelopeId"),
                "status": result.get("status"),
                "uri": result.get("uri"),
            }
    
    async def get_docusign_status(self, envelope_id: str) -> Dict[str, Any]:
        """Get status of a DocuSign envelope"""
        if not DOCUSIGN_API_KEY or not DOCUSIGN_ACCOUNT_ID:
            raise ValueError("DocuSign credentials not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes/{envelope_id}",
                headers={"Authorization": f"Bearer {DOCUSIGN_API_KEY}"}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get DocuSign status: {response.text}")
            
            result = response.json()
            
            return {
                "envelope_id": envelope_id,
                "status": result.get("status"),
                "completed_at": result.get("completedDateTime"),
                "sent_at": result.get("sentDateTime"),
            }
    
    async def download_signed_document(self, envelope_id: str) -> bytes:
        """Download the signed document from DocuSign"""
        if not DOCUSIGN_API_KEY or not DOCUSIGN_ACCOUNT_ID:
            raise ValueError("DocuSign credentials not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes/{envelope_id}/documents/combined",
                headers={"Authorization": f"Bearer {DOCUSIGN_API_KEY}"}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to download signed document: {response.text}")
            
            return response.content
    
    # ============== Adobe Sign Integration ==============
    
    async def create_adobe_agreement(
        self,
        request: SignatureRequest,
        name: str = "Document for Signature",
        message: str = "Please review and sign this document.",
    ) -> Dict[str, Any]:
        """
        Create an Adobe Sign agreement for signing.
        """
        if not ADOBE_SIGN_CLIENT_ID:
            raise ValueError("Adobe Sign credentials not configured")
        
        # First upload the document
        doc_base64 = base64.b64encode(request.document_bytes).decode('utf-8')
        
        async with httpx.AsyncClient() as client:
            # Upload document as transient
            upload_response = await client.post(
                f"{ADOBE_SIGN_BASE_URL}/api/rest/v6/transientDocuments",
                headers={
                    "Authorization": f"Bearer {ADOBE_SIGN_CLIENT_ID}",
                },
                files={
                    "File": (request.document_name, request.document_bytes, "application/pdf")
                }
            )
            
            if upload_response.status_code != 200:
                raise Exception(f"Failed to upload document to Adobe Sign: {upload_response.text}")
            
            transient_doc_id = upload_response.json().get("transientDocumentId")
            
            # Create agreement
            participants = []
            for signer in request.signers:
                participants.append({
                    "memberInfos": [{
                        "email": signer["email"],
                        "name": signer["name"]
                    }],
                    "role": "SIGNER",
                    "order": 1
                })
            
            agreement_data = {
                "fileInfos": [{
                    "transientDocumentId": transient_doc_id
                }],
                "name": name,
                "message": message,
                "participantSetsInfo": participants,
                "signatureType": "ESIGN",
                "state": "IN_PROCESS"
            }
            
            response = await client.post(
                f"{ADOBE_SIGN_BASE_URL}/api/rest/v6/agreements",
                json=agreement_data,
                headers={
                    "Authorization": f"Bearer {ADOBE_SIGN_CLIENT_ID}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 201:
                raise Exception(f"Failed to create Adobe Sign agreement: {response.text}")
            
            result = response.json()
            
            request.external_id = result.get("id")
            request.status = SignatureStatus.SENT
            
            return {
                "agreement_id": result.get("id"),
                "status": "IN_PROCESS",
            }
    
    # ============== Utility Methods ==============
    
    def generate_signature_hash(
        self,
        pdf_bytes: bytes,
        signer_name: str,
        timestamp: datetime
    ) -> str:
        """
        Generate a hash for document integrity verification.
        
        This can be embedded in the document as a simple verification.
        """
        data = pdf_bytes + signer_name.encode() + timestamp.isoformat().encode()
        return hashlib.sha256(data).hexdigest()
    
    def is_docusign_configured(self) -> bool:
        """Check if DocuSign is configured"""
        return bool(DOCUSIGN_API_KEY and DOCUSIGN_ACCOUNT_ID)
    
    def is_adobe_configured(self) -> bool:
        """Check if Adobe Sign is configured"""
        return bool(ADOBE_SIGN_CLIENT_ID)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available signature providers"""
        providers = ["local"]
        if self.is_docusign_configured():
            providers.append("docusign")
        if self.is_adobe_configured():
            providers.append("adobe_sign")
        return providers


# Singleton
_signature_service: Optional[DigitalSignatureService] = None


def get_signature_service() -> DigitalSignatureService:
    global _signature_service
    if _signature_service is None:
        _signature_service = DigitalSignatureService()
    return _signature_service

