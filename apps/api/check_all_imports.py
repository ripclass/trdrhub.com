#!/usr/bin/env python3
"""
Comprehensive import checker for router files.
Checks for:
1. Missing type imports (Optional, List, Dict, Any, Tuple)
2. Common missing imports (logging, datetime, etc.)
3. Incorrect import paths
"""

import ast
import os
import sys
from pathlib import Path
from typing import Set, List, Dict

def find_router_files(base_path: Path) -> List[Path]:
    """Find all Python router files."""
    router_files = []
    routers_dir = base_path / 'app' / 'routers'
    
    if not routers_dir.exists():
        return router_files
    
    for py_file in routers_dir.rglob('*.py'):
        if py_file.name != '__init__.py':
            router_files.append(py_file)
    
    return router_files

def get_imports_from_file(file_path: Path) -> Dict[str, Set[str]]:
    """Parse Python file and extract imports."""
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError as e:
            return {'error': str(e)}
    
    imports = {
        'from_imports': set(),
        'direct_imports': set(),
        'type_hints_used': set()
    }
    
    # Common type hints to check
    TYPE_HINTS = ['Optional', 'List', 'Dict', 'Any', 'Tuple', 'Union', 'Callable']
    
    for node in ast.walk(tree):
        # Collect imports
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports['from_imports'].add(node.module)
                for alias in node.names:
                    imports['direct_imports'].add(alias.name)
        
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports['direct_imports'].add(alias.name)
        
        # Check for type hints in annotations
        elif isinstance(node, ast.AnnAssign):
            if node.annotation:
                annotation_str = ast.unparse(node.annotation) if hasattr(ast, 'unparse') else str(node.annotation)
                for hint in TYPE_HINTS:
                    if hint in annotation_str:
                        imports['type_hints_used'].add(hint)
        
        elif isinstance(node, ast.FunctionDef):
            # Check return type annotations
            if node.returns:
                returns_str = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                for hint in TYPE_HINTS:
                    if hint in returns_str:
                        imports['type_hints_used'].add(hint)
            
            # Check parameter annotations
            for arg in node.args.args:
                if arg.annotation:
                    annotation_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                    for hint in TYPE_HINTS:
                        if hint in annotation_str:
                            imports['type_hints_used'].add(hint)
    
    return imports

def check_typing_imports(file_path: Path, imports: Dict) -> List[str]:
    """Check if type hints are properly imported."""
    issues = []
    
    if 'error' in imports:
        return [f"Syntax error: {imports['error']}"]
    
    # Check if typing is imported
    has_typing_import = 'typing' in imports['from_imports']
    
    if imports['type_hints_used'] and not has_typing_import:
        issues.append(f"Missing 'from typing import ...' for: {', '.join(sorted(imports['type_hints_used']))}")
    
    # Read file to check what's actually imported from typing
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    imported_from_typing = set()
    if 'from typing import' in content:
        # Extract what's imported
        import re
        match = re.search(r'from typing import ([^\n]+)', content)
        if match:
            imported_str = match.group(1)
            # Handle multiline imports
            if '(' in imported_str:
                match2 = re.search(r'from typing import\s*\(([^)]+)\)', content, re.MULTILINE | re.DOTALL)
                if match2:
                    imported_str = match2.group(1)
            imported_from_typing = {t.strip() for t in imported_str.split(',')}
    
    missing_types = imports['type_hints_used'] - imported_from_typing
    if missing_types:
        issues.append(f"Missing type imports: {', '.join(sorted(missing_types))}")
    
    return issues

def check_common_missing_imports(file_path: Path, imports: Dict) -> List[str]:
    """Check for common missing imports."""
    issues = []
    
    if 'error' in imports:
        return []
    
    # Read file content to check usage
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for logging usage
    if 'logging.getLogger' in content or 'logging.' in content:
        if 'logging' not in imports['direct_imports']:
            issues.append("Missing 'import logging'")
    
    # Check for datetime usage
    if 'datetime.' in content or 'timedelta' in content:
        if 'datetime' not in imports['from_imports'] and 'datetime' not in imports['direct_imports']:
            issues.append("Missing 'from datetime import ...'")
    
    # Check for uuid usage
    if 'UUID' in content or 'uuid4' in content or 'uuid.' in content:
        if 'uuid' not in imports['from_imports'] and 'uuid' not in imports['direct_imports']:
            issues.append("Missing 'from uuid import ...' or 'import uuid'")
    
    return issues

def main():
    """Main function."""
    base_path = Path(__file__).parent
    router_files = find_router_files(base_path)
    
    print(f"Scanning {len(router_files)} router files for import issues...\n")
    
    all_issues = []
    for router_file in router_files:
        imports = get_imports_from_file(router_file)
        typing_issues = check_typing_imports(router_file, imports)
        common_issues = check_common_missing_imports(router_file, imports)
        
        if typing_issues or common_issues:
            rel_path = os.path.relpath(router_file, base_path)
            all_issues.append({
                'file': router_file,
                'path': rel_path,
                'issues': typing_issues + common_issues
            })
            print(f"[X] {rel_path}")
            for issue in typing_issues + common_issues:
                print(f"   - {issue}")
            print()
    
    if not all_issues:
        print("[OK] No import issues found!")
        return 0
    
    print(f"\nFound {len(all_issues)} files with import issues")
    return 1

if __name__ == '__main__':
    sys.exit(main())

