// ── API Type Definitions ─ Matches backend OpenAPI 3.1 schema ─────────────────

// ── Enums ─────────────────────────────────────────────────────────────────────

export type TrackerStatus = "ACTIVE" | "PAUSED" | "ARCHIVED"
export type JobStatus = "QUEUED" | "DISPATCHING" | "RUNNING_EXTERNAL" | "IMPORTING" | "PROCESSING" | "SUCCESS" | "PARTIAL_SUCCESS" | "FAILED"
export type AvailabilityStatus = "IN_STOCK" | "OUT_OF_STOCK" | "INACTIVE" | "UNKNOWN"
export type BuyBoxStatus = "HAS_BUY_BOX" | "NO_BUY_BOX" | "UNKNOWN"
export type Severity = "LOW" | "MEDIUM" | "HIGH"
export type Timeframe = "DAILY" | "WEEKLY" | "MONTHLY"
export type TriggerMode = "SCHEDULED" | "MANUAL" | "RETRY"
export type TrackerType = "CATEGORY" | "COMPETITOR"

export type EventType =
  | "NEW_ENTRANT_TOP50"
  | "RETURNING_TOP50"
  | "EXIT_TOP50"
  | "ENTER_TOP10"
  | "EXIT_TOP10"
  | "PRICE_CHANGED"
  | "PROMOTION_CHANGED"
  | "TITLE_CHANGED"
  | "MAIN_IMAGE_CHANGED"
  | "VARIATIONS_ADDED"
  | "CONTENT_CHANGED"
  | "AVAILABILITY_CHANGED"
  | "BUY_BOX_CHANGED"

// ── Paged Response ────────────────────────────────────────────────────────────

export interface PagedResponse<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardOverview {
  timeframe: Timeframe
  generated_at: string
  summary: DashboardOverviewSummary
  top_events: Event[]
  top_threats: Threat[]
  category_highlights: CategoryHighlight[]
  competitor_highlights: CompetitorHighlight[]
}

export interface DashboardOverviewSummary {
  active_category_tracker_count: number
  active_competitor_tracker_count: number
  tracked_product_count: number
  new_entrant_count: number
  returning_count: number
  top10_enter_count: number
  price_change_count: number
  listing_change_count: number
}

export interface CategoryHighlight {
  tracker_code: string
  tracker_name: string
  new_entrant_count: number
  exit_count: number
  top10_enter_count: number
}

export interface CompetitorHighlight {
  tracker_code: string
  tracker_name: string
  price_change_count: number
  availability_change_count: number
  listing_change_count: number
}

export interface Threat {
  asin: string
  marketplace: string
  reason: string
  event_types?: EventType[]
  tracker_refs: TrackerRef[]
}

// ── Category Tracker ──────────────────────────────────────────────────────────

export interface CategoryTracker {
  tracker_code: string
  name: string
  marketplace: string
  scope: CategoryScope
  tracking_config: CategoryTrackingConfig
  schedule: TrackerSchedule
  status: TrackerStatus
  stats: CategoryTrackerStats
  latest_snapshot_summary?: CategoryTrackerLatestSnapshotSummary
  created_at: string
  updated_at: string
}

export interface CategoryScope {
  browse_node_id?: string
  browse_node_url?: string
}

export interface CategoryTrackingConfig {
  top_n: number
  top10_alert_enabled: boolean
}

export interface TrackerSchedule {
  frequency: "DAILY"
  hour_utc: number
}

export interface CategoryTrackerStats {
  last_job_at: string | null
  last_success_at: string | null
  snapshot_count: number
}

export interface CategoryTrackerLatestSnapshotSummary {
  snapshot_date: string
  captured_at: string
  top10_asins: string[]
}

// ── Category Snapshot ─────────────────────────────────────────────────────────

export interface CategorySnapshot {
  tracker_code: string
  marketplace: string
  browse_node_id: string
  snapshot_date: string
  captured_at: string
  top_n: number
  products: CategorySnapshotProduct[]
  summary: CategorySnapshotSummary
  source_refs?: {
    job_code?: string
    provider?: string
  }
}

export interface CategorySnapshotProduct {
  asin: string
  rank_position: number
  title: string
  brand: string
  product_url: string
  price_current: number
  price_original?: number | null
  currency: string
  rating_value: number
  review_count: number
  image_url: string
  availability_status: AvailabilityStatus
  buy_box_status: BuyBoxStatus
  coupon_text?: string | null
}

export interface CategorySnapshotSummary {
  asin_count: number
  new_entrant_count: number
  returning_count: number
  exit_count: number
  enter_top10_count: number
  exit_top10_count: number
}

// ── Competitor Tracker ────────────────────────────────────────────────────────

export interface CompetitorTracker {
  tracker_code: string
  name: string
  marketplace: string
  tracked_asins: TrackedAsin[]
  track_fields: CompetitorTrackFields
  schedule: TrackerSchedule
  status: TrackerStatus
  stats: CompetitorTrackerStats
  created_at: string
  updated_at: string
}

export interface CompetitorTrackerDetail extends CompetitorTracker {
  tracked_products?: TrackedProductSummary[]
}

export interface TrackedAsin {
  asin: string
  enabled: boolean
  added_at: string
}

export interface CompetitorTrackFields {
  bsr: boolean
  price: boolean
  buy_box: boolean
  availability: boolean
  promotions: boolean
  title_change: boolean
  main_image_change: boolean
  variation_change: boolean
  content_change: boolean
}

export interface CompetitorTrackerStats {
  tracked_asin_count: number
  last_job_at: string | null
  last_success_at: string | null
}

export interface TrackedProductSummary {
  asin: string
  brand: string
  title: string
  current_bsr_position: number | null
  current_price: number | null
  currency: string | null
  availability_status: AvailabilityStatus
  last_snapshot_date: string
  recent_event_count_7d?: number
}

// ── Product ───────────────────────────────────────────────────────────────────

export interface ProductDetail {
  marketplace: string
  asin: string
  parent_asin?: string | null
  brand: string
  title_latest: string
  product_url: string
  main_image_url_latest: string
  first_seen_at: string
  last_seen_at: string
  current_state: ProductCurrentState
  tracker_refs: TrackerRef[]
}

export interface ProductCurrentState {
  price_current?: number | null
  price_original?: number | null
  currency?: string | null
  bsr_position?: number | null
  availability_status: AvailabilityStatus
  buy_box_status: BuyBoxStatus
  buy_box_seller_name?: string | null
  coupon_text?: string | null
  last_snapshot_date: string
}

export interface TrackerRef {
  tracker_type: TrackerType
  tracker_code: string
  tracker_name: string
}

// ── Product Timeline ──────────────────────────────────────────────────────────

export interface ProductTimelineResponse {
  marketplace: string
  asin: string
  from_date: string
  to_date: string
  granularity: Timeframe
  points: ProductTimelinePoint[]
  events: Event[]
  summary: ProductTimelineSummary
}

export interface ProductTimelinePoint {
  snapshot_date: string
  bsr_position?: number | null
  price_current?: number | null
  price_original?: number | null
  coupon_text?: string | null
  availability_status: AvailabilityStatus
  buy_box_status: BuyBoxStatus
  rating_value?: number | null
  review_count?: number | null
  title_hash?: string | null
  main_image_hash?: string | null
  variation_count?: number | null
}

export interface ProductTimelineSummary {
  price_change_count: number
  availability_change_count: number
  listing_change_count: number
  buy_box_change_count: number
}

// ── Events ────────────────────────────────────────────────────────────────────

export interface Event {
  event_code: string
  tracker_type: TrackerType
  tracker_code: string
  marketplace: string
  asin: string
  event_type: EventType
  event_time: string
  snapshot_date: string
  severity: Severity
  title: string
  summary: string
  payload: EventPayload
  job_code?: string
  dedupe_key?: string
}

export interface EventPayload {
  rank_today?: number
  first_seen_in_tracker?: boolean
  last_seen_date?: string
  days_absent?: number
  previous_rank?: number
  current_rank?: number
  present_today?: boolean
  previous?: EventChangeState
  current?: EventChangeState
  delta?: EventDelta
}

export interface EventChangeState {
  price_current?: number | null
  price_original?: number | null
  coupon_text?: string | null
  title?: string
  main_image_url?: string
  variation_count?: number
  content_signature_hash?: string
  a_plus_signature_hash?: string
  availability_status?: AvailabilityStatus
  buy_box_status?: BuyBoxStatus
  buy_box_seller_name?: string
}

export interface EventDelta {
  price_current_abs?: number
  price_current_pct?: number
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export interface Job {
  job_code: string
  tracker_type: TrackerType
  tracker_code: string
  snapshot_date: string
  trigger_mode: TriggerMode
  status: JobStatus
  run_strategy: JobRunStrategy
  external_run?: ExternalRunSummary | null
  summary: JobSummary
  error?: JobError | null
  created_at: string
  started_at?: string | null
  finished_at?: string | null
}

export interface JobRunStrategy {
  provider: "APIFY"
  binding_code?: string
}

export interface ExternalRunSummary {
  provider_run_id?: string
  status?: "READY" | "RUNNING" | "SUCCEEDED" | "FAILED" | "TIMED_OUT" | "ABORTED"
  started_at?: string | null
  finished_at?: string | null
}

export interface JobSummary {
  expected_items: number
  imported_items: number
  events_emitted: number
}

export interface JobError {
  code?: string
  message?: string
}

// ── Weekly Digest ─────────────────────────────────────────────────────────────

export interface WeeklyDigest {
  digest_code: string
  week_start: string
  week_end: string
  tracker_refs: TrackerRef[]
  summary: WeeklyDigestSummary
  threats: Threat[]
  report_storage_uri?: string | null
  created_at: string
}

export interface WeeklyDigestSummary {
  new_entrant_count: number
  returning_count: number
  top10_enter_count: number
  price_change_count: number
  listing_change_count: number
}

// ── Category Tracker Create ───────────────────────────────────────────────────

export interface CategoryTrackingConfigInput {
  top10_alert_enabled?: boolean
}

export interface TrackerScheduleInput {
  frequency: "DAILY"
  hour_utc: number
}

export interface CategoryTrackerCreateRequest {
  name: string
  marketplace: string
  scope: CategoryScope
  tracking_config?: CategoryTrackingConfigInput
  schedule: TrackerScheduleInput
}

// ── Competitor Tracker Create ─────────────────────────────────────────────────

export interface TrackedAsinInput {
  asin: string
  enabled: boolean
}

export interface CompetitorTrackerCreateRequest {
  name: string
  marketplace: string
  tracked_asins: TrackedAsinInput[]
  track_fields: CompetitorTrackFields
  schedule: TrackerScheduleInput
}
