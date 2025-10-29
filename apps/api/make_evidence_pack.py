#!/usr/bin/env python3
"""
Standalone Evidence Pack Creation Script
Creates tamper-proof evidence packages for LC compliance validation results.

Usage:
    python make_evidence_pack.py --lc-file lc_document.json --result-file compliance_result.json [options]
    python make_evidence_pack.py --verify evidence_package.zip
    python make_evidence_pack.py --list
    python make_evidence_pack.py --extract evidence_package.zip [--to /path/to/extract]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add the trust platform to path
sys.path.append(str(Path(__file__).parent))

from trust_platform.evidence.evidence_packager import EvidencePackager

def create_evidence_pack(args):
    """Create a new evidence package"""
    print("🔒 Creating Evidence Package...")

    # Validate input files
    lc_file = Path(args.lc_file)
    result_file = Path(args.result_file)

    if not lc_file.exists():
        print(f"❌ LC document file not found: {lc_file}")
        return False

    if not result_file.exists():
        print(f"❌ Compliance result file not found: {result_file}")
        return False

    # Load input data
    try:
        with open(lc_file, 'r') as f:
            lc_document = json.load(f)
        print(f"✅ Loaded LC document: {lc_document.get('lc_number', 'Unknown')}")

        with open(result_file, 'r') as f:
            compliance_result = json.load(f)
        print(f"✅ Loaded compliance result (Score: {compliance_result.get('compliance_score', 0):.1%})")

    except Exception as e:
        print(f"❌ Error loading input files: {str(e)}")
        return False

    # Create evidence packager
    packager = EvidencePackager(export_directory=args.export_dir)

    try:
        # Create the evidence package
        package_path, package_hash = packager.create_evidence_pack(
            compliance_result=compliance_result,
            lc_document=lc_document,
            original_pdf_path=args.pdf_file,
            tier=args.tier,
            customer_id=args.customer_id
        )

        print(f"✅ Evidence package created successfully!")
        print(f"📦 Package: {package_path}")
        print(f"🔐 SHA-256 Hash: {package_hash}")

        if args.tier == "enterprise":
            print("🔏 Digital signature applied (Enterprise tier)")

        # Display package info
        package_size = Path(package_path).stat().st_size / (1024 * 1024)
        print(f"📊 Package size: {package_size:.2f} MB")

        return True

    except Exception as e:
        print(f"❌ Error creating evidence package: {str(e)}")
        return False

def verify_evidence_pack(args):
    """Verify an existing evidence package"""
    print(f"🔍 Verifying Evidence Package: {args.package}")

    if not Path(args.package).exists():
        print(f"❌ Package file not found: {args.package}")
        return False

    packager = EvidencePackager()

    try:
        verification_result = packager.verify_evidence_pack(args.package)

        print(f"📋 Package: {verification_result['package_path']}")
        print(f"⏰ Verified at: {verification_result['verification_timestamp']}")

        if verification_result["verified"]:
            print("✅ PACKAGE INTEGRITY VERIFIED")
            print("   ✅ Manifest valid")
            print("   ✅ Checksums valid")
            print("   ✅ Package hash valid")

            if verification_result["digital_signature_valid"] is not None:
                if verification_result["digital_signature_valid"]:
                    print("   ✅ Digital signature valid")
                else:
                    print("   ❌ Digital signature invalid")

        else:
            print("❌ PACKAGE INTEGRITY FAILED")
            if not verification_result["manifest_valid"]:
                print("   ❌ Manifest invalid")
            if not verification_result["checksums_valid"]:
                print("   ❌ Checksums invalid")
            if not verification_result["package_hash_valid"]:
                print("   ❌ Package hash invalid")

        # Show details
        if verification_result.get("details"):
            print("\n📝 Details:")
            for detail in verification_result["details"]:
                print(f"   • {detail}")

        return verification_result["verified"]

    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        return False

def list_evidence_packs(args):
    """List all evidence packages"""
    print("📋 Evidence Packages:")

    packager = EvidencePackager(export_directory=args.export_dir)

    try:
        packages = packager.list_evidence_packs()

        if not packages:
            print("   No evidence packages found.")
            return True

        print(f"   Found {len(packages)} package(s):")
        print()

        for package in packages:
            print(f"   📦 {package['filename']}")
            print(f"      LC: {package['lc_number']}")
            print(f"      Created: {package['creation_timestamp']}")
            print(f"      Tier: {package['tier']}")
            print(f"      Score: {package['compliance_score']:.1%}")
            print(f"      Size: {package['file_size_mb']:.2f} MB")
            print()

        return True

    except Exception as e:
        print(f"❌ Error listing packages: {str(e)}")
        return False

def extract_evidence_pack(args):
    """Extract an evidence package"""
    print(f"📦 Extracting Evidence Package: {args.package}")

    if not Path(args.package).exists():
        print(f"❌ Package file not found: {args.package}")
        return False

    packager = EvidencePackager()

    try:
        extract_result = packager.extract_evidence_pack(args.package, args.to)

        if extract_result["success"]:
            print(f"✅ Package extracted successfully!")
            print(f"📁 Extracted to: {extract_result['extracted_to']}")

            manifest = extract_result["manifest"]
            print(f"🏷️  Package ID: {manifest['package_id']}")
            print(f"📋 LC Number: {manifest['lc_number']}")
            print(f"⭐ Compliance Score: {manifest['compliance_score']:.1%}")
            print(f"📊 Rules: {manifest['total_rules_checked']} total, {manifest['failed_rules']} failed")

            if extract_result["verification"]["verified"]:
                print("🔒 Package integrity verified")
            else:
                print("⚠️  Package integrity verification failed")

        else:
            print(f"❌ Extraction failed: {extract_result['error']}")

        return extract_result["success"]

    except Exception as e:
        print(f"❌ Extraction error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Evidence Pack Management for LC Compliance Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create evidence package
    python make_evidence_pack.py --lc-file lc_document.json --result-file result.json --tier pro

    # Create with PDF and custom export directory
    python make_evidence_pack.py --lc-file lc.json --result-file result.json --pdf-file lc.pdf --export-dir /custom/path

    # Verify package integrity
    python make_evidence_pack.py --verify exports/EVP_LC001_20240115_142530.zip

    # List all packages
    python make_evidence_pack.py --list

    # Extract package
    python make_evidence_pack.py --extract package.zip --to /tmp/extracted
        """
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create evidence package")
    create_parser.add_argument("--lc-file", required=True, help="LC document JSON file")
    create_parser.add_argument("--result-file", required=True, help="Compliance result JSON file")
    create_parser.add_argument("--pdf-file", help="Original LC PDF file (optional)")
    create_parser.add_argument("--tier", choices=["free", "pro", "enterprise"], default="free", help="Service tier")
    create_parser.add_argument("--customer-id", help="Customer ID (optional)")
    create_parser.add_argument("--export-dir", default="exports", help="Export directory")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify evidence package")
    verify_parser.add_argument("package", help="Evidence package file (.zip)")

    # List command
    list_parser = subparsers.add_parser("list", help="List evidence packages")
    list_parser.add_argument("--export-dir", default="exports", help="Export directory")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract evidence package")
    extract_parser.add_argument("package", help="Evidence package file (.zip)")
    extract_parser.add_argument("--to", help="Extract to directory (optional)")

    # Legacy direct arguments (for backward compatibility)
    parser.add_argument("--lc-file", help="LC document JSON file")
    parser.add_argument("--result-file", help="Compliance result JSON file")
    parser.add_argument("--pdf-file", help="Original LC PDF file (optional)")
    parser.add_argument("--tier", choices=["free", "pro", "enterprise"], default="free", help="Service tier")
    parser.add_argument("--customer-id", help="Customer ID (optional)")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--verify", help="Verify evidence package")
    parser.add_argument("--list", action="store_true", help="List evidence packages")
    parser.add_argument("--extract", help="Extract evidence package")
    parser.add_argument("--to", help="Extract to directory (optional)")

    args = parser.parse_args()

    # Handle commands
    success = False

    if args.command == "create" or (args.lc_file and args.result_file):
        success = create_evidence_pack(args)
    elif args.command == "verify" or args.verify:
        args.package = args.package if hasattr(args, 'package') else args.verify
        success = verify_evidence_pack(args)
    elif args.command == "list" or args.list:
        success = list_evidence_packs(args)
    elif args.command == "extract" or args.extract:
        args.package = args.package if hasattr(args, 'package') else args.extract
        success = extract_evidence_pack(args)
    else:
        parser.print_help()
        print("\n❌ No valid command provided")
        return 1

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())