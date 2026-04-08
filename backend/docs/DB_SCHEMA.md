# DB_SCHEMA.md

## 1. Purpose

This document defines the MongoDB data model for the backend system of the Market Tracker product.

The backend **does not crawl directly**. It orchestrates **Apify Actors / Tasks**, imports dataset results, normalizes them into internal snapshots, computes business events, and serves dashboard/reporting APIs.

This schema is designed for:

- **FastAPI + Python**
- **MongoDB**
- **Apify as the external data acquisition provider**
- **Snapshot-first historical storage**
- **Event-driven business intelligence**

---

## 2. Design Principles

1. **Business state is owned internally**  
   Apify is an execution/data acquisition provider, not the source of truth for the product.

2. **Snapshots are append-only**  
   Historical state is preserved to support trend analysis, event recomputation, and auditability.

3. **Events are derived, not primary**  
   Events are generated from normalized snapshots and must be reproducible.

4. **External run lifecycle is explicit**  
   External Apify runs are tracked independently from internal business jobs.

5. **Read paths should not depend on raw payloads**  
   Dashboard and product APIs should query normalized collections, not raw imports.

6. **All write paths must be idempotent**  
   Retries must not create duplicate jobs, snapshots, or events.

---

## 3. Collection Overview

| Collection | Purpose |
|---|---|
| `category_trackers` | Stores configuration for Top-N category tracking. |
| `competitor_trackers` | Stores configuration for manual ASIN tracking. |
| `apify_actor_bindings` | Maps internal tracker types to Apify actors/tasks and input templates. |
| `tracking_jobs` | Represents one internal tracking execution intent for a tracker and snapshot date. |
| `apify_runs` | Stores lifecycle and metadata of external Apify runs triggered by the system. |
| `raw_import_batches` | Stores imported raw dataset batches from Apify before/alongside normalization. |
| `products` | Maintains the internal product registry and latest known state per marketplace + ASIN. |
| `category_snapshots` | Stores normalized Top-N category snapshot documents per tracker and day. |
| `product_snapshots` | Stores normalized per-ASIN daily snapshots for competitor/deep tracking. |
| `tracking_events` | Stores derived business events emitted by the event engine. |
| `weekly_digests` | Stores precomputed weekly summaries and report metadata. |

---

## 4. Shared Field Conventions

### 4.1 Identifiers

- `_id`: MongoDB ObjectId
- `workspace_id`: logical tenant/workspace reference
- `tracker_code`, `job_code`, `event_code`, `binding_code`: human-readable stable identifiers for external references
- `asin`: Amazon Standard Identification Number
- `marketplace`: normalized marketplace code such as `amazon_us`, `amazon_de`

### 4.2 Time fields

Use UTC timestamps for all internal datetime fields.

Recommended conventions:

- `created_at`
- `updated_at`
- `started_at`
- `finished_at`
- `captured_at`
- `event_time`

For logical daily grouping, use:

- `snapshot_date` as `YYYY-MM-DD`

### 4.3 Status fields

Use enum-like string values and keep them stable across services.

Examples:

- job status: `QUEUED`, `DISPATCHING`, `RUNNING_EXTERNAL`, `IMPORTING`, `PROCESSING`, `SUCCESS`, `PARTIAL_SUCCESS`, `FAILED`
- Apify run status: `READY`, `RUNNING`, `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `ABORTED`
- tracker status: `ACTIVE`, `PAUSED`, `ARCHIVED`

---

## 5. Collection Specifications

## 5.1 `category_trackers`

**Purpose:** stores business configuration for category-based Top-N monitoring.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "workspace_id": "ObjectId",
  "tracker_code": "ct_001",
  "name": "Baby Bottle Warmers - US",
  "marketplace": "amazon_us",
  "scope": {
    "browse_node_id": "1234567890",
    "browse_node_url": "https://www.amazon.com/..."
  },
  "tracking_config": {
    "top_n": 50,
    "top10_alert_enabled": true
  },
  "schedule": {
    "frequency": "DAILY",
    "hour_utc": 2
  },
  "binding_id": "ObjectId",
  "status": "ACTIVE",
  "stats": {
    "last_job_at": null,
    "last_success_at": null,
    "snapshot_count": 0
  },
  "created_by": "user_001",
  "created_at": "2026-03-29T00:00:00Z",
  "updated_at": "2026-03-29T00:00:00Z"
}
```

### Key indexes

```javascript
db.category_trackers.createIndex(
  { workspace_id: 1, marketplace: 1, "scope.browse_node_id": 1 },
  { unique: true }
)

db.category_trackers.createIndex({ tracker_code: 1 }, { unique: true })
db.category_trackers.createIndex({ workspace_id: 1, status: 1 })
```

---

## 5.2 `competitor_trackers`

**Purpose:** stores business configuration for manual ASIN-level deep tracking.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "workspace_id": "ObjectId",
  "tracker_code": "cmp_001",
  "name": "Bottle Warmer Competitors - US",
  "marketplace": "amazon_us",
  "tracked_asins": [
    {
      "asin": "B0ABC12345",
      "enabled": true,
      "added_at": "2026-03-29T00:00:00Z"
    }
  ],
  "track_fields": {
    "bsr": true,
    "price": true,
    "buy_box": true,
    "availability": true,
    "promotions": true,
    "title_change": true,
    "main_image_change": true,
    "variation_change": true,
    "content_change": true
  },
  "schedule": {
    "frequency": "DAILY",
    "hour_utc": 3
  },
  "binding_id": "ObjectId",
  "status": "ACTIVE",
  "stats": {
    "tracked_asin_count": 1,
    "last_job_at": null,
    "last_success_at": null
  },
  "created_by": "user_001",
  "created_at": "2026-03-29T00:00:00Z",
  "updated_at": "2026-03-29T00:00:00Z"
}
```

### Key indexes

```javascript
db.competitor_trackers.createIndex({ tracker_code: 1 }, { unique: true })
db.competitor_trackers.createIndex({ workspace_id: 1, status: 1 })
db.competitor_trackers.createIndex({ "tracked_asins.asin": 1 })
```

---

## 5.3 `apify_actor_bindings`

**Purpose:** decouples internal business trackers from Apify-specific execution details.

### Why this collection exists

Without this abstraction, tracker records become tightly coupled to one actor implementation. This collection allows the system to:

- switch actors/tasks without changing tracker schema
- version field mappings
- support different bindings by tracker type or marketplace
- evolve provider integration cleanly

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "binding_code": "bind_001",
  "binding_type": "CATEGORY",
  "provider": "APIFY",
  "execution_mode": "ACTOR",
  "actor_ref": "owner~amazon-bsr-tracker",
  "task_ref": null,
  "run_mode": "ASYNC",
  "input_template": {
    "browse_node_id": "{{scope.browse_node_id}}",
    "browse_node_url": "{{scope.browse_node_url}}",
    "marketplace": "{{marketplace}}",
    "limit": "{{tracking_config.top_n}}"
  },
  "dataset_mapping": {
    "item_type": "CATEGORY_TOP_PRODUCT",
    "field_map_version": "v1"
  },
  "webhook_config": {
    "enabled": true,
    "event_types": ["ACTOR.RUN.SUCCEEDED", "ACTOR.RUN.FAILED"]
  },
  "status": "ACTIVE",
  "created_at": "2026-03-29T00:00:00Z",
  "updated_at": "2026-03-29T00:00:00Z"
}
```

### Key indexes

```javascript
db.apify_actor_bindings.createIndex({ binding_code: 1 }, { unique: true })
db.apify_actor_bindings.createIndex({ provider: 1, actor_ref: 1, task_ref: 1 })
```

---

## 5.4 `tracking_jobs`

**Purpose:** represents one internal execution intent for a tracker and a logical snapshot date.

### Why this collection exists

A `tracking_job` is the **business-level job**. It exists even if:

- the external run fails before producing data
- the system needs to retry execution
- multiple external runs are needed for one logical job

This separates internal product logic from external provider execution.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "job_code": "job_001",
  "workspace_id": "ObjectId",
  "tracker_type": "CATEGORY",
  "tracker_id": "ObjectId",
  "snapshot_date": "2026-03-29",
  "trigger_mode": "SCHEDULED",
  "status": "RUNNING_EXTERNAL",
  "run_strategy": {
    "provider": "APIFY",
    "binding_id": "ObjectId"
  },
  "apify_run_refs": ["ObjectId"],
  "summary": {
    "expected_items": 50,
    "imported_items": 0,
    "events_emitted": 0
  },
  "error": null,
  "created_at": "2026-03-29T02:00:00Z",
  "started_at": "2026-03-29T02:00:02Z",
  "finished_at": null
}
```

### Key indexes

```javascript
db.tracking_jobs.createIndex({ job_code: 1 }, { unique: true })

db.tracking_jobs.createIndex(
  { tracker_type: 1, tracker_id: 1, snapshot_date: 1 },
  { unique: true }
)

db.tracking_jobs.createIndex({ status: 1, created_at: -1 })
db.tracking_jobs.createIndex({ workspace_id: 1, created_at: -1 })
```

---

## 5.5 `apify_runs`

**Purpose:** stores external run lifecycle and metadata for one Apify execution.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "tracking_job_id": "ObjectId",
  "provider": "APIFY",
  "actor_ref": "owner~amazon-bsr-tracker",
  "task_ref": null,
  "apify_run_id": "apify_run_123",
  "default_dataset_id": "dataset_123",
  "run_input": {
    "browse_node_id": "1234567890",
    "limit": 50
  },
  "input_hash": "sha256_xxx",
  "status": "SUCCEEDED",
  "apify_status_raw": "SUCCEEDED",
  "origin": "API",
  "started_at": "2026-03-29T02:00:03Z",
  "finished_at": "2026-03-29T02:03:10Z",
  "webhook_received_at": "2026-03-29T02:03:11Z",
  "poll_count": 2,
  "error": null,
  "created_at": "2026-03-29T02:00:03Z",
  "updated_at": "2026-03-29T02:03:11Z"
}
```

### Key indexes

```javascript
db.apify_runs.createIndex({ apify_run_id: 1 }, { unique: true })
db.apify_runs.createIndex({ tracking_job_id: 1 })
db.apify_runs.createIndex({ default_dataset_id: 1 })
db.apify_runs.createIndex({ status: 1, created_at: -1 })
```

---

## 5.6 `raw_import_batches`

**Purpose:** stores raw dataset batches imported from Apify prior to or alongside normalization.

### Notes

- For small payloads, raw items may be embedded directly.
- For large payloads, store `raw_storage_uri` and keep only metadata in MongoDB.
- This collection is the **import boundary**, not the main query model.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "tracking_job_id": "ObjectId",
  "apify_run_id": "ObjectId",
  "dataset_id": "dataset_123",
  "batch_no": 1,
  "source_item_count": 50,
  "import_status": "IMPORTED",
  "raw_items": [
    { "asin": "B0ABC12345", "rank": 1 }
  ],
  "raw_storage_uri": null,
  "imported_at": "2026-03-29T02:04:00Z",
  "created_at": "2026-03-29T02:04:00Z"
}
```

### Key indexes

```javascript
db.raw_import_batches.createIndex(
  { apify_run_id: 1, batch_no: 1 },
  { unique: true }
)

db.raw_import_batches.createIndex({ tracking_job_id: 1 })
db.raw_import_batches.createIndex({ dataset_id: 1 })
```

---

## 5.7 `products`

**Purpose:** stores the canonical product registry and latest known state per marketplace + ASIN.

### Why this collection exists

This is not the historical source. Instead, it provides:

- the latest known product identity
- a fast lookup record for product detail APIs
- a registry to connect snapshots/events across trackers

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "marketplace": "amazon_us",
  "asin": "B0ABC12345",
  "parent_asin": "B0PARENT001",
  "brand": "Example Brand",
  "title_latest": "Example Product",
  "product_url": "https://www.amazon.com/dp/B0ABC12345",
  "main_image_url_latest": "https://...",
  "first_seen_at": "2026-03-20T00:00:00Z",
  "last_seen_at": "2026-03-29T00:00:00Z",
  "current_state": {
    "price_current": 29.99,
    "price_original": 39.99,
    "currency": "USD",
    "bsr_position": 12,
    "availability_status": "IN_STOCK",
    "buy_box_status": "HAS_BUY_BOX",
    "coupon_text": "10% off",
    "last_snapshot_date": "2026-03-29"
  },
  "created_at": "2026-03-20T00:00:00Z",
  "updated_at": "2026-03-29T00:00:00Z"
}
```

### Key indexes

```javascript
db.products.createIndex({ marketplace: 1, asin: 1 }, { unique: true })
db.products.createIndex({ marketplace: 1, parent_asin: 1 })
db.products.createIndex({ brand: 1 })
```

---

## 5.8 `category_snapshots`

**Purpose:** stores one normalized Top-N category snapshot per tracker and date.

### Modeling decision

Because Top-N is small (for example, Top 50), embedding `products` inside one snapshot document is recommended.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "tracking_job_id": "ObjectId",
  "category_tracker_id": "ObjectId",
  "marketplace": "amazon_us",
  "browse_node_id": "1234567890",
  "snapshot_date": "2026-03-29",
  "captured_at": "2026-03-29T02:11:05Z",
  "top_n": 50,
  "products": [
    {
      "asin": "B0ABC12345",
      "rank_position": 1,
      "title": "Example Product",
      "brand": "Example Brand",
      "product_url": "https://www.amazon.com/dp/B0ABC12345",
      "price_current": 29.99,
      "price_original": 39.99,
      "currency": "USD",
      "rating_value": 4.5,
      "rating_count": 1023,
      "review_count": 1023,
      "image_url": "https://...",
      "availability_status": "IN_STOCK",
      "buy_box_status": "HAS_BUY_BOX",
      "coupon_text": "10% off"
    }
  ],
  "source_refs": {
    "provider": "APIFY",
    "apify_run_id": "apify_run_123",
    "dataset_id": "dataset_123"
  },
  "summary": {
    "asin_count": 50
  },
  "created_at": "2026-03-29T02:11:05Z"
}
```

### Key indexes

```javascript
db.category_snapshots.createIndex(
  { category_tracker_id: 1, snapshot_date: -1 },
  { unique: true }
)

db.category_snapshots.createIndex({ "products.asin": 1 })
db.category_snapshots.createIndex({ tracking_job_id: 1 })
```

---

## 5.9 `product_snapshots`

**Purpose:** stores one normalized per-ASIN daily snapshot for deep competitor tracking.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "tracking_job_id": "ObjectId",
  "tracker_refs": [
    {
      "tracker_type": "COMPETITOR",
      "tracker_id": "ObjectId"
    }
  ],
  "marketplace": "amazon_us",
  "asin": "B0ABC12345",
  "snapshot_date": "2026-03-29",
  "captured_at": "2026-03-29T03:05:00Z",
  "identity": {
    "parent_asin": "B0PARENT001",
    "brand": "Example Brand",
    "product_url": "https://www.amazon.com/dp/B0ABC12345"
  },
  "commercial": {
    "bsr_position": 12,
    "price_current": 29.99,
    "price_original": 39.99,
    "currency": "USD",
    "coupon_text": "10% off"
  },
  "availability": {
    "availability_status": "IN_STOCK",
    "buy_box_status": "HAS_BUY_BOX",
    "buy_box_seller_name": "Amazon"
  },
  "listing": {
    "title": "Example Product",
    "title_hash": "sha256_xxx",
    "main_image_url": "https://...",
    "main_image_hash": "sha256_img_xxx",
    "variation_count": 4,
    "variation_signature_hash": "sha256_var_xxx",
    "a_plus_signature_hash": "sha256_aplus_xxx",
    "content_signature_hash": "sha256_content_xxx"
  },
  "ratings": {
    "rating_value": 4.5,
    "rating_count": 1023,
    "review_count": 1023
  },
  "source_refs": {
    "provider": "APIFY",
    "apify_run_id": "apify_run_456",
    "dataset_id": "dataset_456",
    "source_item_index": 3
  },
  "created_at": "2026-03-29T03:05:00Z"
}
```

### Key indexes

```javascript
db.product_snapshots.createIndex(
  { marketplace: 1, asin: 1, snapshot_date: -1 },
  { unique: true }
)

db.product_snapshots.createIndex({ "tracker_refs.tracker_id": 1, snapshot_date: -1 })
db.product_snapshots.createIndex({ tracking_job_id: 1 })
```

---

## 5.10 `tracking_events`

**Purpose:** stores business-significant events derived from snapshot comparison.

### Notes

- Events are reproducible from snapshots.
- Events should be deduplicated with a stable `dedupe_key`.
- This collection is a primary read model for alerting, dashboard markers, and reporting.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "event_code": "evt_001",
  "workspace_id": "ObjectId",
  "tracker_type": "COMPETITOR",
  "tracker_id": "ObjectId",
  "marketplace": "amazon_us",
  "asin": "B0ABC12345",
  "event_type": "PRICE_CHANGED",
  "event_time": "2026-03-29T03:10:00Z",
  "snapshot_date": "2026-03-29",
  "severity": "MEDIUM",
  "title": "Price dropped from 34.99 to 29.99",
  "summary": "Detected price decrease with coupon added.",
  "payload": {
    "previous": {
      "price_current": 34.99,
      "coupon_text": null
    },
    "current": {
      "price_current": 29.99,
      "coupon_text": "10% off"
    },
    "delta": {
      "price_current_abs": -5.0,
      "price_current_pct": -14.29
    }
  },
  "source_refs": {
    "tracking_job_id": "ObjectId",
    "apify_run_id": "apify_run_456"
  },
  "dedupe_key": "PRICE_CHANGED|amazon_us|B0ABC12345|2026-03-29",
  "created_at": "2026-03-29T03:10:00Z"
}
```

### Key indexes

```javascript
db.tracking_events.createIndex({ workspace_id: 1, event_code: 1 }, { unique: true })
db.tracking_events.createIndex(
  { workspace_id: 1, dedupe_key: 1 },
  { unique: true, partialFilterExpression: { dedupe_key: { $type: "string" } } }
)
db.tracking_events.createIndex({ workspace_id: 1, tracker_code: 1, event_time: -1 })
db.tracking_events.createIndex({ asin: 1, event_time: -1 })
db.tracking_events.createIndex({ event_type: 1, event_time: -1 })
```

---

## 5.11 `weekly_digests`

**Purpose:** stores precomputed weekly summaries for dashboards, reports, and export flows.

### Suggested document shape

```json
{
  "_id": "ObjectId",
  "workspace_id": "ObjectId",
  "digest_code": "wd_001",
  "week_start": "2026-03-23",
  "week_end": "2026-03-29",
  "tracker_refs": [
    {
      "tracker_type": "CATEGORY",
      "tracker_id": "ObjectId"
    },
    {
      "tracker_type": "COMPETITOR",
      "tracker_id": "ObjectId"
    }
  ],
  "summary": {
    "new_entrant_count": 8,
    "returning_count": 3,
    "top10_enter_count": 2,
    "price_change_count": 11,
    "listing_change_count": 4
  },
  "threats": [
    {
      "asin": "B0ABC12345",
      "reason": "Entered Top 10 and dropped price"
    }
  ],
  "report_storage_uri": "s3://bucket/reports/weekly/wd_001.json",
  "created_at": "2026-03-29T10:00:00Z"
}
```

### Key indexes

```javascript
db.weekly_digests.createIndex({ digest_code: 1 }, { unique: true })
db.weekly_digests.createIndex({ workspace_id: 1, week_start: -1, week_end: -1 })
```

---

## 6. Recommended Data Ownership

| Data Type | Primary Owner |
|---|---|
| Tracker configuration | MongoDB |
| Business job lifecycle | MongoDB |
| External run lifecycle metadata | MongoDB |
| Raw provider payloads | MongoDB for small batches, object storage for large payloads |
| Normalized snapshots | MongoDB |
| Derived events | MongoDB |
| Large report exports | Object storage |

---

## 7. Idempotency Rules

### 7.1 Jobs
One logical tracker should have at most one job per `snapshot_date`.

Enforced by:
- unique index on `(tracker_type, tracker_id, snapshot_date)`

### 7.2 Raw imports
Each imported dataset batch must be unique by:
- `(apify_run_id, batch_no)`

### 7.3 Category snapshots
One category tracker should have at most one snapshot per day.

Enforced by:
- unique index on `(category_tracker_id, snapshot_date)`

### 7.4 Product snapshots
One marketplace + ASIN should have at most one daily snapshot in the normalized store.

Enforced by:
- unique index on `(marketplace, asin, snapshot_date)`

### 7.5 Events
Each event should be deduplicated by a stable `dedupe_key`.

Examples:

- `NEW_ENTRANT_TOP50|tracker_id|asin|snapshot_date`
- `PRICE_CHANGED|marketplace|asin|snapshot_date`

---

## 8. Retention Guidance

Recommended policy:

- `tracking_jobs`, `apify_runs`, `products`, `category_snapshots`, `product_snapshots`, `tracking_events`, `weekly_digests`: retain long-term
- `raw_import_batches`: keep medium-term if reprocessing is needed; archive or offload large payloads to object storage
- operational logs: external log system, not MongoDB

---

## 9. Query Access Patterns

### High-frequency reads
- get tracker details
- get current product state
- get product timeline
- get event list by tracker/date range
- get weekly summary

### High-frequency writes
- create/update jobs
- update external run status
- insert snapshots
- insert events

### Important optimization note
Read APIs must depend primarily on:
- `products`
- `category_snapshots`
- `product_snapshots`
- `tracking_events`
- `weekly_digests`

They should **not** depend on `raw_import_batches` for normal user-facing traffic.

---

## 10. Non-Goals

This schema intentionally does not model:

- low-level browser crawl state
- proxy/session management
- raw page request logs
- per-URL scrape queues

Those concerns belong to the external provider layer (Apify), not the internal product database.

---

## 11. Final Notes

This schema is optimized for:

- clear separation between internal business state and external provider state
- reliable historical analysis
- reproducible event generation
- low-friction evolution of provider integration
- dashboard-friendly query models
