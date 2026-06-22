from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

from app.core.errors import BadRequestError, NotFoundError
from app.core.utils import slugify, utc_now
from app.models.api import (
    CategoryHighlight,
    CategorySnapshot,
    CategorySnapshotProduct,
    CategoryTracker,
    CompetitorHighlight,
    CompetitorTracker,
    CompetitorTrackerDetail,
    DashboardOverview,
    DashboardOverviewSummary,
    Event,
    EventType,
    Job,
    KeywordHighlight,
    KeywordSnapshot,
    KeywordTracker,
    ProductDetail,
    ProductSnapshot,
    ProductTimelinePoint,
    ProductTimelineResponse,
    ProductTimelineSummary,
    Severity,
    Threat,
    Timeframe,
    TrackedAsin,
    TrackedProductSummary,
    TrackerRef,
    TrackerStatus,
    TrackerType,
    WeeklyDigest,
)
from app.models.documents import (
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    EventDocument,
    JobDocument,
    KeywordSnapshotDocument,
    KeywordTrackerDocument,
    ProductDocument,
    ProductSnapshotDocument,
    WeeklyDigestDocument,
)

LISTING_EVENT_TYPES = {
    EventType.TITLE_CHANGED,
    EventType.MAIN_IMAGE_CHANGED,
    EventType.VARIATIONS_ADDED,
}
SEVERITY_WEIGHT = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
}
THREAT_SCORE_WEIGHT = {
    EventType.AVAILABILITY_CHANGED: 10,
    EventType.ENTER_TOP10: 8,
    EventType.PRICE_CHANGED: 5,
    EventType.NEW_ENTRANT_TOP50: 4,
    EventType.PROMOTION_CHANGED: 3,
    EventType.VARIATIONS_ADDED: 2,
    EventType.RETURNING_TOP50: 4,
    EventType.EXIT_TOP10: 3,
    EventType.EXIT_TOP50: 2,
    EventType.TITLE_CHANGED: 2,
    EventType.MAIN_IMAGE_CHANGED: 2,
    EventType.BUY_BOX_CHANGED: 2,
}


def category_doc_to_model(document: CategoryTrackerDocument) -> CategoryTracker:
    return CategoryTracker.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def keyword_doc_to_model(document: KeywordTrackerDocument) -> KeywordTracker:
    return KeywordTracker.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def snapshot_doc_to_model(document: CategorySnapshotDocument) -> CategorySnapshot:
    snapshot = CategorySnapshot.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )
    deduped_products = _dedupe_category_snapshot_products(snapshot.products)
    if len(deduped_products) == len(snapshot.products):
        return snapshot

    return snapshot.model_copy(
        update={
            "products": deduped_products,
            "summary": snapshot.summary.model_copy(
                update={"asin_count": len(deduped_products)}
            ),
        }
    )


def build_category_snapshot_with_rank_comparison(
    current: CategorySnapshot, comparison: CategorySnapshot | None
) -> CategorySnapshot:
    if comparison is None:
        return current

    comparison_rank_map = {
        product.asin: product.rank_position for product in comparison.products
    }
    products: list[CategorySnapshotProduct] = []
    for product in current.products:
        previous_rank = comparison_rank_map.get(product.asin)
        if previous_rank is None:
            products.append(
                product.model_copy(
                    update={
                        "previous_rank_position": None,
                        "rank_delta": None,
                        "rank_trend": "NEW",
                        "comparison_snapshot_date": comparison.snapshot_date,
                    }
                )
            )
            continue

        rank_delta = previous_rank - product.rank_position
        trend = "STABLE"
        if rank_delta > 0:
            trend = "UP"
        elif rank_delta < 0:
            trend = "DOWN"

        products.append(
            product.model_copy(
                update={
                    "previous_rank_position": previous_rank,
                    "rank_delta": rank_delta,
                    "rank_trend": trend,
                    "comparison_snapshot_date": comparison.snapshot_date,
                }
            )
        )

    return current.model_copy(update={"products": products})


def keyword_snapshot_doc_to_model(document: KeywordSnapshotDocument) -> KeywordSnapshot:
    snapshot = KeywordSnapshot.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )
    deduped_products = _dedupe_category_snapshot_products(snapshot.products)
    if len(deduped_products) == len(snapshot.products):
        return snapshot

    return snapshot.model_copy(
        update={
            "products": deduped_products,
            "summary": snapshot.summary.model_copy(
                update={"asin_count": len(deduped_products)}
            ),
        }
    )


def build_keyword_snapshot_with_rank_comparison(
    current: KeywordSnapshot, comparison: KeywordSnapshot | None
) -> KeywordSnapshot:
    if comparison is None:
        return current

    comparison_rank_map = {
        product.asin: product.rank_position for product in comparison.products
    }
    products: list[CategorySnapshotProduct] = []
    for product in current.products:
        previous_rank = comparison_rank_map.get(product.asin)
        if previous_rank is None:
            products.append(
                product.model_copy(
                    update={
                        "previous_rank_position": None,
                        "rank_delta": None,
                        "rank_trend": "NEW",
                        "comparison_snapshot_date": comparison.snapshot_date,
                    }
                )
            )
            continue

        rank_delta = previous_rank - product.rank_position
        trend = "STABLE"
        if rank_delta > 0:
            trend = "UP"
        elif rank_delta < 0:
            trend = "DOWN"

        products.append(
            product.model_copy(
                update={
                    "previous_rank_position": previous_rank,
                    "rank_delta": rank_delta,
                    "rank_trend": trend,
                    "comparison_snapshot_date": comparison.snapshot_date,
                }
            )
        )

    return current.model_copy(update={"products": products})


def competitor_doc_to_model(
    document: CompetitorTrackerDocument,
) -> CompetitorTrackerDetail:
    return CompetitorTrackerDetail.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def event_doc_to_model(document: EventDocument) -> Event:
    return Event.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def competitor_detail_to_list_model(
    tracker: CompetitorTrackerDetail,
) -> CompetitorTracker:
    return CompetitorTracker.model_validate(
        tracker.model_dump(exclude={"tracked_products"})
    )


def product_doc_to_model(document: ProductDocument) -> ProductDetail:
    return ProductDetail.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def job_doc_to_model(document: JobDocument) -> Job:
    return Job.model_validate(
        document.model_dump(
            exclude={"id", "workspace_id", "pool_code", "current_pool_index"},
            mode="python",
        )
    )


def digest_doc_to_model(document: WeeklyDigestDocument) -> WeeklyDigest:
    return WeeklyDigest.model_validate(
        document.model_dump(exclude={"id", "workspace_id"}, mode="python")
    )


def product_snapshot_doc_to_model(document: ProductSnapshotDocument) -> ProductSnapshot:
    return ProductSnapshot.model_validate(
        document.model_dump(exclude={"id", "workspace_id", "created_at"}, mode="python")
    )


def sort_events(events: Iterable[Event]) -> list[Event]:
    return sorted(
        events,
        key=lambda item: (SEVERITY_WEIGHT[item.severity], -item.event_time.timestamp()),
    )


def timeframe_bounds(timeframe: Timeframe, reference_date: date) -> tuple[date, date]:
    if timeframe == Timeframe.DAILY:
        return reference_date, reference_date
    if timeframe == Timeframe.WEEKLY:
        return reference_date - timedelta(days=6), reference_date
    return reference_date - timedelta(days=29), reference_date


def within_range(
    value: date, from_date: date | None = None, to_date: date | None = None
) -> bool:
    if from_date and value < from_date:
        return False
    if to_date and value > to_date:
        return False
    return True


def aggregate_timeline_points(
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


def build_timeline_summary(events: list[Event]) -> ProductTimelineSummary:
    return ProductTimelineSummary(
        price_change_count=sum(
            1 for event in events if event.event_type == EventType.PRICE_CHANGED
        ),
        availability_change_count=sum(
            1 for event in events if event.event_type == EventType.AVAILABILITY_CHANGED
        ),
        listing_change_count=sum(
            1 for event in events if event.event_type in LISTING_EVENT_TYPES
        ),
        buy_box_change_count=sum(
            1 for event in events if event.event_type == EventType.BUY_BOX_CHANGED
        ),
    )


def build_tracker_name_map(
    category_trackers: Iterable[CategoryTracker],
    competitor_trackers: Iterable[CompetitorTrackerDetail],
    keyword_trackers: Iterable[KeywordTracker] | None = None,
) -> dict[str, str]:
    tracker_name_map = {
        tracker.tracker_code: tracker.name for tracker in category_trackers
    }
    tracker_name_map.update(
        {tracker.tracker_code: tracker.name for tracker in competitor_trackers}
    )
    if keyword_trackers:
        tracker_name_map.update(
            {tracker.tracker_code: tracker.name for tracker in keyword_trackers}
        )
    return tracker_name_map


def build_top_threats(
    events: list[Event],
    tracker_name_map: dict[str, str],
) -> list[Threat]:
    grouped: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in events:
        grouped[(event.marketplace, event.asin)].append(event)

    threats: list[tuple[int, Threat]] = []
    for (marketplace, asin), group in grouped.items():
        unique_event_types: list[EventType] = list(
            dict.fromkeys(event.event_type for event in group)
        )
        if len(unique_event_types) < 2 and not any(
            event.severity == Severity.HIGH for event in group
        ):
            continue

        threat_score = sum(
            THREAT_SCORE_WEIGHT.get(event.event_type, 1) for event in group
        )

        tracker_refs = list(
            {
                (event.tracker_type, event.tracker_code): TrackerRef(
                    tracker_type=event.tracker_type,
                    tracker_code=event.tracker_code,
                    tracker_name=tracker_name_map.get(
                        event.tracker_code, event.tracker_code
                    ),
                )
                for event in group
            }.values()
        )
        reason = (
            f"Observed {', '.join(event_type.value for event_type in unique_event_types)} "
            "during the selected timeframe."
        )
        threats.append(
            (
                threat_score,
                Threat(
                    asin=asin,
                    marketplace=marketplace,
                    reason=reason,
                    event_types=unique_event_types,
                    tracker_refs=tracker_refs,
                ),
            )
        )

    threats.sort(key=lambda x: x[0], reverse=True)
    return [threat for _, threat in threats[:5]]


def _dedupe_category_snapshot_products(
    products: list[CategorySnapshotProduct],
) -> list[CategorySnapshotProduct]:
    deduped_products: list[CategorySnapshotProduct] = []
    seen_asins: set[str] = set()

    for product in products:
        if product.asin in seen_asins:
            continue
        seen_asins.add(product.asin)
        deduped_products.append(
            product.model_copy(update={"rank_position": len(deduped_products) + 1})
        )

    return deduped_products


def build_dashboard_overview(
    *,
    timeframe: Timeframe,
    category_trackers: list[CategoryTracker],
    competitor_trackers: list[CompetitorTrackerDetail],
    keyword_trackers: list[KeywordTracker] | None = None,
    events: list[Event],
) -> DashboardOverview:
    reference_date = max(
        (event.snapshot_date for event in events), default=utc_now().date()
    )
    from_date, to_date = timeframe_bounds(timeframe, reference_date)
    filtered_events = [
        event
        for event in events
        if within_range(event.snapshot_date, from_date, to_date)
    ]
    sorted_events = sort_events(filtered_events)
    tracker_name_map = build_tracker_name_map(
        category_trackers, competitor_trackers, keyword_trackers
    )

    active_category_trackers = [
        tracker
        for tracker in category_trackers
        if tracker.status == TrackerStatus.ACTIVE
    ]
    active_competitor_trackers = [
        tracker
        for tracker in competitor_trackers
        if tracker.status == TrackerStatus.ACTIVE
    ]
    active_keyword_trackers = [
        tracker
        for tracker in (keyword_trackers or [])
        if tracker.status == TrackerStatus.ACTIVE
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
    keyword_event_groups: dict[str, list[Event]] = defaultdict(list)
    for event in filtered_events:
        if event.tracker_type == TrackerType.CATEGORY:
            category_event_groups[event.tracker_code].append(event)
        elif event.tracker_type == TrackerType.KEYWORD:
            keyword_event_groups[event.tracker_code].append(event)
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

    keyword_highlights = [
        KeywordHighlight(
            tracker_code=tracker.tracker_code,
            tracker_name=tracker.name,
            new_entrant_count=sum(
                1
                for event in keyword_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.NEW_ENTRANT_TOP50
            ),
            exit_count=sum(
                1
                for event in keyword_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.EXIT_TOP50
            ),
            top10_enter_count=sum(
                1
                for event in keyword_event_groups.get(tracker.tracker_code, [])
                if event.event_type == EventType.ENTER_TOP10
            ),
        )
        for tracker in active_keyword_trackers
    ]

    return DashboardOverview(
        timeframe=timeframe,
        generated_at=utc_now(),
        summary=DashboardOverviewSummary(
            active_category_tracker_count=len(active_category_trackers),
            active_competitor_tracker_count=len(active_competitor_trackers),
            active_keyword_tracker_count=len(active_keyword_trackers),
            tracked_product_count=tracked_product_count,
            new_entrant_count=sum(
                1
                for event in filtered_events
                if event.event_type == EventType.NEW_ENTRANT_TOP50
            ),
            returning_count=sum(
                1
                for event in filtered_events
                if event.event_type == EventType.RETURNING_TOP50
            ),
            top10_enter_count=sum(
                1
                for event in filtered_events
                if event.event_type == EventType.ENTER_TOP10
            ),
            price_change_count=sum(
                1
                for event in filtered_events
                if event.event_type == EventType.PRICE_CHANGED
            ),
            listing_change_count=sum(
                1
                for event in filtered_events
                if event.event_type in LISTING_EVENT_TYPES
            ),
        ),
        top_events=sorted_events[:5],
        top_threats=build_top_threats(sorted_events, tracker_name_map),
        category_highlights=category_highlights,
        competitor_highlights=competitor_highlights,
        keyword_highlights=keyword_highlights,
    )


def generate_tracker_code(prefix: str, name: str, existing_codes: set[str]) -> str:
    base_code = f"{prefix}_{slugify(name)}"
    candidate = base_code
    counter = 2
    while candidate in existing_codes:
        candidate = f"{base_code}_{counter}"
        counter += 1
    return candidate


def generate_job_code(
    tracker_type: TrackerType, snapshot_date: date, existing_codes: set[str]
) -> str:
    prefix_map = {
        TrackerType.CATEGORY: "cat",
        TrackerType.COMPETITOR: "cmp",
        TrackerType.KEYWORD: "kw",
    }
    tracker_prefix = prefix_map.get(tracker_type, "unk")
    base_code = f"job_{tracker_prefix}_{snapshot_date.strftime('%Y%m%d')}"
    counter = 1
    while True:
        candidate = f"{base_code}_{counter:03d}"
        if candidate not in existing_codes:
            return candidate
        counter += 1


def build_competitor_summaries(
    *,
    marketplace: str,
    tracked_asins: list[TrackedAsin],
    products: list[ProductDetail],
    events: list[Event],
    existing: list[TrackedProductSummary] | None = None,
    reference_date: date | None = None,
    recent_from_date: date | None = None,
    latest_snapshots: dict[str, ProductSnapshotDocument] | None = None,
) -> list[TrackedProductSummary]:
    product_map = {product.asin: product for product in products}
    existing_map = {item.asin: item for item in existing or []}
    snapshots = latest_snapshots or {}

    if reference_date is None:
        reference_date = max(
            (event.snapshot_date for event in events), default=utc_now().date()
        )
    if recent_from_date is None:
        recent_from_date = reference_date - timedelta(days=6)

    summaries: list[TrackedProductSummary] = []
    for tracked_asin in tracked_asins:
        product = product_map.get(tracked_asin.asin)
        snapshot = snapshots.get(tracked_asin.asin)
        recent_event_count = sum(
            1
            for event in events
            if event.asin == tracked_asin.asin
            and event.marketplace == marketplace
            and within_range(event.snapshot_date, recent_from_date, reference_date)
        )
        if product:
            summaries.append(
                TrackedProductSummary(
                    asin=tracked_asin.asin,
                    brand=product.brand,
                    title=product.title_latest,
                    product_url=product.product_url,
                    image_url=product.main_image_url_latest,
                    current_bsr_position=snapshot.bsr_position if snapshot else product.current_state.bsr_position,
                    current_price=snapshot.price_current if snapshot else product.current_state.price_current,
                    currency=snapshot.currency if snapshot else product.current_state.currency,
                    availability_status=snapshot.availability_status if snapshot else product.current_state.availability_status,
                    last_snapshot_date=snapshot.snapshot_date if snapshot else product.current_state.last_snapshot_date,
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


def product_snapshot_to_timeline_point(
    snapshot: ProductSnapshot,
) -> ProductTimelinePoint:
    return ProductTimelinePoint(
        snapshot_date=snapshot.snapshot_date,
        bsr_position=snapshot.bsr_position,
        price_current=snapshot.price_current,
        price_original=snapshot.price_original,
        coupon_text=snapshot.coupon_text,
        availability_status=snapshot.availability_status,
        buy_box_status=snapshot.buy_box_status,
        rating_value=snapshot.rating_value,
        review_count=snapshot.review_count,
        title_hash=snapshot.title_hash,
        main_image_hash=snapshot.main_image_hash,
        variation_count=snapshot.variation_count,
    )


def build_product_timeline_response(
    *,
    marketplace: str,
    asin: str,
    snapshot_documents: list[ProductSnapshotDocument],
    event_documents: list[EventDocument],
    from_date: date | None,
    to_date: date | None,
    granularity: Timeframe,
) -> ProductTimelineResponse:
    if from_date and to_date and from_date > to_date:
        raise BadRequestError("from_date must be less than or equal to to_date.")

    if not snapshot_documents:
        raise NotFoundError("Product timeline not found.")

    snapshots = [
        product_snapshot_doc_to_model(document)
        for document in sorted(snapshot_documents, key=lambda item: item.snapshot_date)
    ]
    filtered_points = [
        product_snapshot_to_timeline_point(snapshot)
        for snapshot in snapshots
        if within_range(snapshot.snapshot_date, from_date, to_date)
    ]
    filtered_events = [
        event_doc_to_model(document)
        for document in sorted(event_documents, key=lambda item: item.event_time)
        if within_range(document.snapshot_date, from_date, to_date)
    ]
    if not filtered_points and (from_date or to_date):
        raise NotFoundError("No timeline data found for the requested range.")

    effective_from = from_date or (
        filtered_points[0].snapshot_date
        if filtered_points
        else snapshots[0].snapshot_date
    )
    effective_to = to_date or (
        filtered_points[-1].snapshot_date
        if filtered_points
        else snapshots[-1].snapshot_date
    )

    return ProductTimelineResponse(
        marketplace=marketplace,
        asin=asin,
        from_date=effective_from,
        to_date=effective_to,
        granularity=granularity,
        points=aggregate_timeline_points(filtered_points, granularity),
        events=filtered_events,
        summary=build_timeline_summary(filtered_events),
    )


# Backward-compatible names re-exported by store.py and imported in existing tests.
_aggregate_timeline_points = aggregate_timeline_points
_build_competitor_summaries = build_competitor_summaries
_build_dashboard_overview = build_dashboard_overview
_build_timeline_summary = build_timeline_summary
_build_top_threats = build_top_threats
_event_doc_to_model = event_doc_to_model
_generate_job_code = generate_job_code
_generate_tracker_code = generate_tracker_code
_sort_events = sort_events
_within_range = within_range
_keyword_doc_to_model = keyword_doc_to_model
_keyword_snapshot_doc_to_model = keyword_snapshot_doc_to_model
