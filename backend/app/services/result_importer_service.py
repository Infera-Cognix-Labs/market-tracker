from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from app.config.config import ApifyConfig, StorageConfig
from app.core.logging import correlation_context, get_logger
from app.core.metrics import get_metrics
from app.core.utils import utc_now
from app.integrations.apify_gateway import ApifyGateway
from app.models.api import (
    ExternalRunStatus,
    ExternalRunSummary,
    ImportWorkerResult,
    JobError,
    JobStatus,
    TrackerType,
)
from app.models.documents import (
    ApifyRunDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    JobDocument,
    RawImportBatchDocument,
)
from app.services.event_engine import EventEngine
from app.services.normalization_service import NormalizationService, RawImportedItem
from app.services.object_storage_service import LocalObjectStorageService
from app.services.run_orchestrator import coerce_datetime
from app.services.snapshot_service import SnapshotService

logger = get_logger(__name__)
metrics = get_metrics()
MAX_CATEGORY_SEARCH_PAGES = 10


@dataclass(frozen=True)
class TrackerContext:
    tracker_type: TrackerType
    marketplace: str
    category_top_n: int | None = None


class ResultImporterService:
    def __init__(
        self,
        gateway: ApifyGateway,
        normalization_service: NormalizationService,
        snapshot_service: SnapshotService,
        event_engine: EventEngine,
        config: ApifyConfig,
        storage_config: StorageConfig,
        object_storage: LocalObjectStorageService | None = None,
    ) -> None:
        self.gateway = gateway
        self.normalization_service = normalization_service
        self.snapshot_service = snapshot_service
        self.event_engine = event_engine
        self.config = config
        self.storage_config = storage_config
        self.object_storage = object_storage

    async def process_pending_jobs(self) -> ImportWorkerResult:
        jobs = await JobDocument.find(
            JobDocument.status == JobStatus.IMPORTING
        ).to_list()
        candidates = sorted(jobs, key=lambda item: item.created_at)[
            : self.config.import_worker_batch_size
        ]

        scanned_jobs = 0
        processed_jobs = 0
        succeeded_jobs = 0
        partial_jobs = 0
        failed_jobs = 0
        skipped_jobs = 0

        for job_document in candidates:
            scanned_jobs += 1
            run_document = await self._load_latest_run_document(
                workspace_id=job_document.workspace_id,
                job_code=job_document.job_code,
            )
            if not self._is_ready_for_import(run_document):
                skipped_jobs += 1
                logger.info(
                    "Skipping import because Apify run is not ready for dataset import.",
                    extra={
                        "context": correlation_context(
                            job_code=job_document.job_code,
                            tracker_code=job_document.tracker_code,
                            apify_run_id=(
                                run_document.apify_run_id
                                if run_document is not None
                                else None
                            ),
                        )
                    },
                )
                continue

            processed_jobs += 1
            try:
                final_status = await self._process_job(job_document, run_document)
            except (
                Exception
            ) as exc:  # pragma: no cover - covered through behavior tests
                logger.exception(
                    "Import processing failed unexpectedly.",
                    extra={
                        "context": correlation_context(
                            job_code=job_document.job_code,
                            tracker_code=job_document.tracker_code,
                            apify_run_id=run_document.apify_run_id,
                        )
                    },
                )
                await self._mark_failed(
                    job_document,
                    code=type(exc).__name__,
                    message=str(exc),
                )
                failed_jobs += 1
                continue

            if final_status == JobStatus.SUCCESS:
                succeeded_jobs += 1
            elif final_status == JobStatus.PARTIAL_SUCCESS:
                partial_jobs += 1
            elif final_status == JobStatus.FAILED:
                failed_jobs += 1

        return ImportWorkerResult(
            scanned_jobs=scanned_jobs,
            processed_jobs=processed_jobs,
            succeeded_jobs=succeeded_jobs,
            partial_jobs=partial_jobs,
            failed_jobs=failed_jobs,
            skipped_jobs=skipped_jobs,
        )

    async def _process_job(
        self,
        job_document: JobDocument,
        run_document: ApifyRunDocument,
    ) -> JobStatus:
        current_time = utc_now()
        job_document.status = JobStatus.PROCESSING
        job_document.started_at = job_document.started_at or current_time
        job_document.error = None
        await job_document.save()

        run_finished_at = coerce_datetime(run_document.finished_at)
        if (
            run_finished_at is not None
            and run_document.finished_at != run_finished_at
        ):
            run_document.finished_at = run_finished_at
            await run_document.save()

        if run_finished_at is not None:
            import_lag_seconds = max(
                0.0,
                (current_time - run_finished_at).total_seconds(),
            )
            metrics.observe(
                "import_lag_seconds",
                import_lag_seconds,
                workspace_id=job_document.workspace_id,
                tracker_code=job_document.tracker_code,
                job_code=job_document.job_code,
            )
        else:
            import_lag_seconds = None

        imported_items, expected_items = await self._load_or_import_raw_items(
            workspace_id=job_document.workspace_id,
            job_document=job_document,
            run_document=run_document,
        )
        tracker_context = await self._load_tracker_context(
            workspace_id=job_document.workspace_id,
            tracker_type=TrackerType(job_document.tracker_type),
            tracker_code=job_document.tracker_code,
        )

        normalization_started = perf_counter()
        normalized = self.normalization_service.normalize_items(
            tracker_type=tracker_context.tracker_type,
            marketplace=tracker_context.marketplace,
            raw_items=imported_items,
        )
        normalization_latency_ms = (perf_counter() - normalization_started) * 1000.0
        metrics.observe(
            "normalization_latency_ms",
            normalization_latency_ms,
            workspace_id=job_document.workspace_id,
            tracker_code=job_document.tracker_code,
            job_code=job_document.job_code,
        )

        invalid_rate = (
            float(normalized.invalid_count) / float(expected_items)
            if expected_items > 0
            else 0.0
        )
        metrics.observe(
            "normalization_invalid_rate",
            invalid_rate,
            workspace_id=job_document.workspace_id,
            tracker_code=job_document.tracker_code,
            job_code=job_document.job_code,
        )

        job_document.summary.expected_items = expected_items
        job_document.summary.imported_items = len(normalized.records)
        job_document.summary.events_emitted = 0
        snapshot_latency_ms = 0.0
        event_generation_latency_ms = 0.0
        category_unique_asin_count: int | None = None

        if (
            tracker_context.tracker_type == TrackerType.CATEGORY
            and normalized.records
        ):
            category_unique_asin_count = _count_unique_asins(normalized.records)
            target_unique_count = tracker_context.category_top_n or 50
            next_max_pages = _next_category_search_max_pages(
                current_max_pages=_current_category_search_max_pages(
                    run_document,
                    fallback_top_n=target_unique_count,
                ),
                current_unique_count=category_unique_asin_count,
                target_unique_count=target_unique_count,
            )
            if next_max_pages is not None:
                retry_status = await self._redispatch_category_run(
                    job_document=job_document,
                    run_document=run_document,
                    target_unique_count=target_unique_count,
                    current_unique_count=category_unique_asin_count,
                    next_max_pages=next_max_pages,
                )
                if retry_status == JobStatus.FAILED:
                    metrics.increment(
                        "import_jobs_completed_total",
                        1.0,
                        workspace_id=job_document.workspace_id,
                        tracker_code=job_document.tracker_code,
                        final_status=retry_status,
                    )
                    await self._update_tracker_stats(
                        workspace_id=job_document.workspace_id,
                        tracker_type=tracker_context.tracker_type,
                        tracker_code=job_document.tracker_code,
                        final_status=retry_status,
                    )
                return retry_status

        if normalized.records:
            snapshot_started = perf_counter()
            await self.snapshot_service.persist_snapshots(
                workspace_id=job_document.workspace_id,
                job_document=job_document,
                apify_run_id=run_document.apify_run_id,
                dataset_id=run_document.default_dataset_id or "",
                records=normalized.records,
            )
            snapshot_latency_ms = (perf_counter() - snapshot_started) * 1000.0
            metrics.observe(
                "snapshot_latency_ms",
                snapshot_latency_ms,
                workspace_id=job_document.workspace_id,
                tracker_code=job_document.tracker_code,
                job_code=job_document.job_code,
            )

            event_started = perf_counter()
            job_document.summary.events_emitted = (
                await self.event_engine.generate_events_for_job(
                    workspace_id=job_document.workspace_id,
                    job_document=job_document,
                )
            )
            event_generation_latency_ms = (perf_counter() - event_started) * 1000.0
            metrics.observe(
                "event_generation_latency_ms",
                event_generation_latency_ms,
                workspace_id=job_document.workspace_id,
                tracker_code=job_document.tracker_code,
                job_code=job_document.job_code,
            )

        if normalized.invalid_count > 0 and normalized.records:
            final_status = JobStatus.PARTIAL_SUCCESS
            job_document.error = JobError(
                code="NORMALIZATION_PARTIAL",
                message=(
                    f"Skipped {normalized.invalid_count} invalid records while processing dataset "
                    f"{run_document.default_dataset_id}."
                ),
            )
        elif (
            tracker_context.tracker_type == TrackerType.CATEGORY
            and normalized.records
            and (tracker_context.category_top_n or 50)
            > (category_unique_asin_count or 0)
        ):
            final_status = JobStatus.PARTIAL_SUCCESS
            job_document.error = JobError(
                code="CATEGORY_UNIQUE_INSUFFICIENT",
                message=(
                    f"Collected only {category_unique_asin_count or 0} unique ASINs for target "
                    f"top {tracker_context.category_top_n or 50} after reaching "
                    f"max_pages={_current_category_search_max_pages(run_document, fallback_top_n=tracker_context.category_top_n or 50)}."
                ),
            )
        elif normalized.invalid_count > 0 and expected_items > 0:
            final_status = JobStatus.FAILED
            job_document.error = JobError(
                code="NORMALIZATION_FAILED",
                message="All imported records were invalid after normalization.",
            )
        else:
            final_status = JobStatus.SUCCESS
            job_document.error = None

        job_document.status = final_status
        job_document.finished_at = utc_now()
        await job_document.save()
        metrics.increment(
            "import_jobs_completed_total",
            1.0,
            workspace_id=job_document.workspace_id,
            tracker_code=job_document.tracker_code,
            final_status=final_status,
        )

        await self._update_tracker_stats(
            workspace_id=job_document.workspace_id,
            tracker_type=tracker_context.tracker_type,
            tracker_code=job_document.tracker_code,
            final_status=final_status,
        )

        logger.info(
            "Completed import processing for tracking job.",
            extra={
                "context": correlation_context(
                    job_code=job_document.job_code,
                    tracker_code=job_document.tracker_code,
                    apify_run_id=run_document.apify_run_id,
                    dataset_id=run_document.default_dataset_id,
                    expected_items=expected_items,
                    imported_items=len(normalized.records),
                    invalid_items=normalized.invalid_count,
                    normalization_invalid_rate=invalid_rate,
                    normalization_latency_ms=normalization_latency_ms,
                    snapshot_latency_ms=snapshot_latency_ms,
                    event_generation_latency_ms=event_generation_latency_ms,
                    import_lag_seconds=import_lag_seconds,
                    events_emitted=job_document.summary.events_emitted,
                    final_status=final_status,
                )
            },
        )
        return final_status

    async def _load_latest_run_document(
        self,
        *,
        workspace_id: str,
        job_code: str,
    ) -> ApifyRunDocument | None:
        runs = await ApifyRunDocument.find(
            ApifyRunDocument.workspace_id == workspace_id,
            ApifyRunDocument.tracking_job_code == job_code,
        ).to_list()
        if not runs:
            return None
        return max(runs, key=_apify_run_sort_key)

    async def _load_or_import_raw_items(
        self,
        *,
        workspace_id: str,
        job_document: JobDocument,
        run_document: ApifyRunDocument,
    ) -> tuple[list[RawImportedItem], int]:
        existing_batches = await RawImportBatchDocument.find(
            RawImportBatchDocument.apify_run_id == run_document.apify_run_id
        ).to_list()
        if existing_batches:
            return await self._flatten_raw_batches(existing_batches)

        dataset_id = run_document.default_dataset_id
        if not dataset_id:
            return [], 0

        batch_size = max(1, self.config.import_batch_size)
        offset = 0
        batch_no = 1
        imported_items: list[RawImportedItem] = []
        total_items: int | None = None

        while True:
            response = await self.gateway.list_dataset_items(
                dataset_id,
                limit=batch_size,
                offset=offset,
            )
            if response.total is not None:
                total_items = response.total

            payload_items = response.items
            if not payload_items:
                break

            raw_storage_uri: str | None = None
            raw_items_to_persist = payload_items
            if self._should_offload_raw_items(payload_items):
                raw_storage_uri = await self._offload_raw_items(
                    workspace_id=workspace_id,
                    apify_run_id=run_document.apify_run_id,
                    batch_no=batch_no,
                    items=payload_items,
                )
                if raw_storage_uri is not None:
                    raw_items_to_persist = []

            await RawImportBatchDocument(
                workspace_id=workspace_id,
                tracking_job_code=job_document.job_code,
                apify_run_id=run_document.apify_run_id,
                dataset_id=dataset_id,
                batch_no=batch_no,
                source_item_count=len(payload_items),
                import_status="IMPORTED",
                raw_items=raw_items_to_persist,
                raw_storage_uri=raw_storage_uri,
                imported_at=utc_now(),
                created_at=utc_now(),
            ).insert()

            imported_items.extend(
                RawImportedItem(
                    batch_no=batch_no,
                    item_index=item_index,
                    payload=item,
                )
                for item_index, item in enumerate(payload_items)
            )

            if len(payload_items) < batch_size:
                break

            offset += len(payload_items)
            batch_no += 1

        expected_items = total_items if total_items is not None else len(imported_items)
        return imported_items, expected_items

    def _should_offload_raw_items(self, payload_items: list[dict[str, object]]) -> bool:
        if not self.storage_config.raw_batch_offload_enabled:
            return False
        if self.object_storage is None:
            return False
        return len(payload_items) >= self.storage_config.raw_batch_offload_min_items

    async def _offload_raw_items(
        self,
        *,
        workspace_id: str,
        apify_run_id: str,
        batch_no: int,
        items: list[dict[str, object]],
    ) -> str | None:
        if self.object_storage is None:
            return None
        storage_uri = await self.object_storage.write_raw_batch(
            workspace_id=workspace_id,
            apify_run_id=apify_run_id,
            batch_no=batch_no,
            items=items,
        )
        logger.info(
            "Offloaded raw import batch payload to object storage.",
            extra={
                "context": correlation_context(
                    workspace_id=workspace_id,
                    apify_run_id=apify_run_id,
                    batch_no=batch_no,
                    source_item_count=len(items),
                    raw_storage_uri=storage_uri,
                )
            },
        )
        return storage_uri

    async def _flatten_raw_batches(
        self,
        batches: list[RawImportBatchDocument],
    ) -> tuple[list[RawImportedItem], int]:
        ordered_batches = sorted(batches, key=lambda item: item.batch_no)
        imported_items: list[RawImportedItem] = []

        for batch in ordered_batches:
            payload_items = batch.raw_items
            if not payload_items and batch.raw_storage_uri:
                if self.object_storage is not None:
                    payload_items = await self.object_storage.read_raw_batch(
                        batch.raw_storage_uri
                    )
                else:
                    payload_items = []

            imported_items.extend(
                RawImportedItem(
                    batch_no=batch.batch_no,
                    item_index=item_index,
                    payload=item,
                )
                for item_index, item in enumerate(payload_items)
                if isinstance(item, dict)
            )

        expected_items = sum(batch.source_item_count for batch in ordered_batches)
        return imported_items, expected_items

    async def _load_tracker_context(
        self,
        *,
        workspace_id: str,
        tracker_type: TrackerType,
        tracker_code: str,
    ) -> TrackerContext:
        if tracker_type == TrackerType.CATEGORY:
            tracker_document = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == workspace_id,
                CategoryTrackerDocument.tracker_code == tracker_code,
            )
            if tracker_document is None:
                raise ValueError("Category tracker not found.")
            return TrackerContext(
                tracker_type=tracker_type,
                marketplace=tracker_document.marketplace,
                category_top_n=tracker_document.tracking_config.top_n,
            )

        tracker_document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == tracker_code,
        )
        if tracker_document is None:
            raise ValueError("Competitor tracker not found.")
        return TrackerContext(
            tracker_type=tracker_type,
            marketplace=tracker_document.marketplace,
        )

    async def _redispatch_category_run(
        self,
        *,
        job_document: JobDocument,
        run_document: ApifyRunDocument,
        target_unique_count: int,
        current_unique_count: int,
        next_max_pages: int,
    ) -> JobStatus:
        binding_code = job_document.run_strategy.binding_code
        if not binding_code:
            await self._mark_failed(
                job_document,
                code="MISSING_BINDING_CODE",
                message=(
                    f"Cannot expand category crawl for job `{job_document.job_code}` "
                    "because binding_code is missing."
                ),
            )
            return JobStatus.FAILED

        run_input = dict(run_document.run_input or {})
        run_input["max_pages"] = next_max_pages

        launch = await self.gateway.start_run(
            binding_code,
            run_input,
            webhooks=self._build_run_webhooks(),
        )
        new_run_document = ApifyRunDocument(
            workspace_id=job_document.workspace_id,
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
            origin="IMPORT_RETRY",
            started_at=coerce_datetime(launch.started_at),
            finished_at=coerce_datetime(launch.finished_at),
            poll_count=0,
            error=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        await new_run_document.insert()

        job_document.external_run = ExternalRunSummary(
            provider_run_id=launch.provider_run_id,
            status=launch.status or ExternalRunStatus.READY,
            started_at=coerce_datetime(launch.started_at) or job_document.started_at,
            finished_at=coerce_datetime(launch.finished_at),
        )
        job_document.finished_at = None
        if launch.status == ExternalRunStatus.SUCCEEDED:
            job_document.status = JobStatus.IMPORTING
            job_document.error = None
        elif launch.status in {
            ExternalRunStatus.FAILED,
            ExternalRunStatus.TIMED_OUT,
            ExternalRunStatus.ABORTED,
        }:
            job_document.status = JobStatus.FAILED
            job_document.error = JobError(
                code=launch.status.value,
                message=f"Apify retry run finished with status `{launch.status.value}`.",
            )
            job_document.finished_at = coerce_datetime(launch.finished_at) or utc_now()
        else:
            job_document.status = JobStatus.RUNNING_EXTERNAL
            job_document.error = None
        await job_document.save()

        logger.info(
            "Expanded category crawl because unique ASIN coverage was below target.",
            extra={
                "context": correlation_context(
                    job_code=job_document.job_code,
                    tracker_code=job_document.tracker_code,
                    previous_apify_run_id=run_document.apify_run_id,
                    new_apify_run_id=launch.provider_run_id,
                    dataset_id=launch.default_dataset_id,
                    current_unique_count=current_unique_count,
                    target_unique_count=target_unique_count,
                    next_max_pages=next_max_pages,
                )
            },
        )
        return JobStatus(job_document.status)

    async def _update_tracker_stats(
        self,
        *,
        workspace_id: str,
        tracker_type: TrackerType,
        tracker_code: str,
        final_status: JobStatus,
    ) -> None:
        now = utc_now()

        if tracker_type == TrackerType.CATEGORY:
            tracker_document = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == workspace_id,
                CategoryTrackerDocument.tracker_code == tracker_code,
            )
            if tracker_document is None:
                return
            tracker_document.stats.last_job_at = now
            if final_status in {JobStatus.SUCCESS, JobStatus.PARTIAL_SUCCESS}:
                tracker_document.stats.last_success_at = now
                tracker_document.stats.snapshot_count += 1
            await tracker_document.save()
            return

        tracker_document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == tracker_code,
        )
        if tracker_document is None:
            return
        tracker_document.stats.last_job_at = now
        if final_status in {JobStatus.SUCCESS, JobStatus.PARTIAL_SUCCESS}:
            tracker_document.stats.last_success_at = now
        await tracker_document.save()

    async def _mark_failed(
        self,
        job_document: JobDocument,
        *,
        code: str,
        message: str,
    ) -> None:
        job_document.status = JobStatus.FAILED
        job_document.error = JobError(code=code, message=message)
        job_document.finished_at = utc_now()
        await job_document.save()

    def _is_ready_for_import(self, run_document: ApifyRunDocument | None) -> bool:
        if run_document is None:
            return False
        return run_document.status == ExternalRunStatus.SUCCEEDED.value and bool(
            run_document.default_dataset_id
        )

    def _build_run_webhooks(self) -> list[dict[str, object]] | None:
        webhook_url = self.config.webhook_url
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


def _count_unique_asins(records) -> int:
    return len({record.asin for record in records})


def _current_category_search_max_pages(
    run_document: ApifyRunDocument,
    *,
    fallback_top_n: int,
) -> int:
    run_input = getattr(run_document, "run_input", {})
    if not isinstance(run_input, dict):
        run_input = {}
    raw_max_pages = run_input.get("max_pages")
    if isinstance(raw_max_pages, int) and raw_max_pages > 0:
        return raw_max_pages
    estimated_items_per_page = 16
    return max(
        1,
        min(MAX_CATEGORY_SEARCH_PAGES, math.ceil(fallback_top_n / estimated_items_per_page)),
    )


def _next_category_search_max_pages(
    *,
    current_max_pages: int,
    current_unique_count: int,
    target_unique_count: int,
) -> int | None:
    if current_unique_count >= target_unique_count:
        return None
    if current_max_pages >= MAX_CATEGORY_SEARCH_PAGES:
        return None

    estimated_next_pages = math.ceil(
        current_max_pages * target_unique_count / max(1, current_unique_count)
    )
    next_max_pages = min(
        MAX_CATEGORY_SEARCH_PAGES,
        max(current_max_pages + 1, estimated_next_pages),
    )
    if next_max_pages <= current_max_pages:
        return None
    return next_max_pages


def _apify_run_sort_key(run_document: ApifyRunDocument) -> tuple[datetime, datetime]:
    default_time = datetime.min.replace(tzinfo=UTC)
    created_at = getattr(run_document, "created_at", None) or default_time
    updated_at = getattr(run_document, "updated_at", None) or created_at
    return created_at, updated_at
