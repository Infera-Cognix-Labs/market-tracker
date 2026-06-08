from __future__ import annotations

from datetime import date

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.core.logging import correlation_context, get_logger
from app.core.utils import paginate, utc_now
from app.models.api import (
    Job,
    JobCreateRequest,
    JobListResponse,
    JobRunStrategy,
    JobStatus,
    JobSummary,
    Provider,
    TrackerType,
)
from app.models.documents import (
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    JobDocument,
    KeywordTrackerDocument,
)
from app.services.run_orchestrator import RunOrchestrator
from app.services.shared import generate_job_code, job_doc_to_model, within_range

logger = get_logger(__name__)


class JobService:
    def __init__(self, run_orchestrator: RunOrchestrator) -> None:
        self.run_orchestrator = run_orchestrator

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
        if from_date and to_date and from_date > to_date:
            raise BadRequestError("from_date must be less than or equal to to_date.")

        items = sorted(
            [
                job_doc_to_model(document)
                for document in await JobDocument.find(
                    JobDocument.workspace_id == workspace_id
                ).to_list()
                if within_range(document.snapshot_date, from_date, to_date)
                and (tracker_type is None or document.tracker_type == tracker_type)
                and (tracker_code is None or document.tracker_code == tracker_code)
                and (status is None or document.status == status)
            ],
            key=lambda job: job.created_at,
            reverse=True,
        )
        paged_items, total = paginate(items, page, page_size)
        return JobListResponse(
            items=paged_items,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def create_job(self, workspace_id: str, payload: JobCreateRequest) -> Job:
        snapshot_date = payload.snapshot_date or utc_now().date()
        if payload.tracker_type == TrackerType.CATEGORY:
            tracker_exists = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == workspace_id,
                CategoryTrackerDocument.tracker_code == payload.tracker_code,
            )
            if tracker_exists is None:
                raise NotFoundError("Category tracker not found.")
        elif payload.tracker_type == TrackerType.KEYWORD:
            tracker_exists = await KeywordTrackerDocument.find_one(
                KeywordTrackerDocument.workspace_id == workspace_id,
                KeywordTrackerDocument.tracker_code == payload.tracker_code,
            )
            if tracker_exists is None:
                raise NotFoundError("Keyword tracker not found.")
        else:
            tracker_exists = await CompetitorTrackerDocument.find_one(
                CompetitorTrackerDocument.workspace_id == workspace_id,
                CompetitorTrackerDocument.tracker_code == payload.tracker_code,
            )
            if tracker_exists is None:
                raise NotFoundError("Competitor tracker not found.")

        existing_jobs = await JobDocument.find(
            JobDocument.workspace_id == workspace_id
        ).to_list()
        existing_job_models = [job_doc_to_model(document) for document in existing_jobs]
        if any(
            item.tracker_type == payload.tracker_type
            and item.tracker_code == payload.tracker_code
            and item.snapshot_date == snapshot_date
            for item in existing_job_models
        ):
            raise ConflictError(
                f"A job already exists for tracker `{payload.tracker_code}` on {snapshot_date}."
            )

        pool_code_map = {
            TrackerType.CATEGORY: "category",
            TrackerType.COMPETITOR: "competitor",
            TrackerType.KEYWORD: "keyword",
        }
        pool_code = pool_code_map[payload.tracker_type]

        job = Job(
            job_code=generate_job_code(
                payload.tracker_type,
                snapshot_date,
                {item.job_code for item in existing_job_models},
            ),
            tracker_type=payload.tracker_type,
            tracker_code=payload.tracker_code,
            snapshot_date=snapshot_date,
            trigger_mode=payload.trigger_mode,
            status=JobStatus.QUEUED,
            run_strategy=JobRunStrategy(
                provider=Provider.APIFY,
                pool_code=pool_code,
            ),
            summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
            created_at=utc_now(),
        )
        await JobDocument(
            workspace_id=workspace_id,
            pool_code=pool_code,
            **job.model_dump(mode="python"),
        ).insert()
        logger.info(
            "Created tracking job.",
            extra={
                "context": correlation_context(
                    job_code=job.job_code,
                    tracker_code=job.tracker_code,
                    snapshot_date=job.snapshot_date,
                )
            },
        )
        return job

    async def dispatch_job(self, workspace_id: str, job_code: str) -> None:
        await self.run_orchestrator.dispatch_job(workspace_id, job_code)

    async def get_job(self, workspace_id: str, job_code: str) -> Job:
        document = await JobDocument.find_one(
            JobDocument.workspace_id == workspace_id,
            JobDocument.job_code == job_code,
        )
        if document is None:
            raise NotFoundError("Job not found.")
        return job_doc_to_model(document)
