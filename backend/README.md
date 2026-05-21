# Market Tracker Backend

Backend service cho Market Tracker, implement bằng `FastAPI` và `MongoDB` qua `Beanie`.

Hiện tại backend đi theo hướng `contract-first`:
- Contract API lấy từ [docs/api/market-tracker.openapi.yaml](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/api/market-tracker.openapi.yaml)
- Dữ liệu demo seed từ [docs/api/mock](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/api/mock)
- Persistence layer chỉ dùng `MongoDB` qua `Beanie`

## Mục tiêu hiện tại

Backend đang tập trung vào các read/write flows chính cho:
- dashboard overview
- category trackers
- competitor trackers
- products và timeline
- events
- jobs
- weekly digests

Lưu ý: webhook receiver, poller fallback, import worker, scheduler worker, digest worker, normalization, snapshot persistence, diff/event generation, raw payload offload, va worker pool runner da co runtime flow co the chay. Observability nang cao tiep tuc duoc nang cap theo nhu cau.

## Tech Stack

- Python `>=3.13`
- FastAPI
- Beanie
- MongoDB
- Pydantic v2
- Pytest
- Uvicorn

## Cấu trúc thư mục

```text
backend/
├── app/
│   ├── api/v1/                 # routers và dependencies
│   ├── config/                 # đọc cấu hình từ env
│   ├── core/                   # errors, utils
│   ├── models/                 # Pydantic schemas + Beanie documents
│   ├── main.py                 # FastAPI app entrypoint
│   ├── seed.py                 # load mock data từ docs
│   └── store.py                # logic layer + persistence abstraction
├── docs/                       # OpenAPI, mock payload, kiến trúc, DB schema
├── tests/                      # logic-only unit tests
├── pyproject.toml
└── uv.lock
```

## Yêu cầu môi trường

- Cài `uv`
- Python `3.13`
- MongoDB

## Cài dependencies

Chạy trong thư mục `backend`:

```bash
uv sync
```

## Cấu hình `.env`

Backend đọc secret từ file `.env`.

Ví dụ tối thiểu:

```env
MONGO_USERNAME=admin
MONGO_PASSWORD=secret
APIFY_TOKEN=your_apify_token
```

Bạn cũng có thể dùng một biến secret duy nhất cho Mongo:

```env
MONGO_URI=mongodb://admin:secret@localhost:27017
```

## App config (`app-config.yaml`)

Tat ca config khong nhay cam (app, mongodb host/port/database, apify runtime + actor bindings, storage, worker intervals) duoc dat trong `app-config.yaml` o root `backend/` va tu dong duoc nap.

```yaml
app:
  seed_demo_data: true
mongodb:
  host: "localhost"
  port: 27017
  database: "market_tracker"
apify:
  webhook_url: "https://your-domain.example.com/v1/webhooks/apify/runs"
  bindings:
    category:
      actor_id: "saswave/amazon-product-scraper"
      task_id: ""
    competitor:
      actor_id: "saswave/amazon-product-scraper"
      task_id: ""
```

Secret `APIFY_TOKEN` tiep tuc lay tu env.

Khuyen nghi hien tai: dung chung actor `saswave/amazon-product-scraper` cho ca category va competitor de giu output schema dong nhat (`asin`, `title`, `url`, `image`, `price`, `rating`, `reviewsCount`) va map on dinh vao luong normalize -> snapshot -> event.

## Storage

Backend chi con mot persistence path:

- `MongoStore`: dung `Beanie` va MongoDB that

App se khoi tao Mongo client va `init_beanie(...)` trong startup lifecycle.

## Chạy ứng dụng

Trong thư mục `backend`:

```bash
uv run uvicorn app.main:app --reload
```

Nếu muốn poll fallback cho Apify runs:

```bash
uv run python -m app.workers.poller_worker --once
```

Hoặc chạy loop liên tục:

```bash
uv run python -m app.workers.poller_worker
```

Chay import worker mot lan:

```bash
uv run python -m app.workers.import_worker --once
```

Hoac chay import worker lien tuc:

```bash
uv run python -m app.workers.import_worker
```

Chay scheduler worker mot lan:

```bash
uv run python -m app.workers.scheduler_worker --once
```

Hoac chay scheduler worker lien tuc:

```bash
uv run python -m app.workers.scheduler_worker
```

Chay digest worker mot lan:

```bash
uv run python -m app.workers.digest_worker --once
```

Hoac chay digest worker lien tuc:

```bash
uv run python -m app.workers.digest_worker
```

Chay worker pool (scheduler + poller + importer + digest) trong 1 process:

```bash
uv run python -m app.workers.worker_pool
```

Chay worker pool 1 batch roi thoat:

```bash
uv run python -m app.workers.worker_pool --once
```

## Airflow 3 orchestration

Repo hiện có sẵn DAG code trong [backend/dags](/home/duncan-nguyen/workspace/infera/market-tracker/backend/dags) để migrate background scheduling sang Airflow 3:

- `market_tracker_schedule_reconcile`
- `market_tracker_apify_poller`
- `market_tracker_importer`
- `market_tracker_weekly_digest`

Các loop worker hiện tại vẫn được giữ để compatibility/manual-run trong giai đoạn cutover, nhưng production orchestration nên chuyển sang Airflow.

Khi tạo mới category tracker hoặc competitor tracker, backend sẽ enqueue một initial fetch ngay sau khi create thành công. Các lịch schedule sau đó vẫn tiếp tục chạy theo cron hoặc scheduler như cấu hình.

Tài liệu deploy và biến môi trường DAG nằm ở [AIRFLOW.md](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/AIRFLOW.md).

Endpoints hữu ích:

- Health check: `GET /health`
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- Apify webhook receiver: `POST /v1/webhooks/apify/runs`

Base API prefix:

```text
/v1
```

## Seed dữ liệu demo

Khi `app.seed_demo_data=true` trong `app-config.yaml`, app sẽ load dữ liệu từ:

- [manifest.json](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/api/mock/manifest.json)
- các file mock response/request trong [docs/api/mock](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/api/mock)

Điều này giúp backend có thể chạy được ngay cả khi chưa có pipeline crawl/import thật.

## Các nhóm API hiện có

- `dashboard`
- `category-trackers`
- `competitor-trackers`
- `products`
- `events`
- `jobs`
- `reports`

Router chính nằm ở [router.py](/home/duncan-nguyen/workspace/infera/market-tracker/backend/app/api/v1/router.py).

## Test

Hiện test suite tập trung vào `logic-only tests`, không request qua FastAPI route.
Vi backend khong con `MemoryStore`, unit tests hien tai tap trung vao helper logic va factory khoi tao `MongoStore` bang mock.

Chạy toàn bộ test:

```bash
uv run pytest -q
```

Chạy riêng unit tests:

```bash
uv run pytest tests/unit -q
```

Test cases được mô tả trong:

- [LOGIC_TEST_CASES.md](/home/duncan-nguyen/workspace/infera/market-tracker/backend/tests/LOGIC_TEST_CASES.md)

Các file test chính:

- [test_store_helpers.py](/home/duncan-nguyen/workspace/infera/market-tracker/backend/tests/unit/test_store_helpers.py)

## Logic layer hiện tại

Core logic hiện chủ yếu nằm trong [store.py](/home/duncan-nguyen/workspace/infera/market-tracker/backend/app/store.py):

- tạo và cập nhật tracker
- filter và paginate events/jobs/digests
- build dashboard overview
- build product timeline summary
- generate tracker/job codes
- seed và phục vụ dữ liệu demo

`MongoStore` dùng `Beanie` documents trong [documents.py](/home/duncan-nguyen/workspace/infera/market-tracker/backend/app/models/documents.py).

## Tài liệu tham chiếu

- [BE_ARCHITECTURE.md](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/BE_ARCHITECTURE.md)
- [DB_SCHEMA.md](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/DB_SCHEMA.md)
- [EVENT_LOGIC.md](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/EVENT_LOGIC.md)
- [Market Tracker.md](/home/duncan-nguyen/workspace/infera/market-tracker/backend/docs/Market%20Tracker.md)

## Ghi chú bảo mật

- Không nên commit `.env` chứa credentials thật.
- Nếu repo hiện đã có secret thật, nên rotate các giá trị đó và thay bằng `.env.example`.
