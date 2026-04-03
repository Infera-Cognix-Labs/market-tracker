from __future__ import annotations

from datetime import UTC, datetime

from app.core.errors import NotFoundError
from app.core.logging import correlation_context, get_logger
from app.core.utils import utc_now
from app.integrations.apify_gateway import (
    ApifyBindingResolutionError,
    ApifyGateway,
    ApifyGatewayError,
    ApifyRunStartError,
)
from app.models.api import ExternalRunStatus, ExternalRunSummary, JobError, JobStatus, TrackerType
from app.models.documents import (
    ApifyRunDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    JobDocument,
)
from app.services.shared import job_doc_to_model

logger = get_logger(__name__)


class RunOrchestrator:
    def __init__(self, gateway: ApifyGateway) -> None:
        self.gateway = gateway

    async def dispatch_job(self, workspace_id: str, job_code: str) -> None:
        job_document = await JobDocument.find_one(
            JobDocument.workspace_id == workspace_id,
            JobDocument.job_code == job_code,
        )
        if job_document is None:
            raise NotFoundError("Job not found.")
        if job_document.status != JobStatus.QUEUED:
            logger.info(
                "Skipping job dispatch because job is no longer queued.",
                extra={"context": correlation_context(job_code=job_code, status=job_document.status)},
            )
            return

        try:
            tracker_document = await self._load_tracker(workspace_id, job_document)
            binding_code = job_document.run_strategy.binding_code
            if not binding_code:
                raise ApifyBindingResolutionError(
                    f"Job `{job_document.job_code}` is missing an Apify binding_code."
                )

            job_document.status = JobStatus.DISPATCHING
            job_document.started_at = job_document.started_at or utc_now()
            await job_document.save()

            run_input = self._build_run_input(job_document, tracker_document)
            log_context = correlation_context(
                job_code=job_document.job_code,
                tracker_code=job_document.tracker_code,
                snapshot_date=job_document.snapshot_date,
                binding_code=binding_code,
            )
            logger.info(
                "Dispatching Apify run for tracking job.",
                extra={"context": log_context},
            )

            launch = await self.gateway.start_run(binding_code, run_input)

            apify_run = ApifyRunDocument(
                workspace_id=workspace_id,
                tracking_job_code=job_document.job_code,
                provider=job_document.run_strategy.provider,
                binding_code=launch.binding.binding_code,
                actor_ref=launch.binding.actor_id,
                task_ref=launch.binding.task_id,
                apify_run_id=launch.provider_run_id,
                default_dataset_id=launch.default_dataset_id,
                run_input=launch.run_input,
                input_hash=launch.input_hash,
                status=(launch.status or ExternalRunStatus.READY).value,
                apify_status_raw=launch.raw_status,
                origin="API",
                started_at=coerce_datetime(launch.started_at),
                finished_at=coerce_datetime(launch.finished_at),
                poll_count=0,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            await apify_run.insert()

            job_document.external_run = ExternalRunSummary(
                provider_run_id=launch.provider_run_id,
                status=launch.status or ExternalRunStatus.READY,
                started_at=coerce_datetime(launch.started_at) or job_document.started_at,
                finished_at=coerce_datetime(launch.finished_at),
            )
            job_document.status = JobStatus.RUNNING_EXTERNAL
            job_document.error = None
            await job_document.save()

            logger.info(
                "Apify run dispatched successfully.",
                extra={
                    "context": correlation_context(
                        **log_context,
                        apify_run_id=launch.provider_run_id,
                        dataset_id=launch.default_dataset_id,
                    )
                },
            )
        except (ApifyGatewayError, NotFoundError, ValueError) as exc:
            job_document.status = JobStatus.FAILED
            job_document.error = JobError(code=type(exc).__name__, message=str(exc))
            job_document.finished_at = utc_now()
            await job_document.save()
            logger.exception(
                "Failed to dispatch tracking job.",
                extra={
                    "context": correlation_context(
                        job_code=job_document.job_code,
                        tracker_code=job_document.tracker_code,
                        snapshot_date=job_document.snapshot_date,
                    )
                },
            )

    async def _load_tracker(
        self,
        workspace_id: str,
        job_document: JobDocument,
    ) -> CategoryTrackerDocument | CompetitorTrackerDocument:
        if job_document.tracker_type == TrackerType.CATEGORY:
            tracker_document = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == workspace_id,
                CategoryTrackerDocument.tracker_code == job_document.tracker_code,
            )
            if tracker_document is None:
                raise NotFoundError("Category tracker not found.")
            return tracker_document

        tracker_document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == job_document.tracker_code,
        )
        if tracker_document is None:
            raise NotFoundError("Competitor tracker not found.")
        return tracker_document

    def _build_run_input(
        self,
        job_document: JobDocument,
        tracker_document: CategoryTrackerDocument | CompetitorTrackerDocument,
    ) -> dict[str, object]:
        job = job_doc_to_model(job_document)
        base_input: dict[str, object] = {
            "snapshot_date": job.snapshot_date.isoformat(),
            "tracker_code": job.tracker_code,
        }

        if job.tracker_type == TrackerType.CATEGORY:
            base_input.update(
                {
                    "marketplace": tracker_document.marketplace,
                    "browse_node_id": tracker_document.scope.browse_node_id,
                    "browse_node_url": tracker_document.scope.browse_node_url,
                    "top_n": tracker_document.tracking_config.top_n,
                }
            )
            return base_input

        base_input.update(
            {
                "marketplace": tracker_document.marketplace,
                "asins": [item.asin for item in tracker_document.tracked_asins if item.enabled],
                "track_fields": tracker_document.track_fields.model_dump(mode="python"),
            }
        )
        return base_input


def coerce_datetime(value: object | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    raise ValueError(f"Unsupported datetime payload: {value!r}")
