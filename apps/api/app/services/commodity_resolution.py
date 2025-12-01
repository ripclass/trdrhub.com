"""
Commodity Resolution Service

The CORE service that resolves commodity names to verified data.
This service NEVER crashes - it always returns a usable result.

Resolution Chain:
1. Exact match in commodities database
2. Fuzzy match against names and aliases
3. HS code lookup (if HS code provided or extractable)
4. AI-assisted classification and estimation
5. Fallback with user guidance

Every step returns a valid result - the system is designed to NEVER fail.
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ResolutionSource(str, Enum):
    """How the commodity was resolved."""
    EXACT_MATCH = "exact_match"          # Found in our database
    FUZZY_MATCH = "fuzzy_match"          # Similar match in database
    HS_CODE = "hs_code"                  # Resolved via HS code
    AI_ESTIMATE = "ai_estimate"          # AI classification
    CATEGORY_FALLBACK = "category_fallback"  # Category-based estimate
    MANUAL = "manual"                    # User-provided data
    UNKNOWN = "unknown"                  # Completely unknown, basic fallback


@dataclass
class ResolvedCommodity:
    """
    Result of commodity resolution.
    Always contains usable data - NEVER None for critical fields.
    """
    # Identification
    name: str                            # The commodity name (original or matched)
    code: Optional[str]                  # Our internal code if matched
    commodity_id: Optional[str]          # Database ID if matched
    
    # Classification
    category: str                        # e.g., "seafood", "agriculture"
    unit: str                            # e.g., "kg", "mt"
    
    # Price information
    price_low: Optional[float]           # Estimated range low
    price_high: Optional[float]          # Estimated range high
    current_estimate: Optional[float]    # Best current estimate
    
    # Resolution metadata
    source: ResolutionSource             # How was this resolved?
    confidence: float                    # 0.0 to 1.0
    matched_to: Optional[str]            # If fuzzy matched, what did it match to?
    hs_code: Optional[str]               # HS code if known
    
    # Quality indicators
    verified: bool                       # Is this admin-verified data?
    has_live_feed: bool                  # Do we have live price data?
    
    # User guidance
    suggestions: List[str]               # Suggestions for user
    warnings: List[str]                  # Warnings to display
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "name": self.name,
            "code": self.code,
            "commodity_id": self.commodity_id,
            "category": self.category,
            "unit": self.unit,
            "price_low": self.price_low,
            "price_high": self.price_high,
            "current_estimate": self.current_estimate,
            "source": self.source.value,
            "confidence": self.confidence,
            "matched_to": self.matched_to,
            "hs_code": self.hs_code,
            "verified": self.verified,
            "has_live_feed": self.has_live_feed,
            "suggestions": self.suggestions,
            "warnings": self.warnings,
        }


class CommodityResolutionService:
    """
    Service that resolves any commodity name to usable price verification data.
    
    Design Principle: NEVER CRASH, ALWAYS RETURN SOMETHING USEFUL.
    
    Usage:
        service = CommodityResolutionService(db_session)
        result = await service.resolve("dry fish")
        # result is ALWAYS a valid ResolvedCommodity
    """
    
    # Category-based fallback estimates (USD per typical unit)
    CATEGORY_DEFAULTS = {
        "seafood": {"unit": "kg", "low": 3, "high": 50},
        "agriculture": {"unit": "mt", "low": 200, "high": 1000},
        "vegetables": {"unit": "kg", "low": 0.5, "high": 10},
        "fruits": {"unit": "kg", "low": 0.5, "high": 15},
        "spices": {"unit": "kg", "low": 2, "high": 100},
        "beverages": {"unit": "kg", "low": 2, "high": 50},
        "textiles": {"unit": "kg", "low": 2, "high": 20},
        "metals": {"unit": "mt", "low": 500, "high": 10000},
        "precious_metals": {"unit": "oz", "low": 15, "high": 2500},
        "energy": {"unit": "barrel", "low": 40, "high": 150},
        "electronics": {"unit": "unit", "low": 50, "high": 5000},
        "chemicals": {"unit": "kg", "low": 1, "high": 50},
        "machinery": {"unit": "unit", "low": 100, "high": 100000},
        "general": {"unit": "kg", "low": 1, "high": 100},  # Ultimate fallback
    }
    
    # Keywords for category detection
    CATEGORY_KEYWORDS = {
        "seafood": ["fish", "shrimp", "crab", "lobster", "prawn", "squid", "seafood", "marine", "tuna", "salmon"],
        "agriculture": ["wheat", "rice", "corn", "maize", "soybean", "grain", "cereal", "paddy"],
        "vegetables": ["potato", "tomato", "onion", "garlic", "carrot", "vegetable", "lettuce"],
        "fruits": ["apple", "orange", "banana", "mango", "grape", "fruit", "citrus", "berry"],
        "spices": ["pepper", "spice", "turmeric", "ginger", "cinnamon", "cumin", "cardamom"],
        "beverages": ["coffee", "tea", "cocoa", "juice", "beverage"],
        "textiles": ["cotton", "fabric", "textile", "garment", "cloth", "yarn", "silk", "wool"],
        "metals": ["steel", "iron", "copper", "aluminum", "zinc", "metal", "alloy"],
        "precious_metals": ["gold", "silver", "platinum", "palladium", "precious"],
        "energy": ["oil", "petroleum", "crude", "gas", "fuel", "diesel", "lng", "lpg"],
        "electronics": ["phone", "computer", "laptop", "electronic", "chip", "semiconductor"],
        "chemicals": ["chemical", "acid", "polymer", "plastic", "fertilizer"],
        "machinery": ["machine", "equipment", "engine", "motor", "pump"],
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
    
    async def resolve(
        self,
        search_term: str,
        hs_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ResolvedCommodity:
        """
        Resolve a commodity search term to usable data.
        
        This method NEVER raises exceptions - it always returns a ResolvedCommodity.
        
        Args:
            search_term: The commodity name to search for (e.g., "dry fish")
            hs_code: Optional HS code if known from document
            context: Optional context (document type, country, etc.)
        
        Returns:
            ResolvedCommodity with usable data (never None)
        """
        search_term = search_term.strip()
        search_lower = search_term.lower()
        
        logger.info(f"Resolving commodity: '{search_term}', HS code: {hs_code}")
        
        # Step 1: Try exact match in database
        result = await self._try_exact_match(search_lower)
        if result:
            logger.info(f"Exact match found: {result.name}")
            return result
        
        # Step 2: Try fuzzy match
        result = await self._try_fuzzy_match(search_lower)
        if result and result.confidence >= 0.7:
            logger.info(f"Fuzzy match found: '{search_term}' → '{result.matched_to}' ({result.confidence:.0%})")
            return result
        
        # Step 3: Try HS code lookup
        if hs_code:
            result = await self._try_hs_code_lookup(hs_code, search_term)
            if result:
                logger.info(f"HS code match: {hs_code} → {result.category}")
                return result
        
        # Step 4: Try AI-assisted classification
        result = await self._try_ai_classification(search_term, context)
        if result and result.confidence >= 0.5:
            logger.info(f"AI classification: '{search_term}' → {result.category} ({result.confidence:.0%})")
            return result
        
        # Step 5: Category-based fallback using keyword detection
        result = self._category_fallback(search_term)
        logger.info(f"Category fallback: '{search_term}' → {result.category}")
        return result
    
    async def _try_exact_match(self, search_lower: str) -> Optional[ResolvedCommodity]:
        """Try exact match against commodities database."""
        if not self.db:
            return self._try_hardcoded_match(search_lower)
        
        try:
            from app.models.commodities import Commodity
            
            # Search by code, name, or aliases
            query = select(Commodity).where(
                or_(
                    func.lower(Commodity.code) == search_lower.upper().replace(" ", "_"),
                    func.lower(Commodity.name) == search_lower,
                    Commodity.aliases.contains([search_lower]),
                ),
                Commodity.is_active == True
            )
            
            result = self.db.execute(query).scalar_one_or_none()
            
            if result:
                return ResolvedCommodity(
                    name=result.name,
                    code=result.code,
                    commodity_id=str(result.id),
                    category=result.category,
                    unit=result.unit,
                    price_low=float(result.price_low) if result.price_low else None,
                    price_high=float(result.price_high) if result.price_high else None,
                    current_estimate=float(result.current_estimate) if result.current_estimate else None,
                    source=ResolutionSource.EXACT_MATCH,
                    confidence=1.0,
                    matched_to=None,
                    hs_code=result.hs_codes[0] if result.hs_codes else None,
                    verified=result.verified,
                    has_live_feed=bool(result.data_sources),
                    suggestions=[],
                    warnings=[],
                )
        except Exception as e:
            logger.warning(f"Database exact match failed: {e}")
        
        return self._try_hardcoded_match(search_lower)
    
    def _try_hardcoded_match(self, search_lower: str) -> Optional[ResolvedCommodity]:
        """Fallback to hardcoded commodities database."""
        try:
            from app.services.price_verification import COMMODITIES_DATABASE
            
            # Try direct code match
            code_upper = search_lower.upper().replace(" ", "_")
            if code_upper in COMMODITIES_DATABASE:
                data = COMMODITIES_DATABASE[code_upper]
                return self._commodity_from_hardcoded(code_upper, data)
            
            # Try name/alias match
            for code, data in COMMODITIES_DATABASE.items():
                if data["name"].lower() == search_lower:
                    return self._commodity_from_hardcoded(code, data)
                if search_lower in [a.lower() for a in data.get("aliases", [])]:
                    return self._commodity_from_hardcoded(code, data)
            
        except Exception as e:
            logger.warning(f"Hardcoded match failed: {e}")
        
        return None
    
    def _commodity_from_hardcoded(self, code: str, data: Dict) -> ResolvedCommodity:
        """Convert hardcoded commodity to ResolvedCommodity."""
        return ResolvedCommodity(
            name=data["name"],
            code=code,
            commodity_id=None,
            category=data.get("category", "general"),
            unit=data.get("unit", "kg"),
            price_low=data.get("typical_range", (None, None))[0],
            price_high=data.get("typical_range", (None, None))[1],
            current_estimate=data.get("current_estimate"),
            source=ResolutionSource.EXACT_MATCH,
            confidence=1.0,
            matched_to=None,
            hs_code=data.get("hs_codes", [None])[0],
            verified=True,  # Hardcoded = system-verified
            has_live_feed=bool(data.get("data_sources")),
            suggestions=[],
            warnings=[],
        )
    
    async def _try_fuzzy_match(self, search_lower: str) -> Optional[ResolvedCommodity]:
        """Try fuzzy matching against all commodities."""
        best_match = None
        best_score = 0.0
        best_commodity = None
        
        # Try database first
        if self.db:
            try:
                from app.models.commodities import Commodity
                commodities = self.db.execute(
                    select(Commodity).where(Commodity.is_active == True)
                ).scalars().all()
                
                for commodity in commodities:
                    # Check name similarity
                    score = self._similarity(search_lower, commodity.name.lower())
                    if score > best_score:
                        best_score = score
                        best_match = commodity.name
                        best_commodity = commodity
                    
                    # Check aliases
                    for alias in (commodity.aliases or []):
                        score = self._similarity(search_lower, alias.lower())
                        if score > best_score:
                            best_score = score
                            best_match = commodity.name
                            best_commodity = commodity
            except Exception as e:
                logger.warning(f"Database fuzzy match failed: {e}")
        
        # Also check hardcoded
        try:
            from app.services.price_verification import COMMODITIES_DATABASE
            
            for code, data in COMMODITIES_DATABASE.items():
                score = self._similarity(search_lower, data["name"].lower())
                if score > best_score:
                    best_score = score
                    best_match = data["name"]
                    best_commodity = (code, data)
                
                for alias in data.get("aliases", []):
                    score = self._similarity(search_lower, alias.lower())
                    if score > best_score:
                        best_score = score
                        best_match = data["name"]
                        best_commodity = (code, data)
        except Exception as e:
            logger.warning(f"Hardcoded fuzzy match failed: {e}")
        
        if best_score >= 0.6 and best_commodity:
            # Build result based on type
            if isinstance(best_commodity, tuple):
                code, data = best_commodity
                result = self._commodity_from_hardcoded(code, data)
            else:
                result = ResolvedCommodity(
                    name=best_commodity.name,
                    code=best_commodity.code,
                    commodity_id=str(best_commodity.id),
                    category=best_commodity.category,
                    unit=best_commodity.unit,
                    price_low=float(best_commodity.price_low) if best_commodity.price_low else None,
                    price_high=float(best_commodity.price_high) if best_commodity.price_high else None,
                    current_estimate=float(best_commodity.current_estimate) if best_commodity.current_estimate else None,
                    source=ResolutionSource.FUZZY_MATCH,
                    confidence=best_score,
                    matched_to=best_match,
                    hs_code=best_commodity.hs_codes[0] if best_commodity.hs_codes else None,
                    verified=best_commodity.verified,
                    has_live_feed=bool(best_commodity.data_sources),
                    suggestions=[f"Did you mean '{best_match}'?"],
                    warnings=["Price range is based on similar commodity"] if best_score < 0.85 else [],
                )
            
            # Update source and confidence
            result.source = ResolutionSource.FUZZY_MATCH
            result.confidence = best_score
            result.matched_to = best_match
            if best_score < 0.85:
                result.suggestions = [f"Did you mean '{best_match}'?"]
                result.warnings = ["Price range is based on similar commodity"]
            
            return result
        
        return None
    
    async def _try_hs_code_lookup(self, hs_code: str, original_name: str) -> Optional[ResolvedCommodity]:
        """Look up commodity category by HS code."""
        # Normalize HS code
        hs_code = re.sub(r'[^0-9]', '', hs_code)[:6]  # Keep first 6 digits
        
        if not self.db:
            return self._hs_code_hardcoded_lookup(hs_code, original_name)
        
        try:
            from app.models.commodities import HSCode
            
            # Try exact match first, then prefix matches
            for length in [6, 4, 2]:
                prefix = hs_code[:length]
                result = self.db.execute(
                    select(HSCode).where(HSCode.code.startswith(prefix))
                ).scalar_one_or_none()
                
                if result:
                    return ResolvedCommodity(
                        name=original_name,
                        code=None,
                        commodity_id=None,
                        category=result.category or "general",
                        unit=result.typical_unit or "kg",
                        price_low=float(result.price_range_low) if result.price_range_low else None,
                        price_high=float(result.price_range_high) if result.price_range_high else None,
                        current_estimate=None,
                        source=ResolutionSource.HS_CODE,
                        confidence=0.8 if length >= 4 else 0.6,
                        matched_to=result.description,
                        hs_code=hs_code,
                        verified=False,
                        has_live_feed=False,
                        suggestions=[f"HS Code {hs_code} → {result.description}"],
                        warnings=["Price range based on HS code category average"],
                    )
        except Exception as e:
            logger.warning(f"HS code lookup failed: {e}")
        
        return self._hs_code_hardcoded_lookup(hs_code, original_name)
    
    def _hs_code_hardcoded_lookup(self, hs_code: str, original_name: str) -> Optional[ResolvedCommodity]:
        """Hardcoded HS code chapter mapping."""
        HS_CHAPTERS = {
            "01": ("animals", "head", 100, 5000),
            "02": ("meat", "kg", 2, 30),
            "03": ("seafood", "kg", 3, 50),
            "04": ("dairy", "kg", 1, 20),
            "07": ("vegetables", "kg", 0.5, 10),
            "08": ("fruits", "kg", 0.5, 15),
            "09": ("spices", "kg", 2, 100),
            "10": ("agriculture", "mt", 200, 800),
            "12": ("agriculture", "mt", 300, 1500),
            "15": ("oils", "mt", 500, 2000),
            "17": ("sugar", "mt", 300, 800),
            "18": ("cocoa", "kg", 2, 15),
            "27": ("energy", "barrel", 40, 150),
            "52": ("textiles", "kg", 1.5, 8),
            "71": ("precious_metals", "oz", 15, 2500),
            "72": ("metals", "mt", 400, 1000),
            "74": ("metals", "mt", 5000, 12000),
            "76": ("metals", "mt", 1800, 3500),
            "84": ("machinery", "unit", 100, 50000),
            "85": ("electronics", "unit", 50, 5000),
        }
        
        chapter = hs_code[:2]
        if chapter in HS_CHAPTERS:
            cat, unit, low, high = HS_CHAPTERS[chapter]
            return ResolvedCommodity(
                name=original_name,
                code=None,
                commodity_id=None,
                category=cat,
                unit=unit,
                price_low=low,
                price_high=high,
                current_estimate=(low + high) / 2,
                source=ResolutionSource.HS_CODE,
                confidence=0.6,
                matched_to=f"HS Chapter {chapter}",
                hs_code=hs_code,
                verified=False,
                has_live_feed=False,
                suggestions=[f"Classified via HS code chapter {chapter}"],
                warnings=["Price range is a broad estimate based on HS chapter"],
            )
        
        return None
    
    async def _try_ai_classification(
        self,
        search_term: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ResolvedCommodity]:
        """Use AI to classify unknown commodity."""
        try:
            from app.services.ai_provider import get_ai_provider
            
            provider = get_ai_provider()
            
            prompt = f"""Classify this commodity for trade price verification:

Commodity: "{search_term}"

Respond with ONLY a JSON object:
{{
    "category": "one of: seafood, agriculture, vegetables, fruits, spices, beverages, textiles, metals, precious_metals, energy, electronics, chemicals, machinery, general",
    "typical_unit": "kg, mt, barrel, oz, unit, dozen",
    "price_range_low_usd": number,
    "price_range_high_usd": number,
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}}"""
            
            response = await provider.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3,
            )
            
            # Parse JSON from response
            import json
            # Find JSON in response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return ResolvedCommodity(
                    name=search_term,
                    code=None,
                    commodity_id=None,
                    category=data.get("category", "general"),
                    unit=data.get("typical_unit", "kg"),
                    price_low=data.get("price_range_low_usd"),
                    price_high=data.get("price_range_high_usd"),
                    current_estimate=None,
                    source=ResolutionSource.AI_ESTIMATE,
                    confidence=data.get("confidence", 0.5),
                    matched_to=None,
                    hs_code=None,
                    verified=False,
                    has_live_feed=False,
                    suggestions=[f"AI Classification: {data.get('reasoning', '')}"],
                    warnings=["Price range is an AI estimate - verify with market data"],
                )
                
        except Exception as e:
            logger.warning(f"AI classification failed: {e}")
        
        return None
    
    def _category_fallback(self, search_term: str) -> ResolvedCommodity:
        """
        Ultimate fallback - detect category from keywords and provide estimate.
        This NEVER fails - always returns something usable.
        """
        search_lower = search_term.lower()
        
        # Detect category from keywords
        detected_category = "general"
        best_keyword_count = 0
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in search_lower)
            if matches > best_keyword_count:
                best_keyword_count = matches
                detected_category = category
        
        # Get defaults for category
        defaults = self.CATEGORY_DEFAULTS.get(detected_category, self.CATEGORY_DEFAULTS["general"])
        
        return ResolvedCommodity(
            name=search_term,
            code=None,
            commodity_id=None,
            category=detected_category,
            unit=defaults["unit"],
            price_low=defaults["low"],
            price_high=defaults["high"],
            current_estimate=(defaults["low"] + defaults["high"]) / 2,
            source=ResolutionSource.CATEGORY_FALLBACK,
            confidence=0.3 if best_keyword_count > 0 else 0.1,
            matched_to=None,
            hs_code=None,
            verified=False,
            has_live_feed=False,
            suggestions=[
                f"Commodity '{search_term}' not in database",
                "Consider requesting addition for future verifications",
                f"Estimated as '{detected_category}' category"
            ],
            warnings=[
                "Using category-based estimate only",
                "Price range may not be accurate for this specific commodity",
                "Recommend manual price verification"
            ],
        )
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate string similarity ratio."""
        return SequenceMatcher(None, a, b).ratio()


# Singleton instance
_resolution_service: Optional[CommodityResolutionService] = None


def get_commodity_resolution_service(db_session: Optional[Session] = None) -> CommodityResolutionService:
    """Get or create commodity resolution service."""
    global _resolution_service
    if _resolution_service is None or db_session:
        _resolution_service = CommodityResolutionService(db_session)
    return _resolution_service

