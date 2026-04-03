from __future__ import annotations

from datetime import date, datetime

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

from app.models.api import (
    CategorySnapshot,
    CategorySnapshotProduct,
    CategorySnapshotSummary,
    CategoryTrackerLatestSnapshotSummary,
    CategoryTrackerStats,
    CategoryScope,
    CategoryTrackingConfig,
    CompetitorTrackFields,
    CompetitorTrackerStats,
    Event,
    EventPayload,
    ExternalRunSummary,
    Job,
    JobError,
    JobRunStrategy,
    JobSummary,
    ProductCurrentState,
    ProductTimelinePoint,
    ProductTimelineSummary,
    TrackerRef,
    TrackerSchedule,
    Threat,
    TrackedAsin,
    TrackedProductSummary,
    WeeklyDigestSummary,
)


class WorkspaceDocument(Document):
    workspace_id: str


class CategoryTrackerDocument(WorkspaceDocument):
    tracker_code: str
    name: str
    marketplace: str
    scope: CategoryScope
    tracking_config: CategoryTrackingConfig
    schedule: TrackerSchedule
    status: str
    stats: CategoryTrackerStats
    latest_snapshot_summary: CategoryTrackerLatestSnapshotSummary | None = None
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "category_trackers"
        indexes = [
            IndexModel([("workspace_id", 1), ("tracker_code", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("status", 1)]),
        ]


class CategorySnapshotDocument(WorkspaceDocument):
    tracker_code: str
    marketplace: str
    browse_node_id: str
    snapshot_date: date
    captured_at: datetime
    top_n: int = 50
    products: list[CategorySnapshotProduct] = Field(default_factory=list)
    summary: CategorySnapshotSummary
    source_refs: dict[str, object] | None = None

    class Settings:
        name = "category_snapshots"
        indexes = [
            IndexModel([("workspace_id", 1), ("tracker_code", 1), ("snapshot_date", -1)], unique=True),
        ]


class CompetitorTrackerDocument(WorkspaceDocument):
    tracker_code: str
    name: str
    marketplace: str
    tracked_asins: list[TrackedAsin]
    track_fields: CompetitorTrackFields
    schedule: TrackerSchedule
    status: str
    stats: CompetitorTrackerStats
    tracked_products: list[TrackedProductSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "competitor_trackers"
        indexes = [
            IndexModel([("workspace_id", 1), ("tracker_code", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("status", 1)]),
        ]


class EventDocument(WorkspaceDocument):
    event_code: str
    tracker_type: str
    tracker_code: str
    marketplace: str
    asin: str
    event_type: str
    event_time: datetime
    snapshot_date: date
    severity: str
    title: str
    summary: str
    payload: EventPayload
    job_code: str | None = None
    dedupe_key: str | None = None

    class Settings:
        name = "tracking_events"
        indexes = [
            IndexModel([("workspace_id", 1), ("event_code", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("snapshot_date", -1)]),
            IndexModel([("workspace_id", 1), ("tracker_code", 1)]),
        ]


class ProductDocument(WorkspaceDocument):
    marketplace: str
    asin: str
    parent_asin: str | None = None
    brand: str
    title_latest: str
    product_url: str
    main_image_url_latest: str
    first_seen_at: datetime
    last_seen_at: datetime
    current_state: ProductCurrentState
    tracker_refs: list[TrackerRef]

    class Settings:
        name = "products"
        indexes = [
            IndexModel([("workspace_id", 1), ("marketplace", 1), ("asin", 1)], unique=True),
        ]


class ProductTimelineDocument(WorkspaceDocument):
    marketplace: str
    asin: str
    from_date: date
    to_date: date
    granularity: str
    points: list[ProductTimelinePoint]
    events: list[Event]
    summary: ProductTimelineSummary

    class Settings:
        name = "product_timelines"
        indexes = [
            IndexModel([("workspace_id", 1), ("marketplace", 1), ("asin", 1)], unique=True),
        ]


class JobDocument(WorkspaceDocument):
    job_code: str
    tracker_type: str
    tracker_code: str
    snapshot_date: date
    trigger_mode: str
    status: str
    run_strategy: JobRunStrategy
    external_run: ExternalRunSummary | None = None
    summary: JobSummary
    error: JobError | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    class Settings:
        name = "tracking_jobs"
        indexes = [
            IndexModel([("workspace_id", 1), ("job_code", 1)], unique=True),
            IndexModel(
                [("workspace_id", 1), ("tracker_type", 1), ("tracker_code", 1), ("snapshot_date", 1)],
                unique=True,
            ),
        ]


class WeeklyDigestDocument(WorkspaceDocument):
    digest_code: str
    week_start: date
    week_end: date
    tracker_refs: list[TrackerRef]
    summary: WeeklyDigestSummary
    threats: list[Threat]
    report_storage_uri: str | None = None
    created_at: datetime

    class Settings:
        name = "weekly_digests"
        indexes = [
            IndexModel([("workspace_id", 1), ("digest_code", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("week_start", -1)]),
        ]


DOCUMENT_MODELS = [
    CategoryTrackerDocument,
    CategorySnapshotDocument,
    CompetitorTrackerDocument,
    EventDocument,
    ProductDocument,
    ProductTimelineDocument,
    JobDocument,
    WeeklyDigestDocument,
]
