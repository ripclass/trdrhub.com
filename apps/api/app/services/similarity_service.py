"""
Similarity Service for LC Duplicate Detection
Generates fingerprints, computes similarity scores, and finds duplicate candidates
"""
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from difflib import SequenceMatcher

from app.models.duplicate_detection import (
    LCFingerprint,
    LCSimilarity,
    LCMergeHistory,
    DetectionMethod,
    MergeType,
)
from app.models import ValidationSession, SessionStatus


class SimilarityService:
    """Service for computing LC similarity and detecting duplicates"""
    
    # Fields to include in fingerprint (normalized)
    FINGERPRINT_FIELDS = [
        'lc_number',
        'client_name',
        'beneficiary_name',
        'issuing_bank',
        'amount',
        'currency',
        'expiry_date',
        'shipment_date',
        'port_of_loading',
        'port_of_discharge',
    ]
    
    # Thresholds for similarity detection
    HIGH_SIMILARITY_THRESHOLD = 0.85  # Very likely duplicate
    MEDIUM_SIMILARITY_THRESHOLD = 0.70  # Possible duplicate
    
    def __init__(self, db: Session):
        self.db = db
    
    def normalize_field_value(self, value: Any) -> str:
        """Normalize a field value for comparison"""
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value).strip()
        if isinstance(value, str):
            # Normalize: lowercase, strip, remove extra spaces
            return " ".join(value.lower().strip().split())
        return str(value).strip()
    
    def extract_lc_metadata(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize LC metadata from extracted_data"""
        metadata = {}
        
        # Try to get from bank_metadata first (bank context)
        bank_metadata = extracted_data.get('bank_metadata', {})
        if bank_metadata:
            for field in self.FINGERPRINT_FIELDS:
                value = bank_metadata.get(field)
                if value:
                    metadata[field] = self.normalize_field_value(value)
        
        # Fallback to top-level fields
        for field in self.FINGERPRINT_FIELDS:
            if field not in metadata:
                value = extracted_data.get(field)
                if value:
                    metadata[field] = self.normalize_field_value(value)
        
        return metadata
    
    def generate_fingerprint(self, session: ValidationSession) -> Tuple[str, Dict[str, Any]]:
        """Generate a content hash and fingerprint data for a validation session"""
        if not session.extracted_data:
            raise ValueError("Session has no extracted_data")
        
        metadata = self.extract_lc_metadata(session.extracted_data)
        
        # Create normalized fingerprint data
        fingerprint_data = {
            'lc_number': metadata.get('lc_number', ''),
            'client_name': metadata.get('client_name', ''),
            'fields': metadata,
        }
        
        # Generate hash from normalized data
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        content_hash = hashlib.sha256(fingerprint_json.encode()).hexdigest()
        
        return content_hash, fingerprint_data
    
    def create_or_update_fingerprint(
        self,
        session: ValidationSession,
        company_id: Optional[UUID] = None
    ) -> LCFingerprint:
        """Create or update fingerprint for a validation session"""
        content_hash, fingerprint_data = self.generate_fingerprint(session)
        
        # Extract LC number and client name
        metadata = self.extract_lc_metadata(session.extracted_data or {})
        lc_number = metadata.get('lc_number', '')
        client_name = metadata.get('client_name', '')
        
        # Check if fingerprint already exists
        existing = self.db.query(LCFingerprint).filter(
            LCFingerprint.validation_session_id == session.id
        ).first()
        
        if existing:
            # Update existing fingerprint
            existing.content_hash = content_hash
            existing.fingerprint_data = fingerprint_data
            existing.lc_number = lc_number
            existing.client_name = client_name
            if company_id:
                existing.company_id = company_id
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new fingerprint
            fingerprint = LCFingerprint(
                validation_session_id=session.id,
                lc_number=lc_number,
                client_name=client_name,
                company_id=company_id or session.company_id,
                content_hash=content_hash,
                fingerprint_data=fingerprint_data,
            )
            self.db.add(fingerprint)
            self.db.commit()
            self.db.refresh(fingerprint)
            return fingerprint
    
    def compute_similarity(
        self,
        fingerprint1: LCFingerprint,
        fingerprint2: LCFingerprint
    ) -> Dict[str, Any]:
        """Compute similarity score between two fingerprints"""
        fields1 = fingerprint1.fingerprint_data.get('fields', {})
        fields2 = fingerprint2.fingerprint_data.get('fields', {})
        
        # Compute field-level similarities
        field_scores = {}
        total_weight = 0.0
        weighted_sum = 0.0
        
        # Field weights (more important fields have higher weights)
        field_weights = {
            'lc_number': 0.3,
            'client_name': 0.2,
            'amount': 0.15,
            'currency': 0.1,
            'expiry_date': 0.1,
            'beneficiary_name': 0.05,
            'issuing_bank': 0.05,
            'shipment_date': 0.03,
            'port_of_loading': 0.01,
            'port_of_discharge': 0.01,
        }
        
        # Compare each field
        all_fields = set(fields1.keys()) | set(fields2.keys())
        for field in all_fields:
            val1 = fields1.get(field, '')
            val2 = fields2.get(field, '')
            
            if not val1 and not val2:
                continue  # Both empty, skip
            
            weight = field_weights.get(field, 0.01)
            
            if val1 == val2:
                score = 1.0
            elif not val1 or not val2:
                score = 0.0
            else:
                # Use SequenceMatcher for text similarity
                score = SequenceMatcher(None, val1, val2).ratio()
            
            field_scores[field] = {
                'value1': val1,
                'value2': val2,
                'score': score,
                'weight': weight,
            }
            
            weighted_sum += score * weight
            total_weight += weight
        
        # Overall similarity score
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Content similarity (text-based)
        content1 = json.dumps(fields1, sort_keys=True)
        content2 = json.dumps(fields2, sort_keys=True)
        content_similarity = SequenceMatcher(None, content1, content2).ratio()
        
        # Metadata similarity (field-by-field)
        metadata_similarity = overall_score
        
        return {
            'similarity_score': overall_score,
            'content_similarity': content_similarity,
            'metadata_similarity': metadata_similarity,
            'field_matches': field_scores,
        }
    
    def find_duplicate_candidates(
        self,
        session_id: UUID,
        threshold: float = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find duplicate candidates for a given session"""
        if threshold is None:
            threshold = self.MEDIUM_SIMILARITY_THRESHOLD
        
        # Get fingerprint for the session
        fingerprint = self.db.query(LCFingerprint).filter(
            LCFingerprint.validation_session_id == session_id
        ).first()
        
        if not fingerprint:
            return []
        
        # Find similar fingerprints (same content hash or similar LC number/client)
        candidates_query = self.db.query(LCFingerprint).filter(
            and_(
                LCFingerprint.id != fingerprint.id,
                LCFingerprint.validation_session_id != session_id,
                or_(
                    LCFingerprint.content_hash == fingerprint.content_hash,  # Exact match
                    and_(
                        LCFingerprint.lc_number == fingerprint.lc_number,
                        LCFingerprint.client_name == fingerprint.client_name,
                    ),
                ),
            )
        )
        
        # If company_id is set, prefer same company
        if fingerprint.company_id:
            candidates_query = candidates_query.order_by(
                func.nullif(LCFingerprint.company_id == fingerprint.company_id, False).desc(),
                LCFingerprint.created_at.desc()
            )
        else:
            candidates_query = candidates_query.order_by(LCFingerprint.created_at.desc())
        
        candidate_fingerprints = candidates_query.limit(limit * 2).all()  # Get more for filtering
        
        # Compute similarity scores and filter by threshold
        candidates = []
        for candidate_fp in candidate_fingerprints:
            similarity = self.compute_similarity(fingerprint, candidate_fp)
            
            if similarity['similarity_score'] >= threshold:
                # Get validation session details
                session = self.db.query(ValidationSession).filter(
                    ValidationSession.id == candidate_fp.validation_session_id
                ).first()
                
                if session:
                    candidates.append({
                        'session_id': candidate_fp.validation_session_id,
                        'lc_number': candidate_fp.lc_number,
                        'client_name': candidate_fp.client_name,
                        'similarity_score': similarity['similarity_score'],
                        'content_similarity': similarity['content_similarity'],
                        'metadata_similarity': similarity['metadata_similarity'],
                        'field_matches': similarity['field_matches'],
                        'completed_at': session.processing_completed_at,
                    })
        
        # Sort by similarity score descending
        candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return candidates[:limit]
    
    def record_similarity(
        self,
        fingerprint1: LCFingerprint,
        fingerprint2: LCFingerprint,
        similarity_data: Dict[str, Any],
        detected_by: Optional[UUID] = None,
        method: DetectionMethod = DetectionMethod.FINGERPRINT
    ) -> LCSimilarity:
        """Record a similarity between two fingerprints"""
        # Ensure fingerprint_id_1 < fingerprint_id_2
        if fingerprint1.id > fingerprint2.id:
            fingerprint1, fingerprint2 = fingerprint2, fingerprint1
        
        # Check if similarity already exists
        existing = self.db.query(LCSimilarity).filter(
            and_(
                LCSimilarity.fingerprint_id_1 == fingerprint1.id,
                LCSimilarity.fingerprint_id_2 == fingerprint2.id,
            )
        ).first()
        
        if existing:
            # Update existing similarity
            existing.similarity_score = similarity_data['similarity_score']
            existing.content_similarity = similarity_data.get('content_similarity')
            existing.metadata_similarity = similarity_data.get('metadata_similarity')
            existing.field_matches = similarity_data.get('field_matches')
            existing.detection_method = method.value
            if detected_by:
                existing.detected_by = detected_by
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new similarity record
            similarity = LCSimilarity(
                fingerprint_id_1=fingerprint1.id,
                fingerprint_id_2=fingerprint2.id,
                session_id_1=fingerprint1.validation_session_id,
                session_id_2=fingerprint2.validation_session_id,
                similarity_score=similarity_data['similarity_score'],
                content_similarity=similarity_data.get('content_similarity'),
                metadata_similarity=similarity_data.get('metadata_similarity'),
                field_matches=similarity_data.get('field_matches'),
                detection_method=method.value,
                detected_by=detected_by,
            )
            self.db.add(similarity)
            self.db.commit()
            self.db.refresh(similarity)
            return similarity

