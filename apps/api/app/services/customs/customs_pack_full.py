# apps/api/app/services/customs/customs_pack_full.py

import io
import json
import zipfile
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.services import S3Service            # <- Your real S3Service
from app.models import Document, ValidationSession  # assumes these exist

# Which docs we try to bundle (friendly_name -> candidate document_type aliases)
REQUIRED_DOCS: List[Tuple[str, List[str]]] = [
    ("lc", ["lc", "letter_of_credit"]),
    ("invoice", ["invoice", "commercial_invoice"]),
    ("packing_list", ["packing_list", "packing"]),
    ("bill_of_lading", ["bill_of_lading", "bl", "boL", "sea_waybill"]),
    ("certificate_of_origin", ["certificate_of_origin", "coo"]),
    ("insurance", ["insurance", "insurance_certificate"]),
]

DEFAULT_URL_TTL_SECONDS = 3600  # 1 hour


class CustomsPackBuilderFull:
    """
    Builds an in-memory ZIP containing:
      - Trade PDFs from S3 (resolved via Document.s3_key)
      - lc_structured.json (if present on session)
      - risk.json (if present on session)
      - metadata/ files (session id, generated_at)
    Uploads the ZIP to S3 and returns a signed URL + checksum/size.
    """

    def __init__(self, url_ttl_seconds: int = DEFAULT_URL_TTL_SECONDS):
        self.s3 = S3Service()  # has .s3_client and .bucket_name (or ._impl for stubs)
        self.url_ttl_seconds = url_ttl_seconds

    # -------- Public API --------

    def build_and_upload(self, db: Session, session_id: str) -> Dict[str, Any]:
        session = self._get_session(db, session_id)
        if not session:
            raise ValueError("Validation session not found")

        docs = self._get_documents(db, session_id)

        # Extract structured_result from validation_results JSON
        validation_results = session.validation_results or {}
        structured_result = validation_results.get("structured_result", {})
        lc_structured = structured_result.get("lc_structured")
        risk = structured_result.get("risk") or validation_results.get("analytics", {}).get("customs_risk")

        buf, sha256_hex, size_bytes, missing = self._build_zip(
            session_id=session_id,
            docs=docs,
            lc_structured=lc_structured,
            risk=risk,
        )

        s3_key = f"customs-packs/{session_id}/customs_pack.zip"
        self._put_zip_to_s3(s3_key, buf.getvalue())

        signed_url = self._sign_url(s3_key, self.url_ttl_seconds)
        expires_at = (datetime.utcnow() + timedelta(seconds=self.url_ttl_seconds)).isoformat() + "Z"

        return {
            "session_id": session_id,
            "bucket": self._get_bucket_name(),
            "s3_key": s3_key,
            "download_url": signed_url,
            "expires_at": expires_at,
            "size_bytes": size_bytes,
            "sha256": sha256_hex,
            "ready": True,
            "missing_documents": missing,  # helpful for UI & audit
        }

    # -------- Internals --------

    def _get_session(self, db: Session, session_id: str) -> Optional[ValidationSession]:
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return None
        
        return db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == session_uuid,
                ValidationSession.deleted_at.is_(None)
            )
        ).one_or_none()

    def _get_documents(self, db: Session, session_id: str) -> List[Document]:
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return []
        
        return db.query(Document).filter(
            and_(
                Document.validation_session_id == session_uuid,
                Document.deleted_at.is_(None)
            )
        ).all()

    def _build_zip(
        self,
        session_id: str,
        docs: List[Document],
        lc_structured: Optional[Dict[str, Any]],
        risk: Optional[Dict[str, Any]],
    ) -> Tuple[io.BytesIO, str, int, List[str]]:
        buf = io.BytesIO()
        missing: List[str] = []
        by_type = self._index_docs(docs)

        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 1) PDFs
            for friendly, aliases in REQUIRED_DOCS:
                doc = self._match_doc(by_type, aliases)
                if not doc:
                    missing.append(friendly)
                    zf.writestr(f"{friendly}.MISSING.txt", "Document not found in session.")
                    continue

                try:
                    body = self._download_s3(doc.s3_key)
                    filename = self._safe_pdf_name(doc.original_filename, fallback=f"{friendly}.pdf")
                    zf.writestr(filename, body)
                except Exception as e:
                    # If download fails, mark as missing but continue
                    missing.append(friendly)
                    zf.writestr(f"{friendly}.MISSING.txt", f"Document found but download failed: {str(e)}")

            # 2) Metadata
            zf.writestr("metadata/session_id.txt", session_id.encode("utf-8"))
            zf.writestr("metadata/generated_at.txt", datetime.utcnow().isoformat().encode("utf-8"))

            # 3) Machine JSONs
            if lc_structured:
                zf.writestr(
                    "lc_structured.json",
                    json.dumps(lc_structured, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                )
            if risk:
                zf.writestr(
                    "risk.json",
                    json.dumps(risk, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                )

        # finalize checksum/size
        buf.seek(0)
        data = buf.getvalue()
        sha256_hex = hashlib.sha256(data).hexdigest()
        return buf, sha256_hex, len(data), missing

    def _index_docs(self, docs: List[Document]) -> Dict[str, List[Document]]:
        out: Dict[str, List[Document]] = {}
        for d in docs:
            key = (d.document_type or "").lower()
            out.setdefault(key, []).append(d)
        return out

    def _match_doc(self, by_type: Dict[str, List[Document]], aliases: List[str]) -> Optional[Document]:
        aliases = [a.lower() for a in aliases]
        # exact match first
        for a in aliases:
            if a in by_type and by_type[a]:
                return by_type[a][0]
        # fuzzy contains fallback
        for a in aliases:
            for k, arr in by_type.items():
                if a in k and arr:
                    return arr[0]
        return None

    def _safe_pdf_name(self, name: str, fallback: str) -> str:
        n = (name or "").strip() or fallback
        if not n.lower().endswith(".pdf"):
            n += ".pdf"
        return n

    def _download_s3(self, key: str) -> bytes:
        """Download file from S3, handling both stub and real implementations."""
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        
        resp = s3_client.get_object(Bucket=bucket_name, Key=key)
        return resp["Body"].read()

    def _put_zip_to_s3(self, key: str, data: bytes) -> None:
        """Upload ZIP to S3, handling both stub and real implementations."""
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=data,
            ContentType="application/zip",
            Metadata={"created_at": datetime.utcnow().isoformat()},
        )

    def _sign_url(self, key: str, ttl_seconds: int) -> str:
        """Generate presigned URL, handling both stub and real implementations."""
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        
        return s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=ttl_seconds,
        )

    def _get_s3_client(self):
        """Get S3 client, handling stub mode."""
        # In stub mode, S3Service wraps implementation in _impl and doesn't expose s3_client
        if hasattr(self.s3, '_impl'):
            raise RuntimeError(
                "Customs pack builder requires real S3 storage. "
                "Stub mode is not supported for ZIP generation. "
                "Set USE_STUBS=false to enable customs pack downloads."
            )
        if not hasattr(self.s3, 's3_client') or self.s3.s3_client is None:
            raise RuntimeError("S3Service is not properly initialized with s3_client")
        return self.s3.s3_client

    def _get_bucket_name(self) -> str:
        """Get bucket name, handling stub mode."""
        if hasattr(self.s3, '_impl'):
            raise RuntimeError(
                "Customs pack builder requires real S3 storage. "
                "Stub mode is not supported for ZIP generation."
            )
        if not hasattr(self.s3, 'bucket_name') or not self.s3.bucket_name:
            raise RuntimeError("S3Service is not properly initialized with bucket_name")
        return self.s3.bucket_name

