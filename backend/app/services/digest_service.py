from __future__ import annotations

from datetime import date, timedelta
from time import perf_counter

from app.core.logging import correlation_context, get_logger
from app.core.metrics import get_metrics
from app.core.utils import utc_now
from app.models.api import (
    DigestWorkerResult,
    EventType,
    TrackerRef,
    WeeklyDigestSummary,
)
from app.models.documents import (
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    EventDocument,
    WeeklyDigestDocument,
)
from app.services.shared import build_top_threats, event_doc_to_model, sort_events

logger = get_logger(__name__)
metrics = get_metrics()

_LISTING_EVENT_TYPES = {
    EventType.TITLE_CHANGED,
    EventType.MAIN_IMAGE_CHANGED,
    EventType.VARIATIONS_ADDED,
}


class DigestService:
    async def generate_weekly_digests(
        self,
        *,
        reference_date: date | None = None,
    ) -> DigestWorkerResult:
        effective_reference = reference_date or utc_now().date()
        week_end = effective_reference
        week_start = week_end - timedelta(days=6)

        workspace_ids = await self._list_workspace_ids()
        scanned_workspaces = 0
        generated_digests = 0
        skipped_digests = 0
        failed_digests = 0

        for workspace_id in workspace_ids:
            scanned_workspaces += 1
            digest_started = perf_counter()
            try:
                created = await self.generate_workspace_digest(
                    workspace_id=workspace_id,
                    week_start=week_start,
                    week_end=week_end,
                )
                digest_latency_ms = (perf_counter() - digest_started) * 1000.0
                metrics.observe(
                    "digest_generation_latency_ms",
                    digest_latency_ms,
                    workspace_id=workspace_id,
                )
                if created:
                    generated_digests += 1
                    metrics.increment(
                        "weekly_digests_generated_total",
                        1.0,
                        workspace_id=workspace_id,
                    )
                else:
                    skipped_digests += 1
                    metrics.increment(
                        "weekly_digests_skipped_total",
                        1.0,
                        workspace_id=workspace_id,
                    )
            except Exception as exc:  # pragma: no cover - behavior tested via results
                failed_digests += 1
                metrics.increment(
                    "weekly_digests_failed_total",
                    1.0,
                    workspace_id=workspace_id,
                    error_type=type(exc).__name__,
                )
                logger.exception(
                    "Failed generating weekly digest.",
                    extra={
                        "context": correlation_context(
                            workspace_id=workspace_id,
                            week_start=week_start,
                            week_end=week_end,
                            error_type=type(exc).__name__,
                        )
                    },
                )

        return DigestWorkerResult(
            scanned_workspaces=scanned_workspaces,
            generated_digests=generated_digests,
            skipped_digests=skipped_digests,
            failed_digests=failed_digests,
        )

    async def generate_workspace_digest(
        self,
        *,
        workspace_id: str,
        week_start: date,
        week_end: date,
    ) -> bool:
        iso_year, iso_week, _ = week_end.isocalendar()
        digest_code = f"wd_{iso_year}w{iso_week:02d}_{workspace_id}"

        existing = await WeeklyDigestDocument.find_one(
            {
                "workspace_id": workspace_id,
                "digest_code": digest_code,
            }
        )
        if existing is not None:
            logger.info(
                "Skipping digest generation because digest already exists.",
                extra={
                    "context": correlation_context(
                        workspace_id=workspace_id,
                        digest_code=digest_code,
                        week_start=week_start,
                        week_end=week_end,
                    )
                },
            )
            return False

        event_documents = await EventDocument.find(
            {
                "workspace_id": workspace_id,
                "snapshot_date": {
                    "$gte": week_start,
                    "$lte": week_end,
                },
            }
        ).to_list()
        events = [event_doc_to_model(document) for document in event_documents]
        if not events:
            logger.info(
                "Skipping digest generation because no events were found in range.",
                extra={
                    "context": correlation_context(
                        workspace_id=workspace_id,
                        digest_code=digest_code,
                        week_start=week_start,
                        week_end=week_end,
                    )
                },
            )
            return False

        category_trackers = await CategoryTrackerDocument.find(
            {"workspace_id": workspace_id}
        ).to_list()
        competitor_trackers = await CompetitorTrackerDocument.find(
            {"workspace_id": workspace_id}
        ).to_list()
        tracker_name_map = {
            tracker.tracker_code: tracker.name
            for tracker in [*category_trackers, *competitor_trackers]
        }

        sorted_events = sort_events(events)
        tracker_refs = list(
            {
                (event.tracker_type, event.tracker_code): TrackerRef(
                    tracker_type=event.tracker_type,
                    tracker_code=event.tracker_code,
                    tracker_name=tracker_name_map.get(
                        event.tracker_code, event.tracker_code
                    ),
                )
                for event in sorted_events
            }.values()
        )

        summary = WeeklyDigestSummary(
            new_entrant_count=sum(
                1
                for event in sorted_events
                if event.event_type == EventType.NEW_ENTRANT_TOP50
            ),
            returning_count=sum(
                1
                for event in sorted_events
                if event.event_type == EventType.RETURNING_TOP50
            ),
            top10_enter_count=sum(
                1
                for event in sorted_events
                if event.event_type == EventType.ENTER_TOP10
            ),
            price_change_count=sum(
                1
                for event in sorted_events
                if event.event_type == EventType.PRICE_CHANGED
            ),
            listing_change_count=sum(
                1 for event in sorted_events if event.event_type in _LISTING_EVENT_TYPES
            ),
        )

        digest_document = WeeklyDigestDocument(
            workspace_id=workspace_id,
            digest_code=digest_code,
            week_start=week_start,
            week_end=week_end,
            tracker_refs=tracker_refs,
            summary=summary,
            threats=build_top_threats(sorted_events, tracker_name_map),
            report_storage_uri=None,
            created_at=utc_now(),
        )
        await digest_document.insert()

        logger.info(
            "Generated weekly digest.",
            extra={
                "context": correlation_context(
                    workspace_id=workspace_id,
                    digest_code=digest_code,
                    week_start=week_start,
                    week_end=week_end,
                    tracker_ref_count=len(tracker_refs),
                    event_count=len(sorted_events),
                )
            },
        )
        return True

    async def _list_workspace_ids(self) -> list[str]:
        category_trackers = await CategoryTrackerDocument.find({}).to_list()
        competitor_trackers = await CompetitorTrackerDocument.find({}).to_list()
        event_documents = await EventDocument.find({}).to_list()
        digest_documents = await WeeklyDigestDocument.find({}).to_list()
        return sorted(
            {
                *(tracker.workspace_id for tracker in category_trackers),
                *(tracker.workspace_id for tracker in competitor_trackers),
                *(event.workspace_id for event in event_documents),
                *(digest.workspace_id for digest in digest_documents),
            }
        )
