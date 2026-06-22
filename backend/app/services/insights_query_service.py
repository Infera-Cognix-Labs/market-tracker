from __future__ import annotations

import time
from datetime import date, timedelta

from beanie.operators import In

from app.core.logging import get_logger
from app.core.utils import utc_now
from app.models.api import (
    AvailabilityStatus,
    CategoryEntrantItem,
    CategoryInsights,
    CompetitorAlertCounts,
    CompetitorInsights,
    EventType,
    KeywordInsights,
    PriceChangeItem,
    PromotionItem,
    ReturningEntrantItem,
    Timeframe,
    TrackerType,
    VariationChangeItem,
    AvailabilityChangeItem,
)
from app.models.documents import (
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    EventDocument,
    KeywordTrackerDocument,
    ProductDocument,
)
from app.services.shared import (
    event_doc_to_model,
    timeframe_bounds,
    within_range,
)

CATEGORY_ENTRANT_EVENT_TYPES = {
    EventType.ENTER_TOP10,
    EventType.NEW_ENTRANT_TOP50,
    EventType.RETURNING_TOP50,
}

COMPETITOR_CHANGE_EVENT_TYPES = {
    EventType.PRICE_CHANGED,
    EventType.PROMOTION_CHANGED,
    EventType.AVAILABILITY_CHANGED,
    EventType.VARIATIONS_ADDED,
}


_logger = get_logger("app.services.insights_query")


class InsightsQueryService:
    async def get_category_insights(
        self, workspace_id: str, timeframe: Timeframe
    ) -> CategoryInsights:
        t0 = time.monotonic()
        cutoff_date = date.today() - timedelta(days=60)
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            In(EventDocument.event_type, list(CATEGORY_ENTRANT_EVENT_TYPES)),
            EventDocument.snapshot_date >= cutoff_date,
        ).to_list()

        events = [event_doc_to_model(doc) for doc in event_docs]

        tracker_docs = await CategoryTrackerDocument.find(
            CategoryTrackerDocument.workspace_id == workspace_id
        ).to_list()
        tracker_name_map = {doc.tracker_code: doc.name for doc in tracker_docs}

        asin_keys = list({(e.marketplace, e.asin) for e in events})
        if asin_keys:
            product_docs = await ProductDocument.find(
                ProductDocument.workspace_id == workspace_id,
                In(ProductDocument.asin, [k[1] for k in asin_keys]),
            ).to_list()
        else:
            product_docs = []
        product_map = {(doc.marketplace, doc.asin): doc for doc in product_docs}
        t_db = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        new_entrant_keys = {
            (e.asin, e.tracker_code, e.snapshot_date)
            for e in events
            if e.event_type == EventType.NEW_ENTRANT_TOP50
        }

        reference_date = max(
            (event.snapshot_date for event in events), default=utc_now().date()
        )
        from_date, to_date = timeframe_bounds(timeframe, reference_date)
        filtered_events = [
            event
            for event in events
            if within_range(event.snapshot_date, from_date, to_date)
        ]

        new_top10_entrants: list[CategoryEntrantItem] = []
        first_time_entrants: list[CategoryEntrantItem] = []
        returning_entrants: list[ReturningEntrantItem] = []
        seen_top10: set[tuple[str, str]] = set()
        seen_first_time: set[tuple[str, str]] = set()

        for event in filtered_events:
            product = product_map.get((event.marketplace, event.asin))
            if not product:
                continue

            image_url = product.main_image_url_latest or ""
            title = product.title_latest
            brand = product.brand
            tracker_name = tracker_name_map.get(event.tracker_code, event.tracker_code)

            current_rank = event.payload.current_rank or 0
            previous_rank = event.payload.previous_rank
            dedup_key = (event.asin, event.tracker_code)

            if event.event_type == EventType.ENTER_TOP10:
                is_first_time = (
                    event.asin,
                    event.tracker_code,
                    event.snapshot_date,
                ) in new_entrant_keys

                item = CategoryEntrantItem(
                    asin=event.asin,
                    title=title,
                    brand=brand,
                    image_url=image_url,
                    current_rank=current_rank,
                    previous_rank=previous_rank,
                    entered_at=event.snapshot_date,
                    is_first_time_entrant=is_first_time,
                    tracker_code=event.tracker_code,
                    tracker_name=tracker_name,
                )
                if dedup_key not in seen_top10:
                    seen_top10.add(dedup_key)
                    new_top10_entrants.append(item)
                if is_first_time and dedup_key not in seen_first_time:
                    seen_first_time.add(dedup_key)
                    first_time_entrants.append(item)

            elif event.event_type == EventType.NEW_ENTRANT_TOP50:
                item = CategoryEntrantItem(
                    asin=event.asin,
                    title=title,
                    brand=brand,
                    image_url=image_url,
                    current_rank=current_rank,
                    previous_rank=previous_rank,
                    entered_at=event.snapshot_date,
                    is_first_time_entrant=True,
                    tracker_code=event.tracker_code,
                    tracker_name=tracker_name,
                )
                if dedup_key not in seen_first_time:
                    seen_first_time.add(dedup_key)
                    first_time_entrants.append(item)
                if (
                    current_rank > 0
                    and current_rank <= 10
                    and dedup_key not in seen_top10
                ):
                    seen_top10.add(dedup_key)
                    new_top10_entrants.append(item)

            elif event.event_type == EventType.RETURNING_TOP50:
                days_absent = event.payload.days_absent or 0
                returning_entrants.append(
                    ReturningEntrantItem(
                        asin=event.asin,
                        title=title,
                        brand=brand,
                        image_url=image_url,
                        current_rank=current_rank,
                        previous_rank=previous_rank,
                        entered_at=event.snapshot_date,
                        days_absent=days_absent,
                        tracker_code=event.tracker_code,
                        tracker_name=tracker_name,
                    )
                )

        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "get_category_insights timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "event_count": len(event_docs),
                    "product_count": len(product_docs),
                }
            },
        )
        return CategoryInsights(
            timeframe=timeframe,
            generated_at=utc_now(),
            new_top10_entrants=new_top10_entrants,
            first_time_entrants=first_time_entrants,
            returning_entrants=returning_entrants,
        )

    async def get_competitor_insights(
        self, workspace_id: str, timeframe: Timeframe
    ) -> CompetitorInsights:
        t0 = time.monotonic()
        cutoff_date = date.today() - timedelta(days=30)
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            EventDocument.tracker_type == TrackerType.COMPETITOR.value,
            In(EventDocument.event_type, list(COMPETITOR_CHANGE_EVENT_TYPES)),
            EventDocument.snapshot_date >= cutoff_date,
        ).to_list()

        events = [event_doc_to_model(doc) for doc in event_docs]

        competitor_docs = await CompetitorTrackerDocument.find(
            CompetitorTrackerDocument.workspace_id == workspace_id
        ).to_list()
        tracker_name_map = {doc.tracker_code: doc.name for doc in competitor_docs}

        asin_list = list({e.asin for e in events})
        if asin_list:
            product_docs = await ProductDocument.find(
                ProductDocument.workspace_id == workspace_id,
                In(ProductDocument.asin, asin_list),
            ).to_list()
        else:
            product_docs = []
        product_map = {(doc.marketplace, doc.asin): doc for doc in product_docs}
        t_db = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()

        reference_date = max(
            (event.snapshot_date for event in events), default=utc_now().date()
        )
        from_date, to_date = timeframe_bounds(timeframe, reference_date)
        filtered_events = [
            event
            for event in events
            if within_range(event.snapshot_date, from_date, to_date)
        ]

        price_changes: list[PriceChangeItem] = []
        promotions: list[PromotionItem] = []
        availability_changes: list[AvailabilityChangeItem] = []
        variation_changes: list[VariationChangeItem] = []

        for event in filtered_events:
            product = product_map.get((event.marketplace, event.asin))
            if not product:
                continue

            image_url = product.main_image_url_latest or ""
            title = product.title_latest
            brand = product.brand
            tracker_name = tracker_name_map.get(event.tracker_code, event.tracker_code)
            payload = event.payload

            if event.event_type == EventType.PRICE_CHANGED:
                current_price = (
                    payload.current.price_current if payload.current else None
                )
                previous_price = (
                    payload.previous.price_current if payload.previous else None
                )
                delta_abs = payload.delta.price_current_abs if payload.delta else None
                delta_pct = payload.delta.price_current_pct if payload.delta else None

                price_changes.append(
                    PriceChangeItem(
                        asin=event.asin,
                        title=title,
                        brand=brand,
                        image_url=image_url,
                        previous_price=previous_price,
                        current_price=current_price,
                        currency=product.current_state.currency,
                        delta_abs=delta_abs,
                        delta_pct=delta_pct,
                        changed_at=event.snapshot_date,
                        tracker_code=event.tracker_code,
                        tracker_name=tracker_name,
                    )
                )

            elif event.event_type == EventType.PROMOTION_CHANGED:
                coupon_text = payload.current.coupon_text if payload.current else None
                deal_info = product.current_state.deal_info

                promotions.append(
                    PromotionItem(
                        asin=event.asin,
                        title=title,
                        brand=brand,
                        image_url=image_url,
                        coupon_text=coupon_text,
                        deal_info=deal_info,
                        changed_at=event.snapshot_date,
                        tracker_code=event.tracker_code,
                        tracker_name=tracker_name,
                    )
                )

            elif event.event_type == EventType.AVAILABILITY_CHANGED:
                current_status = (
                    payload.current.availability_status
                    if payload.current
                    else AvailabilityStatus.UNKNOWN
                )
                previous_status = (
                    payload.previous.availability_status
                    if payload.previous
                    else AvailabilityStatus.UNKNOWN
                )

                availability_changes.append(
                    AvailabilityChangeItem(
                        asin=event.asin,
                        title=title,
                        brand=brand,
                        image_url=image_url,
                        previous_status=previous_status,
                        current_status=current_status,
                        changed_at=event.snapshot_date,
                        tracker_code=event.tracker_code,
                        tracker_name=tracker_name,
                    )
                )

            elif event.event_type == EventType.VARIATIONS_ADDED:
                current_var = (
                    payload.current.variation_count if payload.current else None
                )
                previous_var = (
                    payload.previous.variation_count if payload.previous else None
                )

                variation_changes.append(
                    VariationChangeItem(
                        asin=event.asin,
                        title=title,
                        brand=brand,
                        image_url=image_url,
                        previous_variation_count=previous_var,
                        current_variation_count=current_var,
                        changed_at=event.snapshot_date,
                        tracker_code=event.tracker_code,
                        tracker_name=tracker_name,
                    )
                )

        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "get_competitor_insights timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "event_count": len(event_docs),
                    "product_count": len(product_docs),
                }
            },
        )
        return CompetitorInsights(
            timeframe=timeframe,
            generated_at=utc_now(),
            price_changes=price_changes,
            promotions=promotions,
            availability_changes=availability_changes,
            variation_changes=variation_changes,
        )

    async def get_competitor_alerts(self, workspace_id: str) -> CompetitorAlertCounts:
        t0 = time.monotonic()
        today = utc_now().date()
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            EventDocument.tracker_type == TrackerType.COMPETITOR.value,
            In(EventDocument.event_type, list(COMPETITOR_CHANGE_EVENT_TYPES)),
            EventDocument.snapshot_date == today,
        ).to_list()

        events = [event_doc_to_model(doc) for doc in event_docs]
        t_db = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        filtered_events = events

        oos_count = 0
        price_drop_count = 0
        price_increase_count = 0
        new_promotion_count = 0
        new_variation_count = 0

        for event in filtered_events:
            if event.event_type == EventType.AVAILABILITY_CHANGED:
                current_status = (
                    event.payload.current.availability_status
                    if event.payload.current
                    else None
                )
                if current_status == AvailabilityStatus.OUT_OF_STOCK:
                    oos_count += 1

            elif event.event_type == EventType.PRICE_CHANGED:
                delta_abs = (
                    event.payload.delta.price_current_abs
                    if event.payload.delta
                    else None
                )
                if delta_abs is not None:
                    if delta_abs < 0:
                        price_drop_count += 1
                    elif delta_abs > 0:
                        price_increase_count += 1

            elif event.event_type == EventType.PROMOTION_CHANGED:
                new_promotion_count += 1

            elif event.event_type == EventType.VARIATIONS_ADDED:
                new_variation_count += 1

        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "get_competitor_alerts timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "event_count": len(event_docs),
                }
            },
        )
        return CompetitorAlertCounts(
            oos_count=oos_count,
            price_drop_count=price_drop_count,
            price_increase_count=price_increase_count,
            new_promotion_count=new_promotion_count,
            new_variation_count=new_variation_count,
        )

    async def get_keyword_insights(
        self, workspace_id: str, timeframe: Timeframe
    ) -> KeywordInsights:
        t0 = time.monotonic()
        cutoff_date = date.today() - timedelta(days=60)
        event_docs = await EventDocument.find(
            EventDocument.workspace_id == workspace_id,
            EventDocument.tracker_type == "KEYWORD",
            In(EventDocument.event_type, list(CATEGORY_ENTRANT_EVENT_TYPES)),
            EventDocument.snapshot_date >= cutoff_date,
        ).to_list()

        events = [event_doc_to_model(doc) for doc in event_docs]

        tracker_docs = await KeywordTrackerDocument.find(
            KeywordTrackerDocument.workspace_id == workspace_id
        ).to_list()
        tracker_name_map = {doc.tracker_code: doc.name for doc in tracker_docs}

        asin_keys = list({(e.marketplace, e.asin) for e in events})
        if asin_keys:
            product_docs = await ProductDocument.find(
                ProductDocument.workspace_id == workspace_id,
                In(ProductDocument.asin, [k[1] for k in asin_keys]),
            ).to_list()
        else:
            product_docs = []
        product_map = {(doc.marketplace, doc.asin): doc for doc in product_docs}
        t_db = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        new_entrant_keys = {
            (e.asin, e.tracker_code, e.snapshot_date)
            for e in events
            if e.event_type == EventType.NEW_ENTRANT_TOP50
        }

        reference_date = max(
            (event.snapshot_date for event in events), default=utc_now().date()
        )
        from_date, to_date = timeframe_bounds(timeframe, reference_date)
        filtered_events = [
            event
            for event in events
            if within_range(event.snapshot_date, from_date, to_date)
        ]

        new_top10_entrants: list[CategoryEntrantItem] = []
        first_time_entrants: list[CategoryEntrantItem] = []
        returning_entrants: list[ReturningEntrantItem] = []
        seen_top10: set[tuple[str, str]] = set()
        seen_first_time: set[tuple[str, str]] = set()

        for event in filtered_events:
            product = product_map.get((event.marketplace, event.asin))
            if not product:
                continue

            image_url = product.main_image_url_latest or ""
            title = product.title_latest
            brand = product.brand
            tracker_name = tracker_name_map.get(event.tracker_code, event.tracker_code)

            current_rank = event.payload.current_rank or 0
            previous_rank = event.payload.previous_rank
            dedup_key = (event.asin, event.tracker_code)

            if event.event_type == EventType.ENTER_TOP10:
                is_first_time = (
                    event.asin,
                    event.tracker_code,
                    event.snapshot_date,
                ) in new_entrant_keys

                item = CategoryEntrantItem(
                    asin=event.asin,
                    title=title,
                    brand=brand,
                    image_url=image_url,
                    current_rank=current_rank,
                    previous_rank=previous_rank,
                    entered_at=event.snapshot_date,
                    is_first_time_entrant=is_first_time,
                    tracker_code=event.tracker_code,
                    tracker_name=tracker_name,
                )
                if dedup_key not in seen_top10:
                    seen_top10.add(dedup_key)
                    new_top10_entrants.append(item)
                if is_first_time and dedup_key not in seen_first_time:
                    seen_first_time.add(dedup_key)
                    first_time_entrants.append(item)

            elif event.event_type == EventType.NEW_ENTRANT_TOP50:
                item = CategoryEntrantItem(
                    asin=event.asin,
                    title=title,
                    brand=brand,
                    image_url=image_url,
                    current_rank=current_rank,
                    previous_rank=previous_rank,
                    entered_at=event.snapshot_date,
                    is_first_time_entrant=True,
                    tracker_code=event.tracker_code,
                    tracker_name=tracker_name,
                )
                if dedup_key not in seen_first_time:
                    seen_first_time.add(dedup_key)
                    first_time_entrants.append(item)
                if (
                    current_rank > 0
                    and current_rank <= 10
                    and dedup_key not in seen_top10
                ):
                    seen_top10.add(dedup_key)
                    new_top10_entrants.append(item)

            elif event.event_type == EventType.RETURNING_TOP50:
                days_absent = event.payload.days_absent or 0
                returning_entrants.append(
                    ReturningEntrantItem(
                        asin=event.asin,
                        title=title,
                        brand=brand,
                        image_url=image_url,
                        current_rank=current_rank,
                        previous_rank=previous_rank,
                        entered_at=event.snapshot_date,
                        days_absent=days_absent,
                        tracker_code=event.tracker_code,
                        tracker_name=tracker_name,
                    )
                )

        t_transform = (time.monotonic() - t1) * 1000
        _logger.info(
            "get_keyword_insights timing.",
            extra={
                "context": {
                    "workspace_id": workspace_id,
                    "db_ms": round(t_db, 2),
                    "transform_ms": round(t_transform, 2),
                    "event_count": len(event_docs),
                    "product_count": len(product_docs),
                }
            },
        )
        return KeywordInsights(
            timeframe=timeframe,
            generated_at=utc_now(),
            new_top10_entrants=new_top10_entrants,
            first_time_entrants=first_time_entrants,
            returning_entrants=returning_entrants,
        )
