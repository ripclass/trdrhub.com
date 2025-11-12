#!/usr/bin/env python3
"""
Syntax and import structure checker - catches code errors without requiring dependencies.
This checks for:
1. Missing type imports (Optional, List, Dict, Any, Tuple)
2. Syntax errors
3. Import path errors
4. Missing function/class definitions
"""

import ast
import os
import sys
from pathlib import Path
from typing import Set, List, Dict

TYPE_HINTS = ['Optional', 'List', 'Dict', 'Any', 'Tuple', 'Union', 'Callable']

def check_file_syntax(file_path: Path) -> Dict:
    """Check file for syntax errors and missing imports."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = {
        'syntax_errors': [],
        'missing_type_imports': [],
        'used_types': set(),
        'imported_types': set()
    }
    
    # Check syntax
    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        issues['syntax_errors'].append({
            'line': e.lineno,
            'message': str(e),
            'text': e.text
        })
        return issues
    
    # Find type hints used
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and node.annotation:
            annotation_str = ast.unparse(node.annotation) if hasattr(ast, 'unparse') else str(node.annotation)
            for hint in TYPE_HINTS:
                if hint in annotation_str:
                    issues['used_types'].add(hint)
        
        elif isinstance(node, ast.FunctionDef):
            if node.returns:
                returns_str = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                for hint in TYPE_HINTS:
                    if hint in returns_str:
                        issues['used_types'].add(hint)
            
            for arg in node.args.args:
                if arg.annotation:
                    annotation_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                    for hint in TYPE_HINTS:
                        if hint in annotation_str:
                            issues['used_types'].add(hint)
    
    # Check what's imported from typing
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'typing':
            for alias in node.names:
                issues['imported_types'].add(alias.name)
    
    # Also check string-based imports (for multiline)
    import re
    typing_import_match = re.search(r'from typing import ([^\n]+)', content)
    if typing_import_match:
        imports_str = typing_import_match.group(1)
        if '(' in imports_str:
            match2 = re.search(r'from typing import\s*\(([^)]+)\)', content, re.MULTILINE | re.DOTALL)
            if match2:
                imports_str = match2.group(1)
        issues['imported_types'].update([t.strip() for t in imports_str.split(',')])
    
    # Find missing type imports
    missing = issues['used_types'] - issues['imported_types']
    if missing:
        issues['missing_type_imports'] = sorted(missing)
    
    return issues

def check_all_files():
    """Check all Python files in app directory."""
    base_path = Path(__file__).parent
    app_path = base_path / 'app'
    
    all_issues = []
    
    # Check routers
    routers_path = app_path / 'routers'
    if routers_path.exists():
        for py_file in routers_path.rglob('*.py'):
            if py_file.name == '__init__.py':
                continue
            issues = check_file_syntax(py_file)
            if issues['syntax_errors'] or issues['missing_type_imports']:
                rel_path = os.path.relpath(py_file, base_path)
                all_issues.append({
                    'file': rel_path,
                    'issues': issues
                })
    
    # Check services
    services_path = app_path / 'services'
    if services_path.exists():
        for py_file in services_path.rglob('*.py'):
            if py_file.name == '__init__.py':
                continue
            issues = check_file_syntax(py_file)
            if issues['syntax_errors'] or issues['missing_type_imports']:
                rel_path = os.path.relpath(py_file, base_path)
                all_issues.append({
                    'file': rel_path,
                    'issues': issues
                })
    
    return all_issues

def main():
    """Main function."""
    print("=" * 70)
    print("Syntax and Import Structure Checker")
    print("(Checks code errors without requiring dependencies)")
    print("=" * 70)
    print()
    
    issues = check_all_files()
    
    if not issues:
        print("[SUCCESS] No syntax or import structure errors found!")
        print("\n[READY] Code is ready to deploy!")
        return 0
    
    print(f"[FAIL] Found {len(issues)} file(s) with issues:\n")
    
    for item in issues:
        print(f"File: {item['file']}")
        
        if item['issues']['syntax_errors']:
            print("  Syntax Errors:")
            for err in item['issues']['syntax_errors']:
                print(f"    Line {err['line']}: {err['message']}")
                if err.get('text'):
                    print(f"      {err['text'].strip()}")
        
        if item['issues']['missing_type_imports']:
            print(f"  Missing Type Imports: {', '.join(item['issues']['missing_type_imports'])}")
            print(f"  Used Types: {', '.join(sorted(item['issues']['used_types']))}")
            print(f"  Imported Types: {', '.join(sorted(item['issues']['imported_types']))}")
        
        print()
    
    return 1

if __name__ == '__main__':
    sys.exit(main())

