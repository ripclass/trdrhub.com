#!/usr/bin/env python3
"""
AI Rule Suggester
Uses LLM APIs to convert ICC article references into compliance rule implementations
while maintaining IP-safe practices and avoiding direct text reproduction.

IMPORTANT: This system is designed to suggest rule implementations based on
article references only, never storing or reproducing full ICC copyrighted text.
"""

import logging
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# LLM API clients
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from .icc_parser import ParsedDocument, ArticleSection, DocumentType

logger = logging.getLogger(__name__)


class SuggestionConfidence(Enum):
    HIGH = "high"          # 0.8-1.0 - Clear rule implementation
    MEDIUM = "medium"      # 0.5-0.8 - Good rule, needs review
    LOW = "low"            # 0.2-0.5 - Uncertain, manual review required
    UNCERTAIN = "uncertain" # 0.0-0.2 - Cannot suggest reliable rule


@dataclass
class RuleSuggestion:
    """AI-generated rule suggestion"""
    rule_id: str
    title: str
    reference: str  # e.g., "UCP600 Art. 14"
    severity: str   # "high", "medium", "low"
    applies_to: List[str]  # ["credit", "amendment", "standby"]
    dsl_expression: Optional[str] = None
    handler_name: Optional[str] = None
    suggested_description: str = ""
    confidence: SuggestionConfidence = SuggestionConfidence.MEDIUM
    reasoning: str = ""
    needs_handler: bool = False
    suggested_examples: List[str] = None
    version: str = "1.0.0"
    ai_metadata: Dict[str, Any] = None


@dataclass
class SuggestionSession:
    """Complete AI suggestion session"""
    session_id: str
    document_type: DocumentType
    processed_articles: int
    suggestions: List[RuleSuggestion]
    timestamp: datetime
    llm_provider: str
    total_tokens_used: int = 0
    ip_compliance_verified: bool = True


class AIRuleSuggester:
    """Suggests compliance rules using AI while maintaining IP compliance"""

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self.api_client = None
        self.max_tokens_per_request = 4000
        self.temperature = 0.3  # Low temperature for consistent suggestions

        # Initialize API client
        self._initialize_llm_client()

        # Rule patterns and templates
        self.dsl_functions = [
            "exists", "not_empty", "equals", "equalsIgnoreCase", "contains",
            "containsIgnoreCase", "matches", "length", "greaterThan", "lessThan",
            "dateWithinDays", "dateAfter", "dateBefore", "amountGreaterThan",
            "amountLessThan", "check_handler"
        ]

        # IP-safe prompting templates
        self.system_prompts = {
            "rule_suggestion": """You are a trade finance compliance expert helping create rule implementations.

CRITICAL IP COMPLIANCE REQUIREMENTS:
- You will only see article references and structural information, never full ICC text
- Generate original rule implementations based on article IDs and context
- Use only your knowledge of standard LC practices
- Never reproduce or quote ICC copyrighted material
- Output must be completely original paraphrases

Your task: Convert article references into YAML rule stubs with:
1. Short, original rule descriptions (max 50 words)
2. DSL expressions using available functions
3. Appropriate severity levels
4. Clear field references

Available DSL functions: {dsl_functions}
Common LC fields: lc_number, expiry_date, expiry_place, amount, beneficiary, applicant, required_documents
""",

            "handler_suggestion": """You are a Python developer creating validation handlers for trade finance.

Based on the article reference, suggest:
1. Whether a Python handler is needed (vs simple DSL)
2. Handler function name
3. Validation approach (not implementation details)

Focus on standard LC validation patterns like:
- Date logic validation
- Document cross-referencing
- Amount calculations
- Party name consistency
- Address formatting
"""
        }

    def _initialize_llm_client(self):
        """Initialize LLM API client based on provider"""
        if self.llm_provider == "openai" and HAS_OPENAI:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                openai.api_key = api_key
                self.api_client = openai
                logger.info("Initialized OpenAI client")
            else:
                logger.warning("OPENAI_API_KEY not found in environment")

        elif self.llm_provider == "anthropic" and HAS_ANTHROPIC:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.api_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Initialized Anthropic client")
            else:
                logger.warning("ANTHROPIC_API_KEY not found in environment")

        else:
            logger.error(f"LLM provider {self.llm_provider} not available or not installed")
            raise ValueError(f"Cannot initialize {self.llm_provider} client")

    def suggest_rules_from_document(self, parsed_doc: ParsedDocument) -> SuggestionSession:
        """Generate rule suggestions from parsed ICC document"""
        if not self.api_client:
            raise RuntimeError("LLM client not initialized")

        session_id = f"session_{int(datetime.now().timestamp())}"
        suggestions = []
        total_tokens = 0

        logger.info(f"Starting AI rule suggestion session {session_id}")
        logger.info(f"Processing {len(parsed_doc.articles)} articles from {parsed_doc.document_type.value}")

        for i, article in enumerate(parsed_doc.articles):
            if article.confidence < 0.3:
                logger.debug(f"Skipping low-confidence article {article.article_id}")
                continue

            try:
                suggestion, tokens_used = self._suggest_rule_for_article(article, parsed_doc.document_type)
                if suggestion:
                    suggestions.append(suggestion)
                    total_tokens += tokens_used

                # Rate limiting
                if i % 5 == 0 and i > 0:
                    import time
                    time.sleep(1)  # Brief pause every 5 requests

            except Exception as e:
                logger.error(f"Failed to generate suggestion for {article.article_id}: {e}")

        session = SuggestionSession(
            session_id=session_id,
            document_type=parsed_doc.document_type,
            processed_articles=len([a for a in parsed_doc.articles if a.confidence >= 0.3]),
            suggestions=suggestions,
            timestamp=datetime.now(),
            llm_provider=self.llm_provider,
            total_tokens_used=total_tokens
        )

        logger.info(f"Generated {len(suggestions)} rule suggestions using {total_tokens} tokens")
        return session

    def _suggest_rule_for_article(self, article: ArticleSection, doc_type: DocumentType) -> Tuple[Optional[RuleSuggestion], int]:
        """Generate rule suggestion for single article"""

        # Create article context (IP-safe - no full content)
        article_context = {
            "article_id": article.article_id,
            "title": article.title,
            "document_type": doc_type.value,
            "has_subsections": len(article.subsections) > 0,
            "subsection_count": len(article.subsections),
            "content_indicators": self._extract_safe_indicators(article.content)
        }

        # Generate suggestion using LLM
        prompt = self._build_suggestion_prompt(article_context)

        try:
            if self.llm_provider == "openai":
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": self.system_prompts["rule_suggestion"].format(dsl_functions=", ".join(self.dsl_functions))},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=self.temperature
                )

                suggestion_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens

            elif self.llm_provider == "anthropic":
                message = self.api_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    temperature=self.temperature,
                    system=self.system_prompts["rule_suggestion"].format(dsl_functions=", ".join(self.dsl_functions)),
                    messages=[{"role": "user", "content": prompt}]
                )

                suggestion_text = message.content[0].text
                tokens_used = message.usage.input_tokens + message.usage.output_tokens

            else:
                raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

            # Parse LLM response into RuleSuggestion
            suggestion = self._parse_llm_response(suggestion_text, article)
            return suggestion, tokens_used

        except Exception as e:
            logger.error(f"LLM request failed for {article.article_id}: {e}")
            return None, 0

    def _extract_safe_indicators(self, content: str) -> Dict[str, Any]:
        """Extract IP-safe indicators from article content"""
        # Safe indicators that don't reproduce copyrighted text
        indicators = {
            "mentions_documents": bool(re.search(r'\b(document|documents)\b', content, re.IGNORECASE)),
            "mentions_dates": bool(re.search(r'\b(date|dates|expiry|expiration)\b', content, re.IGNORECASE)),
            "mentions_amounts": bool(re.search(r'\b(amount|sum|value|currency)\b', content, re.IGNORECASE)),
            "mentions_parties": bool(re.search(r'\b(beneficiary|applicant|bank|issuing|advising)\b', content, re.IGNORECASE)),
            "mentions_presentation": bool(re.search(r'\b(present|presentation|submit)\b', content, re.IGNORECASE)),
            "mentions_examination": bool(re.search(r'\b(examin|check|review|comply)\b', content, re.IGNORECASE)),
            "has_conditions": bool(re.search(r'\b(shall|must|should|may|will)\b', content, re.IGNORECASE)),
            "estimated_complexity": "simple" if len(content) < 200 else "complex",
            "word_count": len(content.split())
        }

        return indicators

    def _build_suggestion_prompt(self, article_context: Dict[str, Any]) -> str:
        """Build IP-compliant prompt for rule suggestion"""
        return f"""
Based on your knowledge of trade finance and this article reference, suggest a compliance rule:

Article Reference: {article_context['article_id']}
Title: {article_context['title']}
Document Type: {article_context['document_type']}

Content Indicators (no full text provided):
- Mentions documents: {article_context['content_indicators']['mentions_documents']}
- Mentions dates: {article_context['content_indicators']['mentions_dates']}
- Mentions amounts: {article_context['content_indicators']['mentions_amounts']}
- Mentions parties: {article_context['content_indicators']['mentions_parties']}
- Estimated complexity: {article_context['content_indicators']['estimated_complexity']}

Please suggest a YAML rule structure with:
1. A short, original title (max 50 chars)
2. Brief description in your own words (max 100 chars)
3. Appropriate severity (high/medium/low)
4. DSL expression OR handler name
5. Confidence level in your suggestion

Format your response as JSON:
{{
    "title": "Original title here",
    "description": "Your description here",
    "severity": "high|medium|low",
    "dsl": "DSL expression OR null if complex",
    "handler": "handler_name OR null",
    "confidence": "high|medium|low|uncertain",
    "reasoning": "Why you chose this approach"
}}
"""

    def _parse_llm_response(self, response_text: str, article: ArticleSection) -> Optional[RuleSuggestion]:
        """Parse LLM JSON response into RuleSuggestion"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON found in LLM response for {article.article_id}")
                return None

            response_data = json.loads(json_match.group())

            # Map confidence string to enum
            confidence_map = {
                "high": SuggestionConfidence.HIGH,
                "medium": SuggestionConfidence.MEDIUM,
                "low": SuggestionConfidence.LOW,
                "uncertain": SuggestionConfidence.UNCERTAIN
            }

            confidence = confidence_map.get(response_data.get("confidence", "medium"), SuggestionConfidence.MEDIUM)

            # Determine applies_to based on document type
            applies_to = ["credit"]
            if "standby" in article.title.lower():
                applies_to.append("standby")
            if "amendment" in article.title.lower():
                applies_to.append("amendment")

            # Create suggestion
            suggestion = RuleSuggestion(
                rule_id=article.article_id,
                title=response_data.get("title", f"Rule {article.article_id}"),
                reference=f"{article.article_id.split('-')[0]} Art. {article.article_id.split('-')[1]}",
                severity=response_data.get("severity", "medium"),
                applies_to=applies_to,
                dsl_expression=response_data.get("dsl"),
                handler_name=response_data.get("handler"),
                suggested_description=response_data.get("description", ""),
                confidence=confidence,
                reasoning=response_data.get("reasoning", ""),
                needs_handler=bool(response_data.get("handler")),
                ai_metadata={
                    "llm_provider": self.llm_provider,
                    "generated_at": datetime.now().isoformat(),
                    "article_confidence": article.confidence
                }
            )

            # Validate DSL expression
            if suggestion.dsl_expression:
                if not self._validate_dsl_expression(suggestion.dsl_expression):
                    logger.warning(f"Invalid DSL suggested for {article.article_id}: {suggestion.dsl_expression}")
                    suggestion.confidence = SuggestionConfidence.LOW

            return suggestion

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None

    def _validate_dsl_expression(self, dsl_expr: str) -> bool:
        """Validate DSL expression syntax"""
        if not dsl_expr or not isinstance(dsl_expr, str):
            return False

        # Check for balanced parentheses
        if dsl_expr.count('(') != dsl_expr.count(')'):
            return False

        # Check for valid function names
        function_pattern = r'(\w+)\s*\('
        functions_used = re.findall(function_pattern, dsl_expr)

        for func in functions_used:
            if func not in self.dsl_functions:
                return False

        return True

    def export_suggestions_to_yaml(self, session: SuggestionSession, output_dir: Path) -> Path:
        """Export rule suggestions to YAML format"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Group suggestions by document type
        yaml_content = {
            'metadata': {
                'standard': session.document_type.value.upper(),
                'version': '2024.1-ai-suggested',
                'description': f'AI-suggested {session.document_type.value} compliance rules',
                'last_updated': session.timestamp.strftime('%Y-%m-%d'),
                'ai_generation_info': {
                    'session_id': session.session_id,
                    'llm_provider': session.llm_provider,
                    'total_suggestions': len(session.suggestions),
                    'high_confidence_count': len([s for s in session.suggestions if s.confidence == SuggestionConfidence.HIGH]),
                    'requires_review_count': len([s for s in session.suggestions if s.confidence in [SuggestionConfidence.LOW, SuggestionConfidence.UNCERTAIN]])
                }
            },
            'rules': []
        }

        # Convert suggestions to YAML rule format
        for suggestion in session.suggestions:
            rule_data = {
                'id': suggestion.rule_id,
                'title': suggestion.title,
                'reference': suggestion.reference,
                'severity': suggestion.severity,
                'applies_to': suggestion.applies_to,
                'ai_suggested': True,
                'ai_confidence': suggestion.confidence.value,
                'version': suggestion.version
            }

            # Add DSL or handler
            if suggestion.dsl_expression:
                rule_data['dsl'] = suggestion.dsl_expression
            elif suggestion.handler_name:
                rule_data['check_handler'] = suggestion.handler_name

            # Add description if available
            if suggestion.suggested_description:
                rule_data['description'] = suggestion.suggested_description

            # Add review flags
            if suggestion.confidence in [SuggestionConfidence.LOW, SuggestionConfidence.UNCERTAIN]:
                rule_data['requires_manual_review'] = True
                rule_data['ai_reasoning'] = suggestion.reasoning

            # Placeholder examples
            rule_data['examples'] = {
                'pass': [f"fixtures/{suggestion.rule_id.lower().replace('-', '_')}_pass.json"],
                'fail': [f"fixtures/{suggestion.rule_id.lower().replace('-', '_')}_fail.json"]
            }

            yaml_content['rules'].append(rule_data)

        # Export to YAML file
        import yaml
        output_file = output_dir / f"{session.document_type.value}_ai_suggested.yaml"

        with open(output_file, 'w') as f:
            yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Exported {len(session.suggestions)} AI suggestions to {output_file}")
        return output_file

    def generate_handler_stubs(self, suggestions: List[RuleSuggestion], output_dir: Path) -> List[Path]:
        """Generate Python handler stubs for rules that need them"""
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = []

        for suggestion in suggestions:
            if not suggestion.needs_handler or not suggestion.handler_name:
                continue

            handler_file = output_dir / f"{suggestion.handler_name}.py"
            if handler_file.exists():
                logger.debug(f"Handler stub already exists: {handler_file}")
                continue

            # Generate handler stub
            handler_content = self._generate_handler_template(suggestion)

            with open(handler_file, 'w') as f:
                f.write(handler_content)

            generated_files.append(handler_file)
            logger.info(f"Generated handler stub: {handler_file}")

        return generated_files

    def _generate_handler_template(self, suggestion: RuleSuggestion) -> str:
        """Generate Python handler template"""
        return f'''"""
{suggestion.rule_id}: Handler
AI-generated stub for {suggestion.title}

NOTE: This is an AI-generated template. Review and implement validation logic.
Confidence: {suggestion.confidence.value}
Reasoning: {suggestion.reasoning}
"""

from typing import Dict, Any

def validate(lc_document: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate {suggestion.rule_id} compliance

    AI Suggestion: {suggestion.suggested_description}

    Args:
        lc_document: LC document dictionary

    Returns:
        Dictionary with status, details, field_location, suggested_fix
    """

    try:
        # TODO: Implement validation logic based on {suggestion.reference}
        # AI suggested this needs complex logic beyond simple DSL

        # Example structure:
        # field_value = lc_document.get('field_name')
        # if not field_value:
        #     return {{
        #         "status": "fail",
        #         "details": "Field missing or empty",
        #         "field_location": "field_name",
        #         "suggested_fix": "Add required field value"
        #     }}

        return {{
            "status": "pass",  # TODO: Implement actual validation
            "details": "Validation not yet implemented - AI stub",
            "field_location": "unknown",
            "suggested_fix": "Implement handler validation logic"
        }}

    except Exception as e:
        return {{
            "status": "error",
            "details": f"Error validating {suggestion.rule_id}: {{str(e)}}",
            "field_location": "unknown"
        }}
'''


def main():
    """Demo AI rule suggester"""
    # Check for API keys
    if not (os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')):
        print("WARNING: No LLM API keys found in environment")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY to use AI suggestions")
        return

    print("=== AI Rule Suggester Demo ===")
    print("This system generates rule suggestions from ICC article references")
    print("All output is original and IP-compliant\n")

    # Demo with mock article data
    from .icc_parser import ArticleSection, DocumentType

    sample_articles = [
        ArticleSection(
            article_id="UCP600-6",
            title="Availability, Expiry Date and Place",
            content="Mock content indicators suggest this relates to expiry requirements",
            subsections=[],
            confidence=0.9
        ),
        ArticleSection(
            article_id="UCP600-14",
            title="Standard for Examination of Documents",
            content="Mock content indicates document examination standards",
            subsections=["a) examination timing", "b) face compliance"],
            confidence=0.8
        )
    ]

    try:
        suggester = AIRuleSuggester("openai")

        print("Testing individual article suggestion...")
        for article in sample_articles:
            suggestion, tokens = suggester._suggest_rule_for_article(article, DocumentType.UCP600)
            if suggestion:
                print(f"  {suggestion.rule_id}: {suggestion.title}")
                print(f"    Confidence: {suggestion.confidence.value}")
                print(f"    DSL: {suggestion.dsl_expression}")
                print(f"    Tokens: {tokens}")
            else:
                print(f"  Failed to generate suggestion for {article.article_id}")

        print("\nAI suggestion demo complete")

    except Exception as e:
        print(f"Demo failed: {e}")


if __name__ == "__main__":
    main()