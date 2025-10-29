#!/usr/bin/env python3
"""
LCopilot Rule Authoring CLI
Command-line tools for creating, editing, and managing compliance rules.

Commands:
- rules:new --id UCP600-XX        Create new rule with scaffolding
- rules:edit --id UCP600-XX       Edit existing rule
- rules:lint                      Validate all rules
- rules:test --id UCP600-XX       Run tests for specific rule
- rules:list                      List all rules with versions
"""

import argparse
import sys
import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from trust_platform.compliance.rule_linter import RuleLinter
from trust_platform.compliance.rule_engine import RuleEngine

class RuleAuthorCLI:
    """CLI for rule authoring and management"""

    def __init__(self):
        self.base_path = Path(__file__).parent
        self.rules_path = self.base_path / "rules"
        self.handlers_path = self.base_path / "handlers"
        self.fixtures_path = self.base_path / "fixtures"
        self.tests_path = self.base_path / "tests"

        # Ensure directories exist
        for path in [self.rules_path, self.handlers_path, self.fixtures_path, self.tests_path]:
            path.mkdir(exist_ok=True)

        self.linter = RuleLinter()

    def create_new_rule(self, rule_id: str, rule_pack: Optional[str] = None):
        """Create new rule with scaffolding"""

        # Determine rule pack based on ID prefix
        if not rule_pack:
            if rule_id.startswith('UCP600'):
                rule_pack = 'ucp600'
            elif rule_id.startswith('ISBP'):
                rule_pack = 'isbp'
            elif rule_id.startswith('BD'):
                rule_pack = 'local_bd'
            else:
                rule_pack = 'custom'

        rule_file = self.rules_path / f"{rule_pack}.yaml"

        # Load existing rules or create new file
        if rule_file.exists():
            with open(rule_file, 'r') as f:
                rules_data = yaml.safe_load(f)
        else:
            rules_data = {
                'metadata': {
                    'standard': rule_pack.upper(),
                    'version': '2024.1',
                    'description': f'{rule_pack} compliance rules',
                    'last_updated': '2024-12-20'
                },
                'rules': []
            }

        # Check if rule already exists
        existing_rule = next((r for r in rules_data['rules'] if r['id'] == rule_id), None)
        if existing_rule:
            print(f"❌ Rule {rule_id} already exists in {rule_pack}.yaml")
            return False

        # Create rule template
        new_rule = {
            'id': rule_id,
            'title': f'TODO: Add title for {rule_id}',
            'reference': f'TODO: Add reference for {rule_id}',
            'severity': 'medium',
            'applies_to': ['credit'],
            'preconditions': [],
            'dsl': 'TODO: Add DSL expression or set check_handler',
            'examples': {
                'pass': [f'fixtures/{rule_id.lower().replace("-", "_")}_pass.json'],
                'fail': [f'fixtures/{rule_id.lower().replace("-", "_")}_fail.json']
            },
            'version': '1.0.0'
        }

        # Add rule to pack
        rules_data['rules'].append(new_rule)

        # Save updated rules file
        with open(rule_file, 'w') as f:
            yaml.dump(rules_data, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Created rule {rule_id} in {rule_pack}.yaml")

        # Create handler stub if needed
        if 'check_handler' in str(new_rule.get('dsl', '')):
            self._create_handler_stub(rule_id)

        # Create fixture stubs
        self._create_fixture_stubs(rule_id)

        # Create test stub
        self._create_test_stub(rule_id)

        print(f"📁 Created scaffolding files:")
        print(f"   - Rule definition: {rule_file}")
        print(f"   - Test fixtures: {self.fixtures_path}/{rule_id.lower().replace('-', '_')}_*.json")
        print(f"   - Unit test: {self.tests_path}/test_{rule_id.lower().replace('-', '_')}.py")

        return True

    def edit_rule(self, rule_id: str):
        """Edit existing rule"""

        # Find rule file
        rule_file = self._find_rule_file(rule_id)
        if not rule_file:
            print(f"❌ Rule {rule_id} not found")
            return False

        # Open in editor
        editor = os.environ.get('EDITOR', 'nano')
        os.system(f'{editor} {rule_file}')

        print(f"✅ Opened {rule_file} for editing")
        return True

    def lint_rules(self, rule_pack: Optional[str] = None):
        """Lint all rules or specific rule pack"""

        if rule_pack:
            rule_files = [self.rules_path / f"{rule_pack}.yaml"]
        else:
            rule_files = list(self.rules_path.glob("*.yaml"))

        total_errors = 0
        total_warnings = 0

        for rule_file in rule_files:
            if not rule_file.exists():
                continue

            print(f"\n🔍 Linting {rule_file.name}...")

            errors, warnings = self.linter.lint_file(rule_file)

            if errors:
                print(f"❌ {len(errors)} errors:")
                for error in errors:
                    print(f"   - {error}")
                total_errors += len(errors)

            if warnings:
                print(f"⚠️  {len(warnings)} warnings:")
                for warning in warnings:
                    print(f"   - {warning}")
                total_warnings += len(warnings)

            if not errors and not warnings:
                print("✅ No issues found")

        print(f"\n📊 Linting Summary:")
        print(f"   Total errors: {total_errors}")
        print(f"   Total warnings: {total_warnings}")

        return total_errors == 0

    def test_rule(self, rule_id: str):
        """Run tests for specific rule"""

        # Find test file
        test_file = self.tests_path / f"test_{rule_id.lower().replace('-', '_')}.py"

        if not test_file.exists():
            print(f"❌ Test file not found: {test_file}")
            return False

        # Run pytest on specific test
        import subprocess
        try:
            result = subprocess.run(['python', '-m', 'pytest', str(test_file), '-v'],
                                  capture_output=True, text=True, cwd=self.base_path.parent.parent)

            print(f"🧪 Test Results for {rule_id}:")
            print(result.stdout)

            if result.stderr:
                print("Errors:")
                print(result.stderr)

            return result.returncode == 0

        except FileNotFoundError:
            print("❌ pytest not found. Install with: pip install pytest")
            return False

    def list_rules(self):
        """List all rules with versions and severity"""

        print("📋 LCopilot Compliance Rules\n")

        rule_files = list(self.rules_path.glob("*.yaml"))

        for rule_file in rule_files:
            try:
                with open(rule_file, 'r') as f:
                    rules_data = yaml.safe_load(f)

                pack_name = rule_file.stem.upper()
                rules_list = rules_data.get('rules', [])

                print(f"📦 {pack_name} ({len(rules_list)} rules)")

                for rule in rules_list:
                    severity_emoji = {
                        'low': '🟢',
                        'medium': '🟡',
                        'high': '🔴'
                    }.get(rule.get('severity', 'medium'), '⚪')

                    print(f"   {severity_emoji} {rule['id']} v{rule.get('version', '1.0.0')} - {rule.get('title', 'No title')}")

                print()

            except Exception as e:
                print(f"❌ Error reading {rule_file}: {str(e)}")

    def _find_rule_file(self, rule_id: str) -> Optional[Path]:
        """Find which file contains the specified rule"""

        rule_files = list(self.rules_path.glob("*.yaml"))

        for rule_file in rule_files:
            try:
                with open(rule_file, 'r') as f:
                    rules_data = yaml.safe_load(f)

                rules_list = rules_data.get('rules', [])
                if any(rule['id'] == rule_id for rule in rules_list):
                    return rule_file

            except Exception:
                continue

        return None

    def _create_handler_stub(self, rule_id: str):
        """Create Python handler stub"""

        handler_name = rule_id.lower().replace('-', '_')
        handler_file = self.handlers_path / f"{handler_name}.py"

        if handler_file.exists():
            return

        handler_template = f'''"""
{rule_id}: Handler
TODO: Add description for {rule_id} validation logic
"""

from typing import Dict, Any

def validate(lc_document: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate {rule_id} compliance

    TODO: Implement validation logic

    Args:
        lc_document: LC document dictionary

    Returns:
        Dictionary with status, details, field_location, suggested_fix
    """

    try:
        # TODO: Implement validation logic
        return {{
            "status": "pass",  # pass/fail/warning/error
            "details": "TODO: Add validation details",
            "field_location": "TODO: Add field path",
            "suggested_fix": "TODO: Add suggested fix"
        }}

    except Exception as e:
        return {{
            "status": "error",
            "details": f"Error validating {rule_id}: {{str(e)}}",
            "field_location": "unknown"
        }}
'''

        with open(handler_file, 'w') as f:
            f.write(handler_template)

    def _create_fixture_stubs(self, rule_id: str):
        """Create JSON fixture stubs"""

        fixture_base = rule_id.lower().replace('-', '_')

        # Pass fixture
        pass_fixture = {
            "lc_number": "LC2024001",
            "issue_date": "2024-01-15",
            "expiry_date": "2024-03-15",
            "amount": {"value": 50000.00, "currency": "USD"},
            "beneficiary": {"name": "Test Beneficiary"},
            "applicant": {"name": "Test Applicant"},
            "_test_note": f"TODO: Configure this fixture to PASS {rule_id}"
        }

        # Fail fixture
        fail_fixture = {
            "lc_number": "LC2024002",
            "issue_date": "2024-01-15",
            "expiry_date": "2024-03-15",
            "amount": {"value": 50000.00, "currency": "USD"},
            "_test_note": f"TODO: Configure this fixture to FAIL {rule_id}"
        }

        # Write fixtures
        pass_file = self.fixtures_path / f"{fixture_base}_pass.json"
        fail_file = self.fixtures_path / f"{fixture_base}_fail.json"

        with open(pass_file, 'w') as f:
            json.dump(pass_fixture, f, indent=2)

        with open(fail_file, 'w') as f:
            json.dump(fail_fixture, f, indent=2)

    def _create_test_stub(self, rule_id: str):
        """Create unit test stub"""

        test_name = rule_id.lower().replace('-', '_')
        test_file = self.tests_path / f"test_{test_name}.py"

        if test_file.exists():
            return

        test_template = f'''"""
Unit tests for {rule_id}
"""

import unittest
import json
from pathlib import Path

from trust_platform.compliance.rule_engine import RuleEngine

class Test{rule_id.replace("-", "")}(unittest.TestCase):
    """Test cases for {rule_id}"""

    def setUp(self):
        self.engine = RuleEngine()
        self.fixtures_path = Path(__file__).parent.parent / "fixtures"

    def test_{test_name}_pass(self):
        """Test {rule_id} passing case"""

        # Load pass fixture
        with open(self.fixtures_path / "{test_name}_pass.json") as f:
            lc_document = json.load(f)

        # Run validation
        result = self.engine.validate(lc_document, "pro")

        # Find our rule result
        rule_result = next((r for r in result.results if r.id == "{rule_id}"), None)
        self.assertIsNotNone(rule_result, f"Rule {rule_id} not executed")

        # Assert pass
        self.assertEqual(rule_result.status.value, "pass",
                        f"Rule should pass but got: {{rule_result.details}}")

    def test_{test_name}_fail(self):
        """Test {rule_id} failing case"""

        # Load fail fixture
        with open(self.fixtures_path / "{test_name}_fail.json") as f:
            lc_document = json.load(f)

        # Run validation
        result = self.engine.validate(lc_document, "pro")

        # Find our rule result
        rule_result = next((r for r in result.results if r.id == "{rule_id}"), None)
        self.assertIsNotNone(rule_result, f"Rule {rule_id} not executed")

        # Assert fail
        self.assertEqual(rule_result.status.value, "fail",
                        f"Rule should fail but got: {{rule_result.details}}")

if __name__ == "__main__":
    unittest.main()
'''

        with open(test_file, 'w') as f:
            f.write(test_template)

def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(description="LCopilot Rule Authoring CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # rules:new
    new_parser = subparsers.add_parser('rules:new', help='Create new rule')
    new_parser.add_argument('--id', required=True, help='Rule ID (e.g., UCP600-42)')
    new_parser.add_argument('--pack', help='Rule pack (ucp600/isbp/local_bd)')

    # rules:edit
    edit_parser = subparsers.add_parser('rules:edit', help='Edit existing rule')
    edit_parser.add_argument('--id', required=True, help='Rule ID to edit')

    # rules:lint
    lint_parser = subparsers.add_parser('rules:lint', help='Lint rules')
    lint_parser.add_argument('--pack', help='Specific rule pack to lint')

    # rules:test
    test_parser = subparsers.add_parser('rules:test', help='Run rule tests')
    test_parser.add_argument('--id', required=True, help='Rule ID to test')

    # rules:list
    subparsers.add_parser('rules:list', help='List all rules')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = RuleAuthorCLI()

    if args.command == 'rules:new':
        success = cli.create_new_rule(args.id, args.pack)
        sys.exit(0 if success else 1)

    elif args.command == 'rules:edit':
        success = cli.edit_rule(args.id)
        sys.exit(0 if success else 1)

    elif args.command == 'rules:lint':
        success = cli.lint_rules(args.pack)
        sys.exit(0 if success else 1)

    elif args.command == 'rules:test':
        success = cli.test_rule(args.id)
        sys.exit(0 if success else 1)

    elif args.command == 'rules:list':
        cli.list_rules()
        sys.exit(0)

if __name__ == "__main__":
    main()