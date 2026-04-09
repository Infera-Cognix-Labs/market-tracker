from __future__ import annotations

from app.core.errors import ConflictError, NotFoundError
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
    TrackedAsin,
    TrackedAsinReplacementRequest,
    TrackerSchedule,
    TrackerStatus,
)
from app.models.documents import (
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    EventDocument,
    ProductDocument,
)
from app.services.shared import (
    build_competitor_summaries,
    category_doc_to_model,
    competitor_detail_to_list_model,
    competitor_doc_to_model,
    event_doc_to_model,
    generate_tracker_code,
    product_doc_to_model,
    snapshot_doc_to_model,
)


class TrackerManagementService:
    async def list_category_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CategoryTrackerListResponse:
        items = sorted(
            [
                category_doc_to_model(doc)
                for doc in await CategoryTrackerDocument.find(
                    CategoryTrackerDocument.workspace_id == workspace_id
                ).to_list()
            ],
            key=lambda tracker: tracker.updated_at,
            reverse=True,
        )
        paged_items, total = paginate(items, page, page_size)
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
        self, workspace_id: str, tracker_code: str
    ) -> CategorySnapshot:
        documents = await CategorySnapshotDocument.find(
            CategorySnapshotDocument.workspace_id == workspace_id,
            CategorySnapshotDocument.tracker_code == tracker_code,
        ).to_list()
        if not documents:
            raise NotFoundError("Category snapshot not found.")
        document = max(documents, key=lambda item: item.captured_at)
        return snapshot_doc_to_model(document)

    async def list_competitor_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CompetitorTrackerListResponse:
        items = sorted(
            [
                competitor_detail_to_list_model(competitor_doc_to_model(doc))
                for doc in await CompetitorTrackerDocument.find(
                    CompetitorTrackerDocument.workspace_id == workspace_id
                ).to_list()
            ],
            key=lambda tracker: tracker.updated_at,
            reverse=True,
        )
        paged_items, total = paginate(items, page, page_size)
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
        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id
        ).to_list()
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id
        ).to_list()
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
        return competitor_doc_to_model(document)

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

        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id
        ).to_list()
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id
        ).to_list()
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

        product_docs = await ProductDocument.find(
            ProductDocument.workspace_id == workspace_id
        ).to_list()
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id
        ).to_list()
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


def payload_tracking_stats() -> CategoryTrackerStats:
    return CategoryTrackerStats(snapshot_count=0)


def payload_competitor_stats(tracked_asin_count: int) -> CompetitorTrackerStats:
    return CompetitorTrackerStats(
        tracked_asin_count=tracked_asin_count,
        last_job_at=None,
        last_success_at=None,
    )
