from __future__ import annotations

import time
from datetime import date

from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import get_logger

from app.models.api import (
    DashboardOverview,
    EventListResponse,
    EventType,
    ProductDetail,
    ProductTimelineResponse,
    Severity,
    Timeframe,
    TrackerType,
    WeeklyDigest,
    WeeklyDigestListResponse,
)
from app.models.documents import (
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    EventDocument,
    KeywordTrackerDocument,
    ProductDocument,
    ProductSnapshotDocument,
    WeeklyDigestDocument,
)
from app.services.shared import (
    build_dashboard_overview,
    build_product_timeline_response,
    category_doc_to_model,
    competitor_doc_to_model,
    digest_doc_to_model,
    event_doc_to_model,
    keyword_doc_to_model,
    product_doc_to_model,
)

_logger = get_logger("app.services.dashboard_query")


class DashboardQueryService:
    async def get_dashboard_overview(
        self, workspace_id: str, timeframe: Timeframe
    ) -> DashboardOverview:
        t0 = time.monotonic()
        category_docs = await CategoryTrackerDocument.find(
            CategoryTrackerDocument.workspace_id == workspace_id
        ).to_list()
        competitor_docs = await CompetitorTrackerDocument.find(
            CompetitorTrackerDocument.workspace_id == workspace_id
        ).to_list()
        keyword_docs = await KeywordTrackerDocument.find(
            KeywordTrackerDocument.workspace_id == workspace_id
        ).to_list()

        # Compute timeframe bounds to limit event query
        from app.services.shared import timeframe_bounds
        from datetime import date as _date

        reference_date = _date.today()
        from_date, to_date = timeframe_bounds(timeframe, reference_date)

        event_docs = (
            await EventDocument.find(
                EventDocument.workspace_id == workspace_id,
                EventDocument.snapshot_date >= from_date,
                EventDocument.snapshot_date <= to_date,
            )
            .sort(("event_time", -1))
            .limit(1000)
            .to_list()
        )
        t_db = (time.monotonic() - t0) * 1000
        t1 = time.monotonic()
        result = build_dashboard_overview(
            timeframe=timeframe,
            category_trackers=[category_doc_to_model(doc) for doc in category_docs],
            competitor_trackers=[
                competitor_doc_to_model(doc) for doc in competitor_docs
            ],
            keyword_trackers=[keyword_doc_to_model(doc) for doc in keyword_docs],
            events=[event_doc_to_model(doc) for doc in event_docs],
        )
        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "get_dashboard_overview timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "category_count": len(category_docs),
                    "competitor_count": len(competitor_docs),
                    "keyword_count": len(keyword_docs),
                    "event_count": len(event_docs),
                }
            },
        )
        return result

    async def get_product_detail(
        self, workspace_id: str, marketplace: str, asin: str
    ) -> ProductDetail:
        document = await ProductDocument.find_one(
            ProductDocument.workspace_id == workspace_id,
            ProductDocument.marketplace == marketplace,
            ProductDocument.asin == asin,
        )
        if document is None:
            raise NotFoundError("Product not found.")
        return product_doc_to_model(document)

    async def get_product_timeline(
        self,
        workspace_id: str,
        marketplace: str,
        asin: str,
        from_date: date | None,
        to_date: date | None,
        granularity: Timeframe,
        tracker_code: str | None = None,
    ) -> ProductTimelineResponse:
        if from_date and to_date and from_date > to_date:
            raise BadRequestError("from_date must be less than or equal to to_date.")

        t0 = time.monotonic()
        snapshot_documents = await ProductSnapshotDocument.find(
            ProductSnapshotDocument.workspace_id == workspace_id,
            ProductSnapshotDocument.marketplace == marketplace,
            ProductSnapshotDocument.asin == asin,
        ).to_list()
        event_documents = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            EventDocument.marketplace == marketplace,
            EventDocument.asin == asin,
        ).to_list()
        t_db = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        if tracker_code is not None:
            snapshot_documents = [
                document
                for document in snapshot_documents
                if any(
                    ref.tracker_code == tracker_code for ref in document.tracker_refs
                )
            ]
            event_documents = [
                document
                for document in event_documents
                if document.tracker_code == tracker_code
            ]

        result = build_product_timeline_response(
            marketplace=marketplace,
            asin=asin,
            snapshot_documents=snapshot_documents,
            event_documents=event_documents,
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
        )
        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "get_product_timeline timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "marketplace": marketplace,
                    "asin": asin,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "snapshot_count": len(snapshot_documents),
                    "event_count": len(event_documents),
                }
            },
        )
        return result

    async def list_events(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        from_date: date | None = None,
        to_date: date | None = None,
        tracker_type: TrackerType | None = None,
        tracker_code: str | None = None,
        marketplace: str | None = None,
        asin: str | None = None,
        event_type: EventType | None = None,
        severity: Severity | None = None,
    ) -> EventListResponse:
        if from_date and to_date and from_date > to_date:
            raise BadRequestError("from_date must be less than or equal to to_date.")

        t0 = time.monotonic()
        query_filters = [EventDocument.workspace_id == workspace_id]
        if from_date is not None:
            query_filters.append(EventDocument.snapshot_date >= from_date)
        if to_date is not None:
            query_filters.append(EventDocument.snapshot_date <= to_date)
        if tracker_type is not None:
            query_filters.append(EventDocument.tracker_type == tracker_type.value)
        if tracker_code is not None:
            query_filters.append(EventDocument.tracker_code == tracker_code)
        if marketplace is not None:
            query_filters.append(EventDocument.marketplace == marketplace)
        if asin is not None:
            query_filters.append(EventDocument.asin == asin)
        if event_type is not None:
            query_filters.append(EventDocument.event_type == event_type.value)
        if severity is not None:
            query_filters.append(EventDocument.severity == severity.value)

        query = EventDocument.find(*query_filters)
        total = await query.count()
        page_docs = await (
            query.sort(("event_time", -1))
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        t_db = (time.monotonic() - t0) * 1000
        t1 = time.monotonic()
        paged_items = [event_doc_to_model(doc) for doc in page_docs]
        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "list_events timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "total": total,
                    "page_docs": len(page_docs),
                }
            },
        )
        return EventListResponse(
            items=paged_items,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def list_weekly_digests(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        week_start: date | None = None,
    ) -> WeeklyDigestListResponse:
        query_filters = [WeeklyDigestDocument.workspace_id == workspace_id]
        if week_start is not None:
            #hung 25/06/2026: fix reports filter to include digests from the selected week_start onward.
            query_filters.append(WeeklyDigestDocument.week_start >= week_start)
        query = WeeklyDigestDocument.find(*query_filters)
        total = await query.count()
        page_docs = await (
            query.sort(("week_start", -1))
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        items = [digest_doc_to_model(doc) for doc in page_docs]
        return WeeklyDigestListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_weekly_digest(
        self, workspace_id: str, digest_code: str
    ) -> WeeklyDigest:
        document = await WeeklyDigestDocument.find_one(
            WeeklyDigestDocument.workspace_id == workspace_id,
            WeeklyDigestDocument.digest_code == digest_code,
        )
        if document is None:
            raise NotFoundError("Weekly digest not found.")
        return digest_doc_to_model(document)
