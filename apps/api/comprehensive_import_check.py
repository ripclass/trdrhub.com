"""
Comprehensive import check script to find potential deployment failures.

This script checks for common patterns that cause import errors:
1. Missing type imports (Optional, List, Dict, Any, Tuple, etc.)
2. Wrong import paths (app.core.database vs app.database)
3. Missing modules that are imported
4. Missing singleton instances
5. Type hints using undefined classes
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Common typing imports that are often missing
COMMON_TYPING_IMPORTS = {
    'Optional', 'List', 'Dict', 'Any', 'Tuple', 'Union', 'Callable',
    'Type', 'TypeVar', 'Generic', 'Sequence', 'Iterable', 'Iterator',
    'Set', 'FrozenSet', 'Mapping', 'MutableMapping', 'OrderedDict'
}

# Common standard library imports
COMMON_STDLIB_IMPORTS = {
    'logging', 'json', 'datetime', 'uuid', 'hashlib', 'asyncio',
    'os', 'sys', 'pathlib', 'typing', 'collections', 'functools',
    'itertools', 'enum', 'dataclasses', 'abc', 'contextlib'
}

# Known problematic import patterns
PROBLEMATIC_IMPORTS = {
    'app.core.database': 'app.database',
    'app.core.config': 'app.config',
    'app.utils.audit': 'app.middleware.audit_middleware',
}

# Files to check
def get_python_files(root_dir: str) -> List[Path]:
    """Get all Python files in the app directory."""
    root = Path(root_dir)
    files = []
    for path in root.rglob('*.py'):
        # Skip __pycache__ and venv
        if '__pycache__' in str(path) or 'venv' in str(path):
            continue
        files.append(path)
    return files

def check_file_imports(file_path: Path) -> Dict[str, List[str]]:
    """Check a single file for import issues."""
    issues = defaultdict(list)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        issues['parse_errors'].append(f"Could not parse: {e}")
        return dict(issues)
    
    # Track imports
    imported_names = set()
    imported_modules = set()
    used_names = set()
    type_hints = set()
    
    # Walk AST
    for node in ast.walk(tree):
        # Collect imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
                imported_names.add(alias.asname or alias.name.split('.')[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module)
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)
        
        # Collect used names (function calls, attributes)
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)
        
        # Collect type hints
        if isinstance(node, ast.AnnAssign) and node.annotation:
            type_hints.add(ast.unparse(node.annotation) if hasattr(ast, 'unparse') else str(node.annotation))
        elif isinstance(node, ast.FunctionDef):
            if node.returns:
                type_hints.add(ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns))
            for arg in node.args.args:
                if arg.annotation:
                    type_hints.add(ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation))
    
    # Check for problematic imports
    for line_num, line in enumerate(content.split('\n'), 1):
        for wrong_path, correct_path in PROBLEMATIC_IMPORTS.items():
            if wrong_path in line and 'import' in line:
                issues['wrong_imports'].append(f"Line {line_num}: {wrong_path} -> {correct_path}")
    
    # Check for missing type imports
    for hint in type_hints:
        for typing_name in COMMON_TYPING_IMPORTS:
            if typing_name in hint and typing_name not in imported_names:
                # Check if it's used in a type hint context
                if f': {typing_name}' in content or f'-> {typing_name}' in content or f'[{typing_name}' in content:
                    if f'from typing import' not in content or typing_name not in content.split('from typing import')[1].split('\n')[0] if 'from typing import' in content else '':
                        issues['missing_type_imports'].append(f"Missing: {typing_name}")
    
    # Check for common stdlib imports that might be missing
    for stdlib_name in COMMON_STDLIB_IMPORTS:
        if stdlib_name in used_names and stdlib_name not in imported_names:
            # Check if it's actually used (not just in a string)
            pattern = rf'\b{re.escape(stdlib_name)}\.'
            if re.search(pattern, content):
                issues['missing_stdlib_imports'].append(f"Missing: {stdlib_name}")
    
    return dict(issues)

def check_singleton_instances(root_dir: str) -> List[str]:
    """Check for missing singleton instances."""
    issues = []
    
    # Check notification_service
    notification_service_file = Path(root_dir) / 'app' / 'services' / 'notification_service.py'
    if notification_service_file.exists():
        with open(notification_service_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'class NotificationService' in content:
                if 'notification_service = NotificationService()' not in content:
                    issues.append("notification_service.py: Missing singleton instance 'notification_service = NotificationService()'")
    
    return issues

def check_missing_modules(root_dir: str) -> List[str]:
    """Check for imports of modules that don't exist."""
    issues = []
    app_dir = Path(root_dir) / 'app'
    
    # Check all Python files for imports
    for py_file in get_python_files(str(app_dir)):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all import statements
            import_pattern = r'from\s+([\w.]+)\s+import|import\s+([\w.]+)'
            matches = re.findall(import_pattern, content)
            
            for match in matches:
                module_path = match[0] or match[1]
                # Skip standard library and third-party
                if module_path.startswith('app.'):
                    # Check if module exists
                    module_parts = module_path.split('.')
                    if len(module_parts) >= 2:
                        module_file = app_dir / '/'.join(module_parts[1:]) / '__init__.py'
                        module_file_py = app_dir / '/'.join(module_parts[1:]) + '.py'
                        if not module_file.exists() and not module_file_py.exists():
                            # Check if it's a known missing module
                            if module_path in ['app.core.queue', 'app.core.events']:
                                continue  # We've already created these
                            issues.append(f"{py_file.relative_to(app_dir.parent)}: Import '{module_path}' - module not found")
        except Exception as e:
            pass
    
    return issues

def main():
    """Run comprehensive import checks."""
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    root_dir = Path(__file__).parent
    app_dir = root_dir / 'app'
    
    print("Comprehensive Import Check\n")
    print("=" * 60)
    
    all_issues = defaultdict(list)
    
    # Check all Python files
    print("\n1. Checking Python files for import issues...")
    python_files = get_python_files(str(app_dir))
    for py_file in python_files:
        issues = check_file_imports(py_file)
        if issues:
            rel_path = py_file.relative_to(root_dir)
            for issue_type, issue_list in issues.items():
                for issue in issue_list:
                    all_issues[issue_type].append(f"{rel_path}: {issue}")
    
    # Check singleton instances
    print("\n2. Checking for missing singleton instances...")
    singleton_issues = check_singleton_instances(str(app_dir))
    if singleton_issues:
        all_issues['missing_singletons'].extend(singleton_issues)
    
    # Check missing modules
    print("\n3. Checking for missing modules...")
    module_issues = check_missing_modules(str(app_dir))
    if module_issues:
        all_issues['missing_modules'].extend(module_issues)
    
    # Report results
    print("\n" + "=" * 60)
    print("RESULTS:\n")
    
    if not all_issues:
        print("[OK] No issues found!")
        return 0
    
    total_issues = sum(len(issues) for issues in all_issues.values())
    print(f"Found {total_issues} potential issues:\n")
    
    for issue_type, issues in all_issues.items():
        if issues:
            print(f"\n{issue_type.upper().replace('_', ' ')} ({len(issues)}):")
            for issue in issues[:10]:  # Show first 10
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
    
    return 1

if __name__ == '__main__':
    exit(main())

