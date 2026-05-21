# market-tracker

Monorepo with two packages: `backend/` (FastAPI + MongoDB/Beanie) and `frontend/` (Next.js 16 + React 19).

## Developer Commands

### Backend
```bash
cd backend
uv sync                    # install dependencies
uv run uvicorn app.main:app --reload  # dev server (port 5000)
uv run pytest -q           # run tests
uv run ruff check .        # lint

# Workers (use --once for single run)
uv run python -m app.workers.poller_worker
uv run python -m app.workers.import_worker
uv run python -m app.workers.scheduler_worker
uv run python -m app.workers.digest_worker
uv run python -m app.workers.worker_pool    # all workers in one process
```

### Frontend
```bash
cd frontend
npm install
npm run dev              # dev server (port 3000)
npm run build            # production build
npm run lint             # lint
npx tsc --noEmit         # typecheck
```

## Architecture

- **Backend API prefix**: `/v1`
- **Health check**: `GET /health`
- **Swagger**: `GET /docs`
- **Contract-first**: OpenAPI spec at `backend/docs/api/market-tracker.openapi.yaml`
- **Demo data**: seeded from `backend/docs/api/mock/` when `app.seed_demo_data=true` in `app-config.yaml`
- **Persistence**: MongoDB via Beanie documents in `backend/app/models/documents.py`
- **Core logic**: `backend/app/store.py`

## Configuration

- Backend secrets: `.env` (MONGO_URI, APIFY_TOKEN)
- Backend config: `backend/app-config.yaml` (non-secrets)
- Frontend env: `.env.local` (NEXT_PUBLIC_API_URL)

## Airflow 3

DAGs in `backend/dags/` for production orchestration. Workers above are for dev/manual runs.

## Test Flow

1. Backend: `ruff check .` → `pytest -q`
2. Frontend: `npm run lint` → `npx tsc --noEmit` → `npm run build`

## Staging Deploy

GitHub Actions auto-deploy to staging on PR to `develop`.

Key files/directories for agents to understand the repo structure:
- backend/app/api/v1/router.py - main API routes
- backend/app/store.py - core logic
- backend/app/models/documents.py - MongoDB documents
- frontend/components/ - React components
- frontend/app/ - Next.js app router pages

# Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.