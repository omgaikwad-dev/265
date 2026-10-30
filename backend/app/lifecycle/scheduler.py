import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.database import SessionLocal
from app.lifecycle.service import LifecycleService

logger = logging.getLogger("fdrsetu.scheduler")

scheduler: BackgroundScheduler = None

def run_scheduled_maturity_scan():
    """
    Scheduled cron job callback executed by APScheduler.
    Evaluates upcoming maturities, flags RENEWAL_DUE, and marks MATURED instruments.
    """
    logger.info("Executing scheduled FDR maturity and validity monitoring scan...")
    db = SessionLocal()
    try:
        summary = LifecycleService.scan_and_update_maturities(db, trigger_source="AUTOMATED_CRON")
        logger.info(
            f"Scheduled scan finished. Checked: {summary['total_scanned']}, "
            f"Matured: {summary['matured_count']}, Renewal Due: {summary['renewal_due_count']}"
        )
    except Exception as e:
        logger.error(f"Error during scheduled maturity scan: {e}")
    finally:
        db.close()

def start_lifecycle_scheduler():
    """
    Initializes and starts the background scheduler during FastAPI lifespan startup.
    """
    global scheduler
    if scheduler and scheduler.running:
        return

    scheduler = BackgroundScheduler(timezone="UTC")
    # Run once daily at 00:05 UTC
    scheduler.add_job(
        run_scheduled_maturity_scan,
        trigger=CronTrigger(hour=0, minute=5, timezone="UTC"),
        id="daily_fdr_maturity_scan",
        name="Daily FDR Maturity & Validity Scan",
        replace_existing=True
    )
    scheduler.start()
    logger.info("APScheduler initialized: Daily FDR Maturity Scan scheduled at 00:05 UTC.")

def shutdown_lifecycle_scheduler():
    """
    Gracefully shuts down the background scheduler.
    """
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler background tasks successfully terminated.")
