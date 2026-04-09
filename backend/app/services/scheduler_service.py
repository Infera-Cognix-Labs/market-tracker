from __future__ import annotations

from datetime import datetime

from app.core.errors import ConflictError
from app.core.logging import correlation_context, get_logger
from app.core.metrics import get_metrics
from app.core.utils import utc_now
from app.models.api import (
    Frequency,
    JobCreateRequest,
    SchedulerWorkerResult,
    TrackerType,
    TriggerMode,
)
from app.models.documents import CategoryTrackerDocument, CompetitorTrackerDocument
from app.services.job_service import JobService

logger = get_logger(__name__)
metrics = get_metrics()


class SchedulerService:
    def __init__(self, job_service: JobService) -> None:
        self.job_service = job_service

    async def schedule_due_jobs(
        self,
        *,
        reference_time: datetime | None = None,
    ) -> SchedulerWorkerResult:
        now = reference_time or utc_now()

        category_trackers = await CategoryTrackerDocument.find(
            {"status": "ACTIVE"}
        ).to_list()
        competitor_trackers = await CompetitorTrackerDocument.find(
            {"status": "ACTIVE"}
        ).to_list()

        scanned_trackers = 0
        due_trackers = 0
        created_jobs = 0
        dispatched_jobs = 0
        skipped_existing = 0
        failed_jobs = 0

        for tracker in category_trackers:
            scanned_trackers += 1
            if not self._is_due(schedule=tracker.schedule, now=now):
                continue

            due_trackers += 1
            try:
                created_job = await self.job_service.create_job(
                    tracker.workspace_id,
                    JobCreateRequest(
                        tracker_type=TrackerType.CATEGORY,
                        tracker_code=tracker.tracker_code,
                        snapshot_date=now.date(),
                        trigger_mode=TriggerMode.SCHEDULED,
                    ),
                )
                created_jobs += 1
                await self.job_service.dispatch_job(
                    tracker.workspace_id,
                    created_job.job_code,
                )
                dispatched_jobs += 1
                logger.info(
                    "Scheduler created and dispatched category tracking job.",
                    extra={
                        "context": correlation_context(
                            tracker_code=tracker.tracker_code,
                            job_code=created_job.job_code,
                            snapshot_date=created_job.snapshot_date,
                        )
                    },
                )
            except ConflictError:
                skipped_existing += 1
                logger.info(
                    "Scheduler skipped category tracker because a job already exists.",
                    extra={
                        "context": correlation_context(
                            tracker_code=tracker.tracker_code,
                            snapshot_date=now.date(),
                        )
                    },
                )
            except Exception as exc:  # pragma: no cover - behavior tested via results
                failed_jobs += 1
                metrics.increment(
                    "scheduler_job_failures_total",
                    1.0,
                    workspace_id=tracker.workspace_id,
                    tracker_code=tracker.tracker_code,
                    tracker_type=TrackerType.CATEGORY,
                    error_type=type(exc).__name__,
                )
                logger.exception(
                    "Scheduler failed to process category tracker.",
                    extra={
                        "context": correlation_context(
                            tracker_code=tracker.tracker_code,
                            snapshot_date=now.date(),
                            error_type=type(exc).__name__,
                        )
                    },
                )

        for tracker in competitor_trackers:
            scanned_trackers += 1
            if not self._is_due(schedule=tracker.schedule, now=now):
                continue

            due_trackers += 1
            try:
                created_job = await self.job_service.create_job(
                    tracker.workspace_id,
                    JobCreateRequest(
                        tracker_type=TrackerType.COMPETITOR,
                        tracker_code=tracker.tracker_code,
                        snapshot_date=now.date(),
                        trigger_mode=TriggerMode.SCHEDULED,
                    ),
                )
                created_jobs += 1
                await self.job_service.dispatch_job(
                    tracker.workspace_id,
                    created_job.job_code,
                )
                dispatched_jobs += 1
                logger.info(
                    "Scheduler created and dispatched competitor tracking job.",
                    extra={
                        "context": correlation_context(
                            tracker_code=tracker.tracker_code,
                            job_code=created_job.job_code,
                            snapshot_date=created_job.snapshot_date,
                        )
                    },
                )
            except ConflictError:
                skipped_existing += 1
                logger.info(
                    "Scheduler skipped competitor tracker because a job already exists.",
                    extra={
                        "context": correlation_context(
                            tracker_code=tracker.tracker_code,
                            snapshot_date=now.date(),
                        )
                    },
                )
            except Exception as exc:  # pragma: no cover - behavior tested via results
                failed_jobs += 1
                metrics.increment(
                    "scheduler_job_failures_total",
                    1.0,
                    workspace_id=tracker.workspace_id,
                    tracker_code=tracker.tracker_code,
                    tracker_type=TrackerType.COMPETITOR,
                    error_type=type(exc).__name__,
                )
                logger.exception(
                    "Scheduler failed to process competitor tracker.",
                    extra={
                        "context": correlation_context(
                            tracker_code=tracker.tracker_code,
                            snapshot_date=now.date(),
                            error_type=type(exc).__name__,
                        )
                    },
                )

        metrics.increment("scheduler_trackers_scanned_total", float(scanned_trackers))
        metrics.increment("scheduler_trackers_due_total", float(due_trackers))
        metrics.increment("scheduler_jobs_created_total", float(created_jobs))
        metrics.increment("scheduler_jobs_dispatched_total", float(dispatched_jobs))
        metrics.increment("scheduler_jobs_skipped_total", float(skipped_existing))

        return SchedulerWorkerResult(
            scanned_trackers=scanned_trackers,
            due_trackers=due_trackers,
            created_jobs=created_jobs,
            dispatched_jobs=dispatched_jobs,
            skipped_existing=skipped_existing,
            failed_jobs=failed_jobs,
        )

    def _is_due(self, *, schedule, now: datetime) -> bool:
        if schedule.frequency != Frequency.DAILY:
            return False
        return schedule.hour_utc == now.hour
