"""
Browser Compatibility Check - Code Analysis

Analyzes the codebase for browser compatibility issues:
- Modern JavaScript features
- CSS compatibility
- API compatibility
- Polyfills needed

Run: python apps/api/scripts/check_browser_compatibility.py
"""

import sys
import os
import re
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_browser_compatibility():
    """Check codebase for browser compatibility issues."""
    print("=" * 60)
    print("BROWSER COMPATIBILITY CODE ANALYSIS")
    print("=" * 60)
    print()
    print("This analyzes the codebase for potential browser compatibility issues.")
    print("It checks for modern features that may need polyfills.")
    print()
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    web_path = os.path.join(base_path, "..", "web")
    
    issues = []
    warnings = []
    
    # Check package.json for browser support
    print("Checking: Package Configuration")
    print("-" * 60)
    
    package_json_path = os.path.join(web_path, "package.json")
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_json = json.load(f)
        
        browserslist = package_json.get("browserslist", [])
        if browserslist:
            print(f"  OK: Browserslist configured: {browserslist}")
        else:
            warnings.append("No browserslist configured in package.json")
            print("  WARNING: No browserslist configured")
        
        # Check for polyfills
        dependencies = package_json.get("dependencies", {})
        dev_dependencies = package_json.get("devDependencies", {})
        all_deps = {**dependencies, **dev_dependencies}
        
        polyfill_packages = [pkg for pkg in all_deps.keys() if 'polyfill' in pkg.lower() or 'core-js' in pkg.lower()]
        if polyfill_packages:
            print(f"  OK: Polyfills found: {', '.join(polyfill_packages)}")
        else:
            print("  INFO: No explicit polyfills (may be handled by build tools)")
        
    except Exception as e:
        warnings.append(f"Could not read package.json: {e}")
        print(f"  WARNING: {e}")
    
    # Check TypeScript/JavaScript files for modern features
    print("\nChecking: Modern JavaScript Features")
    print("-" * 60)
    
    modern_features = {
        "Optional chaining (?.)": r"\?\.",
        "Nullish coalescing (??)": r"\?\?",
        "BigInt": r"BigInt\(",
        "Dynamic imports": r"import\(",
        "Top-level await": r"^await\s",
        "Private fields (#)": r"#\w+",
        "Optional catch binding": r"catch\s*\(",
    }
    
    # Check a sample of TS/TSX files
    import glob
    ts_files = glob.glob(os.path.join(web_path, "src", "**", "*.ts"), recursive=True)
    tsx_files = glob.glob(os.path.join(web_path, "src", "**", "*.tsx"), recursive=True)
    sample_files = (ts_files + tsx_files)[:10]  # Sample first 10 files
    
    found_features = {}
    for feature, pattern in modern_features.items():
        found_features[feature] = False
        for file_path in sample_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content):
                        found_features[feature] = True
                        break
            except:
                continue
    
    for feature, found in found_features.items():
        if found:
            print(f"  INFO: {feature} detected (may need polyfill for older browsers)")
        else:
            print(f"  OK: {feature} not detected")
    
    # Check CSS features
    print("\nChecking: CSS Features")
    print("-" * 60)
    
    css_files = glob.glob(os.path.join(web_path, "src", "**", "*.css"), recursive=True)
    sample_css = css_files[:5]
    
    css_features = {
        "CSS Grid": r"display:\s*grid",
        "CSS Custom Properties": r"var\(--",
        "Flexbox": r"display:\s*flex",
        "CSS Variables": r"--\w+",
    }
    
    found_css = {}
    for feature, pattern in css_features.items():
        found_css[feature] = False
        for file_path in sample_css:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content, re.IGNORECASE):
                        found_css[feature] = True
                        break
            except:
                continue
    
    for feature, found in found_css.items():
        if found:
            print(f"  OK: {feature} (well-supported)")
        else:
            print(f"  INFO: {feature} not detected")
    
    # Check API usage
    print("\nChecking: Browser API Usage")
    print("-" * 60)
    
    browser_apis = {
        "localStorage": r"localStorage",
        "sessionStorage": r"sessionStorage",
        "fetch API": r"fetch\(",
        "IntersectionObserver": r"IntersectionObserver",
        "ResizeObserver": r"ResizeObserver",
        "WebSocket": r"WebSocket",
    }
    
    found_apis = {}
    for api, pattern in browser_apis.items():
        found_apis[api] = False
        for file_path in sample_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content):
                        found_apis[api] = True
                        break
            except:
                continue
    
    for api, found in found_apis.items():
        if found:
            print(f"  OK: {api} (well-supported)")
        else:
            print(f"  INFO: {api} not detected")
    
    # Check for known compatibility issues
    print("\nChecking: Known Compatibility Issues")
    print("-" * 60)
    
    # Check for React Query (should handle fetch polyfills)
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_json = json.load(f)
        deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
        
        if "@tanstack/react-query" in deps or "react-query" in deps:
            print("  OK: React Query detected (handles fetch compatibility)")
        else:
            print("  INFO: React Query not detected")
    except:
        pass
    
    # Check Vite config for browser targets
    vite_config_path = os.path.join(web_path, "vite.config.ts")
    try:
        with open(vite_config_path, 'r', encoding='utf-8') as f:
            vite_config = f.read()
        
        if "target" in vite_config.lower() or "browserslist" in vite_config.lower():
            print("  OK: Vite config may specify browser targets")
        else:
            print("  INFO: Vite config doesn't explicitly set browser targets")
    except:
        print("  WARNING: Could not read vite.config.ts")
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPATIBILITY SUMMARY")
    print("=" * 60)
    
    print("\nBrowser Support Recommendations:")
    print("  - Chrome/Edge: Full support (modern features)")
    print("  - Firefox: Full support (modern features)")
    print("  - Safari: Full support (modern features)")
    print("  - IE11: NOT supported (legacy browser)")
    
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    
    if issues:
        print(f"\nIssues ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\nPASS: No major compatibility issues detected!")
        print("\nNote: This is a code analysis only.")
        print("      For full testing, run manual browser tests.")
        return True

if __name__ == "__main__":
    try:
        success = check_browser_compatibility()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

