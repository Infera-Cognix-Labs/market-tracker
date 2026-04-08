# BE_ARCHITECTURE_TODO.md

Derived from `backend/docs/BE_ARCHITECTURE.md` and reviewed against the current backend codebase on 2026-04-03.

## Legend

- `[x]` implemented clearly in the current codebase
- `[ ]` not implemented yet, or only partially scaffolded

## Quick Review

- The current backend matches a contract-first `FastAPI + MongoDB` monolith more than the target modular monolith with workers.
- Read-side APIs, tracker CRUD, and snapshot-backed product timeline reads are implemented.
- The backend now has real `services/` and `integrations/` seams plus an Apify dispatch path.
- Webhook/poller -> importer worker -> normalization -> snapshot -> diff/event runtime generation now runs in code.
- `app/store.py` is now a thin facade over extracted services instead of the main home for business logic.

## 1. App Shell And Topology

- [x] FastAPI app bootstrap, healthcheck, and API router wiring exist.
- [x] MongoDB + Beanie is the active persistence path.
- [x] Background worker process pool exists.
- [x] Scheduler worker exists.
- [x] Poller worker exists.
- [x] Import worker exists.
- [x] Digest worker exists.
- [x] Object storage integration exists.

## 2. Logical Domains And Modules

- [x] `tracker_management`
  Notes: category/competitor tracker CRUD, validation, and tracked ASIN replacement are implemented.
- [x] `apify_gateway`
  Notes: dedicated `app/integrations/apify_gateway.py` exists and resolves dispatch bindings from `apify-config.yaml` (non-secret actor config) plus secret token from env/secret file.
- [x] `run_orchestrator`
  Notes: background dispatch now moves jobs from `QUEUED` into the external-run path and records failures on the job.
- [x] `webhook_receiver`
- [x] `result_importer`
  Notes: `ResultImporterService` imports Apify dataset items into `raw_import_batches` with replay via stored batches.
- [x] `normalization_service`
  Notes: deterministic normalization now maps common provider payload shapes into internal product records.
- [x] `snapshot_service`
  Notes: runtime writes now create/update `category_snapshots`, `product_snapshots`, and update `products`.
- [x] `diff_engine`
  Notes: `app/services/diff_service.py` compares current snapshots with historical snapshots and emits diff candidates.
- [x] `event_engine`
  Notes: `app/services/event_engine.py` maps diff candidates into events, computes deterministic dedupe keys, and persists idempotently.
- [x] `dashboard_query`
  Notes: dashboard, product, event, job, and digest read APIs exist; product timeline now reads from `product_snapshots` instead of `product_timelines`.
- [x] `report_service`
  Notes: weekly digest generation now runs in `app/services/digest_service.py`; read APIs continue using `weekly_digests` read model.
- [x] `ops_monitoring`

## 3. Runtime Flow

- [x] Create logical tracking jobs from API requests.
- [x] Dispatch external Apify runs from created jobs.
- [x] Persist `apify_runs` records.
- [x] Receive and validate Apify webhooks.
- [x] Poll Apify run status as fallback.
- [x] Import dataset items into internal raw storage.
- [x] Normalize provider payloads into stable internal models.
- [x] Create category/product snapshots from normalized data.
- [x] Diff snapshots and emit event candidates.
- [x] Apply event rules and persist derived events.
- [x] Update jobs through `QUEUED -> DISPATCHING -> RUNNING_EXTERNAL/FAILED` during dispatch.
- [x] Update jobs through `IMPORTING -> PROCESSING -> SUCCESS/PARTIAL_SUCCESS/FAILED` during downstream processing.

## 4. State And Data Ownership

- [x] Internal tracker configuration is owned in MongoDB.
- [x] Internal job records exist in `tracking_jobs`.
- [x] Internal copy of external run metadata exists in `apify_runs`.
- [x] Raw provider payload storage exists via `raw_import_batches` or object storage.
  Notes: raw payload batches can now be offloaded to local object storage via `raw_storage_uri` and replayed back for normalization.
- [x] Internal product registry exists in `products`.
- [x] Internal category snapshots collection exists.
- [x] Internal product snapshots collection exists.
- [x] Internal tracking events collection exists.
- [x] Internal weekly digests collection exists.
- [x] Append-only snapshot/event write policy is enforced in runtime code.
  Notes: runtime snapshot writes no longer overwrite existing snapshot payloads; existing snapshots only merge tracker refs when needed.

## 5. Idempotency

- [x] One logical job per `(workspace_id, tracker_type, tracker_code, snapshot_date)`.
- [x] One `apify_run` per `apify_run_id`.
- [x] One raw import batch per `(apify_run_id, batch_no)`.
- [x] One category snapshot per `(workspace_id, tracker_code, snapshot_date)`.
- [x] One product snapshot per `(marketplace, asin, snapshot_date)`.
  Notes: the implemented unique index is workspace-scoped as `(workspace_id, marketplace, asin, snapshot_date)`.
- [x] Stable event dedupe key is enforced.
  Notes: event engine now generates deterministic `dedupe_key` values and `tracking_events` enforces workspace-scoped uniqueness on `(workspace_id, dedupe_key)`.

## 6. API And Read Side

- [x] Dashboard overview API exists.
- [x] Category tracker CRUD plus latest snapshot API exists.
- [x] Competitor tracker CRUD plus tracked ASIN replacement API exists.
- [x] Product detail and timeline APIs exist.
- [x] Event list API exists.
- [x] Job list/create/detail APIs exist.
- [x] Weekly digest list/detail APIs exist.

## 7. Observability And Security

- [x] Request IDs are attached at HTTP middleware level.
- [x] Structured logs for job/run/import/snapshot/event lifecycle exist.
  Notes: structured logs now span dispatch, webhook/poller lifecycle, import/snapshot/event phases, scheduler, and digest generation.
- [x] Metrics for jobs, run latency, import lag, normalization error rate, snapshot latency, and digest latency exist.
- [x] Correlation keys such as `job_code`, `tracker_code`, `apify_run_id`, and `snapshot_date` are propagated consistently.
- [x] Apify token is loaded from environment config instead of being hardcoded in app logic.
- [x] Secret management integration beyond local env loading exists.
  Notes: `APIFY_TOKEN_FILE` can be used for mounted secret files while keeping non-secret actor config in `apify-config.yaml`.
- [x] Restricted and verified webhook endpoint exists.
  Notes: `APIFY_WEBHOOK_SECRET` is enforced when configured; local/dev can still run unsigned when the secret is intentionally unset.
- [x] Data minimization and raw payload offload strategy exists.
  Notes: importer can offload large raw batches to object storage and keep only storage URI in MongoDB.

## 8. Folder Structure Alignment

- [x] `app/api`, `app/config`, `app/core`, `app/models`, and `app/main.py` exist.
- [ ] Separate `schemas/` package exists.
- [x] Separate `integrations/` package exists.
- [x] Separate `services/` package exists.
- [x] Separate `workers/` package exists.
- [x] Module boundaries from the architecture doc are reflected in the code layout.
  Notes: first real seams now live in `services/`, `integrations/`, and a thinner `store` facade; dedicated worker pool runner is available under `app/workers/worker_pool.py`.

## Suggested Next Steps

1. [x] Extract `tracker_management`, `dashboard_query`, and `job_service` out of `app/store.py` to create the first real module seams without changing API contracts.
2. [x] Implement `apify_gateway` and `run_orchestrator` so the `create_job` flow can dispatch beyond `QUEUED`.
3. [x] Add `apify_runs` and `raw_import_batches` documents before building importer/normalization logic, so idempotency and replay are modeled explicitly.
4. [x] Remove `product_timelines` as the source of truth and serve product timeline reads from `product_snapshots`.
5. [x] Add lightweight structured logging and correlation context for job creation and Apify dispatch flows.

## Next Follow-Up

1. [x] Implement `webhook_receiver` and `poller` so `RUNNING_EXTERNAL` jobs can progress without manual inspection.
2. [x] Build `result_importer`, `normalization_service`, and `snapshot_service` on top of `raw_import_batches`.
3. [x] Add runtime diff/event generation plus event dedupe enforcement on top of persisted snapshots.
4. [x] Add scheduler and digest workers with periodic loops and one-shot execution mode.
5. [x] Add optional raw payload offload and replay path before importer volume grows.
