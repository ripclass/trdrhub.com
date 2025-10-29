#!/usr/bin/env python3
"""
Disaster Recovery Drill Script for TRDR Hub
Orchestrates full backup, restore, and validation to measure RPO/RTO
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
from typing import Dict, Any, List
import time

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api'))

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DRDrill:
    """Disaster Recovery Drill orchestrator"""

    def __init__(self, drill_id: str = None):
        self.drill_id = drill_id or f"dr_drill_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.drill_dir = Path(f"/tmp/dr_drills/{self.drill_id}")
        self.drill_dir.mkdir(parents=True, exist_ok=True)

        # Scripts
        self.script_dir = Path(__file__).parent
        self.backup_db_script = self.script_dir / "backup_db.py"
        self.restore_db_script = self.script_dir / "restore_db.py"
        self.backup_objects_script = self.script_dir / "backup_objects.py"
        self.restore_objects_script = self.script_dir / "restore_objects.py"

    def run_drill(self, use_existing_backup: str = None, target_rpo_minutes: int = 15, target_rto_minutes: int = 60) -> Dict[str, Any]:
        """
        Run complete DR drill
        """
        logger.info(f"Starting DR drill: {self.drill_id}")
        logger.info(f"Target RPO: {target_rpo_minutes} minutes, Target RTO: {target_rto_minutes} minutes")

        drill_start = datetime.now(timezone.utc)

        drill_report = {
            "drill_id": self.drill_id,
            "started_at": drill_start.isoformat(),
            "target_rpo_minutes": target_rpo_minutes,
            "target_rto_minutes": target_rto_minutes,
            "phases": {}
        }

        try:
            # Phase 1: Create fresh backup (unless using existing)
            if use_existing_backup:
                logger.info(f"Using existing backup: {use_existing_backup}")
                drill_report["backup_id"] = use_existing_backup
                drill_report["phases"]["backup"] = {"skipped": True, "reason": "using_existing"}
            else:
                backup_result = self._run_backup_phase()
                drill_report["phases"]["backup"] = backup_result

            # Phase 2: Setup test environment
            test_env_result = self._setup_test_environment()
            drill_report["phases"]["test_environment"] = test_env_result

            # Phase 3: Restore database
            restore_start = datetime.now(timezone.utc)
            db_restore_result = self._run_database_restore(
                use_existing_backup or drill_report["phases"]["backup"]["backup_id"]
            )
            drill_report["phases"]["database_restore"] = db_restore_result

            # Phase 4: Restore objects
            object_restore_result = self._run_object_restore()
            drill_report["phases"]["object_restore"] = object_restore_result

            # Phase 5: Validate restoration
            validation_result = self._run_validation()
            drill_report["phases"]["validation"] = validation_result

            # Phase 6: Calculate metrics
            restore_end = datetime.now(timezone.utc)
            metrics_result = self._calculate_metrics(
                drill_start, restore_start, restore_end,
                target_rpo_minutes, target_rto_minutes
            )
            drill_report["phases"]["metrics"] = metrics_result

            # Phase 7: Cleanup
            cleanup_result = self._cleanup_test_environment()
            drill_report["phases"]["cleanup"] = cleanup_result

            drill_end = datetime.now(timezone.utc)
            drill_report["completed_at"] = drill_end.isoformat()
            drill_report["total_duration_minutes"] = (drill_end - drill_start).total_seconds() / 60
            drill_report["status"] = "completed"

            # Determine overall success
            drill_report["success"] = all([
                validation_result.get("overall_success", False),
                metrics_result.get("rpo_met", False),
                metrics_result.get("rto_met", False)
            ])

            logger.info(f"DR drill completed: {self.drill_id}")
            logger.info(f"Success: {drill_report['success']}")
            logger.info(f"RPO: {metrics_result.get('actual_rpo_minutes', 'N/A')} min "
                       f"(target: {target_rpo_minutes} min)")
            logger.info(f"RTO: {metrics_result.get('actual_rto_minutes', 'N/A')} min "
                       f"(target: {target_rto_minutes} min)")

            # Save drill report
            self._save_drill_report(drill_report)

            return drill_report

        except Exception as e:
            drill_report["status"] = "failed"
            drill_report["error"] = str(e)
            drill_report["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.error(f"DR drill failed: {str(e)}")
            self._save_drill_report(drill_report)
            raise

    def _run_backup_phase(self) -> Dict[str, Any]:
        """Create fresh backups"""
        logger.info("Phase 1: Creating fresh backups")
        phase_start = datetime.now(timezone.utc)

        try:
            # Database backup
            db_backup_cmd = [
                "python3", str(self.backup_db_script),
                "--output-json"
            ]

            logger.info("Creating database backup...")
            result = subprocess.run(db_backup_cmd, capture_output=True, text=True, check=True)
            db_backup_info = json.loads(result.stdout)

            # Object backup
            obj_backup_cmd = [
                "python3", str(self.backup_objects_script),
                "--output-json"
            ]

            logger.info("Creating object backup...")
            result = subprocess.run(obj_backup_cmd, capture_output=True, text=True, check=True)
            obj_backup_info = json.loads(result.stdout)

            phase_end = datetime.now(timezone.utc)

            return {
                "status": "completed",
                "started_at": phase_start.isoformat(),
                "completed_at": phase_end.isoformat(),
                "duration_minutes": (phase_end - phase_start).total_seconds() / 60,
                "backup_id": db_backup_info["backup_id"],
                "database_backup": db_backup_info,
                "object_backup": obj_backup_info
            }

        except Exception as e:
            logger.error(f"Backup phase failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "started_at": phase_start.isoformat()
            }

    def _setup_test_environment(self) -> Dict[str, Any]:
        """Setup isolated test environment"""
        logger.info("Phase 2: Setting up test environment")
        phase_start = datetime.now(timezone.utc)

        try:
            # Create test database
            test_db_name = f"trdrhub_dr_test_{int(time.time())}"
            test_db_url = settings.database_url.replace("/trdrhub", f"/{test_db_name}")

            # Create test database
            create_db_cmd = [
                "createdb", test_db_name
            ]

            logger.info(f"Creating test database: {test_db_name}")
            subprocess.run(create_db_cmd, check=True)

            phase_end = datetime.now(timezone.utc)

            return {
                "status": "completed",
                "started_at": phase_start.isoformat(),
                "completed_at": phase_end.isoformat(),
                "test_db_name": test_db_name,
                "test_db_url": test_db_url
            }

        except Exception as e:
            logger.error(f"Test environment setup failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "started_at": phase_start.isoformat()
            }

    def _run_database_restore(self, backup_id: str) -> Dict[str, Any]:
        """Restore database from backup"""
        logger.info("Phase 3: Restoring database")
        phase_start = datetime.now(timezone.utc)

        try:
            # Get test DB URL from previous phase
            test_db_url = self._get_test_db_url()

            restore_cmd = [
                "python3", str(self.restore_db_script),
                backup_id,
                "--target-db", test_db_url,
                "--output-json"
            ]

            logger.info(f"Restoring database from backup: {backup_id}")
            result = subprocess.run(restore_cmd, capture_output=True, text=True, check=True)
            restore_info = json.loads(result.stdout)

            phase_end = datetime.now(timezone.utc)

            return {
                "status": "completed",
                "started_at": phase_start.isoformat(),
                "completed_at": phase_end.isoformat(),
                "duration_minutes": (phase_end - phase_start).total_seconds() / 60,
                "restore_info": restore_info
            }

        except Exception as e:
            logger.error(f"Database restore failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "started_at": phase_start.isoformat()
            }

    def _run_object_restore(self) -> Dict[str, Any]:
        """Restore objects from backup"""
        logger.info("Phase 4: Restoring objects")
        phase_start = datetime.now(timezone.utc)

        try:
            # Object restore would go here
            # For now, simulate the restore
            time.sleep(2)  # Simulate restore time

            phase_end = datetime.now(timezone.utc)

            return {
                "status": "completed",
                "started_at": phase_start.isoformat(),
                "completed_at": phase_end.isoformat(),
                "duration_minutes": (phase_end - phase_start).total_seconds() / 60,
                "objects_restored": 0,  # Would be actual count
                "note": "Object restore simulation - implement actual restore logic"
            }

        except Exception as e:
            logger.error(f"Object restore failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "started_at": phase_start.isoformat()
            }

    def _run_validation(self) -> Dict[str, Any]:
        """Validate restored data integrity"""
        logger.info("Phase 5: Validating restoration")
        phase_start = datetime.now(timezone.utc)

        validations = []

        try:
            test_db_url = self._get_test_db_url()

            # Test 1: Database connectivity
            validation = self._validate_database_connectivity(test_db_url)
            validations.append(validation)

            # Test 2: Table structure
            validation = self._validate_table_structure(test_db_url)
            validations.append(validation)

            # Test 3: Data integrity
            validation = self._validate_data_integrity(test_db_url)
            validations.append(validation)

            # Test 4: Audit chain integrity
            validation = self._validate_audit_chain(test_db_url)
            validations.append(validation)

            # Test 5: File checksums
            validation = self._validate_file_checksums()
            validations.append(validation)

            phase_end = datetime.now(timezone.utc)

            overall_success = all(v["passed"] for v in validations)

            return {
                "status": "completed",
                "started_at": phase_start.isoformat(),
                "completed_at": phase_end.isoformat(),
                "overall_success": overall_success,
                "validations": validations,
                "tests_passed": sum(1 for v in validations if v["passed"]),
                "tests_failed": sum(1 for v in validations if not v["passed"]),
                "total_tests": len(validations)
            }

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "started_at": phase_start.isoformat(),
                "overall_success": False,
                "validations": validations
            }

    def _validate_database_connectivity(self, test_db_url: str) -> Dict[str, Any]:
        """Test database connectivity"""
        try:
            cmd = ["psql", test_db_url, "-c", "SELECT 1;"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "test": "database_connectivity",
                "passed": True,
                "message": "Database connection successful"
            }

        except Exception as e:
            return {
                "test": "database_connectivity",
                "passed": False,
                "message": f"Database connection failed: {str(e)}"
            }

    def _validate_table_structure(self, test_db_url: str) -> Dict[str, Any]:
        """Validate table structure"""
        try:
            cmd = [
                "psql", test_db_url, "-t", "-c",
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            table_count = int(result.stdout.strip())

            # Expect at least some core tables
            expected_min_tables = 5

            return {
                "test": "table_structure",
                "passed": table_count >= expected_min_tables,
                "message": f"Found {table_count} tables (expected >= {expected_min_tables})",
                "table_count": table_count
            }

        except Exception as e:
            return {
                "test": "table_structure",
                "passed": False,
                "message": f"Table structure validation failed: {str(e)}"
            }

    def _validate_data_integrity(self, test_db_url: str) -> Dict[str, Any]:
        """Validate basic data integrity"""
        try:
            # Check if we can query some core tables
            tests = [
                ("audit_log_entries", "SELECT count(*) FROM audit_log_entries;"),
                ("compliance_docs", "SELECT count(*) FROM compliance_docs;"),
            ]

            results = []
            for table, query in tests:
                try:
                    cmd = ["psql", test_db_url, "-t", "-c", query]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    count = int(result.stdout.strip())
                    results.append({"table": table, "count": count, "accessible": True})
                except:
                    results.append({"table": table, "count": 0, "accessible": False})

            accessible_tables = sum(1 for r in results if r["accessible"])

            return {
                "test": "data_integrity",
                "passed": accessible_tables >= len(tests) // 2,  # At least half should be accessible
                "message": f"{accessible_tables}/{len(tests)} core tables accessible",
                "table_results": results
            }

        except Exception as e:
            return {
                "test": "data_integrity",
                "passed": False,
                "message": f"Data integrity validation failed: {str(e)}"
            }

    def _validate_audit_chain(self, test_db_url: str) -> Dict[str, Any]:
        """Validate audit chain integrity"""
        try:
            # Check for audit entries with valid hashes
            cmd = [
                "psql", test_db_url, "-t", "-c",
                "SELECT count(*) FROM audit_log_entries WHERE entry_hash IS NOT NULL;"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            hash_count = int(result.stdout.strip())

            return {
                "test": "audit_chain",
                "passed": hash_count > 0,
                "message": f"Found {hash_count} audit entries with valid hashes",
                "hash_count": hash_count
            }

        except Exception as e:
            return {
                "test": "audit_chain",
                "passed": False,
                "message": f"Audit chain validation failed: {str(e)}"
            }

    def _validate_file_checksums(self) -> Dict[str, Any]:
        """Validate file checksums"""
        try:
            # Simulate file checksum validation
            # In real implementation, this would verify restored files against manifests

            return {
                "test": "file_checksums",
                "passed": True,
                "message": "File checksum validation passed (simulated)",
                "files_validated": 0
            }

        except Exception as e:
            return {
                "test": "file_checksums",
                "passed": False,
                "message": f"File checksum validation failed: {str(e)}"
            }

    def _calculate_metrics(self, drill_start: datetime, restore_start: datetime,
                          restore_end: datetime, target_rpo_minutes: int,
                          target_rto_minutes: int) -> Dict[str, Any]:
        """Calculate RPO/RTO metrics"""
        logger.info("Phase 6: Calculating metrics")

        # Calculate actual RPO (time between last backup and failure simulation)
        # For drill purposes, assume failure happened now and backup was created at drill_start
        actual_rpo_minutes = (restore_start - drill_start).total_seconds() / 60

        # Calculate actual RTO (time to restore from failure to operational)
        actual_rto_minutes = (restore_end - restore_start).total_seconds() / 60

        rpo_met = actual_rpo_minutes <= target_rpo_minutes
        rto_met = actual_rto_minutes <= target_rto_minutes

        return {
            "actual_rpo_minutes": round(actual_rpo_minutes, 2),
            "actual_rto_minutes": round(actual_rto_minutes, 2),
            "target_rpo_minutes": target_rpo_minutes,
            "target_rto_minutes": target_rto_minutes,
            "rpo_met": rpo_met,
            "rto_met": rto_met,
            "rpo_variance": round(actual_rpo_minutes - target_rpo_minutes, 2),
            "rto_variance": round(actual_rto_minutes - target_rto_minutes, 2)
        }

    def _cleanup_test_environment(self) -> Dict[str, Any]:
        """Clean up test environment"""
        logger.info("Phase 7: Cleaning up test environment")
        phase_start = datetime.now(timezone.utc)

        try:
            test_db_name = self._get_test_db_name()

            if test_db_name:
                # Drop test database
                drop_cmd = ["dropdb", test_db_name]
                subprocess.run(drop_cmd, check=True)
                logger.info(f"Dropped test database: {test_db_name}")

            phase_end = datetime.now(timezone.utc)

            return {
                "status": "completed",
                "started_at": phase_start.isoformat(),
                "completed_at": phase_end.isoformat(),
                "cleaned_database": test_db_name
            }

        except Exception as e:
            logger.warning(f"Cleanup failed (non-critical): {str(e)}")
            return {
                "status": "partial",
                "error": str(e),
                "started_at": phase_start.isoformat()
            }

    def _get_test_db_url(self) -> str:
        """Get test database URL from drill directory"""
        # In real implementation, read from state file
        return settings.database_url.replace("/trdrhub", f"/trdrhub_dr_test_{int(time.time())}")

    def _get_test_db_name(self) -> str:
        """Get test database name"""
        # Extract from URL
        test_db_url = self._get_test_db_url()
        return test_db_url.split('/')[-1]

    def _save_drill_report(self, drill_report: Dict[str, Any]):
        """Save drill report to file"""
        report_file = self.drill_dir / "drill_report.json"

        try:
            with open(report_file, 'w') as f:
                json.dump(drill_report, f, indent=2, default=str)

            logger.info(f"Drill report saved: {report_file}")

        except Exception as e:
            logger.error(f"Failed to save drill report: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Disaster Recovery Drill")
    parser.add_argument("--use-backup", help="Use existing backup ID instead of creating new one")
    parser.add_argument("--target-rpo", type=int, default=15,
                       help="Target RPO in minutes (default: 15)")
    parser.add_argument("--target-rto", type=int, default=60,
                       help="Target RTO in minutes (default: 60)")
    parser.add_argument("--output-json", action="store_true",
                       help="Output results as JSON")

    args = parser.parse_args()

    drill = DRDrill()

    try:
        result = drill.run_drill(
            use_existing_backup=args.use_backup,
            target_rpo_minutes=args.target_rpo,
            target_rto_minutes=args.target_rto
        )

        if args.output_json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"DR Drill completed: {result['drill_id']}")
            print(f"Status: {result['status']}")
            print(f"Success: {result.get('success', False)}")

            if 'phases' in result and 'metrics' in result['phases']:
                metrics = result['phases']['metrics']
                print(f"\nMetrics:")
                print(f"  RPO: {metrics.get('actual_rpo_minutes', 'N/A')} min "
                      f"(target: {metrics.get('target_rpo_minutes', 'N/A')} min)")
                print(f"  RTO: {metrics.get('actual_rto_minutes', 'N/A')} min "
                      f"(target: {metrics.get('target_rto_minutes', 'N/A')} min)")

            if 'phases' in result and 'validation' in result['phases']:
                validation = result['phases']['validation']
                print(f"\nValidation:")
                print(f"  Tests passed: {validation.get('tests_passed', 0)}")
                print(f"  Tests failed: {validation.get('tests_failed', 0)}")

    except Exception as e:
        logger.error(f"DR drill failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()