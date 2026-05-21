from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MarketplaceCode = Annotated[str, StringConstraints(pattern=r"^amazon_[a-z]{2}$")]
AsinCode = Annotated[str, StringConstraints(min_length=10, max_length=12)]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, str_strip_whitespace=True
    )


class FlexibleApiModel(BaseModel):
    model_config = ConfigDict(
        extra="allow", populate_by_name=True, str_strip_whitespace=True
    )


class Timeframe(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class TrackerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class TrackerType(str, Enum):
    CATEGORY = "CATEGORY"
    COMPETITOR = "COMPETITOR"


class Frequency(str, Enum):
    DAILY = "DAILY"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    DISPATCHING = "DISPATCHING"
    RUNNING_EXTERNAL = "RUNNING_EXTERNAL"
    IMPORTING = "IMPORTING"
    PROCESSING = "PROCESSING"
    DEALS_IMPORTING = "DEALS_IMPORTING"
    DEALS_PROCESSING = "DEALS_PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class TriggerMode(str, Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"
    RETRY = "RETRY"


class EventType(str, Enum):
    NEW_ENTRANT_TOP50 = "NEW_ENTRANT_TOP50"
    RETURNING_TOP50 = "RETURNING_TOP50"
    EXIT_TOP50 = "EXIT_TOP50"
    ENTER_TOP10 = "ENTER_TOP10"
    EXIT_TOP10 = "EXIT_TOP10"
    PRICE_CHANGED = "PRICE_CHANGED"
    PROMOTION_CHANGED = "PROMOTION_CHANGED"
    TITLE_CHANGED = "TITLE_CHANGED"
    MAIN_IMAGE_CHANGED = "MAIN_IMAGE_CHANGED"
    VARIATIONS_ADDED = "VARIATIONS_ADDED"
    CONTENT_CHANGED = "CONTENT_CHANGED"
    AVAILABILITY_CHANGED = "AVAILABILITY_CHANGED"
    BUY_BOX_CHANGED = "BUY_BOX_CHANGED"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AvailabilityStatus(str, Enum):
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class BuyBoxStatus(str, Enum):
    HAS_BUY_BOX = "HAS_BUY_BOX"
    NO_BUY_BOX = "NO_BUY_BOX"
    UNKNOWN = "UNKNOWN"


class DealState(str, Enum):
    AVAILABLE = "AVAILABLE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class DealType(str, Enum):
    BEST_DEAL = "BEST_DEAL"
    LIGHTNING_DEAL = "LIGHTNING_DEAL"
    DEAL_OF_THE_DAY = "DEAL_OF_THE_DAY"


class DealInfo(ApiModel):
    deal_id: str | None = None
    deal_type: str | None = None
    deal_state: str | None = None
    deal_price: float | None = None
    list_price: float | None = None
    savings_percentage: int | None = None
    savings_amount: float | None = None
    currency: str | None = None
    deal_starts_at: datetime | None = None
    deal_ends_at: datetime | None = None
    deal_badge: str | None = None
    captured_at: datetime | None = None


class Provider(str, Enum):
    APIFY = "APIFY"


class ExternalRunStatus(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    ABORTED = "ABORTED"


class ErrorResponse(ApiModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class CategoryScope(ApiModel):
    browse_node_id: str | None = None
    browse_node_url: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "CategoryScope":
        if not self.browse_node_id and not self.browse_node_url:
            raise ValueError(
                "Either browse_node_id or browse_node_url must be provided."
            )
        return self


class CategoryTrackingConfig(ApiModel):
    top_n: int = Field(default=50)
    top10_alert_enabled: bool


class CategoryTrackingConfigInput(ApiModel):
    top10_alert_enabled: bool = True


class TrackerSchedule(ApiModel):
    frequency: Frequency
    hour_utc: int = Field(ge=0, le=23)


class TrackerScheduleInput(ApiModel):
    frequency: Frequency
    hour_utc: int = Field(ge=0, le=23)


class CategoryTrackerStats(ApiModel):
    last_job_at: datetime | None = None
    last_success_at: datetime | None = None
    snapshot_count: int = 0


class CategoryTrackerLatestSnapshotSummary(ApiModel):
    snapshot_date: date
    captured_at: datetime
    top10_asins: list[AsinCode]


class CategoryTracker(ApiModel):
    tracker_code: str
    name: str
    marketplace: MarketplaceCode
    scope: CategoryScope
    tracking_config: CategoryTrackingConfig
    schedule: TrackerSchedule
    status: TrackerStatus
    stats: CategoryTrackerStats
    latest_snapshot_summary: CategoryTrackerLatestSnapshotSummary | None = None
    created_at: datetime
    updated_at: datetime


class CategoryTrackerCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    marketplace: MarketplaceCode
    scope: CategoryScope
    tracking_config: CategoryTrackingConfigInput = Field(
        default_factory=CategoryTrackingConfigInput
    )
    schedule: TrackerScheduleInput


class CategoryTrackerUpdateRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    tracking_config: CategoryTrackingConfigInput | None = None
    schedule: TrackerScheduleInput | None = None
    status: TrackerStatus | None = None


class CategorySnapshotSummary(ApiModel):
    asin_count: int
    new_entrant_count: int
    returning_count: int
    exit_count: int
    enter_top10_count: int
    exit_top10_count: int


class CategorySnapshotProduct(ApiModel):
    asin: AsinCode
    rank_position: int = Field(ge=1, le=50)
    previous_rank_position: int | None = Field(default=None, ge=1, le=50)
    rank_delta: int | None = None
    rank_trend: Literal["UP", "DOWN", "STABLE", "NEW"] | None = None
    comparison_snapshot_date: date | None = None
    title: str
    brand: str
    product_url: str
    price_current: float
    price_original: float | None = None
    currency: str
    rating_value: float
    review_count: int
    image_url: str
    availability_status: AvailabilityStatus
    buy_box_status: BuyBoxStatus
    coupon_text: str | None = None
    deal_info: DealInfo | None = None


class CategorySnapshot(ApiModel):
    tracker_code: str
    marketplace: MarketplaceCode
    browse_node_id: str
    snapshot_date: date
    captured_at: datetime
    top_n: int = 50
    products: list[CategorySnapshotProduct]
    summary: CategorySnapshotSummary
    source_refs: dict[str, Any] | None = None


class TrackedAsinWrite(ApiModel):
    asin: AsinCode
    enabled: bool = True


class TrackedAsin(TrackedAsinWrite):
    added_at: datetime


class TrackedAsinReplacementRequest(ApiModel):
    tracked_asins: list[TrackedAsinWrite] = Field(min_length=1, max_length=200)


class CompetitorTrackFields(ApiModel):
    bsr: bool
    price: bool
    buy_box: bool
    availability: bool
    promotions: bool
    title_change: bool
    main_image_change: bool
    variation_change: bool
    content_change: bool


class CompetitorTrackerStats(ApiModel):
    tracked_asin_count: int
    last_job_at: datetime | None = None
    last_success_at: datetime | None = None


class TrackedProductSummary(ApiModel):
    asin: AsinCode
    brand: str
    title: str
    current_bsr_position: int | None = None
    current_price: float | None = None
    currency: str | None = None
    availability_status: AvailabilityStatus
    last_snapshot_date: date
    recent_event_count_7d: int = 0


class CompetitorTracker(ApiModel):
    tracker_code: str
    name: str
    marketplace: MarketplaceCode
    tracked_asins: list[TrackedAsin]
    track_fields: CompetitorTrackFields
    schedule: TrackerSchedule
    status: TrackerStatus
    stats: CompetitorTrackerStats
    created_at: datetime
    updated_at: datetime


class CompetitorTrackerDetail(CompetitorTracker):
    tracked_products: list[TrackedProductSummary] = Field(default_factory=list)


class CompetitorTrackerCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    marketplace: MarketplaceCode
    tracked_asins: list[TrackedAsinWrite] = Field(min_length=1, max_length=200)
    track_fields: CompetitorTrackFields
    schedule: TrackerScheduleInput


class CompetitorTrackerUpdateRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    track_fields: CompetitorTrackFields | None = None
    schedule: TrackerScheduleInput | None = None
    status: TrackerStatus | None = None


class EventChangeState(FlexibleApiModel):
    price_current: float | None = None
    price_original: float | None = None
    coupon_text: str | None = None
    title: str | None = None
    main_image_url: str | None = None
    variation_count: int | None = None
    content_signature_hash: str | None = None
    a_plus_signature_hash: str | None = None
    availability_status: AvailabilityStatus | None = None
    buy_box_status: BuyBoxStatus | None = None
    buy_box_seller_name: str | None = None


class EventDelta(ApiModel):
    price_current_abs: float | None = None
    price_current_pct: float | None = None


class EventPayload(FlexibleApiModel):
    rank_today: int | None = None
    first_seen_in_tracker: bool | None = None
    last_seen_date: date | None = None
    days_absent: int | None = None
    previous_rank: int | None = None
    current_rank: int | None = None
    present_today: bool | None = None
    previous: EventChangeState | None = None
    current: EventChangeState | None = None
    delta: EventDelta | None = None


class Event(ApiModel):
    event_code: str
    tracker_type: TrackerType
    tracker_code: str
    marketplace: MarketplaceCode
    asin: AsinCode
    event_type: EventType
    event_time: datetime
    snapshot_date: date
    severity: Severity
    title: str
    summary: str
    payload: EventPayload
    job_code: str | None = None
    dedupe_key: str | None = None


class ProductCurrentState(ApiModel):
    price_current: float | None = None
    price_original: float | None = None
    currency: str | None = None
    bsr_position: int | None = None
    availability_status: AvailabilityStatus
    buy_box_status: BuyBoxStatus
    buy_box_seller_name: str | None = None
    coupon_text: str | None = None
    deal_info: DealInfo | None = None
    last_snapshot_date: date


class TrackerRef(ApiModel):
    tracker_type: TrackerType
    tracker_code: str
    tracker_name: str


class ProductDetail(ApiModel):
    marketplace: MarketplaceCode
    asin: AsinCode
    parent_asin: str | None = None
    brand: str
    title_latest: str
    product_url: str
    main_image_url_latest: str
    first_seen_at: datetime
    last_seen_at: datetime
    current_state: ProductCurrentState
    tracker_refs: list[TrackerRef]


class ProductTimelinePoint(ApiModel):
    snapshot_date: date
    bsr_position: int | None = None
    price_current: float | None = None
    price_original: float | None = None
    coupon_text: str | None = None
    availability_status: AvailabilityStatus
    buy_box_status: BuyBoxStatus
    rating_value: float | None = None
    review_count: int | None = None
    title_hash: str | None = None
    main_image_hash: str | None = None
    variation_count: int | None = None


class ProductTimelineSummary(ApiModel):
    price_change_count: int
    availability_change_count: int
    listing_change_count: int
    buy_box_change_count: int


class ProductTimelineResponse(ApiModel):
    marketplace: MarketplaceCode
    asin: AsinCode
    from_date: date
    to_date: date
    granularity: Timeframe
    points: list[ProductTimelinePoint]
    events: list[Event]
    summary: ProductTimelineSummary


class ProductSnapshot(ApiModel):
    marketplace: MarketplaceCode
    asin: AsinCode
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
    deal_info: DealInfo | None = None
    availability_status: AvailabilityStatus
    buy_box_status: BuyBoxStatus
    buy_box_seller_name: str | None = None
    rating_value: float | None = None
    review_count: int | None = None
    variation_count: int | None = None
    source_refs: dict[str, Any] | None = None


class JobSummary(ApiModel):
    expected_items: int
    imported_items: int
    events_emitted: int


class JobRunStrategy(ApiModel):
    provider: Provider
    binding_code: str | None = None


class ExternalRunSummary(ApiModel):
    provider_run_id: str | None = None
    status: ExternalRunStatus | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobError(ApiModel):
    code: str | None = None
    message: str | None = None


class Job(ApiModel):
    job_code: str
    tracker_type: TrackerType
    tracker_code: str
    snapshot_date: date
    trigger_mode: TriggerMode
    status: JobStatus
    run_strategy: JobRunStrategy
    external_run: ExternalRunSummary | None = None
    summary: JobSummary
    error: JobError | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobCreateRequest(ApiModel):
    tracker_type: TrackerType
    tracker_code: str
    snapshot_date: date | None = None
    trigger_mode: TriggerMode = TriggerMode.MANUAL


class ApifyWebhookEnvelope(FlexibleApiModel):
    event_type: str | None = Field(default=None, alias="eventType")
    event_data: dict[str, Any] | str | None = Field(default=None, alias="eventData")
    resource_id: str | None = Field(default=None, alias="resourceId")
    resource: dict[str, Any] | str | None = None
    payload: dict[str, Any] | str | None = None
    data: dict[str, Any] | str | None = None


class ApifyWebhookAck(ApiModel):
    status: Literal["ACCEPTED", "IGNORED"]
    source: Literal["WEBHOOK"] = "WEBHOOK"
    apify_run_id: str | None = None
    tracking_job_code: str | None = None
    provider_status: ExternalRunStatus | None = None
    job_status: JobStatus | None = None


class ApifyRunPollResult(ApiModel):
    source: Literal["POLL"] = "POLL"
    polled_runs: int
    updated_runs: int
    jobs_advanced: int
    jobs_failed: int
    lookup_failures: int


class ImportWorkerResult(ApiModel):
    source: Literal["IMPORT_WORKER"] = "IMPORT_WORKER"
    scanned_jobs: int
    processed_jobs: int
    succeeded_jobs: int
    partial_jobs: int
    failed_jobs: int
    skipped_jobs: int


class SchedulerWorkerResult(ApiModel):
    source: Literal["SCHEDULER_WORKER"] = "SCHEDULER_WORKER"
    scanned_trackers: int
    due_trackers: int
    created_jobs: int
    dispatched_jobs: int
    skipped_existing: int
    failed_jobs: int


class DigestWorkerResult(ApiModel):
    source: Literal["DIGEST_WORKER"] = "DIGEST_WORKER"
    scanned_workspaces: int
    generated_digests: int
    skipped_digests: int
    failed_digests: int


class Threat(ApiModel):
    asin: AsinCode
    marketplace: MarketplaceCode
    reason: str
    event_types: list[EventType] = Field(default_factory=list)
    tracker_refs: list[TrackerRef]


class DashboardOverviewSummary(ApiModel):
    active_category_tracker_count: int
    active_competitor_tracker_count: int
    tracked_product_count: int
    new_entrant_count: int
    returning_count: int
    top10_enter_count: int
    price_change_count: int
    listing_change_count: int


class CategoryHighlight(ApiModel):
    tracker_code: str
    tracker_name: str
    new_entrant_count: int
    exit_count: int
    top10_enter_count: int


class CompetitorHighlight(ApiModel):
    tracker_code: str
    tracker_name: str
    price_change_count: int
    availability_change_count: int
    listing_change_count: int


class DashboardOverview(ApiModel):
    timeframe: Timeframe
    generated_at: datetime
    summary: DashboardOverviewSummary
    top_events: list[Event]
    top_threats: list[Threat]
    category_highlights: list[CategoryHighlight]
    competitor_highlights: list[CompetitorHighlight]


class WeeklyDigestSummary(ApiModel):
    new_entrant_count: int
    returning_count: int
    top10_enter_count: int
    price_change_count: int
    listing_change_count: int


class WeeklyDigest(ApiModel):
    digest_code: str
    week_start: date
    week_end: date
    tracker_refs: list[TrackerRef]
    summary: WeeklyDigestSummary
    threats: list[Threat]
    report_storage_uri: str | None = None
    created_at: datetime


class CategoryTrackerListResponse(ApiModel):
    items: list[CategoryTracker]
    page: int
    page_size: int
    total: int


class CompetitorTrackerListResponse(ApiModel):
    items: list[CompetitorTracker]
    page: int
    page_size: int
    total: int


class EventListResponse(ApiModel):
    items: list[Event]
    page: int
    page_size: int
    total: int


class JobListResponse(ApiModel):
    items: list[Job]
    page: int
    page_size: int
    total: int


class WeeklyDigestListResponse(ApiModel):
    items: list[WeeklyDigest]
    page: int
    page_size: int
    total: int


class CategoryEntrantItem(ApiModel):
    asin: AsinCode
    title: str
    brand: str
    image_url: str
    current_rank: int
    previous_rank: int | None = None
    entered_at: date
    is_first_time_entrant: bool
    tracker_code: str
    tracker_name: str


class ReturningEntrantItem(ApiModel):
    asin: AsinCode
    title: str
    brand: str
    image_url: str
    current_rank: int
    previous_rank: int | None = None
    entered_at: date
    days_absent: int
    tracker_code: str
    tracker_name: str


class CategoryInsights(ApiModel):
    timeframe: Timeframe
    generated_at: datetime
    new_top10_entrants: list[CategoryEntrantItem]
    first_time_entrants: list[CategoryEntrantItem]
    returning_entrants: list[ReturningEntrantItem]


class PriceChangeItem(ApiModel):
    asin: AsinCode
    title: str
    brand: str
    image_url: str
    previous_price: float | None = None
    current_price: float | None = None
    currency: str | None = None
    delta_abs: float | None = None
    delta_pct: float | None = None
    changed_at: date
    tracker_code: str
    tracker_name: str


class PromotionItem(ApiModel):
    asin: AsinCode
    title: str
    brand: str
    image_url: str
    coupon_text: str | None = None
    deal_info: DealInfo | None = None
    changed_at: date
    tracker_code: str
    tracker_name: str


class AvailabilityChangeItem(ApiModel):
    asin: AsinCode
    title: str
    brand: str
    image_url: str
    previous_status: AvailabilityStatus
    current_status: AvailabilityStatus
    changed_at: date
    tracker_code: str
    tracker_name: str


class VariationChangeItem(ApiModel):
    asin: AsinCode
    title: str
    brand: str
    image_url: str
    previous_variation_count: int | None = None
    current_variation_count: int | None = None
    changed_at: date
    tracker_code: str
    tracker_name: str


class CompetitorInsights(ApiModel):
    timeframe: Timeframe
    generated_at: datetime
    price_changes: list[PriceChangeItem]
    promotions: list[PromotionItem]
    availability_changes: list[AvailabilityChangeItem]
    variation_changes: list[VariationChangeItem]


class CompetitorAlertCounts(ApiModel):
    oos_count: int
    price_drop_count: int
    price_increase_count: int
    new_promotion_count: int
    new_variation_count: int
