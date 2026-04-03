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

Lưu ý: phần scheduler, webhook receiver, orchestrator, importer và Apify execution flow mới ở mức khung tài liệu, chưa phải full production workflow.

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
```

Bạn cũng có thể dùng:

```env
MONGO_URI=mongodb://admin:secret@localhost:27017
```

## Storage

Backend chi con mot persistence path:

- `MongoStore`: dung `Beanie` va MongoDB that

App se khoi tao Mongo client va `init_beanie(...)` trong startup lifecycle.

## Chạy ứng dụng

Trong thư mục `backend`:

```bash
uv run uvicorn app.main:app --reload
```

Endpoints hữu ích:

- Health check: `GET /health`
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`

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
