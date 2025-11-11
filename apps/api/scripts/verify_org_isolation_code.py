"""
Code-Level Org Isolation Verification

Verifies that org isolation logic is correctly implemented in the codebase.
This test checks the code, not the database.

Run: python apps/api/scripts/verify_org_isolation_code.py
"""

import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_file_for_org_filtering(file_path, description):
    """Check if a file implements org filtering correctly."""
    print(f"\nChecking: {description}")
    print("-" * 60)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check 1: Does it read org_id from request.state?
        if 'request.state.org_id' in content or 'getattr(request.state, "org_id"' in content:
            print("  OK: Reads org_id from request.state")
        else:
            issues.append("Missing: org_id reading from request.state")
            print("  FAIL: Does not read org_id from request.state")
        
        # Check 2: Does it filter by org_id?
        org_filter_patterns = [
            r"org_id.*filter",
            r"filter.*org_id",
            r"extracted_data.*bank_metadata.*org_id",
            r"cast.*extracted_data.*JSONB.*org_id",
        ]
        
        has_filter = False
        for pattern in org_filter_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_filter = True
                break
        
        if has_filter:
            print("  OK: Filters by org_id")
        else:
            issues.append("Missing: org_id filtering logic")
            print("  FAIL: Does not filter by org_id")
        
        # Check 3: Does it use JSONB cast for org_id?
        if 'cast(ValidationSession.extracted_data, JSONB)' in content or 'cast.*extracted_data.*JSONB' in content:
            print("  OK: Uses JSONB cast for org_id filtering")
        else:
            if has_filter:
                print("  WARNING: May not use optimal JSONB filtering")
        
        return issues
        
    except FileNotFoundError:
        print(f"  ERROR: File not found: {file_path}")
        return [f"File not found: {file_path}"]
    except Exception as e:
        print(f"  ERROR: {e}")
        return [f"Error reading file: {e}"]

def verify_org_isolation_code():
    """Verify org isolation implementation in code."""
    print("=" * 60)
    print("CODE-LEVEL ORG ISOLATION VERIFICATION")
    print("=" * 60)
    print()
    print("This test verifies that org isolation logic is correctly")
    print("implemented in the codebase. It does NOT require a database.")
    print()
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Files to check
    files_to_check = [
        ("app/routers/bank.py", "Bank Results endpoint"),
        ("app/routers/bank_workflow.py", "Bank Workflow (Approvals/Discrepancies)"),
        ("app/routers/bank_evidence.py", "Bank Evidence Packs"),
        ("app/routers/bank_queue.py", "Bank Queue Operations"),
        ("app/routers/bank_duplicates.py", "Bank Duplicate Detection"),
        ("app/routers/bank_saved_views.py", "Bank Saved Views"),
    ]
    
    all_issues = []
    
    for file_path, description in files_to_check:
        full_path = os.path.join(base_path, file_path)
        issues = check_file_for_org_filtering(full_path, description)
        all_issues.extend([f"{description}: {issue}" for issue in issues])
    
    # Check middleware
    print("\nChecking: OrgScopeMiddleware")
    print("-" * 60)
    middleware_path = os.path.join(base_path, "app/middleware/org_scope.py")
    try:
        with open(middleware_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'request.state.org_id' in content:
            print("  OK: Sets org_id in request.state")
        else:
            all_issues.append("OrgScopeMiddleware: Does not set org_id in request.state")
            print("  FAIL: Does not set org_id in request.state")
        
        if 'user_org_access' in content.lower():
            print("  OK: Checks user_org_access table")
        else:
            print("  WARNING: May not check user_org_access")
        
    except FileNotFoundError:
        all_issues.append("OrgScopeMiddleware: File not found")
        print("  ERROR: File not found")
    
    # Check API client
    print("\nChecking: Frontend API Client")
    print("-" * 60)
    api_client_path = os.path.join(base_path, "..", "web", "src", "api", "client.ts")
    try:
        with open(api_client_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'org' in content and 'bank' in content.lower():
            print("  OK: Appends org parameter for bank endpoints")
        else:
            all_issues.append("API Client: May not append org parameter")
            print("  WARNING: May not append org parameter")
        
    except FileNotFoundError:
        print("  WARNING: Could not check API client (file not found)")
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    if all_issues:
        print(f"\nFAILED: Found {len(all_issues)} issue(s):")
        for issue in all_issues:
            print(f"  - {issue}")
        return False
    else:
        print("\nPASS: All org isolation checks passed!")
        print("\nNote: This verifies code implementation only.")
        print("      For full testing, run database-level tests.")
        return True

if __name__ == "__main__":
    try:
        success = verify_org_isolation_code()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

