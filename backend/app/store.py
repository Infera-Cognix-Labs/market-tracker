from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from inspect import isawaitable
from typing import Iterable

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config.config import Config
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.core.utils import paginate, slugify, utc_now
from app.models.api import (
    CategoryHighlight,
    CategorySnapshot,
    CategoryTracker,
    CategoryTrackerCreateRequest,
    CategoryTrackerListResponse,
    CategoryTrackerStats,
    CategoryTrackerUpdateRequest,
    CategoryTrackingConfig,
    CompetitorHighlight,
    CompetitorTracker,
    CompetitorTrackerCreateRequest,
    CompetitorTrackerDetail,
    CompetitorTrackerListResponse,
    CompetitorTrackerStats,
    CompetitorTrackerUpdateRequest,
    DashboardOverview,
    DashboardOverviewSummary,
    Event,
    EventListResponse,
    EventType,
    Frequency,
    Job,
    JobCreateRequest,
    JobListResponse,
    JobRunStrategy,
    JobStatus,
    JobSummary,
    ProductDetail,
    ProductTimelinePoint,
    ProductTimelineResponse,
    ProductTimelineSummary,
    Provider,
    Severity,
    Threat,
    Timeframe,
    TrackerRef,
    TrackerSchedule,
    TrackerStatus,
    TrackerType,
    TrackedAsin,
    TrackedAsinReplacementRequest,
    TrackedProductSummary,
    TriggerMode,
    WeeklyDigest,
    WeeklyDigestListResponse,
)
from app.models.documents import (
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    DOCUMENT_MODELS,
    EventDocument,
    JobDocument,
    ProductDocument,
    ProductTimelineDocument,
    WeeklyDigestDocument,
)
from app.seed import SeedData

LISTING_EVENT_TYPES = {
    EventType.TITLE_CHANGED,
    EventType.MAIN_IMAGE_CHANGED,
    EventType.VARIATIONS_ADDED,
    EventType.CONTENT_CHANGED,
}
SEVERITY_WEIGHT = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
}


def _category_doc_to_model(document: CategoryTrackerDocument) -> CategoryTracker:
    return CategoryTracker.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def _snapshot_doc_to_model(document: CategorySnapshotDocument) -> CategorySnapshot:
    return CategorySnapshot.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def _competitor_doc_to_model(
    document: CompetitorTrackerDocument,
) -> CompetitorTrackerDetail:
    return CompetitorTrackerDetail.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def _event_doc_to_model(document: EventDocument) -> Event:
    return Event.model_validate(document.model_dump(exclude={"id", "workspace_id"}, mode="python"))


def _competitor_detail_to_list_model(tracker: CompetitorTrackerDetail) -> CompetitorTracker:
    return CompetitorTracker.model_validate(tracker.model_dump(exclude={"tracked_products"}))


def _product_doc_to_model(document: ProductDocument) -> ProductDetail:
    return ProductDetail.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def _timeline_doc_to_model(document: ProductTimelineDocument) -> ProductTimelineResponse:
    return ProductTimelineResponse.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def _job_doc_to_model(document: JobDocument) -> Job:
    return Job.model_validate(document.model_dump(exclude={"id", "workspace_id"}, mode="python"))


def _digest_doc_to_model(document: WeeklyDigestDocument) -> WeeklyDigest:
    return WeeklyDigest.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def _sort_events(events: Iterable[Event]) -> list[Event]:
    return sorted(
        events,
        key=lambda item: (SEVERITY_WEIGHT[item.severity], -item.event_time.timestamp()),
    )


def _timeframe_bounds(timeframe: Timeframe, reference_date: date) -> tuple[date, date]:
    if timeframe == Timeframe.DAILY:
        return reference_date, reference_date
    if timeframe == Timeframe.WEEKLY:
        return reference_date - timedelta(days=6), reference_date
    return reference_date - timedelta(days=29), reference_date


def _within_range(
    value: date, from_date: date | None = None, to_date: date | None = None
) -> bool:
    if from_date and value < from_date:
        return False
    if to_date and value > to_date:
        return False
    return True


def _aggregate_timeline_points(
    points: list[ProductTimelinePoint], granularity: Timeframe
) -> list[ProductTimelinePoint]:
    if granularity == Timeframe.DAILY:
        return points

    grouped: dict[date, ProductTimelinePoint] = {}
    for point in sorted(points, key=lambda item: item.snapshot_date):
        if granularity == Timeframe.WEEKLY:
            bucket = point.snapshot_date - timedelta(days=point.snapshot_date.weekday())
        else:
            bucket = point.snapshot_date.replace(day=1)
        grouped[bucket] = point.model_copy(update={"snapshot_date": bucket})
    return list(grouped.values())


def _build_timeline_summary(events: list[Event]) -> ProductTimelineSummary:
    return ProductTimelineSummary(
        price_change_count=sum(1 for event in events if event.event_type == EventType.PRICE_CHANGED),
        availability_change_count=sum(
            1 for event in events if event.event_type == EventType.AVAILABILITY_CHANGED
        ),
        listing_change_count=sum(1 for event in events if event.event_type in LISTING_EVENT_TYPES),
        buy_box_change_count=sum(
            1 for event in events if event.event_type == EventType.BUY_BOX_CHANGED
        ),
    )


def _build_tracker_name_map(
    category_trackers: Iterable[CategoryTracker],
    competitor_trackers: Iterable[CompetitorTrackerDetail],
) -> dict[str, str]:
    tracker_name_map = {tracker.tracker_code: tracker.name for tracker in category_trackers}
    tracker_name_map.update(
        {tracker.tracker_code: tracker.name for tracker in competitor_trackers}
    )
    return tracker_name_map


def _build_top_threats(
    events: list[Event],
    tracker_name_map: dict[str, str],
) -> list[Threat]:
    grouped: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in events:
        grouped[(event.marketplace, event.asin)].append(event)

    threats: list[Threat] = []
    for (marketplace, asin), group in grouped.items():
        unique_event_types: list[EventType] = list(dict.fromkeys(event.event_type for event in group))
        if len(unique_event_types) < 2 and not any(
            event.severity == Severity.HIGH for event in group
        ):
            continue

        tracker_refs = list(
            {
                (event.tracker_type, event.tracker_code): TrackerRef(
                    tracker_type=event.tracker_type,
                    tracker_code=event.tracker_code,
                    tracker_name=tracker_name_map.get(event.tracker_code, event.tracker_code),
                )
                for event in group
            }.values()
        )
        reason = (
            f"Observed {', '.join(event_type.value for event_type in unique_event_types)} "
            "during the selected timeframe."
        )
        threats.append(
            Threat(
                asin=asin,
                marketplace=marketplace,
                reason=reason,
                event_types=unique_event_types,
                tracker_refs=tracker_refs,
            )
        )

    return threats[:5]


def _build_dashboard_overview(
    *,
    timeframe: Timeframe,
    category_trackers: list[CategoryTracker],
    competitor_trackers: list[CompetitorTrackerDetail],
    events: list[Event],
) -> DashboardOverview:
    reference_date = max((event.snapshot_date for event in events), default=utc_now().date())
    from_date, to_date = _timeframe_bounds(timeframe, reference_date)
    filtered_events = [
        event for event in events if _within_range(event.snapshot_date, from_date, to_date)
    ]
    sorted_events = _sort_events(filtered_events)
    tracker_name_map = _build_tracker_name_map(category_trackers, competitor_trackers)

    active_category_trackers = [
        tracker for tracker in category_trackers if tracker.status == TrackerStatus.ACTIVE
    ]
    active_competitor_trackers = [
        tracker for tracker in competitor_trackers if tracker.status == TrackerStatus.ACTIVE
    ]
    tracked_product_count = len(
        {
            asin.asin
            for tracker in active_competitor_trackers
            for asin in tracker.tracked_asins
            if asin.enabled
        }
    )

    category_event_groups: dict[str, list[Event]] = defaultdict(list)
    competitor_event_groups: dict[str, list[Event]] = defaultdict(list)
    for event in filtered_events:
        if event.tracker_type == TrackerType.CATEGORY:
            category_event_groups[event.tracker_code].append(event)
        else:
            competitor_event_groups[event.tracker_code].append(event)

    category_highlights = [
        CategoryHighlight(
            tracker_code=tracker.tracker_code,
            tracker_name=tracker.name,
            new_entrant_count=sum(
                1
                for event in category_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.NEW_ENTRANT_TOP50
            ),
            exit_count=sum(
                1
                for event in category_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.EXIT_TOP50
            ),
            top10_enter_count=sum(
                1
                for event in category_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.ENTER_TOP10
            ),
        )
        for tracker in active_category_trackers
    ]

    competitor_highlights = [
        CompetitorHighlight(
            tracker_code=tracker.tracker_code,
            tracker_name=tracker.name,
            price_change_count=sum(
                1
                for event in competitor_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.PRICE_CHANGED
            ),
            availability_change_count=sum(
                1
                for event in competitor_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.AVAILABILITY_CHANGED
            ),
            listing_change_count=sum(
                1
                for event in competitor_event_groups.get(tracker.tracker_code, [])
                if event.event_type in LISTING_EVENT_TYPES
            ),
        )
        for tracker in active_competitor_trackers
    ]

    return DashboardOverview(
        timeframe=timeframe,
        generated_at=utc_now(),
        summary=DashboardOverviewSummary(
            active_category_tracker_count=len(active_category_trackers),
            active_competitor_tracker_count=len(active_competitor_trackers),
            tracked_product_count=tracked_product_count,
            new_entrant_count=sum(
                1 for event in filtered_events if event.event_type == EventType.NEW_ENTRANT_TOP50
            ),
            returning_count=sum(
                1 for event in filtered_events if event.event_type == EventType.RETURNING_TOP50
            ),
            top10_enter_count=sum(
                1 for event in filtered_events if event.event_type == EventType.ENTER_TOP10
            ),
            price_change_count=sum(
                1 for event in filtered_events if event.event_type == EventType.PRICE_CHANGED
            ),
            listing_change_count=sum(
                1 for event in filtered_events if event.event_type in LISTING_EVENT_TYPES
            ),
        ),
        top_events=sorted_events[:5],
        top_threats=_build_top_threats(sorted_events, tracker_name_map),
        category_highlights=category_highlights,
        competitor_highlights=competitor_highlights,
    )


def _generate_tracker_code(prefix: str, name: str, existing_codes: set[str]) -> str:
    base_code = f"{prefix}_{slugify(name)}"
    candidate = base_code
    counter = 2
    while candidate in existing_codes:
        candidate = f"{base_code}_{counter}"
        counter += 1
    return candidate


def _generate_job_code(
    tracker_type: TrackerType, snapshot_date: date, existing_codes: set[str]
) -> str:
    tracker_prefix = "cat" if tracker_type == TrackerType.CATEGORY else "cmp"
    base_code = f"job_{tracker_prefix}_{snapshot_date.strftime('%Y%m%d')}"
    counter = 1
    while True:
        candidate = f"{base_code}_{counter:03d}"
        if candidate not in existing_codes:
            return candidate
        counter += 1


def _build_competitor_summaries(
    *,
    marketplace: str,
    tracked_asins: list[TrackedAsin],
    products: list[ProductDetail],
    events: list[Event],
    existing: list[TrackedProductSummary] | None = None,
) -> list[TrackedProductSummary]:
    product_map = {
        product.asin: product
        for product in products
        if product.marketplace == marketplace
    }
    existing_map = {item.asin: item for item in existing or []}

    reference_date = max((event.snapshot_date for event in events), default=utc_now().date())
    recent_from_date = reference_date - timedelta(days=6)

    summaries: list[TrackedProductSummary] = []
    for tracked_asin in tracked_asins:
        product = product_map.get(tracked_asin.asin)
        recent_event_count = sum(
            1
            for event in events
            if event.asin == tracked_asin.asin
            and event.marketplace == marketplace
            and _within_range(event.snapshot_date, recent_from_date, reference_date)
        )
        if product:
            summaries.append(
                TrackedProductSummary(
                    asin=tracked_asin.asin,
                    brand=product.brand,
                    title=product.title_latest,
                    current_bsr_position=product.current_state.bsr_position,
                    current_price=product.current_state.price_current,
                    currency=product.current_state.currency,
                    availability_status=product.current_state.availability_status,
                    last_snapshot_date=product.current_state.last_snapshot_date,
                    recent_event_count_7d=recent_event_count,
                )
            )
            continue

        if tracked_asin.asin in existing_map:
            summaries.append(
                existing_map[tracked_asin.asin].model_copy(
                    update={"recent_event_count_7d": recent_event_count}
                )
            )
    return summaries


class BaseStore:
    async def close(self) -> None:
        return None

    async def seed_demo_data(self, seed_data: SeedData) -> None:
        raise NotImplementedError

    async def get_dashboard_overview(
        self, workspace_id: str, timeframe: Timeframe
    ) -> DashboardOverview:
        raise NotImplementedError

    async def list_category_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CategoryTrackerListResponse:
        raise NotImplementedError

    async def create_category_tracker(
        self, workspace_id: str, payload: CategoryTrackerCreateRequest
    ) -> CategoryTracker:
        raise NotImplementedError

    async def get_category_tracker(self, workspace_id: str, tracker_code: str) -> CategoryTracker:
        raise NotImplementedError

    async def update_category_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CategoryTrackerUpdateRequest,
    ) -> CategoryTracker:
        raise NotImplementedError

    async def get_latest_category_snapshot(
        self, workspace_id: str, tracker_code: str
    ) -> CategorySnapshot:
        raise NotImplementedError

    async def list_competitor_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CompetitorTrackerListResponse:
        raise NotImplementedError

    async def create_competitor_tracker(
        self, workspace_id: str, payload: CompetitorTrackerCreateRequest
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def get_competitor_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def update_competitor_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CompetitorTrackerUpdateRequest,
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def replace_tracked_asins(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: TrackedAsinReplacementRequest,
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def get_product_detail(
        self, workspace_id: str, marketplace: str, asin: str
    ) -> ProductDetail:
        raise NotImplementedError

    async def get_product_timeline(
        self,
        workspace_id: str,
        marketplace: str,
        asin: str,
        from_date: date | None,
        to_date: date | None,
        granularity: Timeframe,
    ) -> ProductTimelineResponse:
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

    async def create_job(self, workspace_id: str, payload: JobCreateRequest) -> Job:
        raise NotImplementedError

    async def get_job(self, workspace_id: str, job_code: str) -> Job:
        raise NotImplementedError

    async def list_weekly_digests(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        week_start: date | None = None,
    ) -> WeeklyDigestListResponse:
        raise NotImplementedError

    async def get_weekly_digest(self, workspace_id: str, digest_code: str) -> WeeklyDigest:
        raise NotImplementedError


class MongoStore(BaseStore):
    def __init__(self, client: AsyncMongoClient, database_name: str) -> None:
        self.client = client
        self.database_name = database_name

    async def close(self) -> None:
        result = self.client.close()
        if isawaitable(result):
            await result

    async def seed_demo_data(self, seed_data: SeedData) -> None:
        for tracker in seed_data.category_trackers:
            existing = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == seed_data.workspace_id,
                CategoryTrackerDocument.tracker_code == tracker.tracker_code,
            )
            payload = tracker.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await CategoryTrackerDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for snapshot in seed_data.category_snapshots:
            existing = await CategorySnapshotDocument.find_one(
                CategorySnapshotDocument.workspace_id == seed_data.workspace_id,
                CategorySnapshotDocument.tracker_code == snapshot.tracker_code,
                CategorySnapshotDocument.snapshot_date == snapshot.snapshot_date,
            )
            payload = snapshot.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await CategorySnapshotDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for tracker in seed_data.competitor_trackers:
            existing = await CompetitorTrackerDocument.find_one(
                CompetitorTrackerDocument.workspace_id == seed_data.workspace_id,
                CompetitorTrackerDocument.tracker_code == tracker.tracker_code,
            )
            payload = tracker.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await CompetitorTrackerDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for event in seed_data.events:
            existing = await EventDocument.find_one(
                EventDocument.workspace_id == seed_data.workspace_id,
                EventDocument.event_code == event.event_code,
            )
            payload = event.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await EventDocument(workspace_id=seed_data.workspace_id, **payload).insert()

        for product in seed_data.products:
            existing = await ProductDocument.find_one(
                ProductDocument.workspace_id == seed_data.workspace_id,
                ProductDocument.marketplace == product.marketplace,
                ProductDocument.asin == product.asin,
            )
            payload = product.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await ProductDocument(workspace_id=seed_data.workspace_id, **payload).insert()

        for timeline in seed_data.product_timelines:
            existing = await ProductTimelineDocument.find_one(
                ProductTimelineDocument.workspace_id == seed_data.workspace_id,
                ProductTimelineDocument.marketplace == timeline.marketplace,
                ProductTimelineDocument.asin == timeline.asin,
            )
            payload = timeline.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await ProductTimelineDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for job in seed_data.jobs:
            existing = await JobDocument.find_one(
                JobDocument.workspace_id == seed_data.workspace_id,
                JobDocument.job_code == job.job_code,
            )
            payload = job.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await JobDocument(workspace_id=seed_data.workspace_id, **payload).insert()

        for digest in seed_data.weekly_digests:
            existing = await WeeklyDigestDocument.find_one(
                WeeklyDigestDocument.workspace_id == seed_data.workspace_id,
                WeeklyDigestDocument.digest_code == digest.digest_code,
            )
            payload = digest.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await WeeklyDigestDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

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
        return _build_dashboard_overview(
            timeframe=timeframe,
            category_trackers=[_category_doc_to_model(doc) for doc in category_docs],
            competitor_trackers=[_competitor_doc_to_model(doc) for doc in competitor_docs],
            events=[_event_doc_to_model(doc) for doc in event_docs],
        )

    async def list_category_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CategoryTrackerListResponse:
        items = sorted(
            [
                _category_doc_to_model(doc)
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
        existing_trackers = [_category_doc_to_model(doc) for doc in existing_docs]
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
            tracker_code=_generate_tracker_code(
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
            stats=CategoryTrackerStats(snapshot_count=0),
            latest_snapshot_summary=None,
            created_at=now,
            updated_at=now,
        )
        await CategoryTrackerDocument(
            workspace_id=workspace_id, **tracker.model_dump(mode="python")
        ).insert()
        return tracker

    async def get_category_tracker(self, workspace_id: str, tracker_code: str) -> CategoryTracker:
        document = await CategoryTrackerDocument.find_one(
            CategoryTrackerDocument.workspace_id == workspace_id,
            CategoryTrackerDocument.tracker_code == tracker_code,
        )
        if document is None:
            raise NotFoundError("Category tracker not found.")
        return _category_doc_to_model(document)

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

        tracker = _category_doc_to_model(document).model_copy(deep=True)
        if payload.name is not None:
            tracker.name = payload.name
        if payload.schedule is not None:
            tracker.schedule = TrackerSchedule.model_validate(payload.schedule.model_dump())
        if payload.status is not None:
            tracker.status = payload.status
        if payload.tracking_config is not None and (
            "top10_alert_enabled" in payload.tracking_config.model_fields_set
        ):
            tracker.tracking_config.top10_alert_enabled = payload.tracking_config.top10_alert_enabled
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
        return _snapshot_doc_to_model(document)

    async def list_competitor_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CompetitorTrackerListResponse:
        items = sorted(
            [
                _competitor_detail_to_list_model(_competitor_doc_to_model(doc))
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
        existing_trackers = [_competitor_doc_to_model(doc) for doc in existing_docs]

        now = utc_now()
        tracked_asins = [
            TrackedAsin(asin=item.asin, enabled=item.enabled, added_at=now)
            for item in payload.tracked_asins
        ]
        product_docs = await ProductDocument.find(ProductDocument.workspace_id == workspace_id).to_list()
        event_docs = await EventDocument.find(EventDocument.workspace_id == workspace_id).to_list()
        products = [_product_doc_to_model(doc) for doc in product_docs]
        events = [_event_doc_to_model(doc) for doc in event_docs]
        tracker = CompetitorTrackerDetail(
            tracker_code=_generate_tracker_code(
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
            stats=CompetitorTrackerStats(
                tracked_asin_count=len(tracked_asins),
                last_job_at=None,
                last_success_at=None,
            ),
            tracked_products=_build_competitor_summaries(
                marketplace=payload.marketplace,
                tracked_asins=tracked_asins,
                products=products,
                events=events,
            ),
            created_at=now,
            updated_at=now,
        )
        await CompetitorTrackerDocument(
            workspace_id=workspace_id, **tracker.model_dump(mode="python")
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
        return _competitor_doc_to_model(document)

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

        tracker = _competitor_doc_to_model(document).model_copy(deep=True)
        if payload.name is not None:
            tracker.name = payload.name
        if payload.track_fields is not None:
            tracker.track_fields = payload.track_fields
        if payload.schedule is not None:
            tracker.schedule = TrackerSchedule.model_validate(payload.schedule.model_dump())
        if payload.status is not None:
            tracker.status = payload.status

        product_docs = await ProductDocument.find(ProductDocument.workspace_id == workspace_id).to_list()
        event_docs = await EventDocument.find(EventDocument.workspace_id == workspace_id).to_list()
        tracker.tracked_products = _build_competitor_summaries(
            marketplace=tracker.marketplace,
            tracked_asins=tracker.tracked_asins,
            products=[_product_doc_to_model(doc) for doc in product_docs],
            events=[_event_doc_to_model(doc) for doc in event_docs],
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

        tracker = _competitor_doc_to_model(document).model_copy(deep=True)
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

        product_docs = await ProductDocument.find(ProductDocument.workspace_id == workspace_id).to_list()
        event_docs = await EventDocument.find(EventDocument.workspace_id == workspace_id).to_list()
        tracker.tracked_products = _build_competitor_summaries(
            marketplace=tracker.marketplace,
            tracked_asins=tracker.tracked_asins,
            products=[_product_doc_to_model(doc) for doc in product_docs],
            events=[_event_doc_to_model(doc) for doc in event_docs],
            existing=tracker.tracked_products,
        )

        for key, value in tracker.model_dump(mode="python").items():
            setattr(document, key, value)
        await document.save()
        return tracker

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
        return _product_doc_to_model(document)

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

        document = await ProductTimelineDocument.find_one(
            ProductTimelineDocument.workspace_id == workspace_id,
            ProductTimelineDocument.marketplace == marketplace,
            ProductTimelineDocument.asin == asin,
        )
        if document is None:
            raise NotFoundError("Product timeline not found.")

        timeline = _timeline_doc_to_model(document)
        filtered_points = [
            point
            for point in timeline.points
            if _within_range(point.snapshot_date, from_date, to_date)
        ]
        filtered_events = [
            event
            for event in timeline.events
            if _within_range(event.snapshot_date, from_date, to_date)
        ]
        if not filtered_points and (from_date or to_date):
            raise NotFoundError("No timeline data found for the requested range.")

        effective_from = from_date or (filtered_points[0].snapshot_date if filtered_points else timeline.from_date)
        effective_to = to_date or (filtered_points[-1].snapshot_date if filtered_points else timeline.to_date)

        return ProductTimelineResponse(
            marketplace=timeline.marketplace,
            asin=timeline.asin,
            from_date=effective_from,
            to_date=effective_to,
            granularity=granularity,
            points=_aggregate_timeline_points(filtered_points, granularity),
            events=filtered_events,
            summary=_build_timeline_summary(filtered_events),
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

        items = _sort_events(
            [
                _event_doc_to_model(document)
                for document in await EventDocument.find(
                    EventDocument.workspace_id == workspace_id
                ).to_list()
                if _within_range(document.snapshot_date, from_date, to_date)
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
                _job_doc_to_model(document)
                for document in await JobDocument.find(
                    JobDocument.workspace_id == workspace_id
                ).to_list()
                if _within_range(document.snapshot_date, from_date, to_date)
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
        existing_job_models = [_job_doc_to_model(document) for document in existing_jobs]
        if any(
            item.tracker_type == payload.tracker_type
            and item.tracker_code == payload.tracker_code
            and item.snapshot_date == snapshot_date
            for item in existing_job_models
        ):
            raise ConflictError(
                f"A job already exists for tracker `{payload.tracker_code}` on {snapshot_date}."
            )

        job = Job(
            job_code=_generate_job_code(
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
                binding_code=(
                    "bind_category_top50_v1"
                    if payload.tracker_type == TrackerType.CATEGORY
                    else "bind_competitor_tracking_v1"
                ),
            ),
            summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
            created_at=utc_now(),
        )
        await JobDocument(workspace_id=workspace_id, **job.model_dump(mode="python")).insert()
        return job

    async def get_job(self, workspace_id: str, job_code: str) -> Job:
        document = await JobDocument.find_one(
            JobDocument.workspace_id == workspace_id,
            JobDocument.job_code == job_code,
        )
        if document is None:
            raise NotFoundError("Job not found.")
        return _job_doc_to_model(document)

    async def list_weekly_digests(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        week_start: date | None = None,
    ) -> WeeklyDigestListResponse:
        items = sorted(
            [
                _digest_doc_to_model(document)
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
        return _digest_doc_to_model(document)


async def build_store(settings: Config) -> BaseStore:
    client = AsyncMongoClient(settings.mongodb_config.dsn)
    await init_beanie(
        database=client[settings.mongodb_config.database],
        document_models=DOCUMENT_MODELS,
    )
    return MongoStore(client=client, database_name=settings.mongodb_config.database)
