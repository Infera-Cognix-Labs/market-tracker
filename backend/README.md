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

Backend đọc biến môi trường từ file `.env`.

Ví dụ tối thiểu:

```env
SEED_DEMO_DATA=true
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=market_tracker
```

Ví dụ khi dùng MongoDB:

```env
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=market_tracker
MONGO_USERNAME=admin
MONGO_PASSWORD=secret
SEED_DEMO_DATA=true
APIFY_TOKEN=your_apify_token
APIFY_TOKEN_FILE=/run/secrets/apify_token
APIFY_WEBHOOK_URL=https://your-domain.example.com/v1/webhooks/apify/runs
APIFY_WEBHOOK_SECRET=replace_me
APIFY_POLL_BATCH_SIZE=25
APIFY_POLL_INTERVAL_SECS=60
APIFY_IMPORT_BATCH_SIZE=200
APIFY_IMPORT_WORKER_BATCH_SIZE=10
APIFY_IMPORT_WORKER_INTERVAL_SECS=30
APIFY_CONFIG_FILE=apify-config.yaml
RAW_BATCH_OFFLOAD_ENABLED=false
RAW_BATCH_OFFLOAD_MIN_ITEMS=200
LOCAL_OBJECT_STORE_ROOT=outputs/object-store
SCHEDULER_WORKER_INTERVAL_SECS=60
DIGEST_WORKER_INTERVAL_SECS=3600
```

Bạn cũng có thể dùng:

```env
MONGO_URI=mongodb://admin:secret@localhost:27017
```

## Apify actor config (`apify-config.yaml`)

Toan bo config actor/task/build/memory (khong phai secret) duoc dat trong file `apify-config.yaml`:

```yaml
bindings:
	category:
		name: "Saswave Amazon Product Scraper (Category)"
		actor_id: "saswave/amazon-product-scraper"
		task_id: ""
		input_adapter: "saswave_category"
		amazon_domain: "www.amazon.com"
		build: "latest"
		memory_mbytes: 4096
	competitor:
		name: "Saswave Amazon Product Scraper (Competitor)"
		actor_id: "saswave/amazon-product-scraper"
		task_id: ""
		input_adapter: "saswave_competitor"
		amazon_domain: "www.amazon.com"
		build: "latest"
		memory_mbytes: 4096
```

Secret `APIFY_TOKEN` tiep tuc lay tu env hoac file secret (`APIFY_TOKEN_FILE`).

- `input_adapter: native`: gui payload goc theo schema job hien tai.
- `input_adapter: saswave_category`: map category tracker thanh `search_url + max_pages + amazon_domain`.
- `input_adapter: saswave_competitor`: map competitor tracker thanh `asins + amazon_domain`.

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

Khi `SEED_DEMO_DATA=true`, app sẽ load dữ liệu từ:

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
