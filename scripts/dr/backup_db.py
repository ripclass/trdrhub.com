#!/usr/bin/env python3
"""
Database Backup Script for TRDR Hub
Supports both local pg_dump and pgBackRest for enterprise setups
"""

import os
import subprocess
import sys
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api'))

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Database backup utility with multiple backend support"""

    def __init__(self, backup_method: str = "pg_dump"):
        self.backup_method = backup_method
        self.backup_dir = Path("/tmp/backups/db")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Parse database URL
        self.db_url = settings.database_url
        self.s3_bucket = os.getenv("DR_S3_BUCKET", "trdrhub-dr-backups")
        self.s3_prefix = os.getenv("DR_S3_PREFIX", "database")

    def create_backup(self, compression: bool = True, encryption: bool = False) -> dict:
        """Create database backup"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"trdrhub_backup_{timestamp}"

        if self.backup_method == "pg_dump":
            return self._pg_dump_backup(backup_name, compression, encryption)
        elif self.backup_method == "pgbackrest":
            return self._pgbackrest_backup(backup_name)
        else:
            raise ValueError(f"Unsupported backup method: {self.backup_method}")

    def _pg_dump_backup(self, backup_name: str, compression: bool, encryption: bool) -> dict:
        """Create backup using pg_dump"""
        logger.info(f"Starting pg_dump backup: {backup_name}")

        backup_file = self.backup_dir / f"{backup_name}.sql"
        if compression:
            backup_file = self.backup_dir / f"{backup_name}.sql.gz"

        start_time = datetime.now(timezone.utc)

        try:
            # Build pg_dump command
            cmd = [
                "pg_dump",
                self.db_url,
                "--verbose",
                "--no-password",
                "--format=custom" if compression else "--format=plain",
                "--file", str(backup_file)
            ]

            # Add compression if requested
            if compression and not backup_file.suffix == '.gz':
                cmd.extend(["--compress=9"])

            # Execute backup
            logger.info(f"Executing: {' '.join(cmd[:3])} [DATABASE_URL] {' '.join(cmd[4:])}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Get file size
            file_size = backup_file.stat().st_size

            # Calculate checksums
            sha256_hash = self._calculate_checksum(backup_file)

            backup_info = {
                "backup_id": backup_name,
                "method": "pg_dump",
                "file_path": str(backup_file),
                "file_size": file_size,
                "duration_seconds": duration,
                "compression": compression,
                "encryption": encryption,
                "sha256_hash": sha256_hash,
                "created_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "status": "completed"
            }

            # Upload to S3 if configured
            if self._is_s3_configured():
                s3_key = self._upload_to_s3(backup_file, backup_name)
                backup_info["s3_key"] = s3_key
                backup_info["s3_bucket"] = self.s3_bucket

            logger.info(f"Backup completed successfully: {backup_name}")
            logger.info(f"Size: {file_size / 1024 / 1024:.2f} MB, Duration: {duration:.2f}s")

            return backup_info

        except subprocess.CalledProcessError as e:
            logger.error(f"pg_dump failed: {e}")
            logger.error(f"stderr: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            raise

    def _pgbackrest_backup(self, backup_name: str) -> dict:
        """Create backup using pgBackRest (enterprise)"""
        logger.info(f"Starting pgBackRest backup: {backup_name}")

        start_time = datetime.now(timezone.utc)

        try:
            # Execute pgBackRest backup
            cmd = [
                "pgbackrest",
                "--stanza=trdrhub",
                f"--annotation=backup_id={backup_name}",
                "backup"
            ]

            logger.info(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Get backup info from pgBackRest
            info_cmd = ["pgbackrest", "--stanza=trdrhub", "info", "--output=json"]
            info_result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)

            backup_info = {
                "backup_id": backup_name,
                "method": "pgbackrest",
                "duration_seconds": duration,
                "created_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "status": "completed",
                "pgbackrest_info": info_result.stdout
            }

            logger.info(f"pgBackRest backup completed: {backup_name}")
            logger.info(f"Duration: {duration:.2f}s")

            return backup_info

        except subprocess.CalledProcessError as e:
            logger.error(f"pgBackRest backup failed: {e}")
            logger.error(f"stderr: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            raise

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        import hashlib

        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _is_s3_configured(self) -> bool:
        """Check if S3 is configured for backup storage"""
        return bool(
            os.getenv("AWS_ACCESS_KEY_ID") or
            os.getenv("AWS_PROFILE") or
            os.path.exists(os.path.expanduser("~/.aws/credentials"))
        )

    def _upload_to_s3(self, file_path: Path, backup_name: str) -> str:
        """Upload backup file to S3"""
        try:
            s3_client = boto3.client('s3')
            s3_key = f"{self.s3_prefix}/{backup_name}/{file_path.name}"

            logger.info(f"Uploading to S3: s3://{self.s3_bucket}/{s3_key}")

            # Upload with server-side encryption
            s3_client.upload_file(
                str(file_path),
                self.s3_bucket,
                s3_key,
                ExtraArgs={'ServerSideEncryption': 'AES256'}
            )

            logger.info(f"Successfully uploaded to S3: {s3_key}")
            return s3_key

        except ClientError as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise

    def list_backups(self, limit: int = 10) -> list:
        """List available backups"""
        backups = []

        # List local backups
        if self.backup_dir.exists():
            for backup_file in sorted(self.backup_dir.glob("trdrhub_backup_*"), reverse=True):
                if len(backups) >= limit:
                    break

                stat = backup_file.stat()
                backups.append({
                    "backup_id": backup_file.stem,
                    "method": "pg_dump",
                    "location": "local",
                    "file_path": str(backup_file),
                    "file_size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat()
                })

        # List S3 backups if configured
        if self._is_s3_configured():
            try:
                s3_client = boto3.client('s3')
                response = s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=f"{self.s3_prefix}/",
                    MaxKeys=limit
                )

                for obj in response.get('Contents', []):
                    if obj['Key'].endswith('.sql') or obj['Key'].endswith('.sql.gz'):
                        backups.append({
                            "backup_id": Path(obj['Key']).parent.name,
                            "method": "pg_dump",
                            "location": "s3",
                            "s3_key": obj['Key'],
                            "file_size": obj['Size'],
                            "created_at": obj['LastModified'].isoformat()
                        })

            except ClientError as e:
                logger.warning(f"Could not list S3 backups: {str(e)}")

        return sorted(backups, key=lambda x: x['created_at'], reverse=True)[:limit]


def main():
    parser = argparse.ArgumentParser(description="Database backup utility")
    parser.add_argument("--method", choices=["pg_dump", "pgbackrest"],
                       default="pg_dump", help="Backup method")
    parser.add_argument("--no-compression", action="store_true",
                       help="Disable compression")
    parser.add_argument("--encryption", action="store_true",
                       help="Enable encryption (enterprise)")
    parser.add_argument("--list", action="store_true",
                       help="List available backups")
    parser.add_argument("--output-json", action="store_true",
                       help="Output results as JSON")

    args = parser.parse_args()

    backup = DatabaseBackup(backup_method=args.method)

    if args.list:
        backups = backup.list_backups()
        if args.output_json:
            import json
            print(json.dumps(backups, indent=2))
        else:
            print(f"Found {len(backups)} backups:")
            for b in backups:
                size_mb = b['file_size'] / 1024 / 1024
                print(f"  {b['backup_id']} - {size_mb:.2f}MB - {b['created_at']} ({b['location']})")
    else:
        try:
            result = backup.create_backup(
                compression=not args.no_compression,
                encryption=args.encryption
            )

            if args.output_json:
                import json
                print(json.dumps(result, indent=2))
            else:
                print(f"Backup completed successfully: {result['backup_id']}")
                print(f"File: {result.get('file_path', 'N/A')}")
                print(f"Size: {result['file_size'] / 1024 / 1024:.2f} MB")
                print(f"Duration: {result['duration_seconds']:.2f} seconds")
                if 's3_key' in result:
                    print(f"S3 Location: s3://{result['s3_bucket']}/{result['s3_key']}")

        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()