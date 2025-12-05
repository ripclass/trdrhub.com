"""
Background Job Scheduler for TRDR Hub

Uses APScheduler to run periodic tasks like:
- Checking tracking alerts every 15 minutes
- Refreshing portfolio shipment data
- Cleaning up old notifications
"""

import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def check_tracking_alerts():
    """
    Check all active tracking alerts and send notifications.
    Runs every 15 minutes.
    """
    from app.routers.tracking import check_and_send_alerts
    
    logger.info("Starting scheduled tracking alert check")
    
    db = SessionLocal()
    try:
        await check_and_send_alerts(db)
        logger.info("Completed scheduled tracking alert check")
    except Exception as e:
        logger.error(f"Error in scheduled alert check: {e}")
    finally:
        db.close()


async def refresh_active_shipments():
    """
    Refresh tracking data for active portfolio shipments.
    Runs every hour during business hours.
    """
    from app.models.tracking import TrackedShipment
    from app.routers.tracking import _track_container_internal, _track_vessel_internal
    
    logger.info("Starting scheduled shipment refresh")
    
    db = SessionLocal()
    try:
        # Get active shipments that haven't been checked in 30+ minutes
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        
        shipments = db.query(TrackedShipment).filter(
            TrackedShipment.is_active == True,
            (TrackedShipment.last_checked == None) | (TrackedShipment.last_checked < cutoff)
        ).limit(50).all()  # Process in batches
        
        logger.info(f"Refreshing {len(shipments)} shipments")
        
        for shipment in shipments:
            try:
                if shipment.tracking_type == "container":
                    data = await _track_container_internal(shipment.reference)
                    shipment.status = data.status
                    shipment.eta = datetime.fromisoformat(data.eta.replace("Z", "+00:00")) if data.eta else None
                    shipment.progress = data.progress
                    shipment.current_location = data.current_location
                    if data.vessel:
                        shipment.vessel_name = data.vessel.name
                else:
                    data = await _track_vessel_internal(shipment.reference, "name")
                    shipment.status = data.status
                    shipment.eta = datetime.fromisoformat(data.eta.replace("Z", "+00:00")) if data.eta else None
                
                shipment.last_checked = datetime.utcnow()
                shipment.data_source = data.data_source
                
            except Exception as e:
                logger.error(f"Error refreshing shipment {shipment.reference}: {e}")
        
        db.commit()
        logger.info("Completed scheduled shipment refresh")
        
    except Exception as e:
        logger.error(f"Error in scheduled shipment refresh: {e}")
    finally:
        db.close()


async def cleanup_old_notifications():
    """
    Clean up notifications older than 90 days.
    Runs daily at 3 AM UTC.
    """
    from app.models.tracking import TrackingNotification
    from datetime import timedelta
    
    logger.info("Starting notification cleanup")
    
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=90)
        
        deleted = db.query(TrackingNotification).filter(
            TrackingNotification.created_at < cutoff
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted} old notifications")
        
    except Exception as e:
        logger.error(f"Error in notification cleanup: {e}")
    finally:
        db.close()


def start_scheduler():
    """Initialize and start the background scheduler."""
    logger.info("Starting background job scheduler")
    
    # Check tracking alerts every 15 minutes
    scheduler.add_job(
        check_tracking_alerts,
        IntervalTrigger(minutes=15),
        id='tracking_alerts_checker',
        name='Check Tracking Alerts',
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )
    
    # Refresh shipment data every hour (during business hours)
    scheduler.add_job(
        refresh_active_shipments,
        IntervalTrigger(hours=1),
        id='shipment_refresh',
        name='Refresh Active Shipments',
        replace_existing=True,
        max_instances=1,
    )
    
    # Clean up old notifications daily at 3 AM UTC
    scheduler.add_job(
        cleanup_old_notifications,
        CronTrigger(hour=3, minute=0),
        id='notification_cleanup',
        name='Clean Up Old Notifications',
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Background scheduler started with jobs: tracking_alerts_checker, shipment_refresh, notification_cleanup")


def stop_scheduler():
    """Stop the background scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")


def get_scheduler_status():
    """Get the current status of scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }


@asynccontextmanager
async def lifespan_scheduler(app):
    """
    Context manager for scheduler lifecycle.
    Use with FastAPI's lifespan parameter.
    
    Example:
        app = FastAPI(lifespan=lifespan_scheduler)
    """
    start_scheduler()
    yield
    stop_scheduler()

