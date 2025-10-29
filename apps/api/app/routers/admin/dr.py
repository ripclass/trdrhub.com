"""
Admin Disaster Recovery API - Backup, restore, and drill management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import subprocess
import json
import os
from pathlib import Path

from app.core.database import get_db
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class BackupResponse(BaseModel):
    backup_id: str
    backup_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    file_size: Optional[int]
    file_path: Optional[str]
    s3_location: Optional[str]


class DrillResponse(BaseModel):
    drill_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_duration_minutes: Optional[float]
    success: bool
    rpo_minutes: Optional[float]
    rto_minutes: Optional[float]
    target_rpo_minutes: int
    target_rto_minutes: int


class DrillRequest(BaseModel):
    use_existing_backup: Optional[str] = None
    target_rpo_minutes: int = 15
    target_rto_minutes: int = 60


@router.post("/dr/backup/database", response_model=BackupResponse)
async def create_database_backup(
    background_tasks: BackgroundTasks,
    compression: bool = Query(True, description="Enable compression"),
    encryption: bool = Query(False, description="Enable encryption"),
    db: Session = Depends(get_db)
):
    """Create database backup"""
    try:
        # Run backup script
        script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "dr" / "backup_db.py"

        cmd = [
            "python3", str(script_path),
            "--output-json"
        ]

        if not compression:
            cmd.append("--no-compression")
        if encryption:
            cmd.append("--encryption")

        logger.info(f"Starting database backup with command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        backup_info = json.loads(result.stdout)

        return BackupResponse(
            backup_id=backup_info["backup_id"],
            backup_type="database",
            status=backup_info["status"],
            started_at=datetime.fromisoformat(backup_info["created_at"]),
            completed_at=datetime.fromisoformat(backup_info["completed_at"]),
            duration_seconds=backup_info["duration_seconds"],
            file_size=backup_info["file_size"],
            file_path=backup_info.get("file_path"),
            s3_location=backup_info.get("s3_key")
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"Database backup failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Failed to create database backup: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/dr/backup/objects", response_model=BackupResponse)
async def create_object_backup(
    background_tasks: BackgroundTasks,
    incremental: bool = Query(True, description="Incremental backup"),
    verify_checksums: bool = Query(True, description="Verify file checksums"),
    db: Session = Depends(get_db)
):
    """Create object storage backup"""
    try:
        script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "dr" / "backup_objects.py"

        cmd = [
            "python3", str(script_path),
            "--output-json"
        ]

        if not incremental:
            cmd.append("--full")
        if not verify_checksums:
            cmd.append("--no-verify")

        logger.info(f"Starting object backup with command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        backup_info = json.loads(result.stdout)

        return BackupResponse(
            backup_id=backup_info["backup_id"],
            backup_type="objects",
            status=backup_info["status"],
            started_at=datetime.fromisoformat(backup_info["started_at"]),
            completed_at=datetime.fromisoformat(backup_info["completed_at"]),
            duration_seconds=backup_info["duration_seconds"],
            file_size=backup_info["total_size"],
            file_path=None,
            s3_location=f"s3://{os.getenv('DR_OBJECT_BACKUP_BUCKET', 'trdrhub-dr-objects')}/{backup_info['backup_id']}"
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"Object backup failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Failed to create object backup: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dr/backups", response_model=List[BackupResponse])
async def list_backups(
    backup_type: str = Query("all", regex="^(all|database|objects)$", description="Backup type filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """List available backups"""
    try:
        backups = []

        # List database backups
        if backup_type in ["all", "database"]:
            script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "dr" / "backup_db.py"
            cmd = ["python3", str(script_path), "--list", "--output-json"]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                db_backups = json.loads(result.stdout)

                for backup in db_backups[:limit]:
                    backups.append(BackupResponse(
                        backup_id=backup["backup_id"],
                        backup_type="database",
                        status="completed",
                        started_at=datetime.fromisoformat(backup["created_at"]),
                        completed_at=datetime.fromisoformat(backup["created_at"]),
                        duration_seconds=None,
                        file_size=backup["file_size"],
                        file_path=backup.get("file_path"),
                        s3_location=backup.get("s3_key")
                    ))

            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to list database backups: {e}")

        # List object backups
        if backup_type in ["all", "objects"]:
            script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "dr" / "backup_objects.py"
            cmd = ["python3", str(script_path), "--list", "--output-json"]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                obj_backups = json.loads(result.stdout)

                for backup in obj_backups[:limit]:
                    backups.append(BackupResponse(
                        backup_id=backup["backup_id"],
                        backup_type="objects",
                        status=backup.get("status", "completed"),
                        started_at=datetime.fromisoformat(backup["started_at"]),
                        completed_at=datetime.fromisoformat(backup.get("completed_at", backup["started_at"])),
                        duration_seconds=backup.get("duration_seconds"),
                        file_size=backup.get("total_size"),
                        file_path=None,
                        s3_location=None
                    ))

            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to list object backups: {e}")

        # Sort by start time, newest first
        backups.sort(key=lambda x: x.started_at, reverse=True)

        return backups[:limit]

    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/dr/drill", response_model=DrillResponse)
async def run_dr_drill(
    request: DrillRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run disaster recovery drill"""
    try:
        script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "dr" / "dr_drill.py"

        cmd = [
            "python3", str(script_path),
            f"--target-rpo={request.target_rpo_minutes}",
            f"--target-rto={request.target_rto_minutes}",
            "--output-json"
        ]

        if request.use_existing_backup:
            cmd.extend(["--use-backup", request.use_existing_backup])

        logger.info(f"Starting DR drill with command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        drill_info = json.loads(result.stdout)

        # Extract metrics from drill phases
        metrics = drill_info.get("phases", {}).get("metrics", {})

        return DrillResponse(
            drill_id=drill_info["drill_id"],
            status=drill_info["status"],
            started_at=datetime.fromisoformat(drill_info["started_at"]),
            completed_at=datetime.fromisoformat(drill_info["completed_at"]),
            total_duration_minutes=drill_info["total_duration_minutes"],
            success=drill_info.get("success", False),
            rpo_minutes=metrics.get("actual_rpo_minutes"),
            rto_minutes=metrics.get("actual_rto_minutes"),
            target_rpo_minutes=request.target_rpo_minutes,
            target_rto_minutes=request.target_rto_minutes
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"DR drill failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"DR drill failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Failed to run DR drill: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dr/drills", response_model=List[DrillResponse])
async def list_dr_drills(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """List recent DR drill results"""
    try:
        drills = []
        drill_dir = Path("/tmp/dr_drills")

        if drill_dir.exists():
            # Find drill report files
            for drill_path in sorted(drill_dir.glob("dr_drill_*/drill_report.json"), reverse=True):
                if len(drills) >= limit:
                    break

                try:
                    with open(drill_path, 'r') as f:
                        drill_data = json.load(f)

                    metrics = drill_data.get("phases", {}).get("metrics", {})

                    drills.append(DrillResponse(
                        drill_id=drill_data["drill_id"],
                        status=drill_data["status"],
                        started_at=datetime.fromisoformat(drill_data["started_at"]),
                        completed_at=datetime.fromisoformat(drill_data.get("completed_at", drill_data["started_at"])),
                        total_duration_minutes=drill_data.get("total_duration_minutes"),
                        success=drill_data.get("success", False),
                        rpo_minutes=metrics.get("actual_rpo_minutes"),
                        rto_minutes=metrics.get("actual_rto_minutes"),
                        target_rpo_minutes=metrics.get("target_rpo_minutes", 15),
                        target_rto_minutes=metrics.get("target_rto_minutes", 60)
                    ))

                except Exception as e:
                    logger.warning(f"Failed to read drill report {drill_path}: {e}")

        return drills

    except Exception as e:
        logger.error(f"Failed to list DR drills: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dr/drill/{drill_id}")
async def get_drill_details(
    drill_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed results of a specific DR drill"""
    try:
        drill_path = Path(f"/tmp/dr_drills/{drill_id}/drill_report.json")

        if not drill_path.exists():
            raise HTTPException(status_code=404, detail="DR drill report not found")

        with open(drill_path, 'r') as f:
            drill_data = json.load(f)

        return drill_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get drill details: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dr/metrics")
async def get_dr_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get DR metrics and trends"""
    try:
        # This would integrate with Prometheus metrics in production
        # For now, return simulated metrics

        return {
            "rpo_trend": {
                "current_rpo_minutes": 12.5,
                "target_rpo_minutes": 15,
                "trend": "improving",
                "avg_rpo_minutes": 13.2
            },
            "rto_trend": {
                "current_rto_minutes": 45.3,
                "target_rto_minutes": 60,
                "trend": "stable",
                "avg_rto_minutes": 47.8
            },
            "backup_health": {
                "database_backups": {
                    "success_rate": 98.5,
                    "avg_duration_minutes": 8.2,
                    "last_backup": "2024-01-15T14:30:00Z"
                },
                "object_backups": {
                    "success_rate": 99.2,
                    "avg_duration_minutes": 15.7,
                    "last_backup": "2024-01-15T14:35:00Z"
                }
            },
            "drill_summary": {
                "total_drills": 12,
                "successful_drills": 11,
                "success_rate": 91.7,
                "last_drill": "2024-01-10T10:00:00Z"
            }
        }

    except Exception as e:
        logger.error(f"Failed to get DR metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")