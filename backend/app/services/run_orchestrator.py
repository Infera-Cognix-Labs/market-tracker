from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from app.core.errors import NotFoundError
from app.core.logging import correlation_context, get_logger
from app.core.metrics import get_metrics
from app.core.utils import utc_now
from app.integrations.apify_gateway import (
    ApifyBindingResolutionError,
    ApifyGateway,
)
from app.models.api import (
    ExternalRunStatus,
    ExternalRunSummary,
    JobError,
    JobStatus,
    TrackerType,
)
from app.models.documents import (
    ApifyRunDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    JobDocument,
    KeywordTrackerDocument,
)
from app.services.shared import job_doc_to_model

logger = get_logger(__name__)
metrics = get_metrics()
TERMINAL_APIFY_SUCCEEDED_STATUSES = {
    ExternalRunStatus.SUCCEEDED,
}
TERMINAL_APIFY_FAILED_STATUSES = {
    ExternalRunStatus.FAILED,
    ExternalRunStatus.TIMED_OUT,
    ExternalRunStatus.ABORTED,
}


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
                extra={
                    "context": correlation_context(
                        job_code=job_code, status=job_document.status
                    )
                },
            )
            return

        try:
            tracker_document = await self._load_tracker(workspace_id, job_document)

            pool_code = job_document.pool_code
            if not pool_code:
                raise ApifyBindingResolutionError(
                    f"Job `{job_document.job_code}` is missing a pool_code."
                )

            binding_code = f"{pool_code}:0"

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

            dispatch_started = perf_counter()
            launch = await self.gateway.start_run(
                binding_code,
                run_input,
                webhooks=self._build_run_webhooks(),
            )
            dispatch_latency_ms = (perf_counter() - dispatch_started) * 1000.0

            apify_run = ApifyRunDocument(
                workspace_id=workspace_id,
                tracking_job_code=job_document.job_code,
                provider=job_document.run_strategy.provider,
                binding_code=binding_code,
                actor_ref=launch.binding.actor_id,
                task_ref=launch.binding.task_id,
                apify_run_id=launch.provider_run_id,
                default_dataset_id=launch.default_dataset_id,
                run_input=launch.run_input,
                input_hash=launch.input_hash,
                status=(launch.status or ExternalRunStatus.READY).value,
                apify_status_raw=launch.raw_status,
                origin="API",
                pool_actor_id=launch.pool_actor_id,
                pool_actor_name=launch.pool_actor_name,
                pool_index=launch.pool_index,
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
                started_at=coerce_datetime(launch.started_at)
                or job_document.started_at,
                finished_at=coerce_datetime(launch.finished_at),
            )
            if launch.pool_index is not None:
                job_document.current_pool_index = launch.pool_index
            if launch.status in TERMINAL_APIFY_SUCCEEDED_STATUSES:
                job_document.status = JobStatus.IMPORTING
                job_document.error = None
            elif launch.status in TERMINAL_APIFY_FAILED_STATUSES:
                job_document.status = JobStatus.FAILED
                job_document.error = JobError(
                    code=launch.status.value,
                    message=f"Apify run finished with status `{launch.status.value}`.",
                )
                job_document.finished_at = (
                    coerce_datetime(launch.finished_at) or utc_now()
                )
            else:
                job_document.status = JobStatus.RUNNING_EXTERNAL
                job_document.error = None
            await job_document.save()

            logger.info(
                "Apify run dispatched successfully.",
                extra={
                    "context": correlation_context(
                        **log_context,
                        actor_name=getattr(launch.binding, "actor_name", None),
                        actor_id=launch.binding.actor_id,
                        apify_run_id=launch.provider_run_id,
                        dataset_id=launch.default_dataset_id,
                        dispatch_latency_ms=dispatch_latency_ms,
                    )
                },
            )
            metrics.increment(
                "jobs_dispatched_total",
                1.0,
                workspace_id=workspace_id,
                tracker_code=job_document.tracker_code,
                tracker_type=job_document.tracker_type,
                binding_code=binding_code,
            )
            metrics.observe(
                "dispatch_latency_ms",
                dispatch_latency_ms,
                workspace_id=workspace_id,
                tracker_code=job_document.tracker_code,
                tracker_type=job_document.tracker_type,
                binding_code=binding_code,
            )
        except Exception as exc:
            job_document.status = JobStatus.FAILED
            job_document.error = JobError(code=type(exc).__name__, message=str(exc))
            job_document.finished_at = utc_now()
            await job_document.save()
            metrics.increment(
                "jobs_dispatch_failed_total",
                1.0,
                workspace_id=workspace_id,
                tracker_code=job_document.tracker_code,
                tracker_type=job_document.tracker_type,
                error_type=type(exc).__name__,
            )
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
    ) -> CategoryTrackerDocument | CompetitorTrackerDocument | KeywordTrackerDocument:
        if job_document.tracker_type == TrackerType.CATEGORY:
            tracker_document = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == workspace_id,
                CategoryTrackerDocument.tracker_code == job_document.tracker_code,
            )
            if tracker_document is None:
                raise NotFoundError("Category tracker not found.")
            return tracker_document

        if job_document.tracker_type == TrackerType.KEYWORD:
            tracker_document = await KeywordTrackerDocument.find_one(
                KeywordTrackerDocument.workspace_id == workspace_id,
                KeywordTrackerDocument.tracker_code == job_document.tracker_code,
            )
            if tracker_document is None:
                raise NotFoundError("Keyword tracker not found.")
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
        tracker_document: CategoryTrackerDocument
        | CompetitorTrackerDocument
        | KeywordTrackerDocument,
    ) -> dict[str, object]:
        job = job_doc_to_model(job_document)
        base_input: dict[str, object] = {
            "snapshot_date": job.snapshot_date.isoformat(),
            "tracker_code": job.tracker_code,
        }

        if job.tracker_type == TrackerType.CATEGORY:
            top_n = max(1, tracker_document.tracking_config.top_n)
            browse_node_url = tracker_document.scope.browse_node_url
            amazon_domain = _marketplace_to_amazon_domain(tracker_document.marketplace)

            base_input.update(
                {
                    "marketplace": tracker_document.marketplace,
                    "marketplace_code": tracker_document.marketplace.split(".")[-1]
                    if "." in tracker_document.marketplace
                    else tracker_document.marketplace,
                    "browse_node_url": browse_node_url,
                    "top_n": top_n,
                    "search_url": browse_node_url,
                    "amazon_domain": amazon_domain,
                }
            )
            return base_input

        if job.tracker_type == TrackerType.KEYWORD:
            top_n = max(1, tracker_document.tracking_config.top_n)
            amazon_domain = _marketplace_to_amazon_domain(tracker_document.marketplace)
            base_input.update(
                {
                    "marketplace": tracker_document.marketplace,
                    "keyword": tracker_document.scope.keyword,
                    "sort_by": tracker_document.scope.sort_by,
                    "top_n": top_n,
                    "amazon_domain": amazon_domain,
                }
            )
            return base_input

        base_input.update(
            {
                "marketplace": tracker_document.marketplace,
                "asins": [
                    item.asin for item in tracker_document.tracked_asins if item.enabled
                ],
                "track_fields": tracker_document.track_fields.model_dump(mode="python"),
                "amazon_domain": _marketplace_to_amazon_domain(
                    tracker_document.marketplace
                ),
            }
        )
        return base_input

    def _build_run_webhooks(self) -> list[dict[str, object]] | None:
        webhook_url = self.gateway.config.webhook_url
        if not webhook_url:
            return None

        return [
            {
                "event_types": [
                    "ACTOR.RUN.SUCCEEDED",
                    "ACTOR.RUN.FAILED",
                    "ACTOR.RUN.ABORTED",
                    "ACTOR.RUN.TIMED_OUT",
                ],
                "request_url": webhook_url,
            }
        ]


def coerce_datetime(value: object | None) -> datetime | None:
    if value is None:
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    raise ValueError(f"Unsupported datetime payload: {value!r}")


def _marketplace_to_amazon_domain(marketplace: str) -> str:
    mapping = {
        "amazon_us": "amazon.com",
        "amazon_uk": "amazon.co.uk",
        "amazon_de": "amazon.de",
        "amazon_fr": "amazon.fr",
        "amazon_it": "amazon.it",
        "amazon_es": "amazon.es",
        "amazon_ca": "amazon.ca",
        "amazon_mx": "amazon.com.mx",
        "amazon_jp": "amazon.co.jp",
        "amazon_in": "amazon.in",
        "amazon_au": "amazon.com.au",
    }
    return mapping.get(marketplace.lower(), "amazon.com")
