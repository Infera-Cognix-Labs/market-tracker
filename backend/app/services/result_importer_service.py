from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from time import perf_counter

from app.config.config import ApifyConfig, StorageConfig
from app.core.logging import correlation_context, get_logger
from app.core.metrics import get_metrics
from app.core.utils import utc_now
from app.integrations.apify_gateway import ApifyGateway, ApifyRunStartError
from app.models.api import (
    ExternalRunStatus,
    ImportWorkerResult,
    JobError,
    JobStatus,
    TrackerType,
)
from app.models.documents import (
    ApifyRunDocument,
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    JobDocument,
    KeywordSnapshotDocument,
    KeywordTrackerDocument,
    RawImportBatchDocument,
)
from app.services.event_engine import EventEngine
from app.services.normalization_service import (
    NormalizationResult,
    NormalizationService,
    NormalizedProductRecord,
    RawImportedItem,
)
from app.services.object_storage_service import LocalObjectStorageService
from app.services.run_orchestrator import coerce_datetime
from app.services.snapshot_service import SnapshotService

logger = get_logger(__name__)
metrics = get_metrics()


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
        candidates = await JobDocument.find(
            JobDocument.status == JobStatus.IMPORTING.value
        ).to_list()

        candidates = sorted(candidates, key=lambda item: item.created_at)[
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
            except Exception as exc:
                logger.exception(
                    "Import processing failed unexpectedly.",
                    extra={
                        "context": correlation_context(
                            job_code=job_document.job_code,
                            tracker_code=job_document.tracker_code,
                            apify_run_id=(
                                run_document.apify_run_id
                                if run_document is not None
                                else None
                            ),
                            error_type=type(exc).__name__,
                            error_message=str(exc),
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
        if run_finished_at is not None and run_document.finished_at != run_finished_at:
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

        if tracker_context.tracker_type == TrackerType.CATEGORY and normalized.records:
            null_asins = _detect_asins_with_nulls(normalized.records)
            if null_asins and job_document.pool_code:
                fallback_started = perf_counter()
                logger.info(
                    "Triggering pool fallback for null-field ASINs.",
                    extra={
                        "context": correlation_context(
                            tracker_code=job_document.tracker_code,
                            asins_count=len(null_asins),
                            pool_code=job_document.pool_code,
                        )
                    },
                )
                normalized = await self._try_pool_fallback(
                    job_document=job_document,
                    current_records=normalized.records,
                    run_document=run_document,
                    tracker_context=tracker_context,
                )
                fallback_latency_ms = (perf_counter() - fallback_started) * 1000.0
                metrics.observe(
                    "pool_fallback_latency_ms",
                    fallback_latency_ms,
                    workspace_id=job_document.workspace_id,
                    tracker_code=job_document.tracker_code,
                    job_code=job_document.job_code,
                )

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
            snapshot_date=job_document.snapshot_date,
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

        if tracker_type == TrackerType.KEYWORD:
            tracker_document = await KeywordTrackerDocument.find_one(
                KeywordTrackerDocument.workspace_id == workspace_id,
                KeywordTrackerDocument.tracker_code == tracker_code,
            )
            if tracker_document is None:
                raise ValueError("Keyword tracker not found.")
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

    async def _try_pool_fallback(
        self,
        *,
        job_document: JobDocument,
        current_records: list[NormalizedProductRecord],
        run_document: ApifyRunDocument,
        tracker_context: TrackerContext,
    ) -> NormalizationResult:
        pool_code = job_document.pool_code
        if not pool_code:
            return NormalizationResult(records=current_records, invalid_count=0)

        try:
            pool = self.gateway.resolve_pool(pool_code)
        except Exception:
            logger.warning(
                "Could not resolve pool for fallback.",
                extra={"pool_code": pool_code},
            )
            return NormalizationResult(records=current_records, invalid_count=0)

        current_index = job_document.current_pool_index or 0

        for next_index in range(current_index + 1, len(pool)):
            entry = pool[next_index]

            binding_code = f"{pool_code}:{next_index}"
            run_input = dict(run_document.run_input or {})

            try:
                launch = await self.gateway.start_run(
                    binding_code, run_input, webhooks=self._build_run_webhooks()
                )
            except (ApifyRunStartError, Exception) as exc:
                logger.warning(
                    "Pool fallback dispatch failed, trying next.",
                    extra={
                        "actor_id": entry.actor_id,
                        "pool_code": pool_code,
                        "error": str(exc),
                    },
                )
                metrics.increment(
                    "apify_pool_actor_dispatch_failed_total",
                    1.0,
                    pool_code=pool_code,
                    actor_id=entry.actor_id or "",
                    error_type=type(exc).__name__,
                )
                continue

            new_run = ApifyRunDocument(
                workspace_id=job_document.workspace_id,
                tracking_job_code=job_document.job_code,
                provider=job_document.run_strategy.provider,
                binding_code=f"{pool_code}:{next_index}",
                actor_ref=entry.actor_id,
                task_ref=entry.task_id,
                apify_run_id=launch.provider_run_id,
                default_dataset_id=launch.default_dataset_id,
                run_input=launch.run_input,
                input_hash=launch.input_hash,
                status=(launch.status or ExternalRunStatus.READY).value,
                apify_status_raw=launch.raw_status,
                origin="POOL_FALLBACK",
                pool_actor_id=entry.actor_id,
                pool_actor_name=entry.name,
                pool_index=next_index,
                started_at=coerce_datetime(launch.started_at),
                finished_at=coerce_datetime(launch.finished_at),
                poll_count=0,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            await new_run.insert()

            job_document.current_pool_index = next_index
            await job_document.save()

            metrics.increment(
                "apify_pool_actor_dispatch_total",
                1.0,
                pool_code=pool_code,
                actor_id=entry.actor_id or "",
                pool_index=next_index,
                result="dispatched",
            )

            if launch.status not in {
                ExternalRunStatus.SUCCEEDED,
                ExternalRunStatus.READY,
                ExternalRunStatus.RUNNING,
            }:
                logger.info(
                    "Pool fallback run did not succeed, trying next.",
                    extra={
                        "pool_code": pool_code,
                        "actor_id": entry.actor_id,
                        "status": str(launch.status),
                    },
                )
                continue

            if launch.status != ExternalRunStatus.SUCCEEDED:
                logger.info(
                    "Pool fallback run still running, waiting for completion.",
                    extra={
                        "pool_code": pool_code,
                        "apify_run_id": launch.provider_run_id,
                    },
                )
                continue

            raw_items, _ = await self._load_or_import_raw_items(
                workspace_id=job_document.workspace_id,
                job_document=job_document,
                run_document=new_run,
            )

            fallback_normalized = self.normalization_service.normalize_items(
                tracker_type=tracker_context.tracker_type,
                marketplace=tracker_context.marketplace,
                raw_items=raw_items,
            )

            merged_records = _merge_records(
                current_records, fallback_normalized.records
            )

            if not any(_has_null_critical_fields(r) for r in merged_records):
                metrics.increment(
                    "apify_pool_fallback_completed_total",
                    1.0,
                    pool_code=pool_code,
                )
                return NormalizationResult(
                    records=merged_records,
                    invalid_count=fallback_normalized.invalid_count,
                )

            current_records = merged_records

        metrics.increment(
            "apify_pool_fallback_exhausted_total",
            1.0,
            pool_code=pool_code,
        )
        return NormalizationResult(records=current_records, invalid_count=0)

    async def _update_tracker_stats(
        self,
        *,
        workspace_id: str,
        tracker_type: TrackerType,
        tracker_code: str,
        final_status: JobStatus,
        snapshot_date: date,
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
                await self._update_asin_cache(
                    tracker_document=tracker_document,
                    workspace_id=workspace_id,
                    tracker_code=tracker_code,
                    snapshot_date=snapshot_date,
                    snapshot_doc_class=CategorySnapshotDocument,
                )
            await tracker_document.save()
            return

        if tracker_type == TrackerType.KEYWORD:
            tracker_document = await KeywordTrackerDocument.find_one(
                KeywordTrackerDocument.workspace_id == workspace_id,
                KeywordTrackerDocument.tracker_code == tracker_code,
            )
            if tracker_document is None:
                return
            tracker_document.stats.last_job_at = now
            if final_status in {JobStatus.SUCCESS, JobStatus.PARTIAL_SUCCESS}:
                tracker_document.stats.last_success_at = now
                tracker_document.stats.snapshot_count += 1
                await self._update_asin_cache(
                    tracker_document=tracker_document,
                    workspace_id=workspace_id,
                    tracker_code=tracker_code,
                    snapshot_date=snapshot_date,
                    snapshot_doc_class=KeywordSnapshotDocument,
                )
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

    async def _update_asin_cache(
        self,
        *,
        tracker_document: CategoryTrackerDocument | KeywordTrackerDocument,
        workspace_id: str,
        tracker_code: str,
        snapshot_date: date,
        snapshot_doc_class: type,
    ) -> None:
        """Update the asins_last_seen cache on the tracker document from the
        latest snapshot. Called after snapshot + event processing is complete
        so that diff_service sees the pre-import cache state."""
        snapshot = await snapshot_doc_class.find_one(
            snapshot_doc_class.workspace_id == workspace_id,
            snapshot_doc_class.tracker_code == tracker_code,
            snapshot_doc_class.snapshot_date == snapshot_date,
        )
        if snapshot is None:
            return
        if tracker_document.asins_last_seen is None:
            tracker_document.asins_last_seen = {}
        for product in snapshot.products:
            tracker_document.asins_last_seen[product.asin] = snapshot_date

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


def _apify_run_sort_key(run_document: ApifyRunDocument) -> tuple[datetime, datetime]:
    default_time = datetime.min.replace(tzinfo=UTC)
    created_at = getattr(run_document, "created_at", None) or default_time
    updated_at = getattr(run_document, "updated_at", None) or created_at
    return created_at, updated_at


def _detect_asins_with_nulls(
    records: list[NormalizedProductRecord],
) -> list[str]:
    null_asins: list[str] = []
    for record in records:
        if _has_null_critical_fields(record):
            null_asins.append(record.asin)
    return null_asins


def _has_null_critical_fields(record: NormalizedProductRecord) -> bool:
    return (
        record.price_current is None
        or record.rating_value is None
        or record.review_count is None
    )


def _merge_records(
    base: list[NormalizedProductRecord],
    overlay: list[NormalizedProductRecord],
) -> list[NormalizedProductRecord]:
    overlay_by_asin = {r.asin: r for r in overlay}
    merged: list[NormalizedProductRecord] = []
    for record in base:
        if record.asin in overlay_by_asin:
            o = overlay_by_asin[record.asin]
            merged.append(
                NormalizedProductRecord(
                    marketplace=record.marketplace,
                    asin=record.asin,
                    rank_position=record.rank_position or o.rank_position,
                    captured_at=record.captured_at,
                    brand=record.brand
                    if record.brand not in (None, "Unknown")
                    else o.brand,
                    title=record.title if record.title != record.asin else o.title,
                    product_url=record.product_url or o.product_url,
                    main_image_url=record.main_image_url or o.main_image_url,
                    title_hash=record.title_hash,
                    main_image_hash=record.main_image_hash,
                    bsr_position=record.bsr_position or o.bsr_position,
                    price_current=record.price_current or o.price_current,
                    price_original=record.price_original or o.price_original,
                    currency=record.currency or o.currency,
                    coupon_text=record.coupon_text or o.coupon_text,
                    availability_status=record.availability_status,
                    buy_box_status=record.buy_box_status,
                    buy_box_seller_name=record.buy_box_seller_name
                    or o.buy_box_seller_name,
                    rating_value=record.rating_value or o.rating_value,
                    review_count=record.review_count or o.review_count,
                    variation_count=record.variation_count or o.variation_count,
                    deal_info=record.deal_info or o.deal_info,
                    source_batch_no=record.source_batch_no,
                    source_item_index=record.source_item_index,
                )
            )
        else:
            merged.append(record)
    return merged
