"""
GVP Watch Backend - Reminder Service
-------------------------------------
Background job scheduler using APScheduler.

This service runs periodic checks for:
1. Tickets waiting for citizen verification (send 1-day reminder)
2. Tickets unresponsive for 2 days (auto-resolve)

Jobs run on configurable intervals (default: every hour).
All job executions are logged for audit trail.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import atexit

from config import REMINDER_CHECK_INTERVAL_HOURS
from database import SessionLocal
from ticket_service import TicketService
from logger_config import get_logger

logger = get_logger(__name__)

# Global scheduler instance
_scheduler: BackgroundScheduler = None


class ReminderService:
    """
    Service for managing background reminder and auto-resolution jobs.

    Methods:
    - start() - Start the scheduler
    - stop() - Stop the scheduler gracefully
    """

    def __init__(self):
        """Initialize reminder service"""
        self.scheduler = BackgroundScheduler()
        self.job_ids = []

    def start(self):
        """
        Start the background scheduler with reminder jobs.

        Jobs:
        1. check_reminders() - Every N hours
        2. check_auto_resolve() - Every N hours
        """
        if self.scheduler.running:
            logger.warning("Scheduler is already running")
            return

        try:
            # Job 0: Remind citizens who started reports but missed photo/location
            job0 = self.scheduler.add_job(
                self._check_awaiting_photo_job,
                trigger=IntervalTrigger(hours=REMINDER_CHECK_INTERVAL_HOURS),
                name="check_awaiting_photo",
                id="check_awaiting_photo_job",
                max_instances=1,
                replace_existing=True
            )
            self.job_ids.append(job0.id)

            # Job 1: Check and send reminders for PENDING_VERIFICATION tickets
            job1 = self.scheduler.add_job(
                self._check_reminders_job,
                trigger=IntervalTrigger(hours=REMINDER_CHECK_INTERVAL_HOURS),
                name="check_reminders",
                id="check_reminders_job",
                max_instances=1,  # Only one instance can run at a time
                replace_existing=True
            )
            self.job_ids.append(job1.id)

            # Job 2: Check and auto-resolve UNRESPONSIVE tickets
            job2 = self.scheduler.add_job(
                self._check_auto_resolve_job,
                trigger=IntervalTrigger(hours=REMINDER_CHECK_INTERVAL_HOURS),
                name="check_auto_resolve",
                id="check_auto_resolve_job",
                max_instances=1,
                replace_existing=True
            )
            self.job_ids.append(job2.id)

            self.scheduler.start()

            logger.info(
                f"Reminder Service started. Jobs will run every {REMINDER_CHECK_INTERVAL_HOURS} hour(s)"
            )

            # Graceful shutdown on process exit
            atexit.register(self.stop)

        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise

    def stop(self):
        """Stop the scheduler gracefully"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Reminder Service stopped")

    def _check_reminders_job(self):
        """
        Job function: Check and send reminders for pending tickets.

        This runs on schedule. Gets a fresh DB session for each execution.
        """
        try:
            db = SessionLocal()
            ticket_service = TicketService(db)

            reminder_count = ticket_service.check_and_send_reminders()

            logger.info(f"Reminder job completed: sent {reminder_count} reminders")

            db.close()

        except Exception as e:
            logger.error(f"Error in reminder job: {str(e)}")

    def _check_awaiting_photo_job(self):
        """
        Job function: Send reminder for tickets stuck in AWAITING_PHOTO.

        This runs on schedule. Gets a fresh DB session for each execution.
        """
        try:
            db = SessionLocal()
            ticket_service = TicketService(db)

            reminder_count = ticket_service.check_and_send_awaiting_photo_reminders()

            logger.info(f"Awaiting-photo reminder job completed: sent {reminder_count} reminders")

            db.close()

        except Exception as e:
            logger.error(f"Error in awaiting-photo reminder job: {str(e)}")

    def _check_auto_resolve_job(self):
        """
        Job function: Check and auto-resolve unresponsive tickets.

        This runs on schedule. Gets a fresh DB session for each execution.
        """
        try:
            db = SessionLocal()
            ticket_service = TicketService(db)

            resolve_count = ticket_service.check_and_auto_resolve()

            logger.info(f"Auto-resolve job completed: resolved {resolve_count} tickets")

            db.close()

        except Exception as e:
            logger.error(f"Error in auto-resolve job: {str(e)}")


# Global functions for convenience
def start_reminder_service():
    """Start the global reminder service"""
    global _scheduler
    service = ReminderService()
    service.start()
    _scheduler = service.scheduler
    return service


def stop_reminder_service():
    """Stop the global reminder service"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Global reminder service stopped")


if __name__ == "__main__":
    # Test reminder service (runs indefinitely)
    print("Starting Reminder Service test...")
    service = ReminderService()
    service.start()

    print("Scheduler is running. Press Ctrl+C to exit.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        service.stop()
