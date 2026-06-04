from __future__ import annotations

import hashlib
from datetime import date

from pymongo.errors import DuplicateKeyError

from app.core.logging import correlation_context, get_logger
from app.core.metrics import get_metrics
from app.models.api import (
    AvailabilityStatus,
    EventChangeState,
    EventDelta,
    EventPayload,
    EventType,
    Severity,
    TrackerType,
)
from app.models.documents import EventDocument, JobDocument
from app.services.diff_service import DiffCandidate, DiffService

_CATEGORY_MOVEMENT_TYPES = {
    EventType.NEW_ENTRANT_TOP50,
    EventType.RETURNING_TOP50,
    EventType.EXIT_TOP50,
    EventType.ENTER_TOP10,
    EventType.EXIT_TOP10,
}

logger = get_logger(__name__)
metrics = get_metrics()


class EventEngine:
    def __init__(self, diff_service: DiffService) -> None:
        self.diff_service = diff_service

    async def generate_events_for_job(
        self,
        *,
        workspace_id: str,
        job_document: JobDocument,
    ) -> int:
        tracker_type = TrackerType(job_document.tracker_type)
        candidates = await self.diff_service.build_candidates(
            workspace_id=workspace_id,
            tracker_type=tracker_type,
            tracker_code=job_document.tracker_code,
            snapshot_date=job_document.snapshot_date,
        )
        if not candidates:
            metrics.increment(
                "event_candidates_total",
                0.0,
                workspace_id=workspace_id,
                tracker_code=job_document.tracker_code,
                job_code=job_document.job_code,
            )
            return 0

        metrics.increment(
            "event_candidates_total",
            float(len(candidates)),
            workspace_id=workspace_id,
            tracker_code=job_document.tracker_code,
            job_code=job_document.job_code,
        )

        event_documents = [
            self._build_event_document(
                workspace_id=workspace_id,
                job_document=job_document,
                candidate=candidate,
            )
            for candidate in candidates
        ]
        dedupe_keys = [
            event.dedupe_key
            for event in event_documents
            if event.dedupe_key is not None
        ]
        if dedupe_keys:
            existing = await EventDocument.find(
                {
                    "workspace_id": workspace_id,
                    "dedupe_key": {"$in": dedupe_keys},
                }
            ).to_list()
            existing_dedupe = {
                event.dedupe_key for event in existing if event.dedupe_key
            }
            deduped_count = len(existing_dedupe)
            event_documents = [
                event
                for event in event_documents
                if event.dedupe_key and event.dedupe_key not in existing_dedupe
            ]
            metrics.increment(
                "events_deduped_total",
                float(deduped_count),
                workspace_id=workspace_id,
                tracker_code=job_document.tracker_code,
                job_code=job_document.job_code,
            )

        if not event_documents:
            logger.info(
                "Skipped event insert because all candidates were deduplicated.",
                extra={
                    "context": correlation_context(
                        workspace_id=workspace_id,
                        tracker_code=job_document.tracker_code,
                        job_code=job_document.job_code,
                        snapshot_date=job_document.snapshot_date,
                    )
                },
            )
            return 0

        try:
            await EventDocument.insert_many(event_documents)
        except DuplicateKeyError:
            logger.warning(
                "Duplicate event detected during insert, retrying with dedup.",
                extra={
                    "context": correlation_context(
                        workspace_id=workspace_id,
                        tracker_code=job_document.tracker_code,
                        job_code=job_document.job_code,
                        snapshot_date=job_document.snapshot_date,
                    )
                },
            )
            existing = await EventDocument.find(
                {
                    "workspace_id": workspace_id,
                    "dedupe_key": {"$in": dedupe_keys},
                }
            ).to_list()
            existing_dedupe = {
                event.dedupe_key for event in existing if event.dedupe_key
            }
            event_documents = [
                event
                for event in event_documents
                if event.dedupe_key and event.dedupe_key not in existing_dedupe
            ]
            if event_documents:
                await EventDocument.insert_many(event_documents)
        metrics.increment(
            "events_emitted_total",
            float(len(event_documents)),
            workspace_id=workspace_id,
            tracker_code=job_document.tracker_code,
            job_code=job_document.job_code,
        )
        logger.info(
            "Generated tracking events from snapshot diffs.",
            extra={
                "context": correlation_context(
                    workspace_id=workspace_id,
                    tracker_code=job_document.tracker_code,
                    job_code=job_document.job_code,
                    snapshot_date=job_document.snapshot_date,
                    emitted_count=len(event_documents),
                )
            },
        )
        return len(event_documents)

    def _build_event_document(
        self,
        *,
        workspace_id: str,
        job_document: JobDocument,
        candidate: DiffCandidate,
    ) -> EventDocument:
        payload = self._build_payload(candidate)
        severity = self._severity_for(candidate)
        title = self._title_for(candidate)
        summary = self._summary_for(candidate)
        dedupe_key = self._build_dedupe_key(candidate)
        event_code = self._build_event_code(
            workspace_id=workspace_id,
            snapshot_date=candidate.snapshot_date,
            dedupe_key=dedupe_key,
        )

        return EventDocument(
            workspace_id=workspace_id,
            event_code=event_code,
            tracker_type=candidate.tracker_type,
            tracker_code=candidate.tracker_code,
            marketplace=candidate.marketplace,
            asin=candidate.asin,
            event_type=candidate.event_type,
            event_time=candidate.event_time,
            snapshot_date=candidate.snapshot_date,
            severity=severity,
            title=title,
            summary=summary,
            payload=payload,
            job_code=job_document.job_code,
            dedupe_key=dedupe_key,
        )

    def _build_payload(self, candidate: DiffCandidate) -> EventPayload:
        metadata = candidate.metadata
        event_type = candidate.event_type

        if event_type == EventType.NEW_ENTRANT_TOP50:
            return EventPayload(
                rank_today=metadata.get("rank_today"),
                first_seen_in_tracker=True,
            )

        if event_type == EventType.RETURNING_TOP50:
            return EventPayload(
                rank_today=metadata.get("rank_today"),
                last_seen_date=metadata.get("last_seen_date"),
                days_absent=metadata.get("days_absent"),
            )

        if event_type == EventType.EXIT_TOP50:
            return EventPayload(
                previous_rank=metadata.get("previous_rank"),
                present_today=False,
                previous=EventChangeState(
                    title=metadata.get("previous_title"),
                    brand=metadata.get("previous_brand"),
                    main_image_url=metadata.get("previous_image_url"),
                    price_current=metadata.get("previous_price_current"),
                    price_original=metadata.get("previous_price_original"),
                    coupon_text=metadata.get("previous_coupon_text"),
                    deal_info=metadata.get("previous_deal_info"),
                    rating_value=metadata.get("previous_rating_value"),
                    review_count=metadata.get("previous_review_count"),
                    availability_status=metadata.get("previous_availability_status"),
                    buy_box_status=metadata.get("previous_buy_box_status"),
                ),
            )

        if event_type == EventType.ENTER_TOP10:
            return EventPayload(
                previous_rank=metadata.get("previous_rank"),
                current_rank=metadata.get("current_rank"),
            )

        if event_type == EventType.EXIT_TOP10:
            return EventPayload(
                previous_rank=metadata.get("previous_rank"),
                current_rank=metadata.get("current_rank"),
                previous=EventChangeState(
                    title=metadata.get("previous_title"),
                    brand=metadata.get("previous_brand"),
                    main_image_url=metadata.get("previous_image_url"),
                    price_current=metadata.get("previous_price_current"),
                    price_original=metadata.get("previous_price_original"),
                    coupon_text=metadata.get("previous_coupon_text"),
                    deal_info=metadata.get("previous_deal_info"),
                    rating_value=metadata.get("previous_rating_value"),
                    review_count=metadata.get("previous_review_count"),
                    availability_status=metadata.get("previous_availability_status"),
                    buy_box_status=metadata.get("previous_buy_box_status"),
                ),
                current=EventChangeState(
                    title=metadata.get("current_title"),
                    brand=metadata.get("current_brand"),
                    main_image_url=metadata.get("current_image_url"),
                    price_current=metadata.get("current_price_current"),
                    price_original=metadata.get("current_price_original"),
                    coupon_text=metadata.get("current_coupon_text"),
                    deal_info=metadata.get("current_deal_info"),
                    availability_status=metadata.get("current_availability_status"),
                    buy_box_status=metadata.get("current_buy_box_status"),
                ),
            )

        if event_type == EventType.PRICE_CHANGED:
            return EventPayload(
                previous=EventChangeState(
                    price_current=metadata.get("previous_price_current"),
                    price_original=metadata.get("previous_price_original"),
                ),
                current=EventChangeState(
                    price_current=metadata.get("current_price_current"),
                    price_original=metadata.get("current_price_original"),
                ),
                delta=EventDelta(
                    price_current_abs=metadata.get("delta_abs"),
                    price_current_pct=metadata.get("delta_pct"),
                ),
            )

        if event_type == EventType.PROMOTION_CHANGED:
            return EventPayload(
                previous=EventChangeState(
                    coupon_text=metadata.get("previous_coupon_text"),
                ),
                current=EventChangeState(
                    coupon_text=metadata.get("current_coupon_text"),
                ),
            )

        if event_type == EventType.TITLE_CHANGED:
            return EventPayload(
                previous=EventChangeState(title=metadata.get("previous_title")),
                current=EventChangeState(title=metadata.get("current_title")),
            )

        if event_type == EventType.MAIN_IMAGE_CHANGED:
            return EventPayload(
                previous=EventChangeState(
                    main_image_url=metadata.get("previous_main_image_url"),
                ),
                current=EventChangeState(
                    main_image_url=metadata.get("current_main_image_url"),
                ),
            )

        if event_type == EventType.VARIATIONS_ADDED:
            return EventPayload(
                previous=EventChangeState(
                    variation_count=metadata.get("previous_variation_count"),
                ),
                current=EventChangeState(
                    variation_count=metadata.get("current_variation_count"),
                ),
            )

        if event_type == EventType.AVAILABILITY_CHANGED:
            return EventPayload(
                previous=EventChangeState(
                    availability_status=metadata.get("previous_availability_status"),
                ),
                current=EventChangeState(
                    availability_status=metadata.get("current_availability_status"),
                ),
            )

        if event_type == EventType.BUY_BOX_CHANGED:
            return EventPayload(
                previous=EventChangeState(
                    buy_box_status=metadata.get("previous_buy_box_status"),
                    buy_box_seller_name=metadata.get("previous_buy_box_seller_name"),
                ),
                current=EventChangeState(
                    buy_box_status=metadata.get("current_buy_box_status"),
                    buy_box_seller_name=metadata.get("current_buy_box_seller_name"),
                ),
            )

        return EventPayload()

    def _severity_for(self, candidate: DiffCandidate) -> Severity:
        if candidate.event_type == EventType.ENTER_TOP10:
            return Severity.HIGH
        if candidate.event_type in {
            EventType.NEW_ENTRANT_TOP50,
            EventType.RETURNING_TOP50,
            EventType.EXIT_TOP10,
            EventType.PRICE_CHANGED,
            EventType.TITLE_CHANGED,
            EventType.MAIN_IMAGE_CHANGED,
            EventType.BUY_BOX_CHANGED,
        }:
            return Severity.MEDIUM
        if candidate.event_type == EventType.AVAILABILITY_CHANGED:
            current_status = candidate.metadata.get("current_availability_status")
            if current_status == AvailabilityStatus.OUT_OF_STOCK:
                return Severity.HIGH
            return Severity.MEDIUM
        return Severity.LOW

    def _title_for(self, candidate: DiffCandidate) -> str:
        metadata = candidate.metadata
        event_type = candidate.event_type
        if event_type == EventType.NEW_ENTRANT_TOP50:
            return "Product entered Top 50 for the first time"
        if event_type == EventType.RETURNING_TOP50:
            return "Product returned to Top 50"
        if event_type == EventType.EXIT_TOP50:
            return "Product exited Top 50"
        if event_type == EventType.ENTER_TOP10:
            return "Product entered Top 10"
        if event_type == EventType.EXIT_TOP10:
            return "Product exited Top 10"
        if event_type == EventType.PRICE_CHANGED:
            previous_price = metadata.get("previous_price_current")
            current_price = metadata.get("current_price_current")
            return f"Price changed from {previous_price} to {current_price}"
        if event_type == EventType.PROMOTION_CHANGED:
            return "Promotion state changed"
        if event_type == EventType.TITLE_CHANGED:
            return "Product title changed"
        if event_type == EventType.MAIN_IMAGE_CHANGED:
            return "Main image changed"
        if event_type == EventType.VARIATIONS_ADDED:
            return "New product variations detected"
        if event_type == EventType.AVAILABILITY_CHANGED:
            return "Availability status changed"
        if event_type == EventType.BUY_BOX_CHANGED:
            return "Buy Box state changed"
        return event_type.value

    def _summary_for(self, candidate: DiffCandidate) -> str:
        metadata = candidate.metadata
        event_type = candidate.event_type
        if event_type == EventType.NEW_ENTRANT_TOP50:
            return (
                f"ASIN {candidate.asin} appeared at rank {metadata.get('rank_today')} "
                "for the first time in this tracker."
            )
        if event_type == EventType.RETURNING_TOP50:
            return (
                f"ASIN {candidate.asin} returned at rank {metadata.get('rank_today')} "
                f"after {metadata.get('days_absent')} day(s) absent."
            )
        if event_type == EventType.EXIT_TOP50:
            return (
                f"ASIN {candidate.asin} was previously at rank {metadata.get('previous_rank')} "
                "and is no longer present in Top 50."
            )
        if event_type in {EventType.ENTER_TOP10, EventType.EXIT_TOP10}:
            return (
                f"ASIN {candidate.asin} moved from rank {metadata.get('previous_rank')} "
                f"to {metadata.get('current_rank')}."
            )
        if event_type == EventType.PRICE_CHANGED:
            return (
                f"Price changed from {metadata.get('previous_price_current')} "
                f"to {metadata.get('current_price_current')}."
            )
        if event_type == EventType.PROMOTION_CHANGED:
            return "Detected a change in promotion or coupon text."
        if event_type == EventType.TITLE_CHANGED:
            return "Detected a material change in normalized product title."
        if event_type == EventType.MAIN_IMAGE_CHANGED:
            return "Detected a change in product main image."
        if event_type == EventType.VARIATIONS_ADDED:
            return (
                f"Variation count increased from {metadata.get('previous_variation_count')} "
                f"to {metadata.get('current_variation_count')}."
            )
        if event_type == EventType.AVAILABILITY_CHANGED:
            return (
                f"Availability moved from {metadata.get('previous_availability_status')} "
                f"to {metadata.get('current_availability_status')}."
            )
        if event_type == EventType.BUY_BOX_CHANGED:
            return "Detected a change in Buy Box status or seller."
        return "Detected event from snapshot comparison."

    def _build_dedupe_key(self, candidate: DiffCandidate) -> str:
        scope = (
            candidate.tracker_code
            if candidate.event_type in _CATEGORY_MOVEMENT_TYPES
            else candidate.marketplace
        )
        return (
            f"{candidate.event_type.value}|{scope}|{candidate.asin}|"
            f"{candidate.snapshot_date.isoformat()}"
        )

    def _build_event_code(
        self,
        *,
        workspace_id: str,
        snapshot_date: date,
        dedupe_key: str,
    ) -> str:
        digest = hashlib.sha1(
            f"{workspace_id}|{dedupe_key}".encode("utf-8")
        ).hexdigest()[:10]
        return f"evt_{snapshot_date.strftime('%Y%m%d')}_{digest}"
