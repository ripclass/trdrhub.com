#!/usr/bin/env python3
"""
Comprehensive codebase checker to find ALL potential issues before deployment.
Scans for:
- Missing type imports (Optional, List, Dict, Tuple, Any, Union, Callable)
- Missing function/class imports
- Syntax errors
- Common import issues
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Common type hints that need to be imported
TYPE_HINTS = {
    'Optional', 'List', 'Dict', 'Tuple', 'Any', 'Union', 'Callable',
    'Set', 'Sequence', 'Iterable', 'Iterator', 'Generator', 'AsyncGenerator',
    'Awaitable', 'Coroutine', 'Type', 'TypeVar', 'Generic', 'Protocol',
    'Literal', 'TypedDict', 'Final', 'ClassVar', 'NoReturn', 'Never'
}

# Common standard library imports that might be missing
STD_IMPORTS = {
    'logging', 'uuid', 'datetime', 'time', 'json', 'os', 'sys',
    'asyncio', 'typing', 'collections', 'itertools', 'functools'
}

# Common FastAPI imports
FASTAPI_IMPORTS = {
    'Depends', 'Query', 'Form', 'File', 'UploadFile', 'Body', 'Path',
    'Header', 'Cookie', 'Request', 'Response', 'HTTPException', 'status',
    'APIRouter', 'BackgroundTasks', 'Security'
}

# Common SQLAlchemy imports
SQLALCHEMY_IMPORTS = {
    'Session', 'select', 'func', 'and_', 'or_', 'not_', 'asc', 'desc',
    'cast', 'case', 'JSONB', 'ARRAY', 'String', 'Integer', 'Boolean',
    'DateTime', 'Text', 'ForeignKey', 'relationship', 'Column'
}

ISSUES: List[Dict] = []


def check_file(filepath: Path) -> None:
    """Check a single Python file for issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        ISSUES.append({
            'file': str(filepath),
            'type': 'read_error',
            'message': f'Could not read file: {e}'
        })
        return

    # Check syntax
    try:
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        ISSUES.append({
            'file': str(filepath),
            'type': 'syntax_error',
            'line': e.lineno,
            'message': f'Syntax error: {e.msg}'
        })
        return

    # Extract imports
    imports: Set[str] = set()
    from_imports: Dict[str, Set[str]] = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if module:
                imports.add(module.split('.')[0])
            for alias in node.names:
                name = alias.asname or alias.name
                if module:
                    if module not in from_imports:
                        from_imports[module] = set()
                    from_imports[module].add(name)
                else:
                    imports.add(name)

    # Check for type hints in function signatures and annotations
    used_types: Set[str] = set()
    
    def visit_node(node):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Check return type annotation
            if node.returns:
                extract_type_names(node.returns, used_types)
            # Check parameter annotations
            for arg in node.args.args:
                if arg.annotation:
                    extract_type_names(arg.annotation, used_types)
        elif isinstance(node, ast.AnnAssign):
            if node.annotation:
                extract_type_names(node.annotation, used_types)
        elif isinstance(node, ast.Name):
            if node.id in TYPE_HINTS:
                used_types.add(node.id)
        
        for child in ast.iter_child_nodes(node):
            visit_node(child)
    
    visit_node(tree)
    
    # Check if used types are imported
    has_typing_import = 'typing' in imports or any('typing' in mod for mod in from_imports)
    typing_imports = set()
    if 'typing' in from_imports:
        typing_imports = from_imports['typing']
    elif has_typing_import:
        # Check for 'from typing import ...' patterns
        typing_pattern = re.compile(r'from\s+typing\s+import\s+([^#\n]+)')
        matches = typing_pattern.findall(content)
        for match in matches:
            for item in match.split(','):
                typing_imports.add(item.strip().split(' as ')[0])
    
    # Check for missing type imports
    for type_name in used_types:
        if type_name in TYPE_HINTS:
            if type_name not in typing_imports and not has_typing_import:
                ISSUES.append({
                    'file': str(filepath),
                    'type': 'missing_type_import',
                    'message': f'Missing import: {type_name} from typing'
                })
    
    # Check for common missing imports using regex (faster than AST for this)
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # Check for logging usage without import
        if re.search(r'\blogging\.', line) and 'logging' not in imports:
            ISSUES.append({
                'file': str(filepath),
                'type': 'missing_import',
                'line': i,
                'message': 'Missing import: logging'
            })
        
        # Check for UUID usage without import
        if re.search(r'\bUUID\b', line) and 'uuid' not in imports and 'UUID' not in typing_imports:
            ISSUES.append({
                'file': str(filepath),
                'type': 'missing_import',
                'line': i,
                'message': 'Missing import: UUID from uuid'
            })
        
        # Check for FastAPI imports
        for fastapi_item in FASTAPI_IMPORTS:
            if re.search(rf'\b{fastapi_item}\b', line) and 'fastapi' not in imports:
                ISSUES.append({
                    'file': str(filepath),
                    'type': 'missing_import',
                    'line': i,
                    'message': f'Missing import: {fastapi_item} from fastapi'
                })
        
        # Check for SQLAlchemy imports
        for sa_item in SQLALCHEMY_IMPORTS:
            if re.search(rf'\b{sa_item}\b', line) and 'sqlalchemy' not in imports:
                ISSUES.append({
                    'file': str(filepath),
                    'type': 'missing_import',
                    'line': i,
                    'message': f'Missing import: {sa_item} from sqlalchemy'
                })


def extract_type_names(node: ast.AST, types: Set[str]) -> None:
    """Extract type names from an AST annotation node."""
    if isinstance(node, ast.Name):
        types.add(node.id)
    elif isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name):
            types.add(node.value.id)
        if node.slice:
            if isinstance(node.slice, ast.Tuple):
                for elt in node.slice.elts:
                    extract_type_names(elt, types)
            else:
                extract_type_names(node.slice, types)
    elif isinstance(node, ast.Attribute):
        # Handle things like List[str], Dict[str, int]
        if isinstance(node.value, ast.Name):
            types.add(node.value.id)
    elif isinstance(node, ast.BinOp):
        # Handle Union types
        extract_type_names(node.left, types)
        extract_type_names(node.right, types)


def main():
    """Main entry point."""
    api_dir = Path(__file__).parent / 'app'
    
    if not api_dir.exists():
        print(f"Error: {api_dir} does not exist")
        sys.exit(1)
    
    print("=" * 70)
    print("COMPREHENSIVE CODEBASE CHECK")
    print("=" * 70)
    print()
    
    # Find all Python files
    python_files = list(api_dir.rglob('*.py'))
    print(f"Scanning {len(python_files)} Python files...")
    print()
    
    for filepath in python_files:
        # Skip test files and __pycache__
        if '__pycache__' in str(filepath) or 'test' in str(filepath).lower():
            continue
        check_file(filepath)
    
    # Group issues by type
    issues_by_type: Dict[str, List[Dict]] = {}
    for issue in ISSUES:
        issue_type = issue['type']
        if issue_type not in issues_by_type:
            issues_by_type[issue_type] = []
        issues_by_type[issue_type].append(issue)
    
    # Print results
    if not ISSUES:
        print("✅ No issues found!")
        print()
        print("Codebase is clean and ready to deploy!")
        sys.exit(0)
    
    print(f"Found {len(ISSUES)} issues:")
    print()
    
    for issue_type, type_issues in sorted(issues_by_type.items()):
        print(f"[{issue_type.upper()}] {len(type_issues)} issues")
        for issue in type_issues[:10]:  # Show first 10 of each type
            file_rel = Path(issue['file']).relative_to(Path(__file__).parent)
            if 'line' in issue:
                print(f"  {file_rel}:{issue['line']} - {issue['message']}")
            else:
                print(f"  {file_rel} - {issue['message']}")
        if len(type_issues) > 10:
            print(f"  ... and {len(type_issues) - 10} more")
        print()
    
    print("=" * 70)
    print(f"SUMMARY: {len(ISSUES)} issues found")
    print("=" * 70)
    
    sys.exit(1)


if __name__ == '__main__':
    main()

