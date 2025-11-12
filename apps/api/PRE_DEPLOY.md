# Pre-Deployment Check Guide

## Quick Check Before Deploying

**Run this before every deployment to catch errors early:**

```bash
cd apps/api
python pre_deploy_check.py
```

This will check for:
- ✅ Syntax errors
- ✅ Missing type imports (Optional, List, Dict, Tuple, etc.)
- ✅ Import structure issues

## What It Does

The pre-deploy check runs **without requiring dependencies** (like weasyprint, jwt, etc.) so it's fast and catches code errors that would cause deployment failures.

## Expected Output

If everything is OK:
```
[SUCCESS] All checks passed!
[READY] Safe to deploy!
```

If there are issues:
```
[FAIL] Some checks failed. Fix issues before deploying.
```

## Individual Checks

You can also run checks individually:

```bash
# Check syntax and imports
python check_syntax_imports.py

# Check router imports specifically
python check_all_imports.py

# Check for missing type imports
python check_missing_imports.py
```

## Why This Helps

- **Catches errors in seconds** instead of waiting 10+ minutes for Render deployment
- **No dependencies needed** - works even if packages aren't installed locally
- **Catches the same errors** that cause Render deployment failures

## Workflow

1. Make code changes
2. Run `python pre_deploy_check.py`
3. Fix any issues found
4. Commit and push (Render will auto-deploy)
5. ✅ Deployment should succeed!

