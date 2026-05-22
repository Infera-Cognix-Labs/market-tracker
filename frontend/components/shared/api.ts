// ── API Service — Real backend calls ─────────────────────────────────────────
import type {
  DashboardOverview, CategoryTracker, CategorySnapshot,
  CompetitorTracker, CompetitorTrackerDetail, ProductDetail, ProductTimelineResponse,
  Event, WeeklyDigest, Job, PagedResponse, Timeframe, EventType, Severity, TrackerType, JobStatus,
  CategoryTrackerCreateRequest,
  CompetitorTrackerCreateRequest,
  TrackedAsinInput,
  CompetitorTrackerUpdateRequest,
  CategoryTrackerUpdateRequest,
  CategoryInsights,
  CompetitorInsights,
  CompetitorAlertCounts,
} from "./types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/market-tracker/api"
const WORKSPACE_ID = process.env.NEXT_PUBLIC_WORKSPACE_ID || "ws_demo_us"
const API_PREFIX = `${BASE_URL}/v1/workspaces/${WORKSPACE_ID}`

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => "")
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ""
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export const apiGetDashboardOverview = async (timeframe: Timeframe = "WEEKLY"): Promise<DashboardOverview> => {
  return apiFetch<DashboardOverview>(`/dashboard/overview${qs({ timeframe })}`)
}

// ── Category Trackers ────────────────────────────────────────────────────────

export const apiListCategoryTrackers = async (page = 1, pageSize = 20): Promise<PagedResponse<CategoryTracker>> => {
  return apiFetch<PagedResponse<CategoryTracker>>(`/category-trackers${qs({ page, page_size: pageSize })}`)
}

export const apiGetCategoryTracker = async (trackerCode: string): Promise<CategoryTracker | null> => {
  return apiFetch<CategoryTracker>(`/category-trackers/${trackerCode}`)
}

export const apiGetLatestCategorySnapshot = async (
  trackerCode: string,
  timeframe: Timeframe = "WEEKLY"
): Promise<CategorySnapshot | null> => {
  return apiFetch<CategorySnapshot>(`/category-trackers/${trackerCode}/snapshots/latest${qs({ timeframe })}`)
}

export const apiCreateCategoryTracker = async (payload: CategoryTrackerCreateRequest): Promise<CategoryTracker> => {
  return apiFetch<CategoryTracker>("/category-trackers", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export const apiUpdateCategoryTracker = async (
  trackerCode: string,
  payload: CategoryTrackerUpdateRequest
): Promise<CategoryTracker> => {
  return apiFetch<CategoryTracker>(`/category-trackers/${trackerCode}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

// ── Competitor Trackers ──────────────────────────────────────────────────────

export const apiListCompetitorTrackers = async (page = 1, pageSize = 20): Promise<PagedResponse<CompetitorTracker>> => {
  return apiFetch<PagedResponse<CompetitorTracker>>(`/competitor-trackers${qs({ page, page_size: pageSize })}`)
}

export const apiGetCompetitorTracker = async (trackerCode: string): Promise<CompetitorTrackerDetail | null> => {
  return apiFetch<CompetitorTrackerDetail>(`/competitor-trackers/${trackerCode}`)
}

export const apiCreateCompetitorTracker = async (payload: CompetitorTrackerCreateRequest): Promise<CompetitorTrackerDetail> => {
  return apiFetch<CompetitorTrackerDetail>("/competitor-trackers", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export const apiUpdateCompetitorTracker = async (
  trackerCode: string,
  payload: CompetitorTrackerUpdateRequest
): Promise<CompetitorTrackerDetail> => {
  return apiFetch<CompetitorTrackerDetail>(`/competitor-trackers/${trackerCode}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export const apiReplaceTrackedAsins = async (
  trackerCode: string,
  asins: TrackedAsinInput[]
): Promise<CompetitorTrackerDetail> => {
  return apiFetch<CompetitorTrackerDetail>(`/competitor-trackers/${trackerCode}/tracked-asins`, {
    method: "PUT",
    body: JSON.stringify({ tracked_asins: asins }),
  })
}

// ── Products ─────────────────────────────────────────────────────────────────

export const apiGetProductDetail = async (marketplace: string, asin: string): Promise<ProductDetail | null> => {
  return apiFetch<ProductDetail>(`/products/${marketplace}/${asin}`)
}

export const apiGetProductTimeline = async (
  marketplace: string,
  asin: string,
  params?: {
    from_date?: string
    to_date?: string
    granularity?: Timeframe
    tracker_code?: string
  }
): Promise<ProductTimelineResponse | null> => {
  return apiFetch<ProductTimelineResponse>(
    `/products/${marketplace}/${asin}/timeline${qs({
      from_date: params?.from_date,
      to_date: params?.to_date,
      granularity: params?.granularity,
      tracker_code: params?.tracker_code,
    })}`
  )
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
  return apiFetch<PagedResponse<Event>>(`/events${qs({
    event_type: params?.event_type,
    severity: params?.severity,
    tracker_type: params?.tracker_type,
    tracker_code: params?.tracker_code,
    marketplace: params?.marketplace,
    asin: params?.asin,
    from_date: params?.from_date,
    to_date: params?.to_date,
    page: params?.page,
    page_size: params?.page_size,
  })}`)
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export const apiListJobs = async (params?: {
  tracker_type?: TrackerType
  tracker_code?: string
  status?: JobStatus
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}): Promise<PagedResponse<Job>> => {
  return apiFetch<PagedResponse<Job>>(`/jobs${qs({
    tracker_type: params?.tracker_type,
    tracker_code: params?.tracker_code,
    status: params?.status,
    from_date: params?.from_date,
    to_date: params?.to_date,
    page: params?.page,
    page_size: params?.page_size,
  })}`)
}

export const apiGetJob = async (jobCode: string): Promise<Job | null> => {
  return apiFetch<Job>(`/jobs/${jobCode}`)
}

export const apiTriggerJob = async (trackerType: TrackerType, trackerCode: string): Promise<Job> => {
  const today = new Date().toISOString().slice(0, 10)
  return apiFetch<Job>("/jobs", {
    method: "POST",
    body: JSON.stringify({
      tracker_type: trackerType,
      tracker_code: trackerCode,
      snapshot_date: today,
      trigger_mode: "MANUAL",
    }),
  })
}

// ── Reports / Weekly Digests ─────────────────────────────────────────────────

export const apiListWeeklyDigests = async (params?: {
  week_start?: string
  page?: number
  page_size?: number
}): Promise<PagedResponse<WeeklyDigest>> => {
  return apiFetch<PagedResponse<WeeklyDigest>>(`/reports/weekly-digests${qs({
    week_start: params?.week_start,
    page: params?.page,
    page_size: params?.page_size,
  })}`)
}

export const apiGetWeeklyDigest = async (digestCode: string): Promise<WeeklyDigest | null> => {
  return apiFetch<WeeklyDigest>(`/reports/weekly-digests/${digestCode}`)
}

export const apiDownloadWeeklyDigest = async (
  digestCode: string,
  format: "pdf" | "excel" = "pdf"
): Promise<void> => {
  const url = `${API_PREFIX}/reports/weekly-digests/${digestCode}/download?format=${format}`
  const response = await fetch(url, { credentials: "include" })
  if (!response.ok) throw new Error("Download failed")
  const blob = await response.blob()
  const ext = format === "pdf" ? "pdf" : "xlsx"
  const link = document.createElement("a")
  link.href = URL.createObjectURL(blob)
  link.download = `weekly_digest_${digestCode}.${ext}`
  link.click()
  URL.revokeObjectURL(link.href)
}

// ── Summaries ─────────────────────────────────────────────────────────────────

export const apiGetCategoryInsights = async (timeframe: Timeframe = "WEEKLY"): Promise<CategoryInsights> => {
  return apiFetch<CategoryInsights>(`/summaries/category-insights${qs({ timeframe })}`)
}

export const apiGetCompetitorInsights = async (timeframe: Timeframe = "WEEKLY"): Promise<CompetitorInsights> => {
  return apiFetch<CompetitorInsights>(`/summaries/competitor-insights${qs({ timeframe })}`)
}

export const apiGetCompetitorAlerts = async (): Promise<CompetitorAlertCounts> => {
  return apiFetch<CompetitorAlertCounts>(`/summaries/competitor-alerts`)
}
