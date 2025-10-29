#!/usr/bin/env python3
"""
Database Restore Script for TRDR Hub
Supports both local pg_restore and pgBackRest for enterprise setups
"""

import os
import subprocess
import sys
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import tempfile

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api'))

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseRestore:
    """Database restore utility with multiple backend support"""

    def __init__(self, restore_method: str = "pg_restore"):
        self.restore_method = restore_method
        self.backup_dir = Path("/tmp/backups/db")
        self.s3_bucket = os.getenv("DR_S3_BUCKET", "trdrhub-dr-backups")
        self.s3_prefix = os.getenv("DR_S3_PREFIX", "database")

        # Parse database URL
        self.db_url = settings.database_url

    def restore_backup(self, backup_id: str, target_db: str = None, dry_run: bool = False) -> dict:
        """Restore database from backup"""
        logger.info(f"Starting database restore: {backup_id}")

        if dry_run:
            logger.info("DRY RUN MODE - No actual restore will be performed")

        start_time = datetime.now(timezone.utc)

        # Find backup file
        backup_info = self._find_backup(backup_id)
        if not backup_info:
            raise ValueError(f"Backup not found: {backup_id}")

        # Download from S3 if needed
        local_file = self._ensure_local_backup(backup_info)

        try:
            if self.restore_method == "pg_restore":
                result = self._pg_restore_backup(local_file, target_db, dry_run)
            elif self.restore_method == "pgbackrest":
                result = self._pgbackrest_restore(backup_id, target_db, dry_run)
            else:
                raise ValueError(f"Unsupported restore method: {self.restore_method}")

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            result.update({
                "backup_id": backup_id,
                "restore_started_at": start_time.isoformat(),
                "restore_completed_at": end_time.isoformat(),
                "restore_duration_seconds": duration,
                "dry_run": dry_run
            })

            logger.info(f"Restore {'simulation' if dry_run else 'completed'} successfully: {backup_id}")
            logger.info(f"Duration: {duration:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            raise

    def _find_backup(self, backup_id: str) -> dict:
        """Find backup by ID in local storage or S3"""
        # Check local storage first
        local_files = list(self.backup_dir.glob(f"{backup_id}.*"))
        if local_files:
            backup_file = local_files[0]
            stat = backup_file.stat()
            return {
                "backup_id": backup_id,
                "location": "local",
                "file_path": str(backup_file),
                "file_size": stat.st_size
            }

        # Check S3
        if self._is_s3_configured():
            try:
                s3_client = boto3.client('s3')
                response = s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=f"{self.s3_prefix}/{backup_id}/",
                    MaxKeys=10
                )

                for obj in response.get('Contents', []):
                    if obj['Key'].endswith('.sql') or obj['Key'].endswith('.sql.gz'):
                        return {
                            "backup_id": backup_id,
                            "location": "s3",
                            "s3_key": obj['Key'],
                            "file_size": obj['Size']
                        }

            except ClientError as e:
                logger.warning(f"Could not search S3 for backup: {str(e)}")

        return None

    def _ensure_local_backup(self, backup_info: dict) -> Path:
        """Ensure backup file is available locally"""
        if backup_info["location"] == "local":
            return Path(backup_info["file_path"])

        # Download from S3
        s3_key = backup_info["s3_key"]
        local_file = self.backup_dir / Path(s3_key).name

        logger.info(f"Downloading backup from S3: {s3_key}")

        try:
            s3_client = boto3.client('s3')
            s3_client.download_file(self.s3_bucket, s3_key, str(local_file))
            logger.info(f"Downloaded to: {local_file}")
            return local_file

        except ClientError as e:
            logger.error(f"S3 download failed: {str(e)}")
            raise

    def _pg_restore_backup(self, backup_file: Path, target_db: str, dry_run: bool) -> dict:
        """Restore using pg_restore"""
        logger.info(f"Using pg_restore to restore: {backup_file}")

        # Determine if this is a custom format backup
        is_custom_format = backup_file.suffix in ['.dump', '.bak'] or self._is_custom_format(backup_file)

        if dry_run:
            # For dry run, just list the backup contents
            if is_custom_format:
                cmd = ["pg_restore", "--list", str(backup_file)]
            else:
                cmd = ["head", "-50", str(backup_file)]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "method": "pg_restore",
                "dry_run_output": result.stdout[:2000],  # Limit output
                "status": "dry_run_completed"
            }

        # Build restore command
        restore_db_url = target_db or self.db_url

        if is_custom_format:
            cmd = [
                "pg_restore",
                "--verbose",
                "--clean",
                "--no-acl",
                "--no-owner",
                "--dbname", restore_db_url,
                str(backup_file)
            ]
        else:
            # Plain SQL format
            cmd = [
                "psql",
                restore_db_url,
                "--file", str(backup_file),
                "--quiet"
            ]

        logger.info(f"Executing restore command...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Verify restoration
        verify_result = self._verify_restore(restore_db_url)

        return {
            "method": "pg_restore",
            "backup_file": str(backup_file),
            "target_database": restore_db_url,
            "status": "completed",
            "verification": verify_result
        }

    def _pgbackrest_restore(self, backup_id: str, target_db: str, dry_run: bool) -> dict:
        """Restore using pgBackRest"""
        logger.info(f"Using pgBackRest to restore: {backup_id}")

        if dry_run:
            # For dry run, just show what would be restored
            cmd = ["pgbackrest", "--stanza=trdrhub", "info", "--output=json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "method": "pgbackrest",
                "dry_run_output": result.stdout,
                "status": "dry_run_completed"
            }

        # Stop PostgreSQL for restore
        logger.info("Stopping PostgreSQL for restore...")
        subprocess.run(["systemctl", "stop", "postgresql"], check=True)

        try:
            # Execute pgBackRest restore
            cmd = [
                "pgbackrest",
                "--stanza=trdrhub",
                f"--set={backup_id}",
                "restore"
            ]

            logger.info("Executing pgBackRest restore...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Start PostgreSQL
            logger.info("Starting PostgreSQL...")
            subprocess.run(["systemctl", "start", "postgresql"], check=True)

            # Verify restoration
            verify_result = self._verify_restore(target_db or self.db_url)

            return {
                "method": "pgbackrest",
                "backup_id": backup_id,
                "status": "completed",
                "verification": verify_result
            }

        except Exception as e:
            # Try to start PostgreSQL even if restore failed
            try:
                subprocess.run(["systemctl", "start", "postgresql"], check=False)
            except:
                pass
            raise

    def _is_custom_format(self, backup_file: Path) -> bool:
        """Check if backup file is in PostgreSQL custom format"""
        try:
            with open(backup_file, 'rb') as f:
                header = f.read(5)
                return header == b'PGDMP'
        except:
            return False

    def _is_s3_configured(self) -> bool:
        """Check if S3 is configured"""
        return bool(
            os.getenv("AWS_ACCESS_KEY_ID") or
            os.getenv("AWS_PROFILE") or
            os.path.exists(os.path.expanduser("~/.aws/credentials"))
        )

    def _verify_restore(self, db_url: str) -> dict:
        """Verify the restored database"""
        logger.info("Verifying restored database...")

        verification = {
            "database_accessible": False,
            "table_count": 0,
            "audit_chain_valid": False,
            "sample_data_present": False
        }

        try:
            # Test database connection
            result = subprocess.run([
                "psql", db_url, "-c", "SELECT version();"
            ], capture_output=True, text=True, check=True)

            verification["database_accessible"] = True

            # Count tables
            result = subprocess.run([
                "psql", db_url, "-t", "-c",
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
            ], capture_output=True, text=True, check=True)

            verification["table_count"] = int(result.stdout.strip())

            # Check for audit table
            result = subprocess.run([
                "psql", db_url, "-t", "-c",
                "SELECT count(*) FROM audit_log_entries LIMIT 1;"
            ], capture_output=True, text=True, check=False)

            if result.returncode == 0:
                verification["sample_data_present"] = True

                # Basic audit chain verification
                result = subprocess.run([
                    "psql", db_url, "-t", "-c",
                    "SELECT count(*) FROM audit_log_entries WHERE entry_hash IS NOT NULL;"
                ], capture_output=True, text=True, check=False)

                if result.returncode == 0:
                    hash_count = int(result.stdout.strip())
                    verification["audit_chain_valid"] = hash_count > 0

        except Exception as e:
            logger.warning(f"Verification step failed: {str(e)}")

        logger.info(f"Verification results: {verification}")
        return verification


def main():
    parser = argparse.ArgumentParser(description="Database restore utility")
    parser.add_argument("backup_id", help="Backup ID to restore")
    parser.add_argument("--method", choices=["pg_restore", "pgbackrest"],
                       default="pg_restore", help="Restore method")
    parser.add_argument("--target-db", help="Target database URL (default: current DB)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be restored without doing it")
    parser.add_argument("--output-json", action="store_true",
                       help="Output results as JSON")

    args = parser.parse_args()

    restore = DatabaseRestore(restore_method=args.method)

    try:
        result = restore.restore_backup(
            backup_id=args.backup_id,
            target_db=args.target_db,
            dry_run=args.dry_run
        )

        if args.output_json:
            import json
            print(json.dumps(result, indent=2))
        else:
            print(f"Restore {'simulation' if args.dry_run else 'completed'}: {args.backup_id}")
            if args.dry_run:
                print("This was a dry run - no changes were made")
            else:
                print(f"Duration: {result['restore_duration_seconds']:.2f} seconds")
                if 'verification' in result:
                    v = result['verification']
                    print(f"Verification: DB accessible: {v['database_accessible']}, "
                          f"Tables: {v['table_count']}, "
                          f"Data present: {v['sample_data_present']}")

    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()