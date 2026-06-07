# market-tracker

Monorepo: `backend/` (FastAPI + MongoDB/Beanie) and `frontend/` (Next.js 16 + React 19).

## Developer Commands

### Backend (`cd backend`)

```bash
uv sync                        # install deps (Python 3.13 required)
uv run uvicorn app.main:app --reload  # dev server on :5000
uv run pytest -q               # run tests
uv run ruff check .            # lint
```

Workers support `--once` for single-run or no flag for continuous loop:

```bash
uv run python -m app.workers.worker_pool          # all workers in one process
uv run python -m app.workers.worker_pool --once   # single batch then exit
uv run python -m app.workers.poller_worker
uv run python -m app.workers.import_worker
uv run python -m app.workers.scheduler_worker
uv run python -m app.workers.digest_worker
```

### Frontend (`cd frontend`)

```bash
npm install
npm run dev       # dev server on :3000
npm run build     # production build
npm run lint      # eslint
npx tsc --noEmit  # typecheck (no separate script in package.json)
```

## CI Verification Order

PRs to `develop` trigger per-package CI (`.github/workflows/`):

- **Backend**: `ruff check .` → Docker build → deploy → health check → sync Airflow bind-mounts
- **Frontend**: `npm run lint` → `npx tsc --noEmit` → `npm run build` → Docker build → deploy → health check

Note: Backend pytest is currently **commented out** in CI (`backend-test.yml` line 42). Tests run locally only.

## Architecture

- **API prefix**: `/v1` (configured in `backend/app-config.yaml`)
- **Health check**: `GET /health`
- **Swagger**: `GET /docs`
- **Contract-first**: OpenAPI spec at `backend/docs/api/market-tracker.openapi.yaml`
- **Demo data**: seeded from `backend/docs/api/mock/` when `app.seed_demo_data=true`
- **Persistence**: MongoDB via Beanie documents (`backend/app/models/documents.py`)
- **Core logic**: `backend/app/store.py`
- **Config loader**: `backend/app/config/config.py` (reads `.env` + `app-config.yaml`)

## Configuration

- **Secrets**: `backend/.env` — `MONGO_URI` (or `MONGO_USERNAME`/`MONGO_PASSWORD`), `APIFY_TOKEN`
- **Non-secrets**: `backend/app-config.yaml` — app settings, Apify actor bindings/pools, storage, worker intervals
- **Frontend env**: `frontend/.env.local` — `NEXT_PUBLIC_API_URL`

## Airflow 3

DAGs in `backend/dags/` for production orchestration. In staging, `backend/dags/`, `backend/app/`, and `backend/app-config.yaml` are **bind-mounted** into Airflow containers — no Docker rebuild needed, just `git pull`. Workers in the repo are for dev/manual runs.

## Staging Deploy

GitHub Actions auto-deploy to staging on PR to `develop`. Uses Docker Compose with `docker-compose.staging.yml`. Services: frontend, backend, MongoDB, Redis, Postgres (Airflow metadata), Airflow (scheduler, worker, triggerer, dag-processor, apiserver).

## Key Files

- `backend/app/api/v1/router.py` — all API routes
- `backend/app/store.py` — core business logic
- `backend/app/models/documents.py` — MongoDB/Beanie document models
- `backend/app/config/config.py` — settings loader (env + YAML)
- `backend/dags/` — Airflow DAG definitions
- `frontend/app/` — Next.js app router pages
- `frontend/components/` — React components
