from __future__ import annotations

from datetime import date, datetime

from app.models.api import (
    ApifyRunPollResult,
    ApifyWebhookAck,
    ApifyWebhookEnvelope,
    DigestWorkerResult,
    ImportWorkerResult,
    SchedulerWorkerResult,
)
from app.services.apify_run_lifecycle_service import ApifyRunLifecycleService
from app.services.digest_service import DigestService
from app.services.result_importer_service import ResultImporterService
from app.services.scheduler_service import SchedulerService
from app.services.job_service import JobService
from app.services.run_orchestrator import RunOrchestrator


class WorkerModule:
    def __init__(
        self,
        job_service: JobService,
        result_importer: ResultImporterService,
        apify_lifecycle: ApifyRunLifecycleService,
        digest_service: DigestService,
    ) -> None:
        self._scheduler_service = SchedulerService(job_service)
        self._result_importer = result_importer
        self._apify_lifecycle = apify_lifecycle
        self._digest_service = digest_service

    async def handle_apify_webhook(
        self,
        payload: ApifyWebhookEnvelope,
    ) -> ApifyWebhookAck:
        return await self._apify_lifecycle.handle_webhook(payload)

    async def poll_apify_runs(self) -> ApifyRunPollResult:
        return await self._apify_lifecycle.poll_runs()

    async def process_import_jobs(self) -> ImportWorkerResult:
        return await self._result_importer.process_pending_jobs()

    async def schedule_jobs(
        self, reference_time: datetime | None = None
    ) -> SchedulerWorkerResult:
        return await self._scheduler_service.schedule_due_jobs(
            reference_time=reference_time
        )

    async def process_digest_jobs(
        self, reference_date: date | None = None
    ) -> DigestWorkerResult:
        return await self._digest_service.generate_weekly_digests(
            reference_date=reference_date
        )