// ── MOCK DATA — Matches backend OpenAPI schemas ──────────────────────────────
import type {
  DashboardOverview, CategoryTracker, CategorySnapshot,
  CompetitorTrackerDetail, ProductDetail, ProductTimelineResponse,
  Event, WeeklyDigest, Job, PagedResponse,
} from "./types"

// ── Dashboard Overview ───────────────────────────────────────────────────────

export const MOCK_DASHBOARD_OVERVIEW: DashboardOverview = {
  timeframe: "WEEKLY",
  generated_at: "2026-04-03T08:15:00Z",
  summary: {
    active_category_tracker_count: 2,
    active_competitor_tracker_count: 1,
    active_keyword_tracker_count: 0,
    tracked_product_count: 18,
    new_entrant_count: 4,
    returning_count: 2,
    top10_enter_count: 1,
    price_change_count: 9,
    listing_change_count: 5,
  },
  top_events: [
    {
      event_code: "evt_20260403_001",
      tracker_type: "CATEGORY",
      tracker_code: "ct_baby_bottle_warmers_us",
      marketplace: "amazon_us",
      asin: "B0ABC12345",
      event_type: "ENTER_TOP10",
      event_time: "2026-04-03T02:13:00Z",
      snapshot_date: "2026-04-03",
      severity: "HIGH",
      title: "Product entered Top 10",
      summary: "ASIN B0ABC12345 moved from rank 14 to rank 9.",
      payload: { previous_rank: 14, current_rank: 9 },
      job_code: "job_cat_20260403_001",
      dedupe_key: "ENTER_TOP10|ct_baby_bottle_warmers_us|B0ABC12345|2026-04-03",
    },
    {
      event_code: "evt_20260403_002",
      tracker_type: "COMPETITOR",
      tracker_code: "cmp_baby_bottle_warmers_us",
      marketplace: "amazon_us",
      asin: "B0ABC12345",
      event_type: "PRICE_CHANGED",
      event_time: "2026-04-03T03:09:00Z",
      snapshot_date: "2026-04-03",
      severity: "MEDIUM",
      title: "Price dropped from 39.99 to 34.99",
      summary: "Detected a 12.5% price decrease for tracked competitor B0ABC12345.",
      payload: {
        previous: { price_current: 39.99, price_original: 44.99 },
        current: { price_current: 34.99, price_original: 39.99 },
        delta: { price_current_abs: -5.0, price_current_pct: -12.5 },
      },
      job_code: "job_cmp_20260403_001",
      dedupe_key: "PRICE_CHANGED|amazon_us|B0ABC12345|2026-04-03",
    },
    {
      event_code: "evt_20260403_003",
      tracker_type: "COMPETITOR",
      tracker_code: "cmp_baby_bottle_warmers_us",
      marketplace: "amazon_us",
      asin: "B0XYZ67890",
      event_type: "AVAILABILITY_CHANGED",
      event_time: "2026-04-03T03:09:20Z",
      snapshot_date: "2026-04-03",
      severity: "HIGH",
      title: "Availability changed: IN_STOCK → OUT_OF_STOCK",
      summary: "Tracked competitor B0XYZ67890 became unavailable.",
      payload: {
        previous: { availability_status: "IN_STOCK" },
        current: { availability_status: "OUT_OF_STOCK" },
      },
      job_code: "job_cmp_20260403_001",
      dedupe_key: "AVAILABILITY_CHANGED|amazon_us|B0XYZ67890|2026-04-03",
    },
    {
      event_code: "evt_20260403_004",
      tracker_type: "COMPETITOR",
      tracker_code: "cmp_baby_bottle_warmers_us",
      marketplace: "amazon_us",
      asin: "B0ABC12345",
      event_type: "TITLE_CHANGED",
      event_time: "2026-04-03T03:09:10Z",
      snapshot_date: "2026-04-03",
      severity: "MEDIUM",
      title: "Title changed materially",
      summary: "The normalized title changed for tracked competitor B0ABC12345.",
      payload: {
        previous: { title: "MellowNest Fast Bottle Warmer" },
        current: { title: "MellowNest Fast Bottle Warmer with Night Light" },
      },
      job_code: "job_cmp_20260403_001",
      dedupe_key: "TITLE_CHANGED|amazon_us|B0ABC12345|2026-04-03",
    },
    {
      event_code: "evt_20260402_005",
      tracker_type: "CATEGORY",
      tracker_code: "ct_baby_bottle_warmers_us",
      marketplace: "amazon_us",
      asin: "B0BEST00003",
      event_type: "NEW_ENTRANT_TOP50",
      event_time: "2026-04-02T02:12:00Z",
      snapshot_date: "2026-04-02",
      severity: "MEDIUM",
      title: "New entrant in Top 50",
      summary: "ASIN B0BEST00003 appeared in Top 50 for the first time at rank 3.",
      payload: { rank_today: 3, first_seen_in_tracker: true },
      job_code: "job_cat_20260402_001",
      dedupe_key: "NEW_ENTRANT_TOP50|ct_baby_bottle_warmers_us|B0BEST00003|2026-04-02",
    },
    {
      event_code: "evt_20260401_006",
      tracker_type: "CATEGORY",
      tracker_code: "ct_bottle_sterilizers_us",
      marketplace: "amazon_us",
      asin: "B0STER00010",
      event_type: "RETURNING_TOP50",
      event_time: "2026-04-01T02:14:00Z",
      snapshot_date: "2026-04-01",
      severity: "MEDIUM",
      title: "Product returned to Top 50",
      summary: "ASIN B0STER00010 re-entered the Top 50 after 4 days absent.",
      payload: { rank_today: 39, last_seen_date: "2026-03-28", days_absent: 4 },
      job_code: "job_cat_20260401_002",
      dedupe_key: "RETURNING_TOP50|ct_bottle_sterilizers_us|B0STER00010|2026-04-01",
    },
  ],
  top_threats: [
    {
      asin: "B0ABC12345",
      marketplace: "amazon_us",
      reason: "Entered Top 10 while also lowering price on the same day.",
      event_types: ["ENTER_TOP10", "PRICE_CHANGED"],
      tracker_refs: [
        { tracker_type: "CATEGORY", tracker_code: "ct_baby_bottle_warmers_us", tracker_name: "Baby Bottle Warmers - US" },
        { tracker_type: "COMPETITOR", tracker_code: "cmp_baby_bottle_warmers_us", tracker_name: "Bottle Warmer Competitors - US" },
      ],
    },
    {
      asin: "B0XYZ67890",
      marketplace: "amazon_us",
      reason: "Went out of stock after a Buy Box seller change.",
      event_types: ["BUY_BOX_CHANGED", "AVAILABILITY_CHANGED"],
      tracker_refs: [
        { tracker_type: "COMPETITOR", tracker_code: "cmp_baby_bottle_warmers_us", tracker_name: "Bottle Warmer Competitors - US" },
      ],
    },
  ],
  category_highlights: [
    { tracker_code: "ct_baby_bottle_warmers_us", tracker_name: "Baby Bottle Warmers - US", new_entrant_count: 3, exit_count: 2, top10_enter_count: 1 },
    { tracker_code: "ct_bottle_sterilizers_us", tracker_name: "Bottle Sterilizers - US", new_entrant_count: 1, exit_count: 1, top10_enter_count: 0 },
  ],
  competitor_highlights: [
    { tracker_code: "cmp_baby_bottle_warmers_us", tracker_name: "Bottle Warmer Competitors - US", price_change_count: 9, availability_change_count: 1, listing_change_count: 5 },
  ],
  keyword_highlights: [],
}

// ── Category Trackers List ───────────────────────────────────────────────────

export const MOCK_CATEGORY_TRACKERS: PagedResponse<CategoryTracker> = {
  items: [
    {
      tracker_code: "ct_baby_bottle_warmers_us",
      name: "Baby Bottle Warmers - US",
      marketplace: "amazon_us",
      scope: {
        browse_node_id: "13893610011",
        browse_node_url: "https://www.amazon.com/Best-Sellers-Baby-Bottle-Warmers/zgbs/baby-products/13893610011",
      },
      tracking_config: { top_n: 50, top10_alert_enabled: true },
      schedule: { frequency: "DAILY", hour_utc: 2 },
      status: "ACTIVE",
      stats: { last_job_at: "2026-04-03T02:00:00Z", last_success_at: "2026-04-03T02:13:10Z", snapshot_count: 12 },
      latest_snapshot_summary: {
        snapshot_date: "2026-04-03",
        captured_at: "2026-04-03T02:11:05Z",
        top10_asins: ["B0BEST00001", "B0BEST00002", "B0BEST00003", "B0BEST00004", "B0BEST00005", "B0BEST00006", "B0BEST00007", "B0BEST00008", "B0ABC12345", "B0BEST00010"],
      },
      created_at: "2026-03-22T00:00:00Z",
      updated_at: "2026-04-03T02:13:10Z",
    },
    {
      tracker_code: "ct_bottle_sterilizers_us",
      name: "Bottle Sterilizers - US",
      marketplace: "amazon_us",
      scope: {
        browse_node_id: "166886011",
        browse_node_url: "https://www.amazon.com/Best-Sellers-Baby-Bottle-Sterilizers/zgbs/baby-products/166886011",
      },
      tracking_config: { top_n: 50, top10_alert_enabled: true },
      schedule: { frequency: "DAILY", hour_utc: 2 },
      status: "ACTIVE",
      stats: { last_job_at: "2026-04-03T02:00:00Z", last_success_at: "2026-04-03T02:15:20Z", snapshot_count: 8 },
      latest_snapshot_summary: {
        snapshot_date: "2026-04-03",
        captured_at: "2026-04-03T02:14:30Z",
        top10_asins: ["B0STER00001", "B0STER00002", "B0STER00003", "B0STER00004", "B0STER00005", "B0STER00006", "B0STER00007", "B0STER00008", "B0STER00009", "B0STER00010"],
      },
      created_at: "2026-03-26T00:00:00Z",
      updated_at: "2026-04-03T02:15:20Z",
    },
  ],
  page: 1,
  page_size: 20,
  total: 2,
}

// ── Category Snapshot (Latest) ───────────────────────────────────────────────

export const MOCK_CATEGORY_SNAPSHOTS: Record<string, CategorySnapshot> = {
  ct_baby_bottle_warmers_us: {
    tracker_code: "ct_baby_bottle_warmers_us",
    marketplace: "amazon_us",
    browse_node_id: "13893610011",
    snapshot_date: "2026-04-03",
    captured_at: "2026-04-03T02:11:05Z",
    top_n: 50,
    products: [
      { asin: "B0BEST00001", rank_position: 1, title: "WarmNest Smart Bottle Warmer Pro", brand: "WarmNest", product_url: "https://www.amazon.com/dp/B0BEST00001", price_current: 49.99, price_original: 59.99, currency: "USD", rating_value: 4.8, review_count: 5832, image_url: "https://images.example.com/B0BEST00001.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: "15% off" },
      { asin: "B0BEST00002", rank_position: 2, title: "MilkFlow 6-in-1 Bottle Warmer", brand: "MilkFlow", product_url: "https://www.amazon.com/dp/B0BEST00002", price_current: 42.50, price_original: 42.50, currency: "USD", rating_value: 4.7, review_count: 4112, image_url: "https://images.example.com/B0BEST00002.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: null },
      { asin: "B0BEST00003", rank_position: 3, title: "TinyMorn Fast Steam Bottle Warmer", brand: "TinyMorn", product_url: "https://www.amazon.com/dp/B0BEST00003", price_current: 39.99, price_original: 45.99, currency: "USD", rating_value: 4.6, review_count: 2356, image_url: "https://images.example.com/B0BEST00003.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: "5% off" },
      { asin: "B0BEST00004", rank_position: 4, title: "GlowCare Night Bottle Warmer", brand: "GlowCare", product_url: "https://www.amazon.com/dp/B0BEST00004", price_current: 44.99, price_original: null, currency: "USD", rating_value: 4.6, review_count: 1897, image_url: "https://images.example.com/B0BEST00004.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: null },
      { asin: "B0BEST00005", rank_position: 5, title: "PureFeed Bottle Warmer and Sterilizer", brand: "PureFeed", product_url: "https://www.amazon.com/dp/B0BEST00005", price_current: 56.00, price_original: 64.99, currency: "USD", rating_value: 4.5, review_count: 1430, image_url: "https://images.example.com/B0BEST00005.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: "10% off" },
      { asin: "B0BEST00006", rank_position: 6, title: "NurturEase Portable Bottle Warmer", brand: "NurturEase", product_url: "https://www.amazon.com/dp/B0BEST00006", price_current: 37.99, price_original: 39.99, currency: "USD", rating_value: 4.4, review_count: 1184, image_url: "https://images.example.com/B0BEST00006.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: null },
      { asin: "B0BEST00007", rank_position: 7, title: "Everbaby Precision Bottle Warmer", brand: "Everbaby", product_url: "https://www.amazon.com/dp/B0BEST00007", price_current: 51.99, price_original: 51.99, currency: "USD", rating_value: 4.4, review_count: 972, image_url: "https://images.example.com/B0BEST00007.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: null },
      { asin: "B0BEST00008", rank_position: 8, title: "GentleHeat Bottle Warmer Mini", brand: "GentleHeat", product_url: "https://www.amazon.com/dp/B0BEST00008", price_current: 29.99, price_original: 34.99, currency: "USD", rating_value: 4.3, review_count: 2061, image_url: "https://images.example.com/B0BEST00008.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: "5% off" },
      { asin: "B0ABC12345", rank_position: 9, title: "MellowNest Fast Bottle Warmer with Night Light", brand: "MellowNest", product_url: "https://www.amazon.com/dp/B0ABC12345", price_current: 34.99, price_original: 39.99, currency: "USD", rating_value: 4.5, review_count: 1023, image_url: "https://images.example.com/B0ABC12345.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: "10% off" },
      { asin: "B0BEST00010", rank_position: 10, title: "PicoWarm Instant Bottle Warmer", brand: "PicoWarm", product_url: "https://www.amazon.com/dp/B0BEST00010", price_current: 33.49, price_original: 36.99, currency: "USD", rating_value: 4.4, review_count: 881, image_url: "https://images.example.com/B0BEST00010.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: null },
      // ranks 11-20
      { asin: "B0RANK00011", rank_position: 11, title: "LullaWarm Multi-Function Warmer Set", brand: "LullaWarm", product_url: "https://www.amazon.com/dp/B0RANK00011", price_current: 45.49, price_original: 52.99, currency: "USD", rating_value: 4.3, review_count: 764, image_url: "https://images.example.com/B0RANK00011.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: null },
      { asin: "B0RANK00012", rank_position: 12, title: "BottleBuddy Express Warmer", brand: "BottleBuddy", product_url: "https://www.amazon.com/dp/B0RANK00012", price_current: 27.99, price_original: 29.99, currency: "USD", rating_value: 4.2, review_count: 612, image_url: "https://images.example.com/B0RANK00012.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: "5% off" },
      { asin: "B0RANK00013", rank_position: 13, title: "SunnyFeed Travel Bottle Warmer USB", brand: "SunnyFeed", product_url: "https://www.amazon.com/dp/B0RANK00013", price_current: 22.99, price_original: null, currency: "USD", rating_value: 4.1, review_count: 534, image_url: "https://images.example.com/B0RANK00013.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: null },
      { asin: "B0RANK00014", rank_position: 14, title: "CozyCare Premium Warmer 4-in-1", brand: "CozyCare", product_url: "https://www.amazon.com/dp/B0RANK00014", price_current: 62.99, price_original: 72.99, currency: "USD", rating_value: 4.5, review_count: 489, image_url: "https://images.example.com/B0RANK00014.jpg", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", coupon_text: "15% off" },
      { asin: "B0RANK00015", rank_position: 15, title: "BabyPure Steam Warmer Compact", brand: "BabyPure", product_url: "https://www.amazon.com/dp/B0RANK00015", price_current: 31.49, price_original: 34.99, currency: "USD", rating_value: 4.0, review_count: 378, image_url: "https://images.example.com/B0RANK00015.jpg", availability_status: "OUT_OF_STOCK", buy_box_status: "NO_BUY_BOX", coupon_text: null },
    ],
    summary: {
      asin_count: 50,
      new_entrant_count: 1,
      returning_count: 0,
      exit_count: 2,
      enter_top10_count: 1,
      exit_top10_count: 1,
    },
    source_refs: { job_code: "job_cat_20260403_001", provider: "APIFY" },
  },
}

// ── Competitor Tracker Detail ────────────────────────────────────────────────

export const MOCK_COMPETITOR_TRACKERS: PagedResponse<CompetitorTrackerDetail> = {
  items: [
    {
      tracker_code: "cmp_baby_bottle_warmers_us",
      name: "Bottle Warmer Competitors - US",
      marketplace: "amazon_us",
      tracked_asins: [
        { asin: "B0ABC12345", enabled: true, added_at: "2026-03-25T09:00:00Z" },
        { asin: "B0XYZ67890", enabled: true, added_at: "2026-03-25T09:00:00Z" },
        { asin: "B0LMN45678", enabled: true, added_at: "2026-03-26T09:00:00Z" },
      ],
      track_fields: { bsr: true, price: true, buy_box: true, availability: true, promotions: true, title_change: true, main_image_change: true, variation_change: true, content_change: true },
      schedule: { frequency: "DAILY", hour_utc: 3 },
      status: "ACTIVE",
      stats: { tracked_asin_count: 3, last_job_at: "2026-04-03T03:00:00Z", last_success_at: "2026-04-03T03:10:00Z" },
      tracked_products: [
        { asin: "B0ABC12345", brand: "MellowNest", title: "MellowNest Fast Bottle Warmer with Night Light", current_bsr_position: 9, current_price: 34.99, currency: "USD", availability_status: "IN_STOCK", last_snapshot_date: "2026-04-03", recent_event_count_7d: 3 },
        { asin: "B0XYZ67890", brand: "QuickWarm", title: "QuickWarm Digital Bottle Warmer Pro", current_bsr_position: 17, current_price: 31.99, currency: "USD", availability_status: "OUT_OF_STOCK", last_snapshot_date: "2026-04-03", recent_event_count_7d: 2 },
        { asin: "B0LMN45678", brand: "CozyLatch", title: "CozyLatch Travel Bottle Warmer Set", current_bsr_position: 28, current_price: 27.49, currency: "USD", availability_status: "IN_STOCK", last_snapshot_date: "2026-04-03", recent_event_count_7d: 1 },
      ],
      created_at: "2026-03-25T08:55:00Z",
      updated_at: "2026-04-03T03:10:00Z",
    },
  ],
  page: 1,
  page_size: 20,
  total: 1,
}

// ── Product Detail ───────────────────────────────────────────────────────────

export const MOCK_PRODUCT_DETAILS: Record<string, ProductDetail> = {
  "amazon_us|B0ABC12345": {
    marketplace: "amazon_us",
    asin: "B0ABC12345",
    parent_asin: "B0PARENT0001",
    brand: "MellowNest",
    title_latest: "MellowNest Fast Bottle Warmer with Night Light",
    product_url: "https://www.amazon.com/dp/B0ABC12345",
    main_image_url_latest: "https://images.example.com/B0ABC12345-main.jpg",
    first_seen_at: "2026-03-25T00:00:00Z",
    last_seen_at: "2026-04-03T03:05:00Z",
    current_state: {
      price_current: 34.99, price_original: 39.99, currency: "USD", bsr_position: 9,
      availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", buy_box_seller_name: "Amazon",
      coupon_text: "10% off", last_snapshot_date: "2026-04-03",
    },
    tracker_refs: [
      { tracker_type: "CATEGORY", tracker_code: "ct_baby_bottle_warmers_us", tracker_name: "Baby Bottle Warmers - US" },
      { tracker_type: "COMPETITOR", tracker_code: "cmp_baby_bottle_warmers_us", tracker_name: "Bottle Warmer Competitors - US" },
    ],
  },
}

// ── Product Timeline ─────────────────────────────────────────────────────────

export const MOCK_PRODUCT_TIMELINES: Record<string, ProductTimelineResponse> = {
  "amazon_us|B0ABC12345": {
    marketplace: "amazon_us",
    asin: "B0ABC12345",
    from_date: "2026-03-28",
    to_date: "2026-04-03",
    granularity: "DAILY",
    points: [
      { snapshot_date: "2026-03-28", bsr_position: 18, price_current: 39.99, price_original: 44.99, coupon_text: null, availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", rating_value: 4.5, review_count: 995, title_hash: "sha256_title_v1", main_image_hash: "sha256_img_v1", variation_count: 3 },
      { snapshot_date: "2026-03-29", bsr_position: 16, price_current: 39.99, price_original: 44.99, coupon_text: null, availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", rating_value: 4.5, review_count: 1001, title_hash: "sha256_title_v1", main_image_hash: "sha256_img_v1", variation_count: 3 },
      { snapshot_date: "2026-03-30", bsr_position: 14, price_current: 39.99, price_original: 44.99, coupon_text: null, availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", rating_value: 4.5, review_count: 1009, title_hash: "sha256_title_v1", main_image_hash: "sha256_img_v1", variation_count: 3 },
      { snapshot_date: "2026-04-01", bsr_position: 12, price_current: 37.99, price_original: 42.99, coupon_text: "5% off", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", rating_value: 4.5, review_count: 1016, title_hash: "sha256_title_v1", main_image_hash: "sha256_img_v1", variation_count: 3 },
      { snapshot_date: "2026-04-02", bsr_position: 14, price_current: 39.99, price_original: 44.99, coupon_text: null, availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", rating_value: 4.5, review_count: 1020, title_hash: "sha256_title_v1", main_image_hash: "sha256_img_v1", variation_count: 3 },
      { snapshot_date: "2026-04-03", bsr_position: 9, price_current: 34.99, price_original: 39.99, coupon_text: "10% off", availability_status: "IN_STOCK", buy_box_status: "HAS_BUY_BOX", rating_value: 4.5, review_count: 1023, title_hash: "sha256_title_v2", main_image_hash: "sha256_img_v1", variation_count: 4 },
    ],
    events: MOCK_DASHBOARD_OVERVIEW.top_events.filter(e => e.asin === "B0ABC12345"),
    summary: { price_change_count: 2, availability_change_count: 0, listing_change_count: 2, buy_box_change_count: 0 },
  },
}

// ── Events List ──────────────────────────────────────────────────────────────

export const MOCK_EVENTS: PagedResponse<Event> = {
  items: [...MOCK_DASHBOARD_OVERVIEW.top_events],
  page: 1,
  page_size: 20,
  total: MOCK_DASHBOARD_OVERVIEW.top_events.length,
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export const MOCK_JOBS: PagedResponse<Job> = {
  items: [
    {
      job_code: "job_cat_20260403_001", tracker_type: "CATEGORY", tracker_code: "ct_baby_bottle_warmers_us",
      snapshot_date: "2026-04-03", trigger_mode: "SCHEDULED", status: "SUCCESS",
      run_strategy: { provider: "APIFY", binding_code: "bind_cat_001" },
      external_run: { provider_run_id: "apify_run_abc123", status: "SUCCEEDED", started_at: "2026-04-03T02:00:03Z", finished_at: "2026-04-03T02:10:50Z" },
      summary: { expected_items: 50, imported_items: 50, events_emitted: 3 },
      error: null, created_at: "2026-04-03T02:00:00Z", started_at: "2026-04-03T02:00:02Z", finished_at: "2026-04-03T02:13:10Z",
    },
    {
      job_code: "job_cmp_20260403_001", tracker_type: "COMPETITOR", tracker_code: "cmp_baby_bottle_warmers_us",
      snapshot_date: "2026-04-03", trigger_mode: "SCHEDULED", status: "SUCCESS",
      run_strategy: { provider: "APIFY", binding_code: "bind_cmp_001" },
      external_run: { provider_run_id: "apify_run_def456", status: "SUCCEEDED", started_at: "2026-04-03T03:00:02Z", finished_at: "2026-04-03T03:08:30Z" },
      summary: { expected_items: 3, imported_items: 3, events_emitted: 3 },
      error: null, created_at: "2026-04-03T03:00:00Z", started_at: "2026-04-03T03:00:01Z", finished_at: "2026-04-03T03:10:00Z",
    },
    {
      job_code: "job_cat_20260402_001", tracker_type: "CATEGORY", tracker_code: "ct_baby_bottle_warmers_us",
      snapshot_date: "2026-04-02", trigger_mode: "SCHEDULED", status: "SUCCESS",
      run_strategy: { provider: "APIFY" },
      summary: { expected_items: 50, imported_items: 50, events_emitted: 1 },
      error: null, created_at: "2026-04-02T02:00:00Z", started_at: "2026-04-02T02:00:02Z", finished_at: "2026-04-02T02:12:40Z",
    },
    {
      job_code: "job_cat_20260401_fail", tracker_type: "CATEGORY", tracker_code: "ct_bottle_sterilizers_us",
      snapshot_date: "2026-04-01", trigger_mode: "SCHEDULED", status: "FAILED",
      run_strategy: { provider: "APIFY" },
      external_run: { provider_run_id: "apify_run_fail789", status: "TIMED_OUT", started_at: "2026-04-01T02:00:03Z", finished_at: "2026-04-01T02:30:00Z" },
      summary: { expected_items: 50, imported_items: 0, events_emitted: 0 },
      error: { code: "EXTERNAL_RUN_TIMED_OUT", message: "Apify actor run exceeded 30-minute timeout." },
      created_at: "2026-04-01T02:00:00Z", started_at: "2026-04-01T02:00:02Z", finished_at: "2026-04-01T02:30:05Z",
    },
  ],
  page: 1,
  page_size: 20,
  total: 4,
}

// ── Weekly Digests ───────────────────────────────────────────────────────────

export const MOCK_WEEKLY_DIGESTS: PagedResponse<WeeklyDigest> = {
  items: [
    {
      digest_code: "wd_2026w14_ws_demo_us",
      week_start: "2026-03-28",
      week_end: "2026-04-03",
      tracker_refs: [
        { tracker_type: "CATEGORY", tracker_code: "ct_baby_bottle_warmers_us", tracker_name: "Baby Bottle Warmers - US" },
        { tracker_type: "COMPETITOR", tracker_code: "cmp_baby_bottle_warmers_us", tracker_name: "Bottle Warmer Competitors - US" },
      ],
      summary: { new_entrant_count: 4, returning_count: 2, top10_enter_count: 1, price_change_count: 9, listing_change_count: 5 },
      threats: MOCK_DASHBOARD_OVERVIEW.top_threats,
      report_storage_uri: "s3://market-tracker/reports/weekly/wd_2026w14_ws_demo_us.json",
      created_at: "2026-04-03T10:00:00Z",
    },
  ],
  page: 1,
  page_size: 20,
  total: 1,
}
