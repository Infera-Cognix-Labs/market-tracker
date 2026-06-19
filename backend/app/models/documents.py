from __future__ import annotations

from datetime import date, datetime

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

from app.models.api import (
    CategoryScope,
    CategorySnapshotProduct,
    CategorySnapshotSummary,
    CategoryTrackerLatestSnapshotSummary,
    CategoryTrackerStats,
    CategoryTrackingConfig,
    CompetitorTrackerStats,
    CompetitorTrackFields,
    DealInfo,
    EventPayload,
    ExternalRunSummary,
    JobError,
    JobRunStrategy,
    JobSummary,
    KeywordScope,
    KeywordSnapshotSummary,
    KeywordTrackerLatestSnapshotSummary,
    KeywordTrackerStats,
    KeywordTrackingConfig,
    ProductCurrentState,
    Threat,
    TrackedAsin,
    TrackedProductSummary,
    TrackerRef,
    TrackerSchedule,
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
    top_n: int = 60
    products: list[CategorySnapshotProduct] = Field(default_factory=list)
    summary: CategorySnapshotSummary
    source_refs: dict[str, object] | None = None

    class Settings:
        name = "category_snapshots"
        indexes = [
            IndexModel(
                [("workspace_id", 1), ("tracker_code", 1), ("snapshot_date", -1)],
                unique=True,
            ),
        ]


class KeywordTrackerDocument(WorkspaceDocument):
    tracker_code: str
    name: str
    marketplace: str
    scope: KeywordScope
    tracking_config: KeywordTrackingConfig
    schedule: TrackerSchedule
    status: str
    stats: KeywordTrackerStats
    latest_snapshot_summary: KeywordTrackerLatestSnapshotSummary | None = None
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "keyword_trackers"
        indexes = [
            IndexModel([("workspace_id", 1), ("tracker_code", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("status", 1)]),
        ]


class KeywordSnapshotDocument(WorkspaceDocument):
    tracker_code: str
    marketplace: str
    keyword: str
    snapshot_date: date
    captured_at: datetime
    top_n: int = 50
    products: list[CategorySnapshotProduct] = Field(default_factory=list)
    summary: KeywordSnapshotSummary
    source_refs: dict[str, object] | None = None

    class Settings:
        name = "keyword_snapshots"
        indexes = [
            IndexModel(
                [("workspace_id", 1), ("tracker_code", 1), ("snapshot_date", -1)],
                unique=True,
            ),
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
            IndexModel([("workspace_id", 1), ("severity", 1), ("event_time", -1)]),
            IndexModel([("workspace_id", 1), ("event_type", 1), ("event_time", -1)]),
            IndexModel(
                [
                    ("workspace_id", 1),
                    ("marketplace", 1),
                    ("asin", 1),
                    ("snapshot_date", -1),
                ]
            ),
            IndexModel(
                [
                    ("workspace_id", 1),
                    ("tracker_code", 1),
                    ("snapshot_date", -1),
                    ("event_type", 1),
                ]
            ),
            IndexModel(
                [("workspace_id", 1), ("dedupe_key", 1)],
                unique=True,
                partialFilterExpression={"dedupe_key": {"$type": "string"}},
            ),
        ]


class NotificationRuleDocument(WorkspaceDocument):
    rule_code: str
    name: str
    enabled: bool = True
    webhook_url: str
    severities: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    tracker_type: str | None = None
    tracker_code: str | None = None
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "notification_rules"
        indexes = [
            IndexModel([("workspace_id", 1), ("rule_code", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("enabled", 1)]),
        ]


class NotificationDeliveryDocument(WorkspaceDocument):
    delivery_code: str
    rule_code: str
    event_code: str
    status: str
    attempts: int = 0
    error: str | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "notification_deliveries"
        indexes = [
            IndexModel([("workspace_id", 1), ("delivery_code", 1)], unique=True),
            IndexModel(
                [("workspace_id", 1), ("rule_code", 1), ("event_code", 1)],
                unique=True,
            ),
            IndexModel([("workspace_id", 1), ("status", 1), ("updated_at", 1)]),
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
            IndexModel(
                [("workspace_id", 1), ("marketplace", 1), ("asin", 1)], unique=True
            ),
        ]


class ProductSnapshotDocument(WorkspaceDocument):
    marketplace: str
    asin: str
    snapshot_date: date
    captured_at: datetime
    tracker_refs: list[TrackerRef]
    parent_asin: str | None = None
    brand: str
    title: str
    title_hash: str | None = None
    product_url: str
    main_image_url: str
    main_image_hash: str | None = None
    bsr_position: int | None = None
    price_current: float | None = None
    price_original: float | None = None
    currency: str | None = None
    coupon_text: str | None = None
    availability_status: str
    buy_box_status: str
    buy_box_seller_name: str | None = None
    rating_value: float | None = None
    review_count: int | None = None
    variation_count: int | None = None
    deal_info: DealInfo | None = None
    source_refs: dict[str, object] | None = None
    created_at: datetime

    class Settings:
        name = "product_snapshots"
        indexes = [
            IndexModel(
                [
                    ("workspace_id", 1),
                    ("marketplace", 1),
                    ("asin", 1),
                    ("snapshot_date", -1),
                ],
                unique=True,
            ),
            IndexModel([("workspace_id", 1), ("snapshot_date", -1)]),
            IndexModel(
                [
                    ("workspace_id", 1),
                    ("tracker_refs.tracker_code", 1),
                    ("snapshot_date", -1),
                ]
            ),
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
    pool_code: str | None = None
    current_pool_index: int = 0
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    class Settings:
        name = "tracking_jobs"
        indexes = [
            IndexModel([("workspace_id", 1), ("job_code", 1)], unique=True),
            IndexModel(
                [
                    ("workspace_id", 1),
                    ("tracker_type", 1),
                    ("tracker_code", 1),
                    ("snapshot_date", 1),
                ],
                unique=True,
            ),
        ]


class ApifyRunDocument(WorkspaceDocument):
    tracking_job_code: str
    provider: str
    binding_code: str | None = None
    actor_ref: str | None = None
    task_ref: str | None = None
    apify_run_id: str
    default_dataset_id: str | None = None
    run_input: dict[str, object] = Field(default_factory=dict)
    input_hash: str
    status: str
    apify_status_raw: str | None = None
    origin: str = "API"
    pool_actor_id: str | None = None
    pool_actor_name: str | None = None
    pool_index: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    webhook_received_at: datetime | None = None
    poll_count: int = 0
    error: JobError | None = None
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "apify_runs"
        indexes = [
            IndexModel([("apify_run_id", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("tracking_job_code", 1)]),
            IndexModel([("default_dataset_id", 1)]),
            IndexModel([("workspace_id", 1), ("status", 1), ("created_at", -1)]),
        ]


class RawImportBatchDocument(WorkspaceDocument):
    tracking_job_code: str
    apify_run_id: str
    dataset_id: str | None = None
    batch_no: int
    source_item_count: int
    import_status: str
    raw_items: list[dict[str, object]] = Field(default_factory=list)
    raw_storage_uri: str | None = None
    imported_at: datetime
    created_at: datetime

    class Settings:
        name = "raw_import_batches"
        indexes = [
            IndexModel([("apify_run_id", 1), ("batch_no", 1)], unique=True),
            IndexModel([("workspace_id", 1), ("tracking_job_code", 1)]),
            IndexModel([("dataset_id", 1)]),
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
    KeywordTrackerDocument,
    KeywordSnapshotDocument,
    CompetitorTrackerDocument,
    EventDocument,
    NotificationRuleDocument,
    NotificationDeliveryDocument,
    ProductDocument,
    ProductSnapshotDocument,
    JobDocument,
    ApifyRunDocument,
    RawImportBatchDocument,
    WeeklyDigestDocument,
]
