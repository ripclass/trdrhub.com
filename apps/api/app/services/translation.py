"""
AI-assisted translation service for LCopilot.
Handles automatic translation generation using Claude API.
"""

import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

import anthropic
from sqlalchemy.orm import Session

from ..models.audit_log import AuditLog
from ..models import User
from ..utils.i18n import translation_manager
from ..config import settings

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for AI-assisted translation management."""

    def __init__(self):
        """Initialize the translation service."""
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.locales_dir = Path(__file__).parent.parent.parent / "locales"
        self.auto_generated_dir = self.locales_dir / "auto_generated"
        self.verified_dir = self.locales_dir / "verified"

        # Ensure directories exist
        self.auto_generated_dir.mkdir(parents=True, exist_ok=True)
        self.verified_dir.mkdir(parents=True, exist_ok=True)

    async def generate_missing_translations(
        self,
        target_language: str,
        db: Session,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Generate missing translations for a target language using AI.

        Args:
            target_language: Target language code (e.g., 'bn', 'ar', 'hi')
            db: Database session for audit logging
            user: User requesting the translation (for audit)

        Returns:
            Dictionary with generated translations and metadata
        """
        try:
            # Load English translations as source
            english_translations = translation_manager._load_translation_file("en", "base")

            # Load existing translations for target language
            existing_translations = translation_manager.get_translations(target_language)

            # Find missing keys
            missing_keys = self._find_missing_keys(english_translations, existing_translations)

            if not missing_keys:
                logger.info(f"No missing translations found for {target_language}")
                return {"status": "complete", "generated_count": 0}

            # Generate translations using Claude
            generated_translations = await self._generate_translations_with_ai(
                missing_keys, target_language
            )

            # Save to auto-generated directory
            auto_gen_file = self.auto_generated_dir / f"{target_language}.json"
            existing_auto_gen = {}
            if auto_gen_file.exists():
                with open(auto_gen_file, 'r', encoding='utf-8') as f:
                    existing_auto_gen = json.load(f)

            # Merge new translations
            self._deep_merge(existing_auto_gen, generated_translations)

            # Add metadata
            existing_auto_gen["_metadata"] = {
                "last_generated": datetime.utcnow().isoformat(),
                "generated_by": "AI",
                "total_keys": len(missing_keys),
                "language": target_language
            }

            # Save updated translations
            with open(auto_gen_file, 'w', encoding='utf-8') as f:
                json.dump(existing_auto_gen, f, ensure_ascii=False, indent=2)

            # Log audit entry
            if user:
                await self._log_translation_audit(
                    db, user, target_language, "ai_generated", len(missing_keys)
                )

            # Clear cache to force reload
            translation_manager.clear_cache()

            logger.info(f"Generated {len(missing_keys)} translations for {target_language}")

            return {
                "status": "success",
                "generated_count": len(missing_keys),
                "target_language": target_language,
                "file_path": str(auto_gen_file)
            }

        except Exception as e:
            logger.error(f"Error generating translations for {target_language}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "generated_count": 0
            }

    async def _generate_translations_with_ai(
        self,
        source_data: Dict[str, Any],
        target_language: str
    ) -> Dict[str, Any]:
        """
        Use Claude AI to generate translations.

        Args:
            source_data: English source data to translate
            target_language: Target language code

        Returns:
            Generated translations dictionary
        """
        language_names = {
            "bn": "Bengali/Bangla",
            "ar": "Arabic",
            "hi": "Hindi",
            "ur": "Urdu",
            "zh": "Mandarin Chinese",
            "fr": "French",
            "de": "German",
            "ms": "Malay"
        }

        target_language_name = language_names.get(target_language, target_language)

        prompt = f"""
You are a professional translator specializing in financial and legal documents.
Translate the following JSON structure from English to {target_language_name}.

IMPORTANT GUIDELINES:
1. Maintain the exact JSON structure and key names
2. Only translate the string values, never the keys
3. Preserve formatting placeholders like {{variable}}
4. Use formal, professional language appropriate for financial/legal contexts
5. For technical terms (like "Letter of Credit"), provide accurate translations
6. Ensure cultural appropriateness for business documents
7. Keep translations concise but clear

Source JSON to translate:
{json.dumps(source_data, indent=2, ensure_ascii=False)}

Return only the translated JSON without any additional text or explanation.
"""

        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.1,  # Low temperature for consistent translations
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse the AI response
            translation_text = response.content[0].text.strip()

            # Clean up any markdown code blocks
            if translation_text.startswith("```json"):
                translation_text = translation_text[7:]
            if translation_text.endswith("```"):
                translation_text = translation_text[:-3]

            translated_data = json.loads(translation_text)

            # Add AI source metadata to each translated item
            self._mark_ai_generated(translated_data)

            return translated_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI translation response: {e}")
            raise ValueError(f"Invalid JSON response from AI: {e}")
        except Exception as e:
            logger.error(f"AI translation request failed: {e}")
            raise

    def _find_missing_keys(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        path: str = ""
    ) -> Dict[str, Any]:
        """
        Find missing translation keys by comparing source and target.

        Args:
            source: Source dictionary (English)
            target: Target dictionary (target language)
            path: Current path for nested tracking

        Returns:
            Dictionary containing only missing keys
        """
        missing = {}

        for key, value in source.items():
            current_path = f"{path}.{key}" if path else key

            if key not in target:
                # Entire key is missing
                missing[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                # Recursively check nested dictionaries
                nested_missing = self._find_missing_keys(value, target[key], current_path)
                if nested_missing:
                    missing[key] = nested_missing
            elif isinstance(value, str) and target[key] == value:
                # String value is identical (not translated)
                missing[key] = value

        return missing

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source into target dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _mark_ai_generated(self, data: Dict[str, Any]) -> None:
        """Recursively mark translations as AI-generated."""
        for key, value in data.items():
            if isinstance(value, dict):
                self._mark_ai_generated(value)
            elif isinstance(value, str):
                # Mark as AI-generated in metadata
                if "_metadata" not in data:
                    data["_metadata"] = {}
                if "ai_generated_keys" not in data["_metadata"]:
                    data["_metadata"]["ai_generated_keys"] = []
                data["_metadata"]["ai_generated_keys"].append(key)

    async def verify_translation(
        self,
        language: str,
        key: str,
        verified_value: str,
        db: Session,
        user: User
    ) -> Dict[str, Any]:
        """
        Verify and save a human-approved translation.

        Args:
            language: Target language code
            key: Translation key (dot notation)
            verified_value: Human-verified translation
            db: Database session
            user: User performing verification

        Returns:
            Result dictionary
        """
        try:
            verified_file = self.verified_dir / f"{language}.json"
            verified_translations = {}

            if verified_file.exists():
                with open(verified_file, 'r', encoding='utf-8') as f:
                    verified_translations = json.load(f)

            # Set the verified value using dot notation
            self._set_nested_value(verified_translations, key, verified_value)

            # Add metadata
            if "_metadata" not in verified_translations:
                verified_translations["_metadata"] = {}

            verified_translations["_metadata"].update({
                "last_verified": datetime.utcnow().isoformat(),
                "verified_by": user.email,
                "language": language
            })

            # Save verified translation
            with open(verified_file, 'w', encoding='utf-8') as f:
                json.dump(verified_translations, f, ensure_ascii=False, indent=2)

            # Log audit entry
            await self._log_translation_audit(
                db, user, language, "human_verified", 1, key
            )

            # Clear cache
            translation_manager.clear_cache()

            logger.info(f"Verified translation for {language}.{key}")

            return {
                "status": "success",
                "language": language,
                "key": key,
                "verified_value": verified_value
            }

        except Exception as e:
            logger.error(f"Error verifying translation: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _set_nested_value(self, data: Dict[str, Any], key: str, value: str) -> None:
        """Set nested dictionary value using dot notation."""
        keys = key.split('.')
        current = data

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the final value
        current[keys[-1]] = value

    async def _log_translation_audit(
        self,
        db: Session,
        user: User,
        language: str,
        action: str,
        count: int,
        key: Optional[str] = None
    ) -> None:
        """Log translation activities for compliance."""
        try:
            audit_entry = AuditLog(
                user_id=user.id,
                company_id=user.company_id,
                action=f"translation_{action}",
                resource_type="translation",
                resource_id=f"{language}_{key}" if key else language,
                details={
                    "language": language,
                    "action": action,
                    "count": count,
                    "key": key,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            db.add(audit_entry)
            db.commit()

        except Exception as e:
            logger.error(f"Failed to log translation audit: {e}")
            db.rollback()

    def get_pending_translations(self, language: str) -> Dict[str, Any]:
        """
        Get all AI-generated translations pending human verification.

        Args:
            language: Target language code

        Returns:
            Dictionary of pending translations
        """
        try:
            auto_gen_file = self.auto_generated_dir / f"{language}.json"
            verified_file = self.verified_dir / f"{language}.json"

            if not auto_gen_file.exists():
                return {"pending": {}, "count": 0}

            with open(auto_gen_file, 'r', encoding='utf-8') as f:
                auto_generated = json.load(f)

            verified = {}
            if verified_file.exists():
                with open(verified_file, 'r', encoding='utf-8') as f:
                    verified = json.load(f)

            # Find keys that are auto-generated but not yet verified
            pending = self._find_unverified_keys(auto_generated, verified)

            return {
                "pending": pending,
                "count": self._count_translation_keys(pending),
                "language": language
            }

        except Exception as e:
            logger.error(f"Error getting pending translations: {e}")
            return {"pending": {}, "count": 0}

    def _find_unverified_keys(
        self,
        auto_generated: Dict[str, Any],
        verified: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find auto-generated keys that haven't been verified."""
        unverified = {}

        for key, value in auto_generated.items():
            if key.startswith("_"):  # Skip metadata
                continue

            if key not in verified:
                unverified[key] = value
            elif isinstance(value, dict) and isinstance(verified[key], dict):
                nested_unverified = self._find_unverified_keys(value, verified[key])
                if nested_unverified:
                    unverified[key] = nested_unverified

        return unverified

    def _count_translation_keys(self, data: Dict[str, Any]) -> int:
        """Count the number of translation keys in nested structure."""
        count = 0
        for key, value in data.items():
            if key.startswith("_"):  # Skip metadata
                continue
            if isinstance(value, dict):
                count += self._count_translation_keys(value)
            else:
                count += 1
        return count


# Global translation service instance
translation_service = TranslationService()