"""
Text Guard Utility - Prevents verbatim reproduction of rulebook text.

Uses similarity checking and rephrasing to ensure AI outputs are paraphrased.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class TextGuard:
    """Guard against verbatim rulebook text reproduction."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Maximum allowed similarity (0-1) before flagging
        """
        self.similarity_threshold = similarity_threshold
        self.rule_corpus: List[str] = []
        self._load_rule_corpus()
    
    def _load_rule_corpus(self):
        """Load rule text corpus for similarity checking."""
        # In production, load from DB or ruleset files
        # For now, use common UCP/ISBP phrases that should not be verbatim
        self.rule_corpus = [
            "Documents must be presented not later than",
            "A document presented but not required by the credit",
            "Banks deal with documents and not with goods",
            "An issuing bank is irrevocably bound",
            "A nominated bank acting on its nomination",
            "The description of the goods in the commercial invoice",
            "A transport document bearing a date of issuance",
            "A credit must state whether it is available",
            "A credit must not be issued available",
            "The expiry date of a credit",
            "A presentation including one or more original transport documents",
            "A bank has a maximum of five banking days",
            "When a bank other than the issuing bank",
            "If a credit requires presentation of a document",
            "A document may be dated prior to the issuance date",
            "The words 'about' or 'approximately'",
            "A requirement for a document to be 'legalized'",
            "A requirement for a document to be 'certified'",
            "A requirement for a document to be 'notarized'",
            "A requirement for a document to be 'authenticated'",
        ]
    
    def check_similarity(self, text: str, corpus: Optional[List[str]] = None) -> Tuple[bool, float, Optional[str]]:
        """
        Check if text is too similar to rulebook corpus.
        
        Returns:
            (is_verbatim, max_similarity, matched_phrase)
        """
        corpus = corpus or self.rule_corpus
        
        # Normalize text for comparison
        normalized_text = self._normalize_text(text)
        
        max_similarity = 0.0
        matched_phrase = None
        
        for phrase in corpus:
            normalized_phrase = self._normalize_text(phrase)
            
            # Check sentence-level similarity
            similarity = self._sentence_similarity(normalized_text, normalized_phrase)
            
            if similarity > max_similarity:
                max_similarity = similarity
                matched_phrase = phrase
        
        # Also check for exact substring matches (case-insensitive)
        for phrase in corpus:
            if phrase.lower() in text.lower():
                return True, 1.0, phrase
        
        is_verbatim = max_similarity >= self.similarity_threshold
        return is_verbatim, max_similarity, matched_phrase
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove punctuation for fuzzy matching
        text = re.sub(r'[^\w\s]', '', text)
        # Lowercase
        text = text.lower()
        return text.strip()
    
    def _sentence_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using SequenceMatcher."""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _paragraph_similarity(self, text1: str, text2: str) -> float:
        """Calculate paragraph-level similarity."""
        # Split into sentences
        sentences1 = re.split(r'[.!?]+', text1)
        sentences2 = re.split(r'[.!?]+', text2)
        
        if not sentences1 or not sentences2:
            return 0.0
        
        # Find best matching sentence pairs
        total_similarity = 0.0
        matches = 0
        
        for s1 in sentences1:
            if not s1.strip():
                continue
            best_match = 0.0
            for s2 in sentences2:
                if not s2.strip():
                    continue
                sim = self._sentence_similarity(s1, s2)
                if sim > best_match:
                    best_match = sim
            total_similarity += best_match
            matches += 1
        
        return total_similarity / matches if matches > 0 else 0.0
    
    def validate_output(
        self,
        output: str,
        allow_retry: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate AI output for verbatim content.
        
        Returns:
            (is_valid, output_or_rephrased, warning_message)
        """
        is_verbatim, similarity, matched_phrase = self.check_similarity(output)
        
        if is_verbatim:
            warning = (
                f"Output too similar to rulebook text (similarity: {similarity:.2f}). "
                f"Matched phrase: '{matched_phrase[:50]}...'"
            )
            
            if allow_retry:
                # Return flag to trigger rephrasing
                return False, output, warning
            
            # If retry not allowed, return sanitized version
            sanitized = self._sanitize_output(output, matched_phrase)
            return True, sanitized, warning
        
        return True, output, None
    
    def _sanitize_output(self, output: str, matched_phrase: str) -> str:
        """Sanitize output by replacing verbatim phrases."""
        # Simple approach: replace exact matches with paraphrased versions
        # In production, could use LLM to rephrase
        
        # For now, just add a note that this is paraphrased
        if matched_phrase.lower() in output.lower():
            # Replace with generic reference
            output = output.replace(matched_phrase, "[Referencing relevant UCP/ISBP article]")
        
        return output
    
    def add_rule_phrases(self, phrases: List[str]):
        """Add phrases to the rule corpus."""
        self.rule_corpus.extend(phrases)
    
    def load_ruleset_corpus(self, ruleset_data: Dict[str, Any]):
        """Load corpus from ruleset JSON data."""
        phrases = []
        
        if isinstance(ruleset_data, dict):
            rules = ruleset_data.get("rules", [])
            for rule in rules:
                # Extract text from rule description/message
                if isinstance(rule, dict):
                    description = rule.get("description", "")
                    message = rule.get("message", "")
                    if description:
                        phrases.append(description)
                    if message:
                        phrases.append(message)
        
        self.add_rule_phrases(phrases)
        logger.info(f"Loaded {len(phrases)} phrases from ruleset corpus")

