import asyncio
import logging
from datetime import datetime, timezone

from app.db.session import AsyncSessionLocal
from app.modules.audit.repository import AuditLogRepository
from app.modules.leaves.repository import LeaveRepository
from app.modules.leaves.service import LeaveService

logger = logging.getLogger("uvicorn.error")

_scheduler_task: asyncio.Task | None = None
_stop_event = asyncio.Event()


async def _run_midnight_accrual_loop():
    """Background asyncio task running daily at 00:00 midnight to process periodic leave accruals."""
    logger.info("Leave Accrual Background Scheduler started.")
    last_processed_date = None

    while not _stop_event.is_set():
        try:
            now = datetime.now(timezone.utc)
            current_date = now.date()

            # Execute accrual engine at midnight (00:00) or on startup date transition
            if last_processed_date != current_date:
                async with AsyncSessionLocal() as session:
                    repo = LeaveRepository(session)
                    audit_repo = AuditLogRepository(session)
                    service = LeaveService(session, repo, audit_repo)
                    updated_count = await service.trigger_periodic_accruals(
                        target_date=current_date
                    )
                    await session.commit()

                    logger.info(
                        "Midnight Periodic Accrual completed for date %s: %d allocations updated.",
                        current_date,
                        updated_count,
                    )
                last_processed_date = current_date

            # Wait 3600 seconds (1 hour) or until stopped
            await asyncio.wait_for(_stop_event.wait(), timeout=3600.0)
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.error("Error in background accrual scheduler loop: %s", e)
            await asyncio.sleep(60)


def start_background_scheduler():
    global _scheduler_task
    _stop_event.clear()
    _scheduler_task = asyncio.create_task(_run_midnight_accrual_loop())


async def stop_background_scheduler():
    global _scheduler_task
    _stop_event.set()
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
    logger.info("Leave Accrual Background Scheduler stopped.")
