#!/usr/bin/env python3
"""
Rule Linter for LCopilot Compliance Rules
Validates YAML rule definitions for proper structure and IP-safe practices.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


class RuleLinter:
    """Lints compliance rule YAML files for structure and IP safety"""

    def __init__(self):
        self.forbidden_patterns = [
            # Prevent direct ICC text quotation
            r'shall\s+be\s+[^.]{50,}',  # Long "shall be" clauses often from ICC
            r'must\s+be\s+[^.]{50,}',   # Long "must be" clauses
            r'article\s+\d+\s+[a-z]\)\s*[^.]{30,}',  # Article quotes
            r'ucp\s*600\s*[^.]{100,}',  # Long UCP600 text
            r'isbp\s*[^.]{100,}',       # Long ISBP text
        ]

        self.required_metadata_fields = ['standard', 'version', 'description', 'last_updated']
        self.required_rule_fields = ['id', 'title', 'reference', 'severity', 'applies_to', 'version']
        self.valid_severities = ['low', 'medium', 'high']
        self.valid_statuses = ['pass', 'fail', 'warning', 'error']
        self.valid_applies_to = ['credit', 'amendment', 'standby']

        # DSL function validation patterns
        self.dsl_functions = [
            'exists', 'not_empty', 'equals', 'equalsIgnoreCase', 'contains',
            'containsIgnoreCase', 'matches', 'length', 'greaterThan', 'lessThan',
            'dateWithinDays', 'dateAfter', 'dateBefore', 'amountGreaterThan',
            'amountLessThan', 'check_handler'
        ]

    def lint_file(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """
        Lint a single YAML rule file

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content)

        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {str(e)}")
            return errors, warnings
        except Exception as e:
            errors.append(f"Failed to read file: {str(e)}")
            return errors, warnings

        # Check file structure
        file_errors, file_warnings = self._validate_file_structure(data)
        errors.extend(file_errors)
        warnings.extend(file_warnings)

        # Check IP safety
        ip_errors, ip_warnings = self._validate_ip_safety(content, data)
        errors.extend(ip_errors)
        warnings.extend(ip_warnings)

        # Check metadata
        if 'metadata' in data:
            meta_errors, meta_warnings = self._validate_metadata(data['metadata'])
            errors.extend(meta_errors)
            warnings.extend(meta_warnings)

        # Check rules
        if 'rules' in data:
            for i, rule in enumerate(data['rules']):
                rule_errors, rule_warnings = self._validate_rule(rule, i)
                errors.extend(rule_errors)
                warnings.extend(rule_warnings)

        return errors, warnings

    def _validate_file_structure(self, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate overall file structure"""
        errors = []
        warnings = []

        if not isinstance(data, dict):
            errors.append("Root must be a dictionary")
            return errors, warnings

        if 'metadata' not in data:
            errors.append("Missing 'metadata' section")

        if 'rules' not in data:
            errors.append("Missing 'rules' section")
        elif not isinstance(data['rules'], list):
            errors.append("'rules' must be a list")
        elif len(data['rules']) == 0:
            warnings.append("No rules defined")

        return errors, warnings

    def _validate_ip_safety(self, content: str, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate IP-safe practices"""
        errors = []
        warnings = []

        # Check for forbidden long text patterns
        for pattern in self.forbidden_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match) > 50:
                    errors.append(f"Potential ICC text quotation found: '{match[:50]}...'")

        # Check rule titles and descriptions for excessive length
        if 'rules' in data:
            for rule in data['rules']:
                title = rule.get('title', '')
                if len(title) > 100:
                    warnings.append(f"Rule {rule.get('id', 'unknown')}: Title very long, may contain copyrighted text")

                # Check for direct article quotes in DSL
                dsl = str(rule.get('dsl', ''))
                if len(dsl) > 200 and any(word in dsl.lower() for word in ['shall', 'must', 'article']):
                    warnings.append(f"Rule {rule.get('id', 'unknown')}: DSL may contain direct ICC text")

        return errors, warnings

    def _validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate metadata section"""
        errors = []
        warnings = []

        for field in self.required_metadata_fields:
            if field not in metadata:
                errors.append(f"Missing required metadata field: {field}")
            elif not metadata[field]:
                warnings.append(f"Empty metadata field: {field}")

        # Validate version format
        version = metadata.get('version', '')
        if version and not re.match(r'^\d{4}\.\d+$', str(version)):
            warnings.append(f"Metadata version should follow YYYY.N format: {version}")

        # Validate date format
        last_updated = metadata.get('last_updated', '')
        if last_updated and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(last_updated)):
            warnings.append(f"last_updated should be YYYY-MM-DD format: {last_updated}")

        return errors, warnings

    def _validate_rule(self, rule: Dict[str, Any], index: int) -> Tuple[List[str], List[str]]:
        """Validate individual rule"""
        errors = []
        warnings = []
        rule_id = rule.get('id', f'rule_{index}')

        # Check required fields
        for field in self.required_rule_fields:
            if field not in rule:
                errors.append(f"Rule {rule_id}: Missing required field '{field}'")
            elif not rule[field]:
                errors.append(f"Rule {rule_id}: Empty required field '{field}'")

        # Validate rule ID format
        rule_id_val = rule.get('id', '')
        if rule_id_val:
            if not re.match(r'^[A-Z0-9-]+$', rule_id_val):
                errors.append(f"Rule {rule_id}: ID should be uppercase alphanumeric with hyphens")
            if not any(prefix in rule_id_val for prefix in ['UCP600', 'ISBP', 'BD']):
                warnings.append(f"Rule {rule_id}: ID should include standard prefix (UCP600/ISBP/BD)")

        # Validate severity
        severity = rule.get('severity')
        if severity and severity not in self.valid_severities:
            errors.append(f"Rule {rule_id}: Invalid severity '{severity}'. Must be: {', '.join(self.valid_severities)}")

        # Validate applies_to
        applies_to = rule.get('applies_to', [])
        if applies_to:
            for item in applies_to:
                if item not in self.valid_applies_to:
                    errors.append(f"Rule {rule_id}: Invalid applies_to '{item}'. Must be: {', '.join(self.valid_applies_to)}")

        # Validate version format
        version = rule.get('version', '')
        if version and not re.match(r'^\d+\.\d+\.\d+$', str(version)):
            warnings.append(f"Rule {rule_id}: Version should follow semantic versioning (x.y.z): {version}")

        # Validate DSL syntax
        dsl = rule.get('dsl')
        if dsl:
            dsl_errors, dsl_warnings = self._validate_dsl(rule_id, str(dsl))
            errors.extend(dsl_errors)
            warnings.extend(dsl_warnings)

        # Validate handler reference
        check_handler = rule.get('check_handler')
        if check_handler:
            handler_errors, handler_warnings = self._validate_handler_reference(rule_id, check_handler)
            errors.extend(handler_errors)
            warnings.extend(handler_warnings)

        # Check for TODO placeholders
        for field, value in rule.items():
            if isinstance(value, str) and 'TODO' in value:
                warnings.append(f"Rule {rule_id}: Field '{field}' contains TODO placeholder")

        # Validate examples structure
        examples = rule.get('examples')
        if examples:
            if not isinstance(examples, dict):
                errors.append(f"Rule {rule_id}: 'examples' must be a dictionary")
            else:
                for status in ['pass', 'fail']:
                    if status in examples:
                        if not isinstance(examples[status], list):
                            errors.append(f"Rule {rule_id}: examples.{status} must be a list")

        return errors, warnings

    def _validate_dsl(self, rule_id: str, dsl: str) -> Tuple[List[str], List[str]]:
        """Validate DSL syntax"""
        errors = []
        warnings = []

        # Check for balanced parentheses
        if dsl.count('(') != dsl.count(')'):
            errors.append(f"Rule {rule_id}: Unbalanced parentheses in DSL")

        # Check for valid function calls
        function_pattern = r'(\w+)\s*\('
        functions_used = re.findall(function_pattern, dsl)

        for func in functions_used:
            if func not in self.dsl_functions:
                errors.append(f"Rule {rule_id}: Unknown DSL function '{func}'")

        # Check for string quoting issues
        single_quotes = dsl.count("'")
        double_quotes = dsl.count('"')

        if single_quotes % 2 != 0:
            errors.append(f"Rule {rule_id}: Unmatched single quotes in DSL")
        if double_quotes % 2 != 0:
            errors.append(f"Rule {rule_id}: Unmatched double quotes in DSL")

        # Check for common DSL patterns
        if 'exists(' in dsl and 'not_empty(' not in dsl:
            warnings.append(f"Rule {rule_id}: Consider adding not_empty() check with exists()")

        return errors, warnings

    def _validate_handler_reference(self, rule_id: str, handler: str) -> Tuple[List[str], List[str]]:
        """Validate handler file reference"""
        errors = []
        warnings = []

        # Check if handler file exists
        base_path = Path(__file__).parent
        handler_path = base_path / 'handlers' / f"{handler}.py"

        if not handler_path.exists():
            errors.append(f"Rule {rule_id}: Handler file not found: handlers/{handler}.py")
        else:
            # Check if validate function exists
            try:
                with open(handler_path, 'r') as f:
                    content = f.read()
                    if 'def validate(' not in content:
                        errors.append(f"Rule {rule_id}: Handler {handler}.py missing validate() function")
            except Exception as e:
                warnings.append(f"Rule {rule_id}: Could not validate handler file: {str(e)}")

        return errors, warnings

    def lint_directory(self, directory: Path) -> Dict[str, Tuple[List[str], List[str]]]:
        """Lint all YAML files in directory"""
        results = {}

        for yaml_file in directory.glob("*.yaml"):
            errors, warnings = self.lint_file(yaml_file)
            results[yaml_file.name] = (errors, warnings)

        return results