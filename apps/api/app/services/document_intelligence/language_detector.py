"""
Language Detector - Phase 0.4

Detects document language for proper OCR model selection
and extraction handling. Trade documents may be in various languages.

Supported Languages:
- English (primary)
- Chinese (Simplified/Traditional)
- Arabic
- Spanish
- French
- German
- Portuguese
- Japanese
- Korean
- Bangla
- Hindi

Detection Strategy:
1. Character set analysis (CJK, Arabic, Latin, etc.)
2. Common word patterns
3. Script detection
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported document languages."""
    ENGLISH = "en"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    ARABIC = "ar"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    JAPANESE = "ja"
    KOREAN = "ko"
    BANGLA = "bn"
    HINDI = "hi"
    UNKNOWN = "unknown"
    MIXED = "mixed"  # Multiple languages detected


class Script(str, Enum):
    """Writing script types."""
    LATIN = "latin"
    CJK = "cjk"  # Chinese, Japanese, Korean
    ARABIC = "arabic"
    DEVANAGARI = "devanagari"  # Hindi
    BENGALI = "bengali"
    CYRILLIC = "cyrillic"
    UNKNOWN = "unknown"


@dataclass
class LanguageResult:
    """Result of language detection."""
    primary_language: Language
    confidence: float  # 0.0 to 1.0
    script: Script
    secondary_languages: List[Tuple[Language, float]]  # Other detected languages
    is_english: bool
    requires_special_ocr: bool  # True for non-Latin scripts
    ocr_language_code: str  # Code to pass to OCR provider
    details: str


# Character range definitions for script detection
SCRIPT_RANGES = {
    Script.LATIN: [
        (0x0041, 0x007A),  # Basic Latin letters
        (0x00C0, 0x00FF),  # Latin Extended-A
        (0x0100, 0x017F),  # Latin Extended-B
    ],
    Script.CJK: [
        (0x4E00, 0x9FFF),   # CJK Unified Ideographs
        (0x3400, 0x4DBF),   # CJK Extension A
        (0x3000, 0x303F),   # CJK Punctuation
        (0x3040, 0x309F),   # Hiragana
        (0x30A0, 0x30FF),   # Katakana
        (0xAC00, 0xD7AF),   # Korean Hangul
    ],
    Script.ARABIC: [
        (0x0600, 0x06FF),  # Arabic
        (0x0750, 0x077F),  # Arabic Supplement
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    ],
    Script.DEVANAGARI: [
        (0x0900, 0x097F),  # Devanagari
        (0xA8E0, 0xA8FF),  # Devanagari Extended
    ],
    Script.BENGALI: [
        (0x0980, 0x09FF),  # Bengali
    ],
    Script.CYRILLIC: [
        (0x0400, 0x04FF),  # Cyrillic
        (0x0500, 0x052F),  # Cyrillic Supplement
    ],
}

# Common words for language identification
LANGUAGE_MARKERS = {
    Language.ENGLISH: [
        r'\bthe\b', r'\band\b', r'\bof\b', r'\bto\b', r'\bin\b',
        r'\bfor\b', r'\bis\b', r'\bon\b', r'\bthat\b', r'\bwith\b',
        r'\bby\b', r'\bthis\b', r'\bbe\b', r'\bare\b', r'\bnot\b',
        r'\bwill\b', r'\bhave\b', r'\bshall\b', r'\bfrom\b', r'\bat\b',
        # Trade-specific
        r'\binvoice\b', r'\bshipment\b', r'\bgoods\b', r'\bdate\b',
        r'\bamount\b', r'\bcredit\b', r'\bbank\b', r'\bpayment\b',
    ],
    Language.SPANISH: [
        r'\bel\b', r'\bla\b', r'\bde\b', r'\bque\b', r'\by\b',
        r'\ben\b', r'\blos\b', r'\bdel\b', r'\blas\b', r'\bpor\b',
        r'\bcon\b', r'\buna\b', r'\bsu\b', r'\bpara\b', r'\bes\b',
    ],
    Language.FRENCH: [
        r'\ble\b', r'\bla\b', r'\bde\b', r'\bet\b', r'\bdes\b',
        r'\ben\b', r'\bdu\b', r'\bque\b', r'\bun\b', r'\bdans\b',
        r'\bqui\b', r'\bau\b', r'\bpour\b', r'\bpar\b', r'\bsur\b',
    ],
    Language.GERMAN: [
        r'\bder\b', r'\bdie\b', r'\bund\b', r'\bin\b', r'\bden\b',
        r'\bvon\b', r'\bzu\b', r'\bdas\b', r'\bmit\b', r'\bsich\b',
        r'\bdes\b', r'\bauf\b', r'\bfür\b', r'\bist\b', r'\bim\b',
    ],
    Language.PORTUGUESE: [
        r'\bo\b', r'\bde\b', r'\bque\b', r'\be\b', r'\ba\b',
        r'\bdo\b', r'\bda\b', r'\bem\b', r'\bum\b', r'\bpara\b',
        r'\bcom\b', r'\bnão\b', r'\buma\b', r'\bos\b', r'\bno\b',
    ],
}

# OCR language codes (for Google Document AI / Textract)
OCR_LANGUAGE_CODES = {
    Language.ENGLISH: "en",
    Language.CHINESE_SIMPLIFIED: "zh-Hans",
    Language.CHINESE_TRADITIONAL: "zh-Hant",
    Language.ARABIC: "ar",
    Language.SPANISH: "es",
    Language.FRENCH: "fr",
    Language.GERMAN: "de",
    Language.PORTUGUESE: "pt",
    Language.JAPANESE: "ja",
    Language.KOREAN: "ko",
    Language.BANGLA: "bn",
    Language.HINDI: "hi",
    Language.UNKNOWN: "en",  # Default to English
    Language.MIXED: "en",
}


class LanguageDetector:
    """
    Detects document language for proper OCR and extraction handling.
    
    This is critical for non-English trade documents where OCR models
    and extraction patterns differ significantly.
    """
    
    def __init__(self):
        """Initialize the language detector."""
        self._marker_patterns = {
            lang: [re.compile(p, re.IGNORECASE) for p in patterns]
            for lang, patterns in LANGUAGE_MARKERS.items()
        }
    
    def detect(self, text: str) -> LanguageResult:
        """
        Detect the primary language of the document.
        
        Args:
            text: OCR extracted text
            
        Returns:
            LanguageResult with detected language and confidence
        """
        if not text or len(text.strip()) < 20:
            return self._create_unknown_result("Insufficient text for detection")
        
        # Step 1: Detect script type
        script, script_ratios = self._detect_script(text)
        
        # Step 2: For CJK, differentiate between Chinese/Japanese/Korean
        if script == Script.CJK:
            return self._detect_cjk_language(text, script_ratios)
        
        # Step 3: For Arabic script
        if script == Script.ARABIC:
            return LanguageResult(
                primary_language=Language.ARABIC,
                confidence=script_ratios.get(Script.ARABIC, 0.0),
                script=Script.ARABIC,
                secondary_languages=[],
                is_english=False,
                requires_special_ocr=True,
                ocr_language_code=OCR_LANGUAGE_CODES[Language.ARABIC],
                details="Arabic script detected",
            )
        
        # Step 4: For Bengali script
        if script == Script.BENGALI:
            return LanguageResult(
                primary_language=Language.BANGLA,
                confidence=script_ratios.get(Script.BENGALI, 0.0),
                script=Script.BENGALI,
                secondary_languages=[],
                is_english=False,
                requires_special_ocr=True,
                ocr_language_code=OCR_LANGUAGE_CODES[Language.BANGLA],
                details="Bengali script detected",
            )
        
        # Step 5: For Devanagari script
        if script == Script.DEVANAGARI:
            return LanguageResult(
                primary_language=Language.HINDI,
                confidence=script_ratios.get(Script.DEVANAGARI, 0.0),
                script=Script.DEVANAGARI,
                secondary_languages=[],
                is_english=False,
                requires_special_ocr=True,
                ocr_language_code=OCR_LANGUAGE_CODES[Language.HINDI],
                details="Devanagari script detected",
            )
        
        # Step 6: For Latin script, use word markers
        if script == Script.LATIN:
            return self._detect_latin_language(text)
        
        return self._create_unknown_result("Unable to determine language")
    
    def _detect_script(self, text: str) -> Tuple[Script, Dict[Script, float]]:
        """Detect the dominant writing script."""
        script_counts: Dict[Script, int] = {s: 0 for s in Script}
        total_chars = 0
        
        for char in text:
            code_point = ord(char)
            if char.isspace() or char.isdigit():
                continue
            
            total_chars += 1
            
            for script, ranges in SCRIPT_RANGES.items():
                for start, end in ranges:
                    if start <= code_point <= end:
                        script_counts[script] += 1
                        break
        
        if total_chars == 0:
            return Script.UNKNOWN, {}
        
        # Calculate ratios
        ratios = {s: c / total_chars for s, c in script_counts.items()}
        
        # Find dominant script
        dominant_script = max(script_counts, key=script_counts.get)
        dominant_ratio = ratios.get(dominant_script, 0)
        
        if dominant_ratio < 0.3:
            return Script.UNKNOWN, ratios
        
        return dominant_script, ratios
    
    def _detect_cjk_language(
        self,
        text: str,
        script_ratios: Dict[Script, float],
    ) -> LanguageResult:
        """Differentiate between Chinese, Japanese, and Korean."""
        # Count Japanese-specific characters (Hiragana, Katakana)
        japanese_chars = sum(
            1 for c in text
            if 0x3040 <= ord(c) <= 0x309F  # Hiragana
            or 0x30A0 <= ord(c) <= 0x30FF  # Katakana
        )
        
        # Count Korean-specific characters (Hangul)
        korean_chars = sum(
            1 for c in text
            if 0xAC00 <= ord(c) <= 0xD7AF
        )
        
        # Count Chinese characters
        chinese_chars = sum(
            1 for c in text
            if 0x4E00 <= ord(c) <= 0x9FFF
        )
        
        total_cjk = japanese_chars + korean_chars + chinese_chars
        
        if total_cjk == 0:
            return self._create_unknown_result("No CJK characters found")
        
        # Determine language based on character distribution
        if korean_chars / total_cjk > 0.3:
            return LanguageResult(
                primary_language=Language.KOREAN,
                confidence=korean_chars / total_cjk,
                script=Script.CJK,
                secondary_languages=[],
                is_english=False,
                requires_special_ocr=True,
                ocr_language_code=OCR_LANGUAGE_CODES[Language.KOREAN],
                details=f"Korean detected ({korean_chars} Hangul chars)",
            )
        
        if japanese_chars / total_cjk > 0.2:
            return LanguageResult(
                primary_language=Language.JAPANESE,
                confidence=japanese_chars / total_cjk,
                script=Script.CJK,
                secondary_languages=[],
                is_english=False,
                requires_special_ocr=True,
                ocr_language_code=OCR_LANGUAGE_CODES[Language.JAPANESE],
                details=f"Japanese detected ({japanese_chars} kana chars)",
            )
        
        # Default to Chinese
        # Try to distinguish Simplified vs Traditional (rough heuristic)
        # Traditional Chinese uses more complex characters
        is_traditional = self._is_traditional_chinese(text)
        
        lang = Language.CHINESE_TRADITIONAL if is_traditional else Language.CHINESE_SIMPLIFIED
        return LanguageResult(
            primary_language=lang,
            confidence=chinese_chars / total_cjk,
            script=Script.CJK,
            secondary_languages=[],
            is_english=False,
            requires_special_ocr=True,
            ocr_language_code=OCR_LANGUAGE_CODES[lang],
            details=f"Chinese ({'Traditional' if is_traditional else 'Simplified'}) detected",
        )
    
    def _is_traditional_chinese(self, text: str) -> bool:
        """Rough heuristic to detect Traditional vs Simplified Chinese."""
        # Traditional Chinese markers (commonly used characters)
        traditional_markers = "國個會這學說為對時們過還發來經現說無機類開關還間動時裡頭問過說樂聲義語進動種總廣術應專書業實電學問題長師體視開學員報場義說經過國時書機說問題會還無過語發這現就說時會時現說這"
        # Simplified Chinese markers
        simplified_markers = "国个会这学说为对时们过还发来经现说无机类开关还间动时里头问过说乐声义语进动种总广术应专书业实电学问题长师体视开学员报场义说经过国时书机说问题会还无过语发这现就说时会时现说这"
        
        trad_count = sum(1 for c in text if c in traditional_markers)
        simp_count = sum(1 for c in text if c in simplified_markers)
        
        return trad_count > simp_count
    
    def _detect_latin_language(self, text: str) -> LanguageResult:
        """Detect specific Latin-script language using word markers."""
        scores: Dict[Language, float] = {}
        
        text_lower = text.lower()
        
        for lang, patterns in self._marker_patterns.items():
            match_count = sum(len(p.findall(text_lower)) for p in patterns)
            # Normalize by text length
            scores[lang] = match_count / (len(text) / 100)
        
        # Find best match
        if not scores:
            return self._create_english_result(0.5, "No language markers found, defaulting to English")
        
        best_lang = max(scores, key=scores.get)
        best_score = scores[best_lang]
        
        # Calculate confidence
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.5
        
        # Build secondary languages
        secondary = [
            (lang, scores[lang] / total_score if total_score > 0 else 0)
            for lang in scores
            if lang != best_lang and scores[lang] > 0
        ]
        secondary.sort(key=lambda x: x[1], reverse=True)
        
        return LanguageResult(
            primary_language=best_lang,
            confidence=confidence,
            script=Script.LATIN,
            secondary_languages=secondary[:3],
            is_english=best_lang == Language.ENGLISH,
            requires_special_ocr=False,
            ocr_language_code=OCR_LANGUAGE_CODES[best_lang],
            details=f"{best_lang.value} detected with {confidence:.0%} confidence",
        )
    
    def _create_unknown_result(self, details: str) -> LanguageResult:
        """Create an unknown language result."""
        return LanguageResult(
            primary_language=Language.UNKNOWN,
            confidence=0.0,
            script=Script.UNKNOWN,
            secondary_languages=[],
            is_english=False,
            requires_special_ocr=False,
            ocr_language_code="en",  # Default to English
            details=details,
        )
    
    def _create_english_result(self, confidence: float, details: str) -> LanguageResult:
        """Create an English language result."""
        return LanguageResult(
            primary_language=Language.ENGLISH,
            confidence=confidence,
            script=Script.LATIN,
            secondary_languages=[],
            is_english=True,
            requires_special_ocr=False,
            ocr_language_code="en",
            details=details,
        )
    
    def is_english(self, text: str) -> bool:
        """Quick check if document is primarily English."""
        result = self.detect(text)
        return result.is_english
    
    def needs_special_ocr(self, text: str) -> bool:
        """Check if document needs non-Latin OCR handling."""
        result = self.detect(text)
        return result.requires_special_ocr


# Module-level instance
_detector: Optional[LanguageDetector] = None


def get_language_detector() -> LanguageDetector:
    """Get the global language detector instance."""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector

