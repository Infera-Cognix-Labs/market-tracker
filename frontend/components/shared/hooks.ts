import { useEffect, useMemo, useReducer, useState } from "react"
import { ApiError } from "./api"
import { eventToProduct, FILTER_TO_EVENT, matchesEventSearch, matchesProductSearch } from "./formatting"
import type { CategorySnapshot, CategorySnapshotProduct, Event, EventType, TrackerType } from "./types"

// ── Error Handling ────────────────────────────────────────────────────────────

export function handleApiError(
  err: unknown,
  setError: (msg: string | null) => void,
  duplicateMsg: string,
  fallbackMsg = "Failed to create tracker. Please try again."
) {
  if (err instanceof ApiError) {
    if (err.status === 409) {
      setError(duplicateMsg)
    } else if (err.status === 400 && err.details?.reason) {
      setError(err.details.reason)
    } else {
      setError(err.message || fallbackMsg)
    }
  } else {
    setError(fallbackMsg)
  }
}

// ── useTrackerList ────────────────────────────────────────────────────────────

export function useTrackerList<T extends { tracker_code: string; status?: string }>(
  apiFn: () => Promise<{ items: T[] }>,
  errorMsg: string
) {
  const [trackers, setTrackers] = useState<T[]>([])
  const [selectedCode, setSelectedCode] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFn()
      .then(res => {
        setTrackers(res.items)
        if (res.items.length > 0) {
          const firstActive = res.items.find(t => (t.status ?? "ACTIVE") === "ACTIVE") ?? res.items[0]
          setSelectedCode(firstActive.tracker_code)
        }
      })
      .catch(() => {
        setTrackers([])
        setError(errorMsg)
      })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { trackers, setTrackers, selectedCode, setSelectedCode, loading, setLoading, error, setError }
}

// ── useSnapshot ───────────────────────────────────────────────────────────────

export function useSnapshot(
  selectedCode: string,
  apiFn: (code: string) => Promise<CategorySnapshot | null>,
  deps: unknown[] = []
) {
  const [snapshot, setSnapshot] = useState<CategorySnapshot | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!selectedCode) return
    let cancelled = false
    apiFn(selectedCode)
      .then(snap => { if (!cancelled) { setSnapshot(snap); setLoading(false) } })
      .catch(() => { if (!cancelled) { setSnapshot(null); setLoading(false) } })
    return () => { cancelled = true }
  }, [selectedCode, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps

  return { snapshot, setSnapshot, loading, setLoading }
}

// ── Events Reducer ────────────────────────────────────────────────────────────

export type EventsState = { events: Event[]; loading: boolean; error: string | null }
type EventsAction =
  | { type: "FETCH_START" }
  | { type: "FETCH_OK"; events: Event[] }
  | { type: "FETCH_ERR"; error: string }
  | { type: "RESET" }

export function eventsReducer(state: EventsState, action: EventsAction): EventsState {
  switch (action.type) {
    case "FETCH_START": return { ...state, loading: true, error: null }
    case "FETCH_OK": return { events: action.events, loading: false, error: null }
    case "FETCH_ERR": return { events: [], loading: false, error: action.error }
    case "RESET": return { events: [], loading: false, error: null }
  }
}

// ── useFilteredEvents ─────────────────────────────────────────────────────────

export function useFilteredEvents(
  trackerType: TrackerType,
  trackerCode: string,
  snapshotDate: string | undefined,
  activeKpiFilter: string,
  apiListEvents: (params?: {
    event_type?: EventType
    tracker_type?: TrackerType
    tracker_code?: string
    marketplace?: string
    asin?: string
    from_date?: string
    to_date?: string
    page?: number
    page_size?: number
  }) => Promise<{ items: Event[] }>
) {
  const [eventsState, dispatchEvents] = useReducer(eventsReducer, { events: [], loading: false, error: null })

  const filterToEvent = useMemo(
    () => FILTER_TO_EVENT as Record<string, EventType>,
    []
  )

  useEffect(() => {
    if (!trackerCode || !snapshotDate || activeKpiFilter === "ALL") {
      dispatchEvents({ type: "RESET" })
      return
    }
    let cancelled = false
    dispatchEvents({ type: "FETCH_START" })

    apiListEvents({
      tracker_type: trackerType,
      tracker_code: trackerCode,
      from_date: snapshotDate,
      to_date: snapshotDate,
      page_size: 200,
    })
      .then(res => {
        if (cancelled) return
        dispatchEvents({
          type: "FETCH_OK",
          events: res.items.filter(event => Object.values(filterToEvent).includes(event.event_type)),
        })
      })
      .catch(() => {
        if (cancelled) return
        dispatchEvents({ type: "FETCH_ERR", error: "Failed to load events" })
      })

    return () => { cancelled = true }
  }, [trackerCode, snapshotDate, activeKpiFilter, trackerType, filterToEvent, apiListEvents])

  return { eventsState, dispatchEvents }
}

// ── useTriggerJob ─────────────────────────────────────────────────────────────

export function useTriggerJob(
  trackerType: TrackerType,
  selectedCode: string,
  setRefreshKey: (fn: (k: number) => number) => void,
  apiTriggerJob: (trackerType: TrackerType, code: string) => Promise<unknown>
) {
  const [triggering, setTriggering] = useState(false)

  const handleTriggerJob = async () => {
    if (!selectedCode) return
    setTriggering(true)
    try {
      await apiTriggerJob(trackerType, selectedCode)
      setRefreshKey(k => k + 1)
    } catch {
      // ignore — user can retry
    } finally {
      setTriggering(false)
    }
  }

  return { triggering, handleTriggerJob }
}

// ── useTrackerPage (combined hook for CategoryPage + KeywordPage) ─────────────

type KpiFilter = "ALL" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

export type TableRow =
  | { kind: "product"; key: string; product: CategorySnapshotProduct }
  | { kind: "event"; key: string; event: Event }

export const TRACKER_FILTER_TO_EVENT = FILTER_TO_EVENT as Record<Exclude<KpiFilter, "ALL">, EventType>

interface UseTrackerPageOptions<T> {
  trackerType: TrackerType
  apiListTrackers: () => Promise<{ items: T[] }>
  apiGetSnapshot: (code: string) => Promise<CategorySnapshot | null>
  apiListEvents: (params?: {
    event_type?: EventType
    tracker_type?: TrackerType
    tracker_code?: string
    marketplace?: string
    asin?: string
    from_date?: string
    to_date?: string
    page?: number
    page_size?: number
  }) => Promise<{ items: Event[] }>
  apiTriggerJob: (trackerType: TrackerType, code: string) => Promise<unknown>
  listErrorMsg: string
}

export function useTrackerPage<T extends { tracker_code: string; status?: string }>({
  trackerType,
  apiListTrackers,
  apiGetSnapshot,
  apiListEvents,
  apiTriggerJob,
  listErrorMsg,
}: UseTrackerPageOptions<T>) {
  const { trackers, setTrackers, selectedCode, setSelectedCode, loading, setLoading, error, setError } =
    useTrackerList<T>(apiListTrackers, listErrorMsg)

  const [search, setSearch] = useState("")
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [statusFilter, setStatusFilter] = useState("ACTIVE")
  const [openCouponKey, setOpenCouponKey] = useState<string | null>(null)
  const [openDealKey, setOpenDealKey] = useState<string | null>(null)
  const [activeKpiFilter, setActiveKpiFilter] = useState<KpiFilter>("ALL")
  const [justAdded, setJustAdded] = useState<string | null>(null)
  const [showMetaDetail, setShowMetaDetail] = useState(false)

  const { snapshot, setSnapshot, loading: snapshotLoading } = useSnapshot(
    selectedCode,
    apiGetSnapshot,
    [refreshKey]
  )

  const { eventsState, dispatchEvents } = useFilteredEvents(
    trackerType,
    selectedCode,
    snapshot?.snapshot_date,
    activeKpiFilter,
    apiListEvents
  )

  const { triggering, handleTriggerJob } = useTriggerJob(trackerType, selectedCode, setRefreshKey, apiTriggerJob)

  const selectedTracker = trackers.find(t => t.tracker_code === selectedCode)

  const filterToEvent = TRACKER_FILTER_TO_EVENT

  const filteredProducts = useMemo(() => {
    if (!snapshot) return []
    return snapshot.products.filter(product => matchesProductSearch(search, product))
  }, [snapshot, search])

  const allVisibleRows = useMemo<TableRow[]>(() => {
    if (!snapshot) return []
    if (activeKpiFilter === "ALL") {
      return filteredProducts.map(product => ({
        kind: "product",
        key: `${product.asin}-${product.rank_position}`,
        product,
      }))
    }

    const eventType = filterToEvent[activeKpiFilter]
    const relevantEvents = eventsState.events.filter(event => event.event_type === eventType)

    if (activeKpiFilter === "EXITS") {
      return relevantEvents
        .filter(event => matchesEventSearch(search, event))
        .map(event => {
          const product = eventToProduct(event)
          return { kind: "product" as const, key: `${product.asin}-exit-${event.snapshot_date}`, product }
        })
    }

    if (activeKpiFilter === "EXIT_TOP10") {
      const productsByAsin = new Map(snapshot.products.map(p => [p.asin, p]))
      return relevantEvents
        .filter(event => matchesEventSearch(search, event))
        .map(event => {
          const product = productsByAsin.get(event.asin)
          if (product) return { kind: "product" as const, key: `${product.asin}-${product.rank_position}`, product }
          const fallbackProduct = eventToProduct(event)
          return { kind: "product" as const, key: `${fallbackProduct.asin}-exit10-${event.snapshot_date}`, product: fallbackProduct }
        })
    }

    const eventAsins = new Set(relevantEvents.map(event => event.asin))
    return filteredProducts
      .filter(product => eventAsins.has(product.asin))
      .map(product => ({ kind: "product", key: `${product.asin}-${product.rank_position}`, product }))
  }, [snapshot, activeKpiFilter, filteredProducts, eventsState.events, search, filterToEvent])

  const totalFilteredCount = useMemo(() => {
    if (!snapshot) return 0
    if (activeKpiFilter === "ALL") return snapshot.products.length
    const eventType = filterToEvent[activeKpiFilter]
    if (activeKpiFilter === "EXITS" || activeKpiFilter === "EXIT_TOP10") {
      return eventsState.events.filter(event => event.event_type === eventType).length
    }
    const eventAsins = new Set(
      eventsState.events.filter(event => event.event_type === eventType).map(event => event.asin)
    )
    return snapshot.products.filter(product => eventAsins.has(product.asin)).length
  }, [snapshot, activeKpiFilter, eventsState.events, filterToEvent])

  const handleSelectTracker = (code: string) => {
    setSnapshot(null)
    setLoading(true)
    setSelectedCode(code)
    setRefreshKey(k => k + 1)
  }

  const handleCreate = (tracker: T) => {
    setTrackers(prev => [tracker, ...prev])
    setSelectedCode(tracker.tracker_code)
    setJustAdded(tracker.tracker_code)
    setTimeout(() => setJustAdded(null), 5000)
    setShowCreate(false)
  }

  const handleUpdate = (tracker: T) => {
    setTrackers(prev => prev.map(x => x.tracker_code === tracker.tracker_code ? tracker : x))
    setShowEdit(false)
  }

  const handleDelete = (code: string) => {
    setTrackers(prev => prev.filter(x => x.tracker_code !== code))
    setSelectedCode("")
    setShowEdit(false)
  }

  return {
    trackers, setTrackers, selectedCode, setSelectedCode,
    loading, setLoading, error, setError,
    snapshot, setSnapshot, snapshotLoading,
    search, setSearch,
    showCreate, setShowCreate, showEdit, setShowEdit,
    statusFilter, setStatusFilter,
    refreshKey, setRefreshKey,
    activeKpiFilter, setActiveKpiFilter,
    eventsState, dispatchEvents,
    justAdded, setJustAdded,
    openCouponKey, setOpenCouponKey,
    openDealKey, setOpenDealKey,
    triggering, handleTriggerJob,
    showMetaDetail, setShowMetaDetail,
    selectedTracker,
    filteredProducts, allVisibleRows, totalFilteredCount,
    handleSelectTracker, handleCreate, handleUpdate, handleDelete,
  } as const
}
