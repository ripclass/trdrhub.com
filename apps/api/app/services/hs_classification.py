"""
HS Code Classification Service

AI-powered HS code classification using OpenAI with chapter notes context.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - using fallback classification")


class HSClassificationService:
    """
    AI-powered HS code classification service.
    
    Uses OpenAI GPT-4 with context from:
    - Chapter notes and General Rules of Interpretation
    - Binding rulings from CBP CROSS database
    - Similar product classifications
    """
    
    # System prompt for HS classification
    SYSTEM_PROMPT = """You are an expert customs classification specialist with deep knowledge of the Harmonized System (HS) codes and WCO classification rules.

Your task is to classify products into the correct HS code following the General Rules of Interpretation (GRI):

GRI 1: Classification shall be determined according to the terms of the headings and any relative Section or Chapter Notes.

GRI 2(a): Any reference to an article shall include unfinished articles having the essential character of the finished article.

GRI 2(b): Mixtures and combinations of materials shall be classified as if they consisted of the material which gives them their essential character.

GRI 3: When goods are classifiable under two or more headings:
  (a) The heading which provides the most specific description shall be preferred
  (b) Mixtures shall be classified by the material that gives them essential character
  (c) When (a) and (b) fail, use the last heading in numerical order

GRI 4: Goods which cannot be classified shall be classified under the heading appropriate to the goods to which they are most akin.

GRI 5: Cases, containers, and packing materials are generally classified with the goods they contain.

GRI 6: Classification of goods in subheadings follows the same principles as headings.

When classifying:
1. First identify the Section and Chapter
2. Find the appropriate 4-digit heading
3. Narrow down to 6-digit subheading
4. Apply country-specific extensions (8-10 digit)
5. Consider any relevant binding rulings

Always provide:
- The recommended HS code
- Your reasoning citing specific GRI rules
- Confidence level (0-1)
- 2-3 alternative codes if uncertain
"""

    def __init__(self, db: Session):
        self.db = db
        self.client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
    
    async def classify_product(
        self,
        description: str,
        import_country: str = "US",
        export_country: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classify a product description to HS code using AI.
        
        Args:
            description: Product description in natural language
            import_country: Import destination (ISO 2-letter)
            export_country: Export origin (optional)
            additional_context: Additional context (material, use, etc.)
            
        Returns:
            Classification result with code, confidence, reasoning
        """
        # Get chapter notes context
        chapter_context = await self._get_chapter_context(description)
        
        # Get similar binding rulings
        ruling_context = await self._get_ruling_context(description)
        
        # Build the prompt
        user_prompt = self._build_classification_prompt(
            description=description,
            import_country=import_country,
            export_country=export_country,
            chapter_context=chapter_context,
            ruling_context=ruling_context,
            additional_context=additional_context
        )
        
        # Try OpenAI first
        if self.client:
            try:
                result = await self._classify_with_openai(user_prompt)
                if result:
                    return result
            except Exception as e:
                logger.error(f"OpenAI classification failed: {e}")
        
        # Fallback to keyword matching
        return await self._classify_with_fallback(description, import_country)
    
    async def _classify_with_openai(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI for classification."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for cost efficiency
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,  # Low temp for consistency
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validate required fields
            if "hs_code" not in result:
                logger.warning("OpenAI response missing hs_code")
                return None
            
            return {
                "hs_code": result.get("hs_code", ""),
                "description": result.get("description", ""),
                "confidence": float(result.get("confidence", 0.8)),
                "chapter": result.get("chapter", ""),
                "heading": result.get("heading", ""),
                "subheading": result.get("subheading", result.get("hs_code", "")[:6]),
                "alternatives": result.get("alternatives", []),
                "reasoning": result.get("reasoning", ""),
                "gri_applied": result.get("gri_applied", []),
                "source": "openai"
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    async def _classify_with_fallback(
        self, 
        description: str, 
        import_country: str
    ) -> Dict[str, Any]:
        """
        Fallback classification using keyword matching and database lookup.
        Used when OpenAI is unavailable.
        """
        from app.models.hs_code import HSCodeTariff
        
        desc_lower = description.lower()
        
        # Try to find matches in database
        results = self.db.query(HSCodeTariff).filter(
            HSCodeTariff.country_code == import_country,
            HSCodeTariff.is_active == True,
            or_(
                HSCodeTariff.description.ilike(f"%{desc_lower[:50]}%"),
                func.lower(HSCodeTariff.description).contains(desc_lower[:30])
            )
        ).limit(10).all()
        
        if results:
            best = results[0]
            return {
                "hs_code": best.code,
                "description": best.description,
                "confidence": 0.6,  # Lower confidence for fallback
                "chapter": best.chapter_description or f"Chapter {best.code_2}",
                "heading": best.heading_description or "",
                "subheading": best.code_6 or "",
                "alternatives": [
                    {"code": r.code, "description": r.description, "score": 0.5}
                    for r in results[1:4]
                ],
                "reasoning": f"Matched by description keyword search. Found {len(results)} potential matches.",
                "source": "database_fallback"
            }
        
        # Return default if nothing found
        return {
            "hs_code": "9999.99.9999",
            "description": "Unclassified - requires manual review",
            "confidence": 0.1,
            "chapter": "Chapter 99 - Special classification provisions",
            "heading": "",
            "subheading": "",
            "alternatives": [],
            "reasoning": "No matching classification found. Manual review recommended.",
            "source": "fallback_default"
        }
    
    async def _get_chapter_context(self, description: str) -> str:
        """Get relevant chapter notes for context."""
        from app.models.hs_code import ChapterNote
        
        # Keywords that suggest certain chapters
        chapter_hints = {
            "01": ["animal", "live", "horse", "cattle", "poultry"],
            "02": ["meat", "beef", "pork", "chicken", "frozen meat"],
            "03": ["fish", "seafood", "shrimp", "salmon", "tuna"],
            "61": ["apparel", "clothing", "knitted", "t-shirt", "sweater"],
            "62": ["apparel", "clothing", "woven", "shirt", "pants", "jacket"],
            "84": ["machine", "machinery", "engine", "pump", "turbine", "computer"],
            "85": ["electrical", "electronic", "motor", "phone", "television"],
            "87": ["vehicle", "car", "truck", "automobile", "motorcycle"],
            "90": ["optical", "medical", "instrument", "camera", "lens"],
        }
        
        desc_lower = description.lower()
        relevant_chapters = []
        
        for chapter, keywords in chapter_hints.items():
            if any(kw in desc_lower for kw in keywords):
                relevant_chapters.append(chapter)
        
        if not relevant_chapters:
            return ""
        
        # Get notes for relevant chapters
        notes = self.db.query(ChapterNote).filter(
            ChapterNote.chapter.in_(relevant_chapters),
            ChapterNote.is_active == True
        ).limit(5).all()
        
        if not notes:
            return ""
        
        context = "Relevant Chapter Notes:\n"
        for note in notes:
            context += f"\nChapter {note.chapter} - {note.note_type} {note.note_number}:\n{note.note_text[:500]}\n"
        
        return context
    
    async def _get_ruling_context(self, description: str) -> str:
        """Get similar binding rulings for context."""
        from app.models.hs_code import BindingRuling
        
        # Simple keyword search for similar rulings
        words = description.lower().split()[:5]  # First 5 words
        
        rulings = []
        for word in words:
            if len(word) > 3:  # Skip short words
                found = self.db.query(BindingRuling).filter(
                    BindingRuling.is_active == True,
                    or_(
                        BindingRuling.product_description.ilike(f"%{word}%"),
                        BindingRuling.keywords.contains([word])
                    )
                ).limit(3).all()
                rulings.extend(found)
        
        if not rulings:
            return ""
        
        # Deduplicate
        seen = set()
        unique_rulings = []
        for r in rulings:
            if r.ruling_number not in seen:
                seen.add(r.ruling_number)
                unique_rulings.append(r)
        
        context = "Similar Binding Rulings:\n"
        for r in unique_rulings[:3]:
            context += f"\nRuling {r.ruling_number}: {r.product_description[:200]}\n"
            context += f"Classified as: {r.hs_code}\n"
            if r.reasoning:
                context += f"Reasoning: {r.reasoning[:300]}\n"
        
        return context
    
    def _build_classification_prompt(
        self,
        description: str,
        import_country: str,
        export_country: Optional[str],
        chapter_context: str,
        ruling_context: str,
        additional_context: Optional[str]
    ) -> str:
        """Build the user prompt for classification."""
        prompt = f"""Please classify the following product for import into {import_country}:

PRODUCT DESCRIPTION:
{description}

"""
        if export_country:
            prompt += f"ORIGIN COUNTRY: {export_country}\n\n"
        
        if additional_context:
            prompt += f"ADDITIONAL CONTEXT:\n{additional_context}\n\n"
        
        if chapter_context:
            prompt += f"{chapter_context}\n\n"
        
        if ruling_context:
            prompt += f"{ruling_context}\n\n"
        
        prompt += """Please respond in JSON format with:
{
    "hs_code": "XXXX.XX.XXXX",
    "description": "Official HS code description",
    "confidence": 0.0-1.0,
    "chapter": "Chapter description",
    "heading": "4-digit heading description",
    "subheading": "6-digit subheading",
    "alternatives": [
        {"code": "alternative code", "description": "description", "score": 0.0-1.0}
    ],
    "reasoning": "Explanation of classification decision citing GRI rules",
    "gri_applied": ["GRI 1", "GRI 3a"]
}"""
        
        return prompt
    
    async def get_duty_rates(
        self,
        hs_code: str,
        import_country: str,
        export_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get duty rates for an HS code."""
        from app.models.hs_code import HSCodeTariff, DutyRate, Section301Rate, FTAAgreement, FTARule
        
        # Find the HS code
        tariff = self.db.query(HSCodeTariff).filter(
            HSCodeTariff.code == hs_code,
            HSCodeTariff.country_code == import_country
        ).first()
        
        if not tariff:
            # Try partial match
            tariff = self.db.query(HSCodeTariff).filter(
                HSCodeTariff.code.startswith(hs_code[:6]),
                HSCodeTariff.country_code == import_country
            ).first()
        
        rates = {
            "hs_code": hs_code,
            "import_country": import_country,
            "mfn_rate": 0,
            "preferential_rates": {},
            "section_301_rate": 0,
            "total_rate": 0
        }
        
        if tariff:
            # Get duty rates
            duty_rates = self.db.query(DutyRate).filter(
                DutyRate.hs_code_id == tariff.id,
                DutyRate.is_active == True
            ).all()
            
            for rate in duty_rates:
                if rate.rate_type == "mfn":
                    rates["mfn_rate"] = rate.ad_valorem_rate or 0
                elif rate.origin_country:
                    rates["preferential_rates"][rate.origin_country] = {
                        "rate": rate.ad_valorem_rate or 0,
                        "rate_code": rate.rate_code
                    }
        
        # Check Section 301 rates (US-China)
        if import_country == "US" and export_country == "CN":
            s301 = self.db.query(Section301Rate).filter(
                Section301Rate.hs_code == hs_code,
                Section301Rate.origin_country == "CN",
                Section301Rate.is_active == True,
                Section301Rate.is_excluded == False
            ).first()
            
            if s301:
                rates["section_301_rate"] = s301.additional_rate
                rates["section_301_list"] = s301.list_number
        
        # Calculate total
        base_rate = rates["mfn_rate"]
        if export_country and export_country in rates["preferential_rates"]:
            base_rate = rates["preferential_rates"][export_country]["rate"]
        
        rates["total_rate"] = base_rate + rates.get("section_301_rate", 0)
        
        return rates
    
    async def check_fta_eligibility(
        self,
        hs_code: str,
        import_country: str,
        export_country: str
    ) -> Dict[str, Any]:
        """Check FTA eligibility for a trade lane."""
        from app.models.hs_code import FTAAgreement, FTARule
        
        # Find applicable FTAs
        eligible_ftas = []
        
        ftas = self.db.query(FTAAgreement).filter(
            FTAAgreement.is_active == True,
            FTAAgreement.member_countries.contains([export_country]),
            FTAAgreement.member_countries.contains([import_country])
        ).all()
        
        for fta in ftas:
            # Get rules for this HS code
            rule = self.db.query(FTARule).filter(
                FTARule.fta_id == fta.id,
                FTARule.is_active == True,
                or_(
                    FTARule.hs_code_prefix == hs_code[:2],
                    FTARule.hs_code_prefix == hs_code[:4],
                    FTARule.hs_code_prefix == hs_code[:6]
                )
            ).first()
            
            fta_info = {
                "code": fta.code,
                "name": fta.name,
                "preferential_rate": rule.preferential_rate if rule else 0,
                "certificate_types": fta.certificate_types or [],
                "rules_of_origin": None
            }
            
            if rule:
                fta_info["rules_of_origin"] = {
                    "type": rule.rule_type,
                    "text": rule.rule_text,
                    "ctc_requirement": rule.ctc_requirement,
                    "rvc_threshold": rule.rvc_threshold,
                    "rvc_method": rule.rvc_method
                }
            
            eligible_ftas.append(fta_info)
        
        return {
            "hs_code": hs_code,
            "import_country": import_country,
            "export_country": export_country,
            "eligible_ftas": eligible_ftas,
            "recommended": eligible_ftas[0]["code"] if eligible_ftas else None
        }

