from __future__ import annotations

from dataclasses import dataclass

from app.config.config import ApifyConfig
from app.core.logging import correlation_context, get_logger
from app.core.utils import utc_now
from app.integrations.apify_gateway import ApifyGateway
from app.models.api import (
    ExternalRunStatus,
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
from app.services.normalization_service import NormalizationService, RawImportedItem
from app.services.snapshot_service import SnapshotService

logger = get_logger(__name__)


@dataclass(frozen=True)
class TrackerContext:
    tracker_type: TrackerType
    marketplace: str


class ResultImporterService:
    def __init__(
        self,
        gateway: ApifyGateway,
        normalization_service: NormalizationService,
        snapshot_service: SnapshotService,
        config: ApifyConfig,
    ) -> None:
        self.gateway = gateway
        self.normalization_service = normalization_service
        self.snapshot_service = snapshot_service
        self.config = config

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
            run_document = await ApifyRunDocument.find_one(
                ApifyRunDocument.workspace_id == job_document.workspace_id,
                ApifyRunDocument.tracking_job_code == job_document.job_code,
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

        normalized = self.normalization_service.normalize_items(
            tracker_type=tracker_context.tracker_type,
            marketplace=tracker_context.marketplace,
            raw_items=imported_items,
        )

        job_document.summary.expected_items = expected_items
        job_document.summary.imported_items = len(normalized.records)

        if normalized.records:
            await self.snapshot_service.persist_snapshots(
                workspace_id=job_document.workspace_id,
                job_document=job_document,
                apify_run_id=run_document.apify_run_id,
                dataset_id=run_document.default_dataset_id or "",
                records=normalized.records,
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
                    final_status=final_status,
                )
            },
        )
        return final_status

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
            return _flatten_raw_batches(existing_batches)

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

            await RawImportBatchDocument(
                workspace_id=workspace_id,
                tracking_job_code=job_document.job_code,
                apify_run_id=run_document.apify_run_id,
                dataset_id=dataset_id,
                batch_no=batch_no,
                source_item_count=len(payload_items),
                import_status="IMPORTED",
                raw_items=payload_items,
                raw_storage_uri=None,
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


def _flatten_raw_batches(
    batches: list[RawImportBatchDocument],
) -> tuple[list[RawImportedItem], int]:
    ordered_batches = sorted(batches, key=lambda item: item.batch_no)
    imported_items: list[RawImportedItem] = []
    for batch in ordered_batches:
        imported_items.extend(
            RawImportedItem(
                batch_no=batch.batch_no,
                item_index=item_index,
                payload=item,
            )
            for item_index, item in enumerate(batch.raw_items)
            if isinstance(item, dict)
        )
    expected_items = sum(batch.source_item_count for batch in ordered_batches)
    return imported_items, expected_items
