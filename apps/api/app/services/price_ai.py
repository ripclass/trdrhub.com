"""
AI-Powered Price Verification Enhancements

Adds intelligent features to price verification:
1. Commodity suggestions for typos/variations
2. Price variance explanations
3. TBML risk narratives
"""

import logging
import re
from typing import Dict, Any, List, Optional

from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

# =============================================================================
# AI PROMPTS
# =============================================================================

COMMODITY_SUGGESTION_SYSTEM = """You are an expert in international trade commodities.
Your task is to help identify commodities from potentially misspelled or varied descriptions.
Be precise and suggest only real, tradeable commodities."""

COMMODITY_SUGGESTION_PROMPT = """The user searched for: "{search_term}"

We couldn't find an exact match in our commodity database. Based on the search term, suggest what commodity they might be looking for.

Consider:
- Common misspellings (e.g., "coton" → "cotton", "steal" → "steel")
- Trade name variations (e.g., "black gold" → "crude oil")
- Regional names (e.g., "maize" → "corn")
- HS code prefixes if provided

Our database includes these categories:
- Agriculture: cotton, rice, wheat, sugar, coffee, cocoa, soybeans, corn, palm oil, tea, rubber, jute
- Energy: crude oil, natural gas, coal, LNG
- Metals: copper, aluminum, zinc, nickel, tin, lead, iron ore, steel, gold, silver, platinum
- Textiles: cotton yarn, polyester, denim, garments
- Chemicals: urea, fertilizers, plastics, polymers
- Food & Beverage: shrimp, fish, beef, chicken, fruits
- Electronics: semiconductors, LEDs, solar panels, batteries

Return a JSON object:
{{
    "likely_commodity": "the most likely commodity name",
    "confidence": 0.0-1.0,
    "alternatives": ["other possible matches"],
    "reasoning": "brief explanation of why this match"
}}

Only return JSON, no other text."""


VARIANCE_EXPLANATION_SYSTEM = """You are a trade finance expert explaining price variances to compliance officers and bankers.
Your explanations should be professional, concise, and actionable.
Consider market conditions, seasonal factors, and trade dynamics."""

VARIANCE_EXPLANATION_PROMPT = """Explain this price variance for a compliance review:

**Commodity:** {commodity_name} ({commodity_code})
**Category:** {category}
**Document Price:** ${doc_price:,.2f} per {unit}
**Market Price:** ${market_price:,.2f} per {unit}
**Variance:** {variance_percent:+.1f}% ({direction})
**Risk Level:** {risk_level}

Provide a brief, professional explanation that:
1. States whether this variance is concerning or acceptable
2. Lists 2-3 possible legitimate reasons for this variance
3. Suggests what documentation might justify this price

Keep it under 100 words. Be direct and professional.

Return a JSON object:
{{
    "summary": "One sentence assessment",
    "possible_reasons": ["reason 1", "reason 2", "reason 3"],
    "documentation_needed": ["doc 1", "doc 2"],
    "recommendation": "approve/review/escalate"
}}"""


TBML_NARRATIVE_SYSTEM = """You are a financial crimes compliance expert specializing in Trade-Based Money Laundering (TBML).
Your analysis should be thorough, professional, and suitable for regulatory review.
Reference actual TBML red flags and typologies."""

TBML_NARRATIVE_PROMPT = """Generate a TBML risk assessment narrative for this transaction:

**Commodity:** {commodity_name}
**Document Price:** ${doc_price:,.2f} per {unit}
**Market Price:** ${market_price:,.2f} per {unit}
**Variance:** {variance_percent:+.1f}%
**Direction:** {direction} (over-invoicing / under-invoicing)
**Risk Flags:** {risk_flags}

Consider these TBML typologies:
- Over-invoicing: Inflated prices to move money out of a country
- Under-invoicing: Deflated prices to evade customs duties or move money in
- Multiple invoicing: Same goods invoiced multiple times
- Phantom shipments: Goods described but never shipped

Generate a professional compliance narrative that:
1. Identifies the specific TBML concern
2. Explains why this variance is suspicious
3. Lists red flags present in this transaction
4. Recommends specific due diligence steps

Return a JSON object:
{{
    "tbml_type": "over_invoicing/under_invoicing/other",
    "risk_score": 1-10,
    "narrative": "2-3 paragraph compliance narrative",
    "red_flags": ["flag 1", "flag 2"],
    "due_diligence_steps": ["step 1", "step 2", "step 3"],
    "regulatory_references": ["FATF Guidance on TBML", "FinCEN Advisory"]
}}"""


# =============================================================================
# AI SERVICE CLASS
# =============================================================================

class PriceVerificationAI:
    """AI-powered enhancements for price verification."""
    
    def __init__(self):
        self.llm = LLMProvider()
    
    async def suggest_commodity(
        self,
        search_term: str,
        available_commodities: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Use AI to suggest the correct commodity for a misspelled/varied search term.
        
        Args:
            search_term: User's search input
            available_commodities: Optional list of available commodity names
            
        Returns:
            Dict with likely_commodity, confidence, alternatives, reasoning
        """
        try:
            prompt = COMMODITY_SUGGESTION_PROMPT.format(search_term=search_term)
            
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=COMMODITY_SUGGESTION_SYSTEM,
                temperature=0.3,
                max_tokens=500,
            )
            
            return self._parse_json_response(response, {
                "likely_commodity": None,
                "confidence": 0.0,
                "alternatives": [],
                "reasoning": "Could not determine commodity",
            })
            
        except Exception as e:
            logger.error(f"AI commodity suggestion error: {e}")
            return {
                "likely_commodity": None,
                "confidence": 0.0,
                "alternatives": [],
                "reasoning": f"AI suggestion unavailable: {str(e)}",
            }
    
    async def explain_variance(
        self,
        commodity_name: str,
        commodity_code: str,
        category: str,
        doc_price: float,
        market_price: float,
        unit: str,
        variance_percent: float,
        risk_level: str,
    ) -> Dict[str, Any]:
        """
        Generate an AI explanation for price variance.
        
        Returns professional explanation suitable for compliance review.
        """
        try:
            direction = "above market" if variance_percent > 0 else "below market"
            
            prompt = VARIANCE_EXPLANATION_PROMPT.format(
                commodity_name=commodity_name,
                commodity_code=commodity_code,
                category=category,
                doc_price=doc_price,
                market_price=market_price,
                unit=unit,
                variance_percent=variance_percent,
                direction=direction,
                risk_level=risk_level,
            )
            
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=VARIANCE_EXPLANATION_SYSTEM,
                temperature=0.4,
                max_tokens=600,
            )
            
            return self._parse_json_response(response, {
                "summary": f"Price is {abs(variance_percent):.1f}% {direction}.",
                "possible_reasons": ["Market fluctuation", "Quality premium", "Regional pricing"],
                "documentation_needed": ["Price justification letter", "Market comparison"],
                "recommendation": "review" if abs(variance_percent) > 15 else "approve",
            })
            
        except Exception as e:
            logger.error(f"AI variance explanation error: {e}")
            return {
                "summary": f"Price variance of {variance_percent:+.1f}% detected.",
                "possible_reasons": ["Unable to determine - AI unavailable"],
                "documentation_needed": ["Supporting documentation recommended"],
                "recommendation": "review",
                "error": str(e),
            }
    
    async def generate_tbml_narrative(
        self,
        commodity_name: str,
        doc_price: float,
        market_price: float,
        unit: str,
        variance_percent: float,
        risk_flags: List[str],
    ) -> Dict[str, Any]:
        """
        Generate a professional TBML risk narrative for compliance review.
        
        Only called when TBML risk flags are present (variance > 50%).
        """
        try:
            direction = "over-invoicing" if variance_percent > 0 else "under-invoicing"
            
            prompt = TBML_NARRATIVE_PROMPT.format(
                commodity_name=commodity_name,
                doc_price=doc_price,
                market_price=market_price,
                unit=unit,
                variance_percent=variance_percent,
                direction=direction,
                risk_flags=", ".join(risk_flags) if risk_flags else "High variance detected",
            )
            
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=TBML_NARRATIVE_SYSTEM,
                temperature=0.3,
                max_tokens=1000,
            )
            
            return self._parse_json_response(response, {
                "tbml_type": direction.replace("-", "_"),
                "risk_score": 8,
                "narrative": f"This transaction shows a significant price variance of {abs(variance_percent):.1f}% "
                            f"which may indicate {direction}. Enhanced due diligence is recommended.",
                "red_flags": risk_flags or ["Significant price deviation from market"],
                "due_diligence_steps": [
                    "Verify supplier/buyer legitimacy",
                    "Request price justification documentation",
                    "Cross-check with independent market sources",
                ],
                "regulatory_references": ["FATF Guidance on Trade-Based Money Laundering"],
            })
            
        except Exception as e:
            logger.error(f"AI TBML narrative error: {e}")
            return {
                "tbml_type": "unknown",
                "risk_score": 7,
                "narrative": f"TBML risk detected: {abs(variance_percent):.1f}% price variance. "
                            "Manual compliance review required.",
                "red_flags": risk_flags or ["High price variance"],
                "due_diligence_steps": ["Conduct manual compliance review"],
                "regulatory_references": [],
                "error": str(e),
            }
    
    def _parse_json_response(
        self,
        response: str,
        default: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse JSON from LLM response with fallback."""
        import json
        
        if not response:
            return default
        
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return default


# Singleton instance
_ai_service: Optional[PriceVerificationAI] = None


def get_price_ai_service() -> PriceVerificationAI:
    """Get or create the price AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = PriceVerificationAI()
    return _ai_service

