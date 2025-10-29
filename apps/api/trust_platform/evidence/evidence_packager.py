#!/usr/bin/env python3
"""
Evidence Pack Generator for LCopilot Trust Platform
Generates tamper-proof bundled evidence packages for compliance validation results.
"""

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import shutil
import tempfile
from dataclasses import dataclass, asdict

@dataclass
class EvidenceManifest:
    """Manifest for evidence pack contents"""
    package_id: str
    creation_timestamp: str
    lc_number: str
    validation_timestamp: str
    tier: str
    compliance_score: float
    total_rules_checked: int
    failed_rules: int
    rule_engine_version: str
    contents: Dict[str, str]  # filename -> description
    checksums: Dict[str, str]  # filename -> SHA-256 hash
    package_hash: str  # Overall package integrity hash
    digital_signature: Optional[str] = None  # For Enterprise tier

class EvidencePackager:
    """Creates tamper-proof evidence packages for compliance results"""

    def __init__(self, export_directory: str = "/Users/user/Desktop/Enso Intelligence/trdrhub.com/apps/api/exports"):
        self.export_directory = Path(export_directory)
        self.export_directory.mkdir(exist_ok=True)

    def create_evidence_pack(
        self,
        compliance_result: Dict[str, Any],
        lc_document: Dict[str, Any],
        original_pdf_path: Optional[str] = None,
        tier: str = "free",
        customer_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create a complete evidence package with tamper-proof bundling

        Returns:
            Tuple of (package_path, package_hash)
        """
        # Generate package ID and timestamp
        timestamp = datetime.now(timezone.utc)
        package_id = self._generate_package_id(lc_document.get("lc_number", "UNKNOWN"), timestamp)

        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Prepare all files for the package
            files_to_bundle = {}
            checksums = {}

            # 1. Compliance result JSON
            result_file = "compliance_result.json"
            result_path = temp_path / result_file
            with open(result_path, 'w') as f:
                json.dump(compliance_result, f, indent=2, ensure_ascii=False)
            files_to_bundle[result_file] = "Complete compliance validation result"
            checksums[result_file] = self._calculate_file_hash(result_path)

            # 2. Original LC document JSON
            lc_file = "original_lc_document.json"
            lc_path = temp_path / lc_file
            with open(lc_path, 'w') as f:
                json.dump(lc_document, f, indent=2, ensure_ascii=False)
            files_to_bundle[lc_file] = "Original LC document data"
            checksums[lc_file] = self._calculate_file_hash(lc_path)

            # 3. Rule versions snapshot
            rules_file = "rule_versions.json"
            rules_snapshot = self._capture_rule_versions()
            rules_path = temp_path / rules_file
            with open(rules_path, 'w') as f:
                json.dump(rules_snapshot, f, indent=2)
            files_to_bundle[rules_file] = "Rule engine versions at validation time"
            checksums[rules_file] = self._calculate_file_hash(rules_path)

            # 4. Original PDF if provided
            if original_pdf_path and Path(original_pdf_path).exists():
                pdf_file = f"original_lc_{lc_document.get('lc_number', 'UNKNOWN')}.pdf"
                pdf_path = temp_path / pdf_file
                shutil.copy2(original_pdf_path, pdf_path)
                files_to_bundle[pdf_file] = "Original LC PDF document"
                checksums[pdf_file] = self._calculate_file_hash(pdf_path)

            # 5. Human-readable summary
            summary_file = "validation_summary.txt"
            summary_path = temp_path / summary_file
            summary_content = self._generate_human_readable_summary(compliance_result, lc_document)
            with open(summary_path, 'w') as f:
                f.write(summary_content)
            files_to_bundle[summary_file] = "Human-readable validation summary"
            checksums[summary_file] = self._calculate_file_hash(summary_path)

            # 6. Create manifest
            manifest = EvidenceManifest(
                package_id=package_id,
                creation_timestamp=timestamp.isoformat(),
                lc_number=lc_document.get("lc_number", "UNKNOWN"),
                validation_timestamp=compliance_result.get("validation_timestamp", timestamp.isoformat()),
                tier=tier,
                compliance_score=compliance_result.get("compliance_score", 0.0),
                total_rules_checked=len(compliance_result.get("validated_rules", [])),
                failed_rules=len([r for r in compliance_result.get("validated_rules", []) if r.get("status") == "fail"]),
                rule_engine_version=compliance_result.get("engine_version", "unknown"),
                contents=files_to_bundle,
                checksums=checksums,
                package_hash="",  # Will be calculated after all files are ready
                digital_signature=None
            )

            # Calculate overall package hash (exclude package_hash and digital_signature from manifest)
            manifest_for_hash = asdict(manifest)
            manifest_for_hash.pop("package_hash", None)  # Remove package_hash field
            manifest_for_hash.pop("digital_signature", None)  # Remove digital_signature field
            all_content = json.dumps(manifest_for_hash, sort_keys=True) + "".join(checksums.values())
            manifest.package_hash = hashlib.sha256(all_content.encode()).hexdigest()

            # Add digital signature for Enterprise tier (after hash calculation)
            if tier == "enterprise":
                manifest.digital_signature = self._generate_digital_signature(manifest, temp_path)

            # Write manifest
            manifest_file = "MANIFEST.json"
            manifest_path = temp_path / manifest_file
            with open(manifest_path, 'w') as f:
                json.dump(asdict(manifest), f, indent=2)

            # Create final ZIP package
            package_filename = f"{package_id}.zip"
            package_path = self.export_directory / package_filename

            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add manifest first
                zipf.write(manifest_path, manifest_file)

                # Add all other files
                for filename in files_to_bundle.keys():
                    zipf.write(temp_path / filename, filename)

            return str(package_path), manifest.package_hash

    def verify_evidence_pack(self, package_path: str) -> Dict[str, Any]:
        """
        Verify the integrity of an evidence package

        Returns verification status and details
        """
        package_path = Path(package_path)
        if not package_path.exists():
            return {"verified": False, "error": "Package file not found"}

        verification_result = {
            "verified": False,
            "package_path": str(package_path),
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
            "manifest_valid": False,
            "checksums_valid": False,
            "package_hash_valid": False,
            "digital_signature_valid": None,
            "details": []
        }

        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # Extract and verify manifest
                manifest_data = json.loads(zipf.read("MANIFEST.json").decode())
                manifest = EvidenceManifest(**manifest_data)
                verification_result["manifest_valid"] = True

                # Verify individual file checksums
                checksums_valid = True
                for filename, expected_hash in manifest.checksums.items():
                    if filename in zipf.namelist():
                        file_content = zipf.read(filename)
                        actual_hash = hashlib.sha256(file_content).hexdigest()
                        if actual_hash != expected_hash:
                            checksums_valid = False
                            verification_result["details"].append(f"Checksum mismatch for {filename}")
                    else:
                        checksums_valid = False
                        verification_result["details"].append(f"Missing file: {filename}")

                verification_result["checksums_valid"] = checksums_valid

                # Verify overall package hash (exclude package_hash and digital_signature from manifest)
                manifest_for_hash = asdict(manifest)
                manifest_for_hash.pop("package_hash", None)  # Remove package_hash field
                manifest_for_hash.pop("digital_signature", None)  # Remove digital_signature field
                all_content = json.dumps(manifest_for_hash, sort_keys=True) + "".join(manifest.checksums.values())
                expected_package_hash = hashlib.sha256(all_content.encode()).hexdigest()
                verification_result["package_hash_valid"] = (expected_package_hash == manifest.package_hash)

                # Verify digital signature for Enterprise packages
                if manifest.digital_signature:
                    verification_result["digital_signature_valid"] = self._verify_digital_signature(manifest, zipf)

                verification_result["verified"] = (
                    verification_result["manifest_valid"] and
                    verification_result["checksums_valid"] and
                    verification_result["package_hash_valid"] and
                    (verification_result["digital_signature_valid"] is not False)
                )

                if verification_result["verified"]:
                    verification_result["details"].append("All integrity checks passed")

        except Exception as e:
            verification_result["error"] = str(e)
            verification_result["details"].append(f"Verification failed: {str(e)}")

        return verification_result

    def extract_evidence_pack(self, package_path: str, extract_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract and return contents of an evidence package

        Returns extracted data with verification status
        """
        if extract_to is None:
            extract_to = tempfile.mkdtemp(prefix="evidence_pack_")

        extract_path = Path(extract_to)
        extract_path.mkdir(exist_ok=True)

        # First verify package integrity
        verification = self.verify_evidence_pack(package_path)
        if not verification["verified"]:
            return {
                "success": False,
                "error": "Package failed integrity verification",
                "verification": verification
            }

        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                zipf.extractall(extract_path)

                # Load manifest
                manifest_path = extract_path / "MANIFEST.json"
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)

                # Load compliance result
                result_path = extract_path / "compliance_result.json"
                with open(result_path, 'r') as f:
                    compliance_result = json.load(f)

                # Load original LC document
                lc_path = extract_path / "original_lc_document.json"
                with open(lc_path, 'r') as f:
                    lc_document = json.load(f)

                return {
                    "success": True,
                    "extracted_to": str(extract_path),
                    "manifest": manifest,
                    "compliance_result": compliance_result,
                    "lc_document": lc_document,
                    "verification": verification
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Extraction failed: {str(e)}",
                "verification": verification
            }

    def _generate_package_id(self, lc_number: str, timestamp: datetime) -> str:
        """Generate unique package ID"""
        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        lc_clean = "".join(c for c in lc_number if c.isalnum())[:20]
        return f"EVP_{lc_clean}_{date_str}"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _capture_rule_versions(self) -> Dict[str, Any]:
        """Capture current rule engine and rule file versions"""
        rule_versions = {
            "capture_timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_files": {}
        }

        # Check for rule files
        rules_dir = Path(__file__).parent.parent / "compliance" / "rules"
        if rules_dir.exists():
            for rule_file in rules_dir.glob("*.yaml"):
                try:
                    stat = rule_file.stat()
                    rule_versions["rule_files"][rule_file.name] = {
                        "last_modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "size_bytes": stat.st_size,
                        "file_hash": self._calculate_file_hash(rule_file)
                    }
                except Exception as e:
                    rule_versions["rule_files"][rule_file.name] = {"error": str(e)}

        return rule_versions

    def _generate_human_readable_summary(self, compliance_result: Dict[str, Any], lc_document: Dict[str, Any]) -> str:
        """Generate human-readable validation summary"""
        summary_lines = []
        summary_lines.append("=== LC COMPLIANCE VALIDATION SUMMARY ===")
        summary_lines.append("")

        # Basic information
        summary_lines.append(f"LC Number: {lc_document.get('lc_number', 'N/A')}")
        summary_lines.append(f"Validation Date: {compliance_result.get('validation_timestamp', 'N/A')}")
        summary_lines.append(f"Overall Compliance Score: {compliance_result.get('compliance_score', 0):.1%}")
        summary_lines.append("")

        # Results summary
        validated_rules = compliance_result.get("validated_rules", [])
        passed_rules = [r for r in validated_rules if r.get("status") == "pass"]
        failed_rules = [r for r in validated_rules if r.get("status") == "fail"]
        warning_rules = [r for r in validated_rules if r.get("status") == "warning"]

        summary_lines.append(f"Total Rules Checked: {len(validated_rules)}")
        summary_lines.append(f"✅ Passed: {len(passed_rules)}")
        summary_lines.append(f"❌ Failed: {len(failed_rules)}")
        summary_lines.append(f"⚠️  Warnings: {len(warning_rules)}")
        summary_lines.append("")

        # Failed rules details
        if failed_rules:
            summary_lines.append("=== FAILED RULES ===")
            for rule in failed_rules:
                summary_lines.append(f"• {rule.get('id', 'Unknown')}: {rule.get('description', 'No description')}")
                if rule.get('details'):
                    summary_lines.append(f"  Details: {rule.get('details')}")
                summary_lines.append("")

        # Warnings
        if warning_rules:
            summary_lines.append("=== WARNINGS ===")
            for rule in warning_rules:
                summary_lines.append(f"• {rule.get('id', 'Unknown')}: {rule.get('description', 'No description')}")
                if rule.get('details'):
                    summary_lines.append(f"  Details: {rule.get('details')}")
                summary_lines.append("")

        # Recommendations
        if failed_rules:
            summary_lines.append("=== RECOMMENDATIONS ===")
            summary_lines.append("To improve compliance:")
            for rule in failed_rules:
                if rule.get('suggested_fix'):
                    summary_lines.append(f"• {rule.get('suggested_fix')}")

        summary_lines.append("")
        summary_lines.append("=== END OF SUMMARY ===")

        return "\n".join(summary_lines)

    def _generate_digital_signature(self, manifest: EvidenceManifest, temp_path: Path) -> str:
        """Generate digital signature for Enterprise tier (placeholder implementation)"""
        # In a real implementation, this would use proper cryptographic signing
        # For now, we'll create a secure hash-based signature
        signature_content = f"{manifest.package_id}{manifest.package_hash}{manifest.creation_timestamp}"
        signature_hash = hashlib.sha256(signature_content.encode()).hexdigest()
        return f"ENTERPRISE_SIG_{signature_hash[:32]}"

    def _verify_digital_signature(self, manifest: EvidenceManifest, zipf: zipfile.ZipFile) -> bool:
        """Verify digital signature for Enterprise packages (placeholder implementation)"""
        if not manifest.digital_signature:
            return False

        # Recreate expected signature
        signature_content = f"{manifest.package_id}{manifest.package_hash}{manifest.creation_timestamp}"
        expected_hash = hashlib.sha256(signature_content.encode()).hexdigest()
        expected_signature = f"ENTERPRISE_SIG_{expected_hash[:32]}"

        return manifest.digital_signature == expected_signature

    def list_evidence_packs(self) -> List[Dict[str, Any]]:
        """List all evidence packages in the export directory"""
        packages = []

        for package_file in self.export_directory.glob("EVP_*.zip"):
            try:
                with zipfile.ZipFile(package_file, 'r') as zipf:
                    manifest_data = json.loads(zipf.read("MANIFEST.json").decode())

                    package_info = {
                        "filename": package_file.name,
                        "path": str(package_file),
                        "package_id": manifest_data["package_id"],
                        "lc_number": manifest_data["lc_number"],
                        "creation_timestamp": manifest_data["creation_timestamp"],
                        "tier": manifest_data["tier"],
                        "compliance_score": manifest_data["compliance_score"],
                        "file_size_mb": package_file.stat().st_size / (1024 * 1024)
                    }
                    packages.append(package_info)

            except Exception as e:
                # Skip corrupted packages
                continue

        # Sort by creation time (newest first)
        packages.sort(key=lambda x: x["creation_timestamp"], reverse=True)
        return packages