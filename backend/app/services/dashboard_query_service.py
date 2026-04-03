from __future__ import annotations

from datetime import date

from app.core.errors import BadRequestError, NotFoundError
from app.core.utils import paginate
from app.models.api import (
    DashboardOverview,
    EventListResponse,
    EventType,
    JobStatus,
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
    product_doc_to_model,
    sort_events,
    within_range,
)


class DashboardQueryService:
    async def get_dashboard_overview(
        self, workspace_id: str, timeframe: Timeframe
    ) -> DashboardOverview:
        category_docs = await CategoryTrackerDocument.find(
            CategoryTrackerDocument.workspace_id == workspace_id
        ).to_list()
        competitor_docs = await CompetitorTrackerDocument.find(
            CompetitorTrackerDocument.workspace_id == workspace_id
        ).to_list()
        event_docs = await EventDocument.find(EventDocument.workspace_id == workspace_id).to_list()
        return build_dashboard_overview(
            timeframe=timeframe,
            category_trackers=[category_doc_to_model(doc) for doc in category_docs],
            competitor_trackers=[competitor_doc_to_model(doc) for doc in competitor_docs],
            events=[event_doc_to_model(doc) for doc in event_docs],
        )

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
    ) -> ProductTimelineResponse:
        if from_date and to_date and from_date > to_date:
            raise BadRequestError("from_date must be less than or equal to to_date.")

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

        return build_product_timeline_response(
            marketplace=marketplace,
            asin=asin,
            snapshot_documents=snapshot_documents,
            event_documents=event_documents,
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
        )

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

        items = sort_events(
            [
                event_doc_to_model(document)
                for document in await EventDocument.find(
                    EventDocument.workspace_id == workspace_id
                ).to_list()
                if within_range(document.snapshot_date, from_date, to_date)
                and (tracker_type is None or document.tracker_type == tracker_type)
                and (tracker_code is None or document.tracker_code == tracker_code)
                and (marketplace is None or document.marketplace == marketplace)
                and (asin is None or document.asin == asin)
                and (event_type is None or document.event_type == event_type)
                and (severity is None or document.severity == severity)
            ]
        )
        paged_items, total = paginate(items, page, page_size)
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
        items = sorted(
            [
                digest_doc_to_model(document)
                for document in await WeeklyDigestDocument.find(
                    WeeklyDigestDocument.workspace_id == workspace_id
                ).to_list()
                if week_start is None or document.week_start == week_start
            ],
            key=lambda digest: digest.week_start,
            reverse=True,
        )
        paged_items, total = paginate(items, page, page_size)
        return WeeklyDigestListResponse(
            items=paged_items,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_weekly_digest(self, workspace_id: str, digest_code: str) -> WeeklyDigest:
        document = await WeeklyDigestDocument.find_one(
            WeeklyDigestDocument.workspace_id == workspace_id,
            WeeklyDigestDocument.digest_code == digest_code,
        )
        if document is None:
            raise NotFoundError("Weekly digest not found.")
        return digest_doc_to_model(document)
