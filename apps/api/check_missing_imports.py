#!/usr/bin/env python3
"""
Script to check for missing type imports in router files.
Scans all router files for type hints (Optional, List, Dict, Any, Tuple) 
and checks if they're imported from typing.
"""

import os
import re
from pathlib import Path
from typing import Set, Dict, List as ListType

# Type hints to check for
TYPE_HINTS = ['Optional', 'List', 'Dict', 'Any', 'Tuple', 'Union', 'Callable']

def find_router_files(base_path: Path) -> ListType[Path]:
    """Find all Python router files."""
    router_files = []
    routers_dir = base_path / 'app' / 'routers'
    
    if not routers_dir.exists():
        return router_files
    
    for py_file in routers_dir.rglob('*.py'):
        if py_file.name != '__init__.py':
            router_files.append(py_file)
    
    return router_files

def check_file(file_path: Path) -> Dict[str, any]:
    """Check a single file for missing type imports."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all type hints used in the file
    used_types: Set[str] = set()
    
    # Pattern to match type hints: Optional[...], List[...], Dict[...], etc.
    for type_hint in TYPE_HINTS:
        # Match patterns like: Optional[...], List[...], Dict[str, Any], etc.
        pattern = rf'\b{type_hint}\s*\['
        if re.search(pattern, content):
            used_types.add(type_hint)
        
        # Also check for standalone usage: Optional, List (without brackets)
        # But only if it's used in a type annotation context
        standalone_pattern = rf':\s*{type_hint}\s*[=,\n\)]|->\s*{type_hint}\s*[:\n\)]'
        if re.search(standalone_pattern, content):
            used_types.add(type_hint)
    
    # Check what's imported from typing
    typing_imports: Set[str] = set()
    
    # Match: from typing import Optional, List, Dict
    typing_import_match = re.search(r'from typing import ([^\n]+)', content)
    if typing_import_match:
        imports_str = typing_import_match.group(1)
        # Split by comma and clean up
        imports = [imp.strip() for imp in imports_str.split(',')]
        typing_imports.update(imports)
    
    # Match: from typing import (Optional, List, Dict)
    typing_import_multiline_match = re.search(
        r'from typing import\s*\(([^)]+)\)', 
        content, 
        re.MULTILINE | re.DOTALL
    )
    if typing_import_multiline_match:
        imports_str = typing_import_multiline_match.group(1)
        imports = [imp.strip() for imp in imports_str.split(',')]
        typing_imports.update(imports)
    
    # Find missing imports
    missing = used_types - typing_imports
    
    return {
        'file': str(file_path),
        'used_types': used_types,
        'imported_types': typing_imports,
        'missing': missing
    }

def fix_file(file_path: Path, missing_types: Set[str]) -> bool:
    """Fix missing imports in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the typing import line
    typing_import_line = None
    typing_import_index = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('from typing import'):
            typing_import_line = line
            typing_import_index = i
            break
    
    if typing_import_line is None:
        # No typing import exists, need to add one
        # Find where to insert (after other imports, before fastapi/sqlalchemy imports)
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('from fastapi') or line.strip().startswith('from sqlalchemy'):
                insert_index = i
                break
            if i > 0 and not line.strip().startswith('#') and not line.strip().startswith('import ') and not line.strip().startswith('from '):
                insert_index = i
                break
        
        # Create import line
        sorted_types = sorted(missing_types)
        import_line = f"from typing import {', '.join(sorted_types)}\n"
        lines.insert(insert_index, import_line)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    
    # Update existing typing import
    # Check if it's single line or multiline
    if '(' in typing_import_line:
        # Multiline import - need to handle carefully
        # For now, convert to single line
        current_imports = re.search(r'from typing import\s*\(([^)]+)\)', typing_import_line, re.DOTALL)
        if current_imports:
            existing = [imp.strip() for imp in current_imports.group(1).split(',')]
            all_imports = sorted(set(existing) | missing_types)
            lines[typing_import_index] = f"from typing import {', '.join(all_imports)}\n"
        else:
            # Single line with parentheses but no newline
            existing_match = re.search(r'from typing import\s*\(([^)]+)\)', typing_import_line)
            if existing_match:
                existing = [imp.strip() for imp in existing_match.group(1).split(',')]
                all_imports = sorted(set(existing) | missing_types)
                lines[typing_import_index] = f"from typing import {', '.join(all_imports)}\n"
    else:
        # Single line import
        existing_match = re.search(r'from typing import ([^\n]+)', typing_import_line)
        if existing_match:
            existing = [imp.strip() for imp in existing_match.group(1).split(',')]
            all_imports = sorted(set(existing) | missing_types)
            lines[typing_import_index] = f"from typing import {', '.join(all_imports)}\n"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    return True

def main():
    """Main function."""
    base_path = Path(__file__).parent
    router_files = find_router_files(base_path)
    
    print(f"Scanning {len(router_files)} router files...\n")
    
    issues = []
    for router_file in router_files:
        result = check_file(router_file)
        if result['missing']:
            issues.append(result)
            rel_path = os.path.relpath(result['file'], base_path)
            print(f"[X] {rel_path}")
            print(f"   Missing: {', '.join(sorted(result['missing']))}")
            print(f"   Used: {', '.join(sorted(result['used_types']))}")
            print(f"   Imported: {', '.join(sorted(result['imported_types']))}")
            print()
    
    if not issues:
        print("[OK] No missing type imports found!")
        return 0
    
    print(f"\nFound {len(issues)} files with missing imports\n")
    
    # Auto-fix without asking (for automation)
    print("Auto-fixing files...\n")
    for issue in issues:
        file_path = Path(issue['file'])
        if fix_file(file_path, issue['missing']):
            rel_path = os.path.relpath(issue['file'], base_path)
            print(f"[FIXED] {rel_path}")
    print("\nAll fixes applied!")
    return 0

if __name__ == '__main__':
    exit(main())

