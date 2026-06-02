from __future__ import annotations

import time
from datetime import timedelta

from beanie.operators import In
from pymongo import ASCENDING

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.utils import paginate, utc_now
from app.models.api import (
    CategorySnapshot,
    CategoryTracker,
    CategoryTrackerCreateRequest,
    CategoryTrackerListResponse,
    CategoryTrackerStats,
    CategoryTrackerUpdateRequest,
    CategoryTrackingConfig,
    CompetitorTrackerCreateRequest,
    CompetitorTrackerDetail,
    CompetitorTrackerListResponse,
    CompetitorTrackerStats,
    CompetitorTrackerUpdateRequest,
    Timeframe,
    TrackedAsin,
    TrackedAsinReplacementRequest,
    TrackerSchedule,
    TrackerStatus,
)
from app.models.documents import (
    ApifyRunDocument,
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    EventDocument,
    JobDocument,
    ProductDocument,
    ProductSnapshotDocument,
    RawImportBatchDocument,
)
from app.services.shared import (
    build_competitor_summaries,
    build_category_snapshot_with_rank_comparison,
    category_doc_to_model,
    competitor_detail_to_list_model,
    competitor_doc_to_model,
    event_doc_to_model,
    generate_tracker_code,
    product_doc_to_model,
    snapshot_doc_to_model,
    timeframe_bounds,
)


_logger = get_logger("app.services.tracker_management")


class TrackerManagementService:
    async def _hydrate_competitor_tracker_detail(
        self, workspace_id: str, document: CompetitorTrackerDocument
    ) -> CompetitorTrackerDetail:
        tracker = competitor_doc_to_model(document).model_copy(deep=True)
        tracked_asins = [ta.asin for ta in tracker.tracked_asins]
        if not tracked_asins:
            return tracker

        t0 = time.monotonic()
        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id,
            ProductDocument.marketplace == tracker.marketplace,
            In(ProductDocument.asin, tracked_asins),
        ).to_list()

        reference_date = utc_now().date()
        recent_from_date = reference_date - timedelta(days=6)
        event_docs = (
            await EventDocument.find(
                EventDocument.workspace_id == workspace_id,
                EventDocument.marketplace == tracker.marketplace,
                In(EventDocument.asin, tracked_asins),
            )
            .sort((EventDocument.snapshot_date, ASCENDING))
            .to_list()
        )
        t_db = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        refreshed_tracked_products = build_competitor_summaries(
            marketplace=tracker.marketplace,
            tracked_asins=tracker.tracked_asins,
            products=[product_doc_to_model(doc) for doc in product_docs],
            events=[event_doc_to_model(doc) for doc in event_docs],
            existing=tracker.tracked_products,
            reference_date=reference_date,
            recent_from_date=recent_from_date,
        )
        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "_hydrate_competitor_tracker_detail timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "tracker_code": tracker.tracker_code,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "product_count": len(product_docs),
                    "event_count": len(event_docs),
                    "tracked_asin_count": len(tracked_asins),
                }
            },
        )
        if refreshed_tracked_products != tracker.tracked_products:
            tracker.tracked_products = refreshed_tracked_products
            document.tracked_products = refreshed_tracked_products
            await document.save()
        return tracker

    async def list_category_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CategoryTrackerListResponse:
        t0 = time.monotonic()
        all_docs = await CategoryTrackerDocument.find(
            CategoryTrackerDocument.workspace_id == workspace_id
        ).to_list()
        t_db = (time.monotonic() - t0) * 1000
        t1 = time.monotonic()
        items = sorted(
            [category_doc_to_model(doc) for doc in all_docs],
            key=lambda tracker: tracker.updated_at,
            reverse=True,
        )
        paged_items, total = paginate(items, page, page_size)
        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "list_category_trackers timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "total_docs": len(all_docs),
                }
            },
        )
        return CategoryTrackerListResponse(
            items=paged_items,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def create_category_tracker(
        self, workspace_id: str, payload: CategoryTrackerCreateRequest
    ) -> CategoryTracker:
        existing_docs = await CategoryTrackerDocument.find(
            CategoryTrackerDocument.workspace_id == workspace_id
        ).to_list()
        existing_trackers = [category_doc_to_model(doc) for doc in existing_docs]
        for tracker in existing_trackers:
            same_marketplace = tracker.marketplace == payload.marketplace
            same_browse_node_id = (
                payload.scope.browse_node_id
                and tracker.scope.browse_node_id == payload.scope.browse_node_id
            )
            same_browse_node_url = (
                payload.scope.browse_node_url
                and tracker.scope.browse_node_url == payload.scope.browse_node_url
            )
            if same_marketplace and (same_browse_node_id or same_browse_node_url):
                raise ConflictError(
                    "A category tracker already exists for this marketplace and scope."
                )

        now = utc_now()
        tracker = CategoryTracker(
            tracker_code=generate_tracker_code(
                "ct",
                payload.name,
                {item.tracker_code for item in existing_trackers},
            ),
            name=payload.name,
            marketplace=payload.marketplace,
            scope=payload.scope,
            tracking_config=CategoryTrackingConfig(
                top_n=50,
                top10_alert_enabled=payload.tracking_config.top10_alert_enabled,
            ),
            schedule=TrackerSchedule.model_validate(payload.schedule.model_dump()),
            status=TrackerStatus.ACTIVE,
            stats=payload_tracking_stats(),
            latest_snapshot_summary=None,
            created_at=now,
            updated_at=now,
        )
        await CategoryTrackerDocument(
            workspace_id=workspace_id,
            **tracker.model_dump(mode="python"),
        ).insert()
        return tracker

    async def get_category_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CategoryTracker:
        document = await CategoryTrackerDocument.find_one(
            CategoryTrackerDocument.workspace_id == workspace_id,
            CategoryTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Category tracker not found.")
        return category_doc_to_model(document)

    async def update_category_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CategoryTrackerUpdateRequest,
    ) -> CategoryTracker:
        document = await CategoryTrackerDocument.find_one(
            CategoryTrackerDocument.workspace_id == workspace_id,
            CategoryTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Category tracker not found.")

        tracker = category_doc_to_model(document).model_copy(deep=True)
        if payload.name is not None:
            tracker.name = payload.name
        if payload.schedule is not None:
            tracker.schedule = TrackerSchedule.model_validate(
                payload.schedule.model_dump()
            )
        if payload.status is not None:
            tracker.status = payload.status
        if payload.tracking_config is not None and (
            "top10_alert_enabled" in payload.tracking_config.model_fields_set
        ):
            tracker.tracking_config.top10_alert_enabled = (
                payload.tracking_config.top10_alert_enabled
            )
        tracker.updated_at = utc_now()

        for key, value in tracker.model_dump(mode="python").items():
            setattr(document, key, value)
        await document.save()
        return tracker

    async def get_latest_category_snapshot(
        self,
        workspace_id: str,
        tracker_code: str,
        timeframe: Timeframe = Timeframe.WEEKLY,
    ) -> CategorySnapshot:
        documents = await CategorySnapshotDocument.find(
            CategorySnapshotDocument.workspace_id == workspace_id,
            CategorySnapshotDocument.tracker_code == tracker_code,
        ).to_list()
        if not documents:
            raise NotFoundError("Category snapshot not found.")
        document = max(documents, key=lambda item: item.captured_at)
        latest = snapshot_doc_to_model(document)
        from_date, _ = timeframe_bounds(timeframe, latest.snapshot_date)
        comparison_documents = [
            item
            for item in documents
            if from_date <= item.snapshot_date < latest.snapshot_date
        ]
        if not comparison_documents:
            return latest

        comparison_document = min(
            comparison_documents, key=lambda item: (item.snapshot_date, item.captured_at)
        )
        comparison = snapshot_doc_to_model(comparison_document)
        return build_category_snapshot_with_rank_comparison(latest, comparison)

    async def list_competitor_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CompetitorTrackerListResponse:
        t0 = time.monotonic()
        all_docs = await CompetitorTrackerDocument.find(
            CompetitorTrackerDocument.workspace_id == workspace_id
        ).to_list()
        t_db = (time.monotonic() - t0) * 1000
        t1 = time.monotonic()
        items = sorted(
            [competitor_detail_to_list_model(competitor_doc_to_model(doc)) for doc in all_docs],
            key=lambda tracker: tracker.updated_at,
            reverse=True,
        )
        paged_items, total = paginate(items, page, page_size)
        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "list_competitor_trackers timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "total_docs": len(all_docs),
                }
            },
        )
        return CompetitorTrackerListResponse(
            items=paged_items,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def create_competitor_tracker(
        self, workspace_id: str, payload: CompetitorTrackerCreateRequest
    ) -> CompetitorTrackerDetail:
        existing_docs = await CompetitorTrackerDocument.find(
            CompetitorTrackerDocument.workspace_id == workspace_id
        ).to_list()
        existing_trackers = [competitor_doc_to_model(doc) for doc in existing_docs]

        now = utc_now()
        tracked_asins = [
            TrackedAsin(asin=item.asin, enabled=item.enabled, added_at=now)
            for item in payload.tracked_asins
        ]
        asin_list = [item.asin for item in tracked_asins]
        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id,
            In(ProductDocument.asin, asin_list),
        ).to_list() if asin_list else []
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            In(EventDocument.asin, asin_list),
        ).to_list() if asin_list else []
        tracker = CompetitorTrackerDetail(
            tracker_code=generate_tracker_code(
                "cmp",
                payload.name,
                {item.tracker_code for item in existing_trackers},
            ),
            name=payload.name,
            marketplace=payload.marketplace,
            tracked_asins=tracked_asins,
            track_fields=payload.track_fields,
            schedule=TrackerSchedule.model_validate(payload.schedule.model_dump()),
            status=TrackerStatus.ACTIVE,
            stats=payload_competitor_stats(len(tracked_asins)),
            tracked_products=build_competitor_summaries(
                marketplace=payload.marketplace,
                tracked_asins=tracked_asins,
                products=[product_doc_to_model(doc) for doc in product_docs],
                events=[event_doc_to_model(doc) for doc in event_docs],
            ),
            created_at=now,
            updated_at=now,
        )
        await CompetitorTrackerDocument(
            workspace_id=workspace_id,
            **tracker.model_dump(mode="python"),
        ).insert()
        return tracker

    async def get_competitor_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CompetitorTrackerDetail:
        document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Competitor tracker not found.")
        return await self._hydrate_competitor_tracker_detail(workspace_id, document)

    async def update_competitor_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CompetitorTrackerUpdateRequest,
    ) -> CompetitorTrackerDetail:
        document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Competitor tracker not found.")

        tracker = competitor_doc_to_model(document).model_copy(deep=True)
        if payload.name is not None:
            tracker.name = payload.name
        if payload.track_fields is not None:
            tracker.track_fields = payload.track_fields
        if payload.schedule is not None:
            tracker.schedule = TrackerSchedule.model_validate(
                payload.schedule.model_dump()
            )
        if payload.status is not None:
            tracker.status = payload.status

        asin_list = [ta.asin for ta in tracker.tracked_asins]
        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id,
            In(ProductDocument.asin, asin_list),
        ).to_list() if asin_list else []
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            In(EventDocument.asin, asin_list),
        ).to_list() if asin_list else []
        tracker.tracked_products = build_competitor_summaries(
            marketplace=tracker.marketplace,
            tracked_asins=tracker.tracked_asins,
            products=[product_doc_to_model(doc) for doc in product_docs],
            events=[event_doc_to_model(doc) for doc in event_docs],
            existing=tracker.tracked_products,
        )
        tracker.updated_at = utc_now()

        for key, value in tracker.model_dump(mode="python").items():
            setattr(document, key, value)
        await document.save()
        return tracker

    async def replace_tracked_asins(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: TrackedAsinReplacementRequest,
    ) -> CompetitorTrackerDetail:
        document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Competitor tracker not found.")

        tracker = competitor_doc_to_model(document).model_copy(deep=True)
        now = utc_now()
        existing_by_asin = {item.asin: item for item in tracker.tracked_asins}
        tracker.tracked_asins = [
            TrackedAsin(
                asin=item.asin,
                enabled=item.enabled,
                added_at=existing_by_asin[item.asin].added_at
                if item.asin in existing_by_asin
                else now,
            )
            for item in payload.tracked_asins
        ]
        tracker.stats.tracked_asin_count = len(tracker.tracked_asins)
        tracker.updated_at = now

        asin_list = [ta.asin for ta in tracker.tracked_asins]
        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id,
            In(ProductDocument.asin, asin_list),
        ).to_list() if asin_list else []
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            In(EventDocument.asin, asin_list),
        ).to_list() if asin_list else []
        tracker.tracked_products = build_competitor_summaries(
            marketplace=tracker.marketplace,
            tracked_asins=tracker.tracked_asins,
            products=[product_doc_to_model(doc) for doc in product_docs],
            events=[event_doc_to_model(doc) for doc in event_docs],
            existing=tracker.tracked_products,
        )

        for key, value in tracker.model_dump(mode="python").items():
            setattr(document, key, value)
        await document.save()
        return tracker

    async def _delete_tracker_data(
        self, workspace_id: str, tracker_code: str, tracker_type: str
    ) -> None:
        job_docs = await JobDocument.find(
            JobDocument.workspace_id == workspace_id,
            JobDocument.tracker_code == tracker_code,
        ).to_list()
        job_codes = [j.job_code for j in job_docs]
        if job_codes:
            await JobDocument.find(
                JobDocument.workspace_id == workspace_id,
                JobDocument.tracker_code == tracker_code,
            ).delete()

            await ApifyRunDocument.find(
                ApifyRunDocument.workspace_id == workspace_id,
                In(ApifyRunDocument.tracking_job_code, job_codes),
            ).delete()

            await RawImportBatchDocument.find(
                RawImportBatchDocument.workspace_id == workspace_id,
                In(RawImportBatchDocument.tracking_job_code, job_codes),
            ).delete()

        await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            EventDocument.tracker_code == tracker_code,
        ).delete()

        if tracker_type == "CATEGORY":
            await CategorySnapshotDocument.find(
                CategorySnapshotDocument.workspace_id == workspace_id,
                CategorySnapshotDocument.tracker_code == tracker_code,
            ).delete()

        product_snapshot_docs = await ProductSnapshotDocument.find(
            ProductSnapshotDocument.workspace_id == workspace_id,
            ProductSnapshotDocument.tracker_refs.tracker_code == tracker_code,
        ).to_list()
        for doc in product_snapshot_docs:
            doc.tracker_refs = [
                ref for ref in doc.tracker_refs
                if ref.tracker_code != tracker_code
            ]
            await doc.save()

        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id,
            ProductDocument.tracker_refs.tracker_code == tracker_code,
        ).to_list()
        for doc in product_docs:
            doc.tracker_refs = [
                ref for ref in doc.tracker_refs
                if ref.tracker_code != tracker_code
            ]
            await doc.save()

    async def delete_category_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> None:
        document = await CategoryTrackerDocument.find_one(
            CategoryTrackerDocument.workspace_id == workspace_id,
            CategoryTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Category tracker not found.")

        await self._delete_tracker_data(workspace_id, tracker_code, "CATEGORY")
        await document.delete()

    async def delete_competitor_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> None:
        document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Competitor tracker not found.")

        await self._delete_tracker_data(workspace_id, tracker_code, "COMPETITOR")
        await document.delete()


def payload_tracking_stats() -> CategoryTrackerStats:
    return CategoryTrackerStats(snapshot_count=0)


def payload_competitor_stats(tracked_asin_count: int) -> CompetitorTrackerStats:
    return CompetitorTrackerStats(
        tracked_asin_count=tracked_asin_count,
        last_job_at=None,
        last_success_at=None,
    )
