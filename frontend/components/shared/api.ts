// ── API Service — Matches backend OpenAPI endpoints ──────────────────────────
import type {
  DashboardOverview, CategoryTracker, CategorySnapshot,
  CompetitorTrackerDetail, ProductDetail, ProductTimelineResponse,
  Event, WeeklyDigest, Job, PagedResponse, Timeframe, EventType, Severity, TrackerType, JobStatus,
  CategoryTrackerCreateRequest,
  CompetitorTrackerCreateRequest,
} from "./types"

import {
  MOCK_DASHBOARD_OVERVIEW, MOCK_CATEGORY_TRACKERS, MOCK_CATEGORY_SNAPSHOTS,
  MOCK_COMPETITOR_TRACKERS, MOCK_PRODUCT_DETAILS, MOCK_PRODUCT_TIMELINES,
  MOCK_EVENTS, MOCK_JOBS, MOCK_WEEKLY_DIGESTS,
} from "./MockData"

const delay = (ms: number = 300) => new Promise(res => setTimeout(res, ms))

// ── Dashboard ────────────────────────────────────────────────────────────────

export const apiGetDashboardOverview = async (timeframe: Timeframe = "WEEKLY"): Promise<DashboardOverview> => {
  await delay()
  return { ...MOCK_DASHBOARD_OVERVIEW, timeframe }
}

// ── Category Trackers ────────────────────────────────────────────────────────

export const apiListCategoryTrackers = async (): Promise<PagedResponse<CategoryTracker>> => {
  await delay()
  return MOCK_CATEGORY_TRACKERS
}

export const apiGetCategoryTracker = async (trackerCode: string): Promise<CategoryTracker | null> => {
  await delay()
  return MOCK_CATEGORY_TRACKERS.items.find(t => t.tracker_code === trackerCode) || null
}

export const apiGetLatestCategorySnapshot = async (trackerCode: string): Promise<CategorySnapshot | null> => {
  await delay()
  return MOCK_CATEGORY_SNAPSHOTS[trackerCode] || null
}

export const apiCreateCategoryTracker = async (payload: CategoryTrackerCreateRequest): Promise<CategoryTracker> => {
  await delay(500)
  const now = new Date().toISOString()
  return {
    tracker_code: `cat_${Date.now()}`,
    name: payload.name,
    marketplace: payload.marketplace,
    scope: payload.scope,
    tracking_config: {
      top_n: 50,
      top10_alert_enabled: payload.tracking_config?.top10_alert_enabled ?? true,
    },
    schedule: { frequency: payload.schedule.frequency, hour_utc: payload.schedule.hour_utc },
    status: "ACTIVE",
    stats: { last_job_at: null, last_success_at: null, snapshot_count: 0 },
    created_at: now,
    updated_at: now,
  }
}

// ── Competitor Trackers ──────────────────────────────────────────────────────

export const apiListCompetitorTrackers = async (): Promise<PagedResponse<CompetitorTrackerDetail>> => {
  await delay()
  return MOCK_COMPETITOR_TRACKERS
}

export const apiGetCompetitorTracker = async (trackerCode: string): Promise<CompetitorTrackerDetail | null> => {
  await delay()
  return MOCK_COMPETITOR_TRACKERS.items.find(t => t.tracker_code === trackerCode) || null
}

export const apiCreateCompetitorTracker = async (payload: CompetitorTrackerCreateRequest): Promise<CompetitorTrackerDetail> => {
  await delay(500)
  const now = new Date().toISOString()
  return {
    tracker_code: `comp_${Date.now()}`,
    name: payload.name,
    marketplace: payload.marketplace,
    tracked_asins: payload.tracked_asins.map(a => ({ ...a, added_at: now })),
    track_fields: payload.track_fields,
    schedule: { frequency: payload.schedule.frequency, hour_utc: payload.schedule.hour_utc },
    status: "ACTIVE",
    stats: { tracked_asin_count: payload.tracked_asins.length, last_job_at: null, last_success_at: null },
    tracked_products: [],
    created_at: now,
    updated_at: now,
  }
}

// ── Products ─────────────────────────────────────────────────────────────────

export const apiGetProductDetail = async (marketplace: string, asin: string): Promise<ProductDetail | null> => {
  await delay()
  return MOCK_PRODUCT_DETAILS[`${marketplace}|${asin}`] || null
}

export const apiGetProductTimeline = async (
  marketplace: string,
  asin: string,
  _params?: { from_date?: string; to_date?: string; granularity?: Timeframe }
): Promise<ProductTimelineResponse | null> => {
  await delay()
  return MOCK_PRODUCT_TIMELINES[`${marketplace}|${asin}`] || null
}

// ── Events ───────────────────────────────────────────────────────────────────

export const apiListEvents = async (params?: {
  event_type?: EventType
  severity?: Severity
  tracker_type?: TrackerType
  tracker_code?: string
  marketplace?: string
  asin?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}): Promise<PagedResponse<Event>> => {
  await delay()
  let items = [...MOCK_EVENTS.items]
  if (params?.event_type) items = items.filter(e => e.event_type === params.event_type)
  if (params?.severity) items = items.filter(e => e.severity === params.severity)
  if (params?.tracker_type) items = items.filter(e => e.tracker_type === params.tracker_type)
  if (params?.tracker_code) items = items.filter(e => e.tracker_code === params.tracker_code)
  if (params?.asin) items = items.filter(e => e.asin === params.asin)
  return { items, page: params?.page || 1, page_size: params?.page_size || 20, total: items.length }
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export const apiListJobs = async (params?: {
  tracker_type?: TrackerType
  tracker_code?: string
  status?: JobStatus
  page?: number
  page_size?: number
}): Promise<PagedResponse<Job>> => {
  await delay()
  let items = [...MOCK_JOBS.items]
  if (params?.tracker_type) items = items.filter(j => j.tracker_type === params.tracker_type)
  if (params?.status) items = items.filter(j => j.status === params.status)
  return { items, page: params?.page || 1, page_size: params?.page_size || 20, total: items.length }
}

export const apiTriggerJob = async (trackerType: TrackerType, trackerCode: string): Promise<Job> => {
  await delay(500)
  const now = new Date().toISOString()
  const today = now.slice(0, 10)
  return {
    job_code: `job_manual_${Date.now()}`,
    tracker_type: trackerType,
    tracker_code: trackerCode,
    snapshot_date: today,
    trigger_mode: "MANUAL",
    status: "QUEUED",
    run_strategy: { provider: "APIFY" },
    summary: { expected_items: trackerType === "CATEGORY" ? 50 : 3, imported_items: 0, events_emitted: 0 },
    error: null,
    created_at: now,
    started_at: null,
    finished_at: null,
  }
}

// ── Reports / Weekly Digests ─────────────────────────────────────────────────

export const apiListWeeklyDigests = async (): Promise<PagedResponse<WeeklyDigest>> => {
  await delay()
  return MOCK_WEEKLY_DIGESTS
}

export const apiGetWeeklyDigest = async (digestCode: string): Promise<WeeklyDigest | null> => {
  await delay()
  return MOCK_WEEKLY_DIGESTS.items.find(d => d.digest_code === digestCode) || null
}
