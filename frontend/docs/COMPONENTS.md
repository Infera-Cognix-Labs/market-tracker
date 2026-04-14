# Component Reference

All page components live in `components/`. Each page is a self-contained React component that handles its own data fetching, local state, and rendering.

---

## Shared Infrastructure

### `shared/DesignTokens.ts`
Central design system. Exports a `T` object with all colors (`bg0`–`bg4`, `text0`–`text3`, `border`, `amber`, `blue`, `green`, `red`, `teal`, `purple`), font family references (`mono`, `sans`), and spacing constants. All components import from here — no hardcoded colors anywhere else.

### `shared/types.ts`
All TypeScript interfaces matching backend API response shapes:
- `Workspace`, `DashboardOverview`, `DashboardSummary`
- `CategoryTracker`, `CategorySnapshot`, `CategorySnapshotProduct`
- `CompetitorTracker`, `TrackedProduct`, `ProductDetail`, `ProductTimeline`, `TimelinePoint`
- `ProductEvent`, `Job`, `WeeklyDigest`
- `source_refs` (with `provider`, `apify_run_id`, `dataset_id`)

### `shared/api.ts`
Typed fetch wrappers. All calls go through `/api/*` (the Next.js server-side proxy). Exports helpers for each resource group (`fetchDashboard`, `fetchCategoryTrackers`, `fetchCompetitorTrackers`, etc.).

### `shared/Badge.tsx`
Color-coded status pill. Accepts `type` (`listing` | `stock` | `exit` | `top10` | `info` | ...) and `text`. Used everywhere for availability, buy-box, severity, event type labels.

### `shared/Sidebar.tsx`
Left navigation bar. Links: Dashboard, Categories, Competitors, Alerts, Reports, Search. Jobs is intentionally hidden from navigation (accessible via direct URL only).

### `shared/AlertTypeMeta.tsx`
Maps `event_type` strings (e.g. `PRICE_DROP`, `NEW_ENTRANT`, `OUT_OF_STOCK`) to display metadata: label, color, icon, badge type.

---

## Page Components

### `dashboard/DashboardPage.tsx`

**Purpose:** High-level overview of the workspace — KPI summary, top events, and highlights from category/competitor trackers.

**Data sources:**
- `GET /dashboard/overview?timeframe=WEEKLY`

**Features:**
- 4 KPI cards: Active Trackers, Products Tracked, Events (7d), Threats (7d)
- Timeframe toggle (DAILY / WEEKLY / MONTHLY)
- 3-column highlight grid:
  - **Category Highlights** — top movers from category trackers, links to `/categories`
  - **Competitor Highlights** — tracked products with recent events, links to `/competitors`
  - **Top Threats** — highest-severity events to act on
- Top Events list with severity badges and event type labels

---

### `categories/CategoryPage.tsx`

**Purpose:** Manage category trackers (browse node tracking). View BSR snapshots of the top 50 products in a tracked category.

**Data sources:**
- `GET /category-trackers` — list of trackers
- `GET /category-trackers/{tracker_code}` — tracker detail
- `GET /category-trackers/{tracker_code}/snapshots/latest` — latest product snapshot
- `POST /category-trackers` — create tracker
- `PATCH /category-trackers/{tracker_code}` — edit tracker

**Features:**
- Sidebar list of category trackers with status badges
- Create / Edit modals (tracker name, marketplace, browse node URL/ID, rank depth, schedule)
- Snapshot metadata: captured date, total products, source info (`provider` + `apify_run_id`)
- Searchable/filterable product table with columns:
  - Rank (gold highlight for top 10)
  - Product thumbnail (36×36, fallback on error)
  - ASIN (visible external link with icon → Amazon product URL)
  - Title (truncated with ellipsis)
  - Brand
  - Price (with currency symbol `$`/`£`/`€`, strikethrough original price)
  - Rating (★ or `—` when 0)
  - Reviews (`—` when 0)
  - Availability (Badge)
  - Buy Box (Badge)
  - Coupon text

---

### `competitors/CompetitorPage.tsx`

**Purpose:** Deep-dive tracking on manually selected ASINs. View current state, historical BSR/price trends, and product events.

**Data sources:**
- `GET /competitor-trackers` — list
- `GET /competitor-trackers/{tracker_code}` — tracker + tracked products
- `GET /products/{marketplace}/{asin}` — product detail (first/last seen, buy box seller, currency)
- `GET /products/{marketplace}/{asin}/timeline?granularity=DAILY|WEEKLY|MONTHLY` — time-series data
- `GET /products/{marketplace}/{asin}/events` — event log

**Features:**
- Sidebar list of competitor trackers
- Create / Edit tracker modals
- Product list with current BSR, price, availability, recent event count
- Product detail drawer (right panel):
  - Header: ASIN, title, brand, marketplace chip
  - Stats: BSR, Price (correct currency symbol), Rating★, Reviews
  - First seen / Last seen dates
  - Tracker refs and source references
  - **BSR vs Price Trend chart** — dual Y-axis (BSR reversed left, Price right), daily/weekly/monthly toggle, change event counters
  - **Rating & Reviews Trend chart** — dual Y-axis (Rating 0–5 left, Reviews right with `k` formatting)
  - **Per-day status table** below rating chart: Date, Availability, Buy Box, Coupon, Variants
  - Product Events log (typed badges, severity, summary, timestamp)
  - "View on Amazon" external link

---

### `alerts/EventsPage.tsx`

**Purpose:** Global event feed across all tracked products and categories.

**Data sources:**
- `GET /events` (workspace-level event list)

**Features:**
- Filterable by event type and severity
- Each event shows: type badge, severity badge, title, summary, timestamp, affected ASIN

---

### `jobs/JobsPage.tsx`

**Purpose:** View scrape job queue and execution history. Hidden from main navigation.

**Data sources:**
- `GET /jobs`

**Features:**
- Job list with status, type, triggered time
- Job detail with logs/output

---

### `reports/ReportsPage.tsx`

**Purpose:** Weekly digest reports summarizing top changes across the workspace.

**Data sources:**
- `GET /weekly-digests`

**Features:**
- List of digest reports by date
- Digest detail: top events, biggest movers, new entrants, threats

---

### `search/NodeSearchPage.tsx`

**Purpose:** Search Amazon browse nodes by keyword to find the node ID/URL needed when creating a category tracker.

**Features:**
- Keyword search input
- Results list with node ID, name, path
- Copy node ID / URL action

---

## CSS Patterns

- **`.anim-fade`** — fade-in animation using CSS `animation: fadeIn .3s ease both`. Note: this creates a CSS containing block due to `transform` in keyframes, so `position: fixed` modals must be rendered **outside** any `.anim-fade` wrapper (use React Fragment to escape).
- **`.card`** — standard card container with border, background, border-radius, padding.
- **`.row-hover`** — table row hover highlight.
