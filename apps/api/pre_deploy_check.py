#!/usr/bin/env python3
"""
Pre-deployment check script - Run this before deploying to catch errors early.
This checks for common issues that cause deployment failures.
"""

import sys
import subprocess
from pathlib import Path

def run_check(name: str, script: str, description: str) -> tuple[bool, str]:
    """Run a check script and return success status and output."""
    print(f"\n[{name}] {description}")
    print("-" * 70)
    
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=30
        )
        
        if result.returncode == 0:
            print(result.stdout)
            return True, result.stdout
        else:
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Check timed out"
    except Exception as e:
        return False, f"Error running check: {e}"

def main():
    """Run all pre-deployment checks."""
    print("=" * 70)
    print("PRE-DEPLOYMENT CHECK")
    print("=" * 70)
    print("\nRunning checks to catch errors before deployment...")
    
    checks = [
        ("SYNTAX", "check_syntax_imports.py", "Checking syntax and import structure"),
        ("IMPORTS", "check_all_imports.py", "Checking router imports"),
    ]
    
    results = []
    for name, script, desc in checks:
        success, output = run_check(name, script, desc)
        results.append((name, success, output))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, success, _ in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n[SUCCESS] All checks passed!")
        print("[READY] Safe to deploy!")
        return 0
    else:
        print("\n[FAIL] Some checks failed. Fix issues before deploying.")
        print("\nTo see details, run each check individually:")
        for name, _, _ in results:
            print(f"  python {checks[[c[0] for c in checks].index(name)][1]}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

