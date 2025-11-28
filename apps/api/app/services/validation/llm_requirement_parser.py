"""
LLM Requirement Parser - Stage 1 of Hybrid Validation Pipeline

This module uses LLM to extract ALL requirements from LC text, including:
- Nested obligations (e.g., "clean on board ocean B/L" = 9 rules)
- Tolerances (explicit and UCP600 defaults)
- Document type inference
- Contradiction detection
- Special conditions

Features:
- SHA256 caching to avoid repeated LLM calls
- Structured JSON output (RequirementGraph)
- Bank-specific rule profiles
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class ToleranceSource(str, Enum):
    """Source of tolerance rule."""
    EXPLICIT_LC = "explicit_lc"
    UCP600_ART_30 = "ucp600_art_30"
    UCP600_ART_39 = "ucp600_art_39"
    ISBP745 = "isbp745"
    BANK_PRACTICE = "bank_practice"


class DocumentRequirementType(str, Enum):
    """Types of document requirements."""
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    OPTIONAL = "optional"


@dataclass
class NestedObligation:
    """A single obligation extracted from an LC clause."""
    obligation_id: str
    description: str
    field_to_check: str
    expected_value: Any
    source_clause: str  # e.g., "46A", "47A"
    source_text: str    # Original text this came from
    is_mandatory: bool = True
    ucp_reference: Optional[str] = None
    isbp_reference: Optional[str] = None


@dataclass
class DocumentRequirement:
    """A document required by the LC."""
    document_type: str
    display_name: str
    requirement_type: DocumentRequirementType
    source_clause: str
    
    # Nested obligations for this document
    obligations: List[NestedObligation] = field(default_factory=list)
    
    # Issuer requirements
    issuer: Optional[str] = None
    issuer_strict: bool = False
    
    # Content requirements
    must_contain: List[str] = field(default_factory=list)
    must_state: Optional[str] = None
    
    # Copies
    copies_required: int = 1
    originals_required: int = 0
    
    # Acceptable filename patterns for inference
    filename_patterns: List[str] = field(default_factory=list)


@dataclass
class ToleranceRule:
    """A tolerance rule (explicit or implicit)."""
    field: str  # "amount", "quantity", etc.
    base_value: float
    tolerance_percent: float
    tolerance_absolute: Optional[float] = None
    source: ToleranceSource = ToleranceSource.UCP600_ART_30
    explicit: bool = False
    clause_reference: Optional[str] = None
    
    @property
    def min_value(self) -> float:
        if self.tolerance_absolute:
            return self.base_value - self.tolerance_absolute
        return self.base_value * (1 - self.tolerance_percent / 100)
    
    @property
    def max_value(self) -> float:
        if self.tolerance_absolute:
            return self.base_value + self.tolerance_absolute
        return self.base_value * (1 + self.tolerance_percent / 100)
    
    def is_within_tolerance(self, value: float) -> Tuple[bool, Dict[str, Any]]:
        """Check if value is within tolerance, return audit info."""
        within = self.min_value <= value <= self.max_value
        deviation_pct = ((value - self.base_value) / self.base_value) * 100 if self.base_value else 0
        
        return within, {
            "tolerance_applied": self.tolerance_percent,
            "source": self.source.value,
            "explicit": self.explicit,
            "base_value": self.base_value,
            "actual_value": value,
            "deviation_percent": round(deviation_pct, 2),
            "min_allowed": round(self.min_value, 2),
            "max_allowed": round(self.max_value, 2),
            "clause_reference": self.clause_reference,
        }


@dataclass 
class Contradiction:
    """A detected contradiction between LC clauses."""
    contradiction_id: str
    clause_1: str
    clause_1_text: str
    clause_2: str
    clause_2_text: str
    conflict_type: str  # "quantity", "document_copies", etc.
    resolution: str
    enforced_clause: str
    confidence: float
    ucp_reference: Optional[str] = None


@dataclass
class BLRequirements:
    """Specific B/L requirements extracted from LC."""
    clean: bool = True
    on_board: bool = True
    transport_mode: str = "ocean"  # ocean, multimodal, air
    full_set: bool = True
    copies_required: int = 3
    consignee_type: str = "to_order"  # to_order, named, to_order_of_bank
    endorsement: str = "blank"  # blank, specific
    notify_party_required: bool = True
    freight_indication: str = "any"  # prepaid, collect, any
    ports_must_match: bool = True
    date_constraint: str = "latest_shipment"  # latest_shipment, specific_date
    transshipment_allowed: bool = True
    must_show_fields: List[str] = field(default_factory=list)  # voyage_no, weights, etc.


@dataclass
class RequirementGraph:
    """Complete requirement graph extracted from LC."""
    lc_hash: str
    parsed_at: str
    
    # Core requirements
    required_documents: List[DocumentRequirement] = field(default_factory=list)
    bl_requirements: Optional[BLRequirements] = None
    
    # Tolerances
    tolerances: Dict[str, ToleranceRule] = field(default_factory=dict)
    
    # Special conditions
    special_conditions: List[str] = field(default_factory=list)
    prohibited_items: List[str] = field(default_factory=list)  # e.g., "Israeli vessels"
    
    # Contradictions detected
    contradictions: List[Contradiction] = field(default_factory=list)
    
    # Document type inference mapping
    document_type_mapping: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Metadata
    presentation_period_days: int = 21  # Default per UCP600
    latest_shipment_date: Optional[str] = None
    expiry_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "lc_hash": self.lc_hash,
            "parsed_at": self.parsed_at,
            "required_documents": [
                {
                    "document_type": d.document_type,
                    "display_name": d.display_name,
                    "requirement_type": d.requirement_type.value,
                    "source_clause": d.source_clause,
                    "obligations": [
                        {
                            "obligation_id": o.obligation_id,
                            "description": o.description,
                            "field_to_check": o.field_to_check,
                            "expected_value": o.expected_value,
                            "source_clause": o.source_clause,
                        }
                        for o in d.obligations
                    ],
                    "issuer": d.issuer,
                    "must_contain": d.must_contain,
                    "copies_required": d.copies_required,
                    "originals_required": d.originals_required,
                    "filename_patterns": d.filename_patterns,
                }
                for d in self.required_documents
            ],
            "bl_requirements": {
                "clean": self.bl_requirements.clean,
                "on_board": self.bl_requirements.on_board,
                "transport_mode": self.bl_requirements.transport_mode,
                "full_set": self.bl_requirements.full_set,
                "copies_required": self.bl_requirements.copies_required,
                "consignee_type": self.bl_requirements.consignee_type,
                "endorsement": self.bl_requirements.endorsement,
                "must_show_fields": self.bl_requirements.must_show_fields,
            } if self.bl_requirements else None,
            "tolerances": {
                k: {
                    "field": v.field,
                    "base_value": v.base_value,
                    "tolerance_percent": v.tolerance_percent,
                    "source": v.source.value,
                    "explicit": v.explicit,
                }
                for k, v in self.tolerances.items()
            },
            "contradictions": [
                {
                    "clause_1": c.clause_1,
                    "clause_2": c.clause_2,
                    "resolution": c.resolution,
                    "enforced_clause": c.enforced_clause,
                    "confidence": c.confidence,
                }
                for c in self.contradictions
            ],
            "special_conditions": self.special_conditions,
            "prohibited_items": self.prohibited_items,
            "document_type_mapping": self.document_type_mapping,
            "presentation_period_days": self.presentation_period_days,
        }


# =============================================================================
# CACHE
# =============================================================================

# In-memory cache (in production, use Redis)
_requirement_cache: Dict[str, RequirementGraph] = {}


def _get_cache_key(lc_text: str) -> str:
    """Generate SHA256 cache key from LC text."""
    normalized = lc_text.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def get_cached_requirements(lc_text: str) -> Optional[RequirementGraph]:
    """Get cached requirements if available."""
    cache_key = _get_cache_key(lc_text)
    if cache_key in _requirement_cache:
        logger.info(f"Cache HIT for LC hash {cache_key[:16]}...")
        return _requirement_cache[cache_key]
    logger.info(f"Cache MISS for LC hash {cache_key[:16]}...")
    return None


def cache_requirements(lc_text: str, requirements: RequirementGraph) -> None:
    """Cache requirements for future use."""
    cache_key = _get_cache_key(lc_text)
    _requirement_cache[cache_key] = requirements
    logger.info(f"Cached requirements for LC hash {cache_key[:16]}...")


# =============================================================================
# LLM PROMPT TEMPLATES
# =============================================================================

REQUIREMENT_EXTRACTION_PROMPT = '''You are an expert Letter of Credit document examiner with 20 years of experience at major international banks. Your task is to extract ALL requirements from this LC, including nested obligations.

CRITICAL: One LC clause can contain MULTIPLE nested obligations. For example:
"Full set of clean on board ocean B/L made out to order and blank endorsed"
Contains 7+ separate requirements:
1. document_type = bill_of_lading
2. clean = true (no adverse clauses)
3. on_board = true (shipped, not received for shipment)
4. transport_mode = ocean
5. full_set = true (3/3 originals)
6. consignee = to_order
7. endorsement = blank

LC TEXT:
{lc_text}

Extract and return a JSON object with this EXACT structure:
{{
    "required_documents": [
        {{
            "document_type": "commercial_invoice|bill_of_lading|packing_list|certificate_of_origin|insurance_certificate|inspection_certificate|beneficiary_certificate|draft|other",
            "display_name": "Human readable name",
            "source_clause": "46A|47A|etc",
            "source_text": "Original clause text",
            "requirement_type": "mandatory|conditional|optional",
            "issuer": "Who must issue (if specified)",
            "copies_required": 3,
            "originals_required": 1,
            "must_contain": ["field1", "field2"],
            "must_state": "Exact wording if required",
            "obligations": [
                {{
                    "field": "what to check",
                    "expected": "expected value or condition",
                    "description": "human readable description"
                }}
            ]
        }}
    ],
    "bl_requirements": {{
        "clean": true,
        "on_board": true,
        "transport_mode": "ocean|multimodal|air",
        "full_set": true,
        "copies_required": 3,
        "consignee_type": "to_order|to_order_of_bank|named",
        "endorsement": "blank|specific",
        "notify_party": "party name or null",
        "freight": "prepaid|collect|any",
        "must_show": ["voyage_number", "gross_weight", "net_weight", "container_number", "seal_number"],
        "transshipment_allowed": true
    }},
    "tolerances": {{
        "amount": {{
            "value": 458750.00,
            "tolerance_pct": 5,
            "explicit": false,
            "source": "UCP600 Art 30 (default)"
        }},
        "quantity": {{
            "value": 30000,
            "unit": "pcs",
            "tolerance_pct": 10,
            "explicit": true,
            "source": "45A explicit"
        }}
    }},
    "contradictions": [
        {{
            "clause_1": "46A",
            "clause_1_says": "Full set 3/3 original B/L",
            "clause_2": "47A", 
            "clause_2_says": "1/3 original B/L acceptable",
            "conflict_type": "document_copies",
            "resolution": "47A overrides - 1/3 acceptable",
            "confidence": 0.90
        }}
    ],
    "special_conditions": [
        "No Israeli flag vessels",
        "Goods must be brand new",
        "Country of origin printed on cartons"
    ],
    "presentation_period_days": 21,
    "latest_shipment_date": "2026-09-30",
    "expiry_date": "2026-10-15"
}}

IMPORTANT RULES:
1. If amount tolerance not stated, default to 5% per UCP600 Article 30
2. If quantity tolerance not stated, default to 5% per UCP600 Article 30  
3. Extract ALL document requirements from 46A
4. Extract ALL conditions from 47A
5. Flag any contradictions between clauses
6. Look for special prohibitions (Israeli vessels, specific shipping lines, etc.)

Return ONLY valid JSON, no explanation or markdown.'''


# =============================================================================
# LLM PARSER
# =============================================================================

async def parse_lc_requirements_llm(
    lc_text: str,
    llm_provider: Any,
    bank_profile: Optional[str] = None,
    force_refresh: bool = False,
) -> RequirementGraph:
    """
    Parse LC requirements using LLM.
    
    Args:
        lc_text: Full LC text
        llm_provider: LLM provider instance
        bank_profile: Optional bank-specific profile (e.g., "icbc", "hsbc")
        force_refresh: Skip cache and re-parse
        
    Returns:
        RequirementGraph with all extracted requirements
    """
    # Check cache first
    if not force_refresh:
        cached = get_cached_requirements(lc_text)
        if cached:
            return cached
    
    # Generate cache key
    lc_hash = _get_cache_key(lc_text)
    
    # Build prompt
    prompt = REQUIREMENT_EXTRACTION_PROMPT.format(lc_text=lc_text)
    
    logger.info(f"Parsing LC requirements via LLM (hash={lc_hash[:16]}...)")
    
    try:
        # Call LLM
        response = await llm_provider.generate(prompt)
        
        # Handle tuple response (text, tokens_in, tokens_out)
        if isinstance(response, tuple):
            response_text = response[0]
        else:
            response_text = response
        
        # Parse JSON response
        # Clean up response - remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        parsed = json.loads(response_text)
        
        # Build RequirementGraph
        requirements = _build_requirement_graph(lc_hash, parsed)
        
        # Cache result
        cache_requirements(lc_text, requirements)
        
        logger.info(
            f"Parsed LC: {len(requirements.required_documents)} documents, "
            f"{len(requirements.tolerances)} tolerances, "
            f"{len(requirements.contradictions)} contradictions"
        )
        
        return requirements
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Fall back to regex-based parsing
        return _fallback_regex_parse(lc_text, lc_hash)
    except Exception as e:
        logger.error(f"LLM parsing failed: {e}", exc_info=True)
        return _fallback_regex_parse(lc_text, lc_hash)


def _build_requirement_graph(lc_hash: str, parsed: Dict[str, Any]) -> RequirementGraph:
    """Build RequirementGraph from parsed JSON."""
    
    # Build document requirements
    required_docs = []
    for doc in parsed.get("required_documents", []):
        obligations = []
        for idx, obl in enumerate(doc.get("obligations", [])):
            obligations.append(NestedObligation(
                obligation_id=f"{doc.get('document_type', 'doc')}_{idx}",
                description=obl.get("description", ""),
                field_to_check=obl.get("field", ""),
                expected_value=obl.get("expected", ""),
                source_clause=doc.get("source_clause", "46A"),
                source_text=doc.get("source_text", ""),
            ))
        
        # Build filename patterns for document type inference
        doc_type = doc.get("document_type", "")
        filename_patterns = _get_filename_patterns(doc_type)
        
        required_docs.append(DocumentRequirement(
            document_type=doc_type,
            display_name=doc.get("display_name", doc_type),
            requirement_type=DocumentRequirementType(doc.get("requirement_type", "mandatory")),
            source_clause=doc.get("source_clause", "46A"),
            obligations=obligations,
            issuer=doc.get("issuer"),
            must_contain=doc.get("must_contain", []),
            must_state=doc.get("must_state"),
            copies_required=doc.get("copies_required", 1),
            originals_required=doc.get("originals_required", 0),
            filename_patterns=filename_patterns,
        ))
    
    # Build B/L requirements
    bl_req_data = parsed.get("bl_requirements", {})
    bl_requirements = BLRequirements(
        clean=bl_req_data.get("clean", True),
        on_board=bl_req_data.get("on_board", True),
        transport_mode=bl_req_data.get("transport_mode", "ocean"),
        full_set=bl_req_data.get("full_set", True),
        copies_required=bl_req_data.get("copies_required", 3),
        consignee_type=bl_req_data.get("consignee_type", "to_order"),
        endorsement=bl_req_data.get("endorsement", "blank"),
        notify_party_required=bl_req_data.get("notify_party") is not None,
        freight_indication=bl_req_data.get("freight", "any"),
        transshipment_allowed=bl_req_data.get("transshipment_allowed", True),
        must_show_fields=bl_req_data.get("must_show", []),
    ) if bl_req_data else None
    
    # Build tolerances
    tolerances = {}
    for field_name, tol_data in parsed.get("tolerances", {}).items():
        source = ToleranceSource.UCP600_ART_30
        if tol_data.get("explicit"):
            source = ToleranceSource.EXPLICIT_LC
        elif "art 39" in str(tol_data.get("source", "")).lower():
            source = ToleranceSource.UCP600_ART_39
        
        tolerances[field_name] = ToleranceRule(
            field=field_name,
            base_value=float(tol_data.get("value", 0)),
            tolerance_percent=float(tol_data.get("tolerance_pct", 5)),
            source=source,
            explicit=tol_data.get("explicit", False),
            clause_reference=tol_data.get("source"),
        )
    
    # Add default tolerances if not present
    if "amount" not in tolerances:
        tolerances["amount"] = ToleranceRule(
            field="amount",
            base_value=0,  # Will be set from LC
            tolerance_percent=5.0,
            source=ToleranceSource.UCP600_ART_30,
            explicit=False,
        )
    if "quantity" not in tolerances:
        tolerances["quantity"] = ToleranceRule(
            field="quantity", 
            base_value=0,
            tolerance_percent=5.0,
            source=ToleranceSource.UCP600_ART_30,
            explicit=False,
        )
    
    # Build contradictions
    contradictions = []
    for idx, cont in enumerate(parsed.get("contradictions", [])):
        contradictions.append(Contradiction(
            contradiction_id=f"CONTRA_{idx}",
            clause_1=cont.get("clause_1", ""),
            clause_1_text=cont.get("clause_1_says", ""),
            clause_2=cont.get("clause_2", ""),
            clause_2_text=cont.get("clause_2_says", ""),
            conflict_type=cont.get("conflict_type", "unknown"),
            resolution=cont.get("resolution", ""),
            enforced_clause=cont.get("clause_2", ""),  # Default: later clause wins
            confidence=float(cont.get("confidence", 0.8)),
        ))
    
    # Build document type mapping for inference
    doc_type_mapping = {}
    for doc in required_docs:
        doc_type_mapping[doc.document_type] = {
            "acceptable_names": doc.filename_patterns,
            "issuer": doc.issuer,
            "must_contain": doc.must_contain,
        }
    
    return RequirementGraph(
        lc_hash=lc_hash,
        parsed_at=datetime.utcnow().isoformat(),
        required_documents=required_docs,
        bl_requirements=bl_requirements,
        tolerances=tolerances,
        contradictions=contradictions,
        special_conditions=parsed.get("special_conditions", []),
        prohibited_items=[c for c in parsed.get("special_conditions", []) if "israeli" in c.lower() or "prohibited" in c.lower()],
        document_type_mapping=doc_type_mapping,
        presentation_period_days=parsed.get("presentation_period_days", 21),
        latest_shipment_date=parsed.get("latest_shipment_date"),
        expiry_date=parsed.get("expiry_date"),
    )


def _get_filename_patterns(doc_type: str) -> List[str]:
    """Get filename patterns for document type inference."""
    patterns = {
        "commercial_invoice": ["invoice", "inv", "commercial", "ci"],
        "bill_of_lading": ["bl", "b/l", "bill_of_lading", "lading", "bol"],
        "packing_list": ["packing", "pl", "pack_list", "packing_list"],
        "certificate_of_origin": ["origin", "coo", "co", "certificate_of_origin"],
        "insurance_certificate": ["insurance", "ins", "policy", "ins_cert"],
        "inspection_certificate": ["inspection", "sgs", "intertek", "insp", "quality"],
        "beneficiary_certificate": ["beneficiary", "ben_cert", "bene"],
        "draft": ["draft", "bill_of_exchange", "boe"],
        "letter_of_credit": ["lc", "letter_of_credit", "credit", "mt700"],
    }
    return patterns.get(doc_type, [doc_type])


def _fallback_regex_parse(lc_text: str, lc_hash: str) -> RequirementGraph:
    """Fallback regex-based parsing if LLM fails."""
    logger.warning("Using fallback regex parser")
    
    # Import existing parser
    from app.services.validation.ai_validator import parse_lc_requirements_sync
    
    parsed = parse_lc_requirements_sync(lc_text)
    
    # Convert to RequirementGraph format
    required_docs = []
    for doc in parsed.get("required_documents", []):
        required_docs.append(DocumentRequirement(
            document_type=doc.get("document_type", ""),
            display_name=doc.get("display_name", ""),
            requirement_type=DocumentRequirementType.MANDATORY,
            source_clause="46A",
            issuer=doc.get("issuer"),
            must_state=doc.get("must_state"),
            filename_patterns=_get_filename_patterns(doc.get("document_type", "")),
        ))
    
    bl_must_show = parsed.get("bl_must_show", [])
    bl_requirements = BLRequirements(
        must_show_fields=bl_must_show,
    ) if bl_must_show else None
    
    return RequirementGraph(
        lc_hash=lc_hash,
        parsed_at=datetime.utcnow().isoformat(),
        required_documents=required_docs,
        bl_requirements=bl_requirements,
        tolerances={
            "amount": ToleranceRule(
                field="amount",
                base_value=0,
                tolerance_percent=5.0,
                source=ToleranceSource.UCP600_ART_30,
                explicit=False,
            ),
            "quantity": ToleranceRule(
                field="quantity",
                base_value=0,
                tolerance_percent=5.0,
                source=ToleranceSource.UCP600_ART_30,
                explicit=False,
            ),
        },
    )


# =============================================================================
# SYNCHRONOUS WRAPPER
# =============================================================================

def parse_lc_requirements_sync_v2(lc_text: str) -> RequirementGraph:
    """
    Synchronous version using regex parsing.
    Use this when LLM is not available or for quick parsing.
    """
    lc_hash = _get_cache_key(lc_text)
    
    # Check cache
    cached = get_cached_requirements(lc_text)
    if cached:
        return cached
    
    # Use fallback parser
    requirements = _fallback_regex_parse(lc_text, lc_hash)
    
    # Cache result
    cache_requirements(lc_text, requirements)
    
    return requirements


# =============================================================================
# DOCUMENT TYPE INFERENCE
# =============================================================================

def infer_document_type(
    filename: str,
    extracted_fields: Dict[str, Any],
    requirement_graph: Optional[RequirementGraph] = None,
) -> Tuple[str, float]:
    """
    Infer document type from filename and extracted content.
    
    Returns:
        Tuple of (document_type, confidence)
    """
    filename_lower = filename.lower()
    confidence = 0.5  # Base confidence
    
    # Check against requirement graph mappings first
    if requirement_graph:
        for doc_type, mapping in requirement_graph.document_type_mapping.items():
            for pattern in mapping.get("acceptable_names", []):
                if pattern.lower() in filename_lower:
                    return doc_type, 0.9
    
    # Standard filename matching
    type_patterns = {
        "commercial_invoice": ["invoice", "inv", "commercial"],
        "bill_of_lading": ["bl", "lading", "bol", "bill_of_lading"],
        "packing_list": ["packing", "pack", "pl"],
        "certificate_of_origin": ["origin", "coo", "certificate_of_origin"],
        "insurance_certificate": ["insurance", "ins_cert", "policy"],
        "inspection_certificate": ["inspection", "sgs", "intertek", "quality"],
        "beneficiary_certificate": ["beneficiary", "bene_cert"],
        "letter_of_credit": ["lc", "credit", "mt700", "letter_of_credit"],
    }
    
    for doc_type, patterns in type_patterns.items():
        for pattern in patterns:
            if pattern in filename_lower:
                return doc_type, 0.85
    
    # Check extracted fields for hints
    if extracted_fields:
        if "lc_number" in extracted_fields and "amount" in extracted_fields:
            if "applicant" in extracted_fields:
                return "letter_of_credit", 0.8
            return "commercial_invoice", 0.7
        if "shipper" in extracted_fields and "consignee" in extracted_fields:
            return "bill_of_lading", 0.75
        if "cartons" in extracted_fields or "gross_weight" in extracted_fields:
            return "packing_list", 0.7
    
    return "unknown", 0.3


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "RequirementGraph",
    "DocumentRequirement",
    "NestedObligation",
    "ToleranceRule",
    "ToleranceSource",
    "Contradiction",
    "BLRequirements",
    "parse_lc_requirements_llm",
    "parse_lc_requirements_sync_v2",
    "get_cached_requirements",
    "infer_document_type",
]

