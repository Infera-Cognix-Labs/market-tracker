from __future__ import annotations

from datetime import date

from app.models.api import (
    Job,
    JobCreateRequest,
    JobListResponse,
    JobStatus,
    TrackerType,
)
from app.services.job_service import JobService
from app.services.run_orchestrator import RunOrchestrator
from app.integrations.apify_gateway import ApifyGateway


class JobModule:
    def __init__(self, run_orchestrator: RunOrchestrator) -> None:
        self._service = JobService(run_orchestrator)

    async def list_jobs(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        from_date: date | None = None,
        to_date: date | None = None,
        tracker_type: TrackerType | None = None,
        tracker_code: str | None = None,
        status: JobStatus | None = None,
    ) -> JobListResponse:
        return await self._service.list_jobs(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            from_date=from_date,
            to_date=to_date,
            tracker_type=tracker_type,
            tracker_code=tracker_code,
            status=status,
        )

    async def create_job(self, workspace_id: str, payload: JobCreateRequest) -> Job:
        return await self._service.create_job(workspace_id, payload)

    async def get_job(self, workspace_id: str, job_code: str) -> Job:
        return await self._service.get_job(workspace_id, job_code)

    async def dispatch_job(self, workspace_id: str, job_code: str) -> None:
        await self._service.dispatch_job(workspace_id, job_code)