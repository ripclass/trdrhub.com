"""
LCopilot Rule-Based Compliance Engine
Advanced DSL-driven compliance validation system with versioning and IP-safe practices.

Features:
- DSL-based rule evaluation with flexible expressions
- Version-controlled rule definitions
- Tier-based gating (Free: 3 checks, Pro/Enterprise: unlimited)
- Handler dispatch for complex validation logic
- Scoring with weighted severity
- IP-safe rule authoring practices
"""

import re
import json
import yaml
import logging
import importlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RuleStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIP = "skip"

class RuleSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class RuleResult:
    id: str
    status: RuleStatus
    details: str
    severity: RuleSeverity
    version: str
    field_location: Optional[str] = None
    suggested_fix: Optional[str] = None

@dataclass
class ValidationResult:
    source: str
    results: List[RuleResult]
    score: float
    rule_versions: Dict[str, str]
    tier_used: str
    checks_remaining: Optional[int] = None
    upsell_triggered: bool = False

@dataclass
class RuleDefinition:
    id: str
    title: str
    reference: str
    severity: RuleSeverity
    applies_to: List[str]
    preconditions: List[Dict[str, Any]]
    dsl: Optional[str]
    check_handler: Optional[str]
    examples: Dict[str, List[str]]
    version: str
    description: Optional[str] = None

class DSLEvaluator:
    """Domain Specific Language evaluator for compliance rules"""

    def __init__(self):
        self.functions = {
            'exists': self._exists,
            'not_empty': self._not_empty,
            'equalsIgnoreCase': self._equals_ignore_case,
            'in': self._in,
            'dateWithinDays': self._date_within_days,
            'allPresent': self._all_present,
            'matchesRegex': self._matches_regex,
            'containsText': self._contains_text,
            'presentInDocs': self._present_in_docs,
            'ifThen': self._if_then,
            'length': self._length,
            'numeric': self._numeric,
            'percentage': self._percentage,
            'currency': self._currency,
            'dateFormat': self._date_format,
            'portName': self._port_name,
            'bankCode': self._bank_code,
            'hsCode': self._hs_code
        }

    def evaluate(self, expression: str, context: Dict[str, Any]) -> bool:
        """Evaluate DSL expression against LC document context"""
        try:
            # Store context for function access
            self.context = context

            # Parse and evaluate expression
            result = self._parse_expression(expression)
            return bool(result)

        except Exception as e:
            logger.error(f"DSL evaluation error: {str(e)} in expression: {expression}")
            return False

    def _parse_expression(self, expr: str) -> Any:
        """Parse and evaluate DSL expression"""
        expr = expr.strip()

        # Handle logical operators
        if ' && ' in expr:
            parts = expr.split(' && ')
            return all(self._parse_expression(part.strip()) for part in parts)

        if ' || ' in expr:
            parts = expr.split(' || ')
            return any(self._parse_expression(part.strip()) for part in parts)

        # Handle negation
        if expr.startswith('!'):
            return not self._parse_expression(expr[1:].strip())

        # Handle function calls
        if '(' in expr and ')' in expr:
            return self._evaluate_function(expr)

        # Handle field access
        if '.' in expr:
            return self._get_field_value(expr)

        # Handle literals
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]

        if expr.startswith("'") and expr.endswith("'"):
            return expr[1:-1]

        if expr.isdigit():
            return int(expr)

        try:
            return float(expr)
        except ValueError:
            pass

        if expr.lower() in ['true', 'false']:
            return expr.lower() == 'true'

        # Assume it's a field reference
        return self._get_field_value(expr)

    def _evaluate_function(self, expr: str) -> Any:
        """Evaluate function call"""
        func_match = re.match(r'(\w+)\((.*)\)', expr)
        if not func_match:
            raise ValueError(f"Invalid function call: {expr}")

        func_name = func_match.group(1)
        args_str = func_match.group(2)

        if func_name not in self.functions:
            raise ValueError(f"Unknown function: {func_name}")

        # Parse arguments
        args = self._parse_arguments(args_str)

        # Call function
        return self.functions[func_name](*args)

    def _parse_arguments(self, args_str: str) -> List[Any]:
        """Parse function arguments"""
        if not args_str.strip():
            return []

        args = []
        current_arg = ""
        paren_depth = 0
        bracket_depth = 0
        in_quotes = False
        quote_char = None

        for char in args_str:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
                current_arg += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_arg += char
            elif not in_quotes:
                if char == '(':
                    paren_depth += 1
                    current_arg += char
                elif char == ')':
                    paren_depth -= 1
                    current_arg += char
                elif char == '[':
                    bracket_depth += 1
                    current_arg += char
                elif char == ']':
                    bracket_depth -= 1
                    current_arg += char
                elif char == ',' and paren_depth == 0 and bracket_depth == 0:
                    args.append(self._parse_expression(current_arg.strip()))
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char

        if current_arg.strip():
            args.append(self._parse_expression(current_arg.strip()))

        return args

    def _get_field_value(self, field_path: str) -> Any:
        """Get field value from context using dot notation"""
        parts = field_path.split('.')
        value = self.context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                value = value[idx] if 0 <= idx < len(value) else None
            else:
                return None

            if value is None:
                return None

        return value

    # DSL Functions
    def _exists(self, field_path: str) -> bool:
        """Check if field exists and is not None"""
        value = self._get_field_value(field_path)
        return value is not None

    def _not_empty(self, field_path: str) -> bool:
        """Check if field exists and is not empty"""
        value = self._get_field_value(field_path)
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True

    def _equals_ignore_case(self, field_path: str, expected: str) -> bool:
        """Case-insensitive string comparison"""
        value = self._get_field_value(field_path)
        if value is None:
            return False
        return str(value).lower() == str(expected).lower()

    def _in(self, field_path: str, values: List[str]) -> bool:
        """Check if field value is in list"""
        value = self._get_field_value(field_path)
        if value is None:
            return False
        return str(value) in [str(v) for v in values]

    def _date_within_days(self, date_field: str, base_field: str, days: int) -> bool:
        """Check if date is within specified days of base date"""
        date_value = self._get_field_value(date_field)
        base_value = self._get_field_value(base_field)

        if not date_value or not base_value:
            return False

        try:
            from dateutil.parser import parse
            date_dt = parse(str(date_value))
            base_dt = parse(str(base_value))

            diff = abs((date_dt - base_dt).days)
            return diff <= days
        except:
            return False

    def _all_present(self, field_paths: List[str]) -> bool:
        """Check if all fields are present"""
        return all(self._exists(field) for field in field_paths)

    def _matches_regex(self, field_path: str, pattern: str) -> bool:
        """Check if field matches regex pattern"""
        value = self._get_field_value(field_path)
        if value is None:
            return False

        try:
            return bool(re.match(pattern, str(value)))
        except:
            return False

    def _contains_text(self, field_path: str, token: str) -> bool:
        """Check if field contains text token"""
        value = self._get_field_value(field_path)
        if value is None:
            return False
        return str(token).lower() in str(value).lower()

    def _present_in_docs(self, doc_type: str) -> bool:
        """Check if document type is present in required documents"""
        docs = self._get_field_value('required_documents')
        if not docs:
            return False

        doc_type_lower = doc_type.lower()
        return any(doc_type_lower in str(doc).lower() for doc in docs)

    def _if_then(self, condition: bool, then_expr: Any) -> Any:
        """Conditional expression"""
        return then_expr if condition else True

    def _length(self, field_path: str) -> int:
        """Get length of field value"""
        value = self._get_field_value(field_path)
        if value is None:
            return 0
        return len(str(value))

    def _numeric(self, field_path: str) -> bool:
        """Check if field is numeric"""
        value = self._get_field_value(field_path)
        if value is None:
            return False
        try:
            float(str(value))
            return True
        except:
            return False

    def _percentage(self, field_path: str, min_val: float = 0, max_val: float = 100) -> bool:
        """Check if field is valid percentage"""
        value = self._get_field_value(field_path)
        if value is None:
            return False
        try:
            num = float(str(value).replace('%', ''))
            return min_val <= num <= max_val
        except:
            return False

    def _currency(self, field_path: str, valid_currencies: List[str] = None) -> bool:
        """Check if field is valid currency code"""
        value = self._get_field_value(field_path)
        if value is None:
            return False

        if valid_currencies:
            return str(value).upper() in [c.upper() for c in valid_currencies]

        # Common currency codes
        common_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'BDT', 'CNY', 'INR']
        return str(value).upper() in common_currencies

    def _date_format(self, field_path: str, format_pattern: str = None) -> bool:
        """Check if field is valid date format"""
        value = self._get_field_value(field_path)
        if value is None:
            return False

        try:
            from dateutil.parser import parse
            parse(str(value))
            return True
        except:
            return False

    def _port_name(self, field_path: str) -> bool:
        """Check if field is valid port name"""
        value = self._get_field_value(field_path)
        if value is None:
            return False

        port_value = str(value).lower()
        valid_patterns = ['port', 'airport', 'terminal', 'harbor', 'harbour']
        return any(pattern in port_value for pattern in valid_patterns) or len(port_value) > 3

    def _bank_code(self, field_path: str) -> bool:
        """Check if field is valid bank code format"""
        value = self._get_field_value(field_path)
        if value is None:
            return False

        # SWIFT BIC format or similar
        return len(str(value)) >= 4 and str(value).isalnum()

    def _hs_code(self, field_path: str) -> bool:
        """Check if field is valid HS code format"""
        value = self._get_field_value(field_path)
        if value is None:
            return False

        hs_code = str(value).replace('.', '').replace('-', '')
        return hs_code.isdigit() and len(hs_code) >= 4

class RuleEngine:
    """Main rule engine for compliance validation"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent / "config" / "trust_config.yaml"
        self.dsl_evaluator = DSLEvaluator()
        self.rules: Dict[str, RuleDefinition] = {}
        self.handlers_cache: Dict[str, Any] = {}

        # Load configuration and rules
        self._load_config()
        self._load_rules()

    def _load_config(self):
        """Load trust platform configuration"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config not found at {self.config_path}")
            self.config = {}

    def _load_rules(self):
        """Load all rule packs from configuration"""
        compliance_config = self.config.get('compliance', {})
        rule_packs = compliance_config.get('packs', [])

        for pack_path in rule_packs:
            self._load_rule_pack(pack_path)

        logger.info(f"Loaded {len(self.rules)} compliance rules")

    def _load_rule_pack(self, pack_path: str):
        """Load rules from a YAML pack file"""
        try:
            # Resolve path relative to config directory
            if not Path(pack_path).is_absolute():
                pack_path = self.config_path.parent.parent / pack_path

            with open(pack_path, 'r') as f:
                pack_data = yaml.safe_load(f)

            rules_list = pack_data.get('rules', [])
            for rule_data in rules_list:
                rule = self._parse_rule_definition(rule_data)
                self.rules[rule.id] = rule

            logger.info(f"Loaded {len(rules_list)} rules from {pack_path}")

        except Exception as e:
            logger.error(f"Failed to load rule pack {pack_path}: {str(e)}")

    def _parse_rule_definition(self, rule_data: Dict[str, Any]) -> RuleDefinition:
        """Parse rule definition from YAML data"""
        return RuleDefinition(
            id=rule_data['id'],
            title=rule_data['title'],
            reference=rule_data['reference'],
            severity=RuleSeverity(rule_data['severity']),
            applies_to=rule_data.get('applies_to', []),
            preconditions=rule_data.get('preconditions', []),
            dsl=rule_data.get('dsl'),
            check_handler=rule_data.get('check_handler'),
            examples=rule_data.get('examples', {}),
            version=rule_data['version'],
            description=rule_data.get('description')
        )

    def validate(self, lc_document: Dict[str, Any], tier: str,
                remaining_free_checks: Optional[int] = None) -> ValidationResult:
        """
        Main validation entry point

        Args:
            lc_document: LC document JSON
            tier: Customer tier (free/pro/enterprise)
            remaining_free_checks: Remaining checks for free tier

        Returns:
            ValidationResult with rule results and scoring
        """

        # Check tier limits
        if tier == 'free' and remaining_free_checks is not None and remaining_free_checks <= 0:
            return ValidationResult(
                source="ucp600_isbp",
                results=[],
                score=0.0,
                rule_versions={},
                tier_used=tier,
                checks_remaining=0,
                upsell_triggered=True
            )

        # Execute all applicable rules
        results = []
        rule_versions = {}

        for rule_id, rule in self.rules.items():
            try:
                # Check if rule applies to this document
                if not self._rule_applies(rule, lc_document):
                    continue

                # Check preconditions
                if not self._check_preconditions(rule, lc_document):
                    continue

                # Execute rule
                result = self._execute_rule(rule, lc_document)
                results.append(result)
                rule_versions[rule_id] = rule.version

            except Exception as e:
                logger.error(f"Error executing rule {rule_id}: {str(e)}")
                results.append(RuleResult(
                    id=rule_id,
                    status=RuleStatus.ERROR,
                    details=f"Rule execution error: {str(e)}",
                    severity=rule.severity,
                    version=rule.version
                ))
                rule_versions[rule_id] = rule.version

        # Calculate score
        score = self._calculate_score(results)

        # Update remaining checks for free tier
        checks_remaining = None
        if tier == 'free' and remaining_free_checks is not None:
            checks_remaining = remaining_free_checks - 1

        return ValidationResult(
            source="ucp600_isbp",
            results=results,
            score=score,
            rule_versions=rule_versions,
            tier_used=tier,
            checks_remaining=checks_remaining,
            upsell_triggered=False
        )

    def _rule_applies(self, rule: RuleDefinition, lc_document: Dict[str, Any]) -> bool:
        """Check if rule applies to this document type"""
        if not rule.applies_to:
            return True

        # Check document types in applies_to
        doc_types = set()
        if 'required_documents' in lc_document:
            for doc in lc_document['required_documents']:
                doc_lower = str(doc).lower()
                if 'invoice' in doc_lower:
                    doc_types.add('invoice')
                if 'bill of lading' in doc_lower or 'bl' in doc_lower:
                    doc_types.add('bl')
                if 'insurance' in doc_lower:
                    doc_types.add('insurance')

        # Always includes credit/lc
        doc_types.add('credit')
        doc_types.add('lc')

        return any(applies in doc_types for applies in rule.applies_to)

    def _check_preconditions(self, rule: RuleDefinition, lc_document: Dict[str, Any]) -> bool:
        """Check if rule preconditions are met"""
        for precondition in rule.preconditions:
            if 'field_exists' in precondition:
                field_path = precondition['field_exists']
                if not self.dsl_evaluator._exists(field_path):
                    return False

        return True

    def _execute_rule(self, rule: RuleDefinition, lc_document: Dict[str, Any]) -> RuleResult:
        """Execute individual rule"""

        # Set context for DSL evaluation
        self.dsl_evaluator.context = lc_document

        try:
            if rule.dsl:
                # Use DSL evaluation
                passed = self.dsl_evaluator.evaluate(rule.dsl, lc_document)
                status = RuleStatus.PASS if passed else RuleStatus.FAIL
                details = rule.title if passed else f"Rule failed: {rule.title}"

            elif rule.check_handler:
                # Use Python handler
                handler_result = self._execute_handler(rule.check_handler, lc_document)
                status = handler_result['status']
                details = handler_result['details']

            else:
                # No validation logic defined
                status = RuleStatus.ERROR
                details = "No DSL or handler defined for rule"

            return RuleResult(
                id=rule.id,
                status=status,
                details=details,
                severity=rule.severity,
                version=rule.version
            )

        except Exception as e:
            logger.error(f"Rule execution failed for {rule.id}: {str(e)}")
            return RuleResult(
                id=rule.id,
                status=RuleStatus.ERROR,
                details=f"Execution error: {str(e)}",
                severity=rule.severity,
                version=rule.version
            )

    def _execute_handler(self, handler_name: str, lc_document: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python handler for complex rule logic"""

        if handler_name not in self.handlers_cache:
            try:
                # Import handler module
                handler_module = importlib.import_module(f'trust_platform.compliance.handlers.{handler_name}')
                self.handlers_cache[handler_name] = handler_module
            except ImportError as e:
                raise ValueError(f"Handler not found: {handler_name} - {str(e)}")

        handler_module = self.handlers_cache[handler_name]

        # Call handler validate function
        if hasattr(handler_module, 'validate'):
            return handler_module.validate(lc_document)
        else:
            raise ValueError(f"Handler {handler_name} missing validate function")

    def _calculate_score(self, results: List[RuleResult]) -> float:
        """Calculate weighted compliance score"""
        if not results:
            return 1.0

        # Severity weights
        weights = {
            RuleSeverity.HIGH: 3,
            RuleSeverity.MEDIUM: 2,
            RuleSeverity.LOW: 1
        }

        total_weight = 0
        weighted_passed = 0

        for result in results:
            weight = weights[result.severity]
            total_weight += weight

            if result.status == RuleStatus.PASS:
                weighted_passed += weight
            elif result.status == RuleStatus.WARNING:
                weighted_passed += weight * 0.5  # Partial credit
            # FAIL and ERROR get 0 points

        if total_weight == 0:
            return 1.0

        return weighted_passed / total_weight

    def get_rule_info(self, rule_id: str) -> Optional[RuleDefinition]:
        """Get information about a specific rule"""
        return self.rules.get(rule_id)

    def list_rules(self) -> List[RuleDefinition]:
        """List all loaded rules"""
        return list(self.rules.values())

def main():
    """Demo the rule engine"""
    engine = RuleEngine()

    # Sample LC document
    sample_lc = {
        "lc_number": "LC2024001",
        "issue_date": "2024-01-15",
        "expiry_date": "2024-03-15",
        "expiry_place": "Counters of the nominated bank",
        "latest_shipment_date": "2024-03-01",
        "amount": {"value": 50000.00, "currency": "USD"},
        "beneficiary": {
            "name": "Global Exports Ltd",
            "address": "123 Export Street, Chittagong-4000, Bangladesh"
        },
        "applicant": {
            "name": "American Imports Inc",
            "address": "456 Import Ave, Commerce City, CC 67890"
        },
        "required_documents": [
            "Commercial Invoice signed and dated",
            "Clean on board Bill of Lading",
            "Insurance Policy for 110% of CIF value"
        ]
    }

    print("=== LCopilot Rule Engine Demo ===")
    print(f"Loaded {len(engine.rules)} rules")

    # Test different tiers
    for tier in ['free', 'pro', 'enterprise']:
        print(f"\n--- Testing {tier} tier ---")

        remaining_checks = 3 if tier == 'free' else None
        result = engine.validate(sample_lc, tier, remaining_checks)

        print(f"Score: {result.score:.3f}")
        print(f"Rules evaluated: {len(result.results)}")

        if result.upsell_triggered:
            print("UPSELL: Free tier limits reached")

        # Show rule results
        for rule_result in result.results[:3]:  # First 3 results
            print(f"  {rule_result.id}: {rule_result.status.value} - {rule_result.details}")

if __name__ == "__main__":
    main()