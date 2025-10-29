"""
Internationalization (i18n) utilities for LCopilot.
Handles translation loading, caching, and fallback mechanisms.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class TranslationManager:
    """Manages translations with fallback support and caching."""

    def __init__(self, locales_dir: Optional[Path] = None):
        """
        Initialize the translation manager.

        Args:
            locales_dir: Path to locales directory. Defaults to project locales dir.
        """
        if locales_dir is None:
            self.locales_dir = Path(__file__).parent.parent.parent / "locales"
        else:
            self.locales_dir = Path(locales_dir)

        self.verified_dir = self.locales_dir / "verified"
        self.auto_generated_dir = self.locales_dir / "auto_generated"

        # Translation cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_language = "en"

    @lru_cache(maxsize=128)
    def _load_translation_file(self, language: str, source_type: str) -> Dict[str, Any]:
        """
        Load translation file with caching.

        Args:
            language: Language code (e.g., 'en', 'bn', 'ar')
            source_type: 'verified', 'auto_generated', or 'base'

        Returns:
            Translation dictionary
        """
        try:
            if source_type == "verified":
                file_path = self.verified_dir / f"{language}.json"
            elif source_type == "auto_generated":
                file_path = self.auto_generated_dir / f"{language}.json"
            else:  # base
                file_path = self.locales_dir / f"{language}.json"

            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Translation file not found: {file_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading translation file {file_path}: {e}")
            return {}

    def get_translations(self, language: str) -> Dict[str, Any]:
        """
        Get merged translations for a language with priority:
        verified > auto_generated > base > English fallback

        Args:
            language: Language code

        Returns:
            Merged translation dictionary
        """
        if language in self._cache:
            return self._cache[language]

        # Start with base translations
        translations = self._load_translation_file(language, "base").copy()

        # Merge auto-generated translations
        auto_generated = self._load_translation_file(language, "auto_generated")
        self._deep_merge(translations, auto_generated)

        # Merge verified translations (highest priority)
        verified = self._load_translation_file(language, "verified")
        self._deep_merge(translations, verified)

        # If not English and translations are empty/partial, merge English as fallback
        if language != self.default_language:
            english_translations = self._load_translation_file(self.default_language, "base")
            # Only merge keys that don't exist in target language
            self._merge_missing_keys(translations, english_translations)

        self._cache[language] = translations
        return translations

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Deep merge source dictionary into target dictionary.

        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _merge_missing_keys(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Merge only missing keys from source into target.

        Args:
            target: Target dictionary
            source: Source dictionary (fallback)
        """
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_missing_keys(target[key], value)

    def translate(self, key: str, language: str, **kwargs) -> str:
        """
        Get translation for a key with variable substitution.

        Args:
            key: Translation key (dot notation, e.g., 'report.title')
            language: Target language code
            **kwargs: Variables for string formatting

        Returns:
            Translated string with variables substituted
        """
        translations = self.get_translations(language)

        # Navigate nested keys using dot notation
        value = translations
        for key_part in key.split('.'):
            if isinstance(value, dict) and key_part in value:
                value = value[key_part]
            else:
                # Fallback to English if key not found
                if language != self.default_language:
                    return self.translate(key, self.default_language, **kwargs)
                else:
                    logger.warning(f"Translation key not found: {key}")
                    return key  # Return key as fallback

        if isinstance(value, str):
            try:
                # Perform variable substitution
                return value.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing variable for translation {key}: {e}")
                return value
        else:
            logger.warning(f"Translation key {key} does not point to a string")
            return str(value)

    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported languages based on available translation files.

        Returns:
            List of language codes
        """
        languages = set()

        # Check base locales directory
        for file_path in self.locales_dir.glob("*.json"):
            if file_path.stem not in ["README", "template"]:
                languages.add(file_path.stem)

        # Check verified directory
        if self.verified_dir.exists():
            for file_path in self.verified_dir.glob("*.json"):
                languages.add(file_path.stem)

        # Check auto-generated directory
        if self.auto_generated_dir.exists():
            for file_path in self.auto_generated_dir.glob("*.json"):
                languages.add(file_path.stem)

        return sorted(list(languages))

    def clear_cache(self) -> None:
        """Clear translation cache."""
        self._cache.clear()
        self._load_translation_file.cache_clear()

    def get_language_direction(self, language: str) -> str:
        """
        Get text direction for a language.

        Args:
            language: Language code

        Returns:
            'rtl' for right-to-left languages, 'ltr' for others
        """
        rtl_languages = ['ar', 'he', 'fa', 'ur']
        return 'rtl' if language in rtl_languages else 'ltr'


# Global translation manager instance
translation_manager = TranslationManager()


def translate(key: str, language: str = "en", **kwargs) -> str:
    """
    Convenience function for translation.

    Args:
        key: Translation key
        language: Target language code
        **kwargs: Variables for string formatting

    Returns:
        Translated string
    """
    return translation_manager.translate(key, language, **kwargs)


def get_supported_languages() -> list[str]:
    """Get list of supported languages."""
    return translation_manager.get_supported_languages()


def get_language_direction(language: str) -> str:
    """Get text direction for a language."""
    return translation_manager.get_language_direction(language)


def clear_translation_cache() -> None:
    """Clear translation cache."""
    translation_manager.clear_cache()