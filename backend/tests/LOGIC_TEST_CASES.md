# Backend Logic Test Cases

Muc tieu: chi test business logic va persistence abstraction, khong request qua FastAPI route hay `TestClient`.

Ghi chu:
- Backend da bo hoan toan `MemoryStore`.
- Cac unit tests hien tai tap trung vao helper logic va khoi tao `MongoStore` bang mock.
- Neu can cover sau hon cho `MongoStore`, nen dung test doubles cho Beanie documents hoac mot Mongo test database rieng.

## Store Helper Logic

- `TC_HELPER_001`: tao `tracker_code` khong trung khi slug da ton tai.
- `TC_HELPER_002`: tao `job_code` tang dan dung theo `tracker_type` va `snapshot_date`.
- `TC_HELPER_003`: `_within_range` xu ly inclusive boundary dung voi `from_date` va `to_date`.
- `TC_HELPER_004`: `_aggregate_timeline_points` gom nhom timeline theo `WEEKLY`.
- `TC_HELPER_005`: `_aggregate_timeline_points` gom nhom timeline theo `MONTHLY`.
- `TC_HELPER_006`: `_build_timeline_summary` dem dung `PRICE_CHANGED`, `AVAILABILITY_CHANGED`, listing changes, `BUY_BOX_CHANGED`.
- `TC_HELPER_007`: `_sort_events` uu tien severity cao hon va event moi hon.
- `TC_HELPER_008`: `_build_top_threats` chi tao threat khi co nhieu hon mot event type hoac co event severity cao.
- `TC_HELPER_009`: `_build_dashboard_overview` bo qua tracker khong `ACTIVE`.
- `TC_HELPER_010`: `build_store` khoi tao `MongoStore` va goi `init_beanie` dung database/documents.

## Mongo Store Logic

Nhung case duoi day van la business cases can cover, nhung do backend chi con Mongo path nen nen duoc test bang mock cho Beanie layer hoac bang test database rieng.

## Category Tracker Logic

- `TC_CATEGORY_001`: seed demo data xuat hien trong `list_category_trackers`.
- `TC_CATEGORY_002`: `create_category_tracker` set default `top_n=50`, `status=ACTIVE`, `snapshot_count=0`.
- `TC_CATEGORY_003`: khong cho tao tracker trung `marketplace + browse_node_id`.
- `TC_CATEGORY_004`: `update_category_tracker` chi cap nhat cac mutable fields duoc phep.
- `TC_CATEGORY_005`: `get_category_tracker` nem `NotFoundError` khi tracker khong ton tai.
- `TC_CATEGORY_006`: `get_latest_category_snapshot` tra ve snapshot moi nhat.
- `TC_CATEGORY_007`: `get_latest_category_snapshot` nem `NotFoundError` khi tracker chua co snapshot.

## Competitor Tracker Logic

- `TC_COMPETITOR_001`: `create_competitor_tracker` tao `tracked_asins` voi `added_at`.
- `TC_COMPETITOR_002`: `create_competitor_tracker` build `tracked_products` tu product/event da seed.
- `TC_COMPETITOR_003`: `replace_tracked_asins` giu nguyen `added_at` cua ASIN da ton tai.
- `TC_COMPETITOR_004`: `replace_tracked_asins` cap nhat dung `tracked_asin_count`.
- `TC_COMPETITOR_005`: `update_competitor_tracker` cap nhat `track_fields`, `schedule`, `status`, `name`.
- `TC_COMPETITOR_006`: `get_competitor_tracker` nem `NotFoundError` khi tracker khong ton tai.

## Product Logic

- `TC_PRODUCT_001`: `get_product_detail` tra ve canonical product da seed.
- `TC_PRODUCT_002`: `get_product_timeline` loc dung timeline theo `from_date`/`to_date`.
- `TC_PRODUCT_003`: `get_product_timeline` aggregate dung voi `WEEKLY`.
- `TC_PRODUCT_004`: `get_product_timeline` aggregate dung voi `MONTHLY`.
- `TC_PRODUCT_005`: `get_product_timeline` nem `BadRequestError` neu `from_date > to_date`.
- `TC_PRODUCT_006`: `get_product_timeline` nem `NotFoundError` neu khoang thoi gian khong co du lieu.
- `TC_PRODUCT_007`: `get_product_detail` nem `NotFoundError` voi ASIN khong ton tai.

## Event Logic

- `TC_EVENT_001`: `list_events` loc dung theo `tracker_type`, `tracker_code`, `marketplace`, `asin`, `event_type`, `severity`.
- `TC_EVENT_002`: `list_events` phan trang dung.
- `TC_EVENT_003`: `list_events` nem `BadRequestError` neu `from_date > to_date`.

## Job Logic

- `TC_JOB_001`: `list_jobs` loc dung theo `tracker_type` va `status`.
- `TC_JOB_002`: `create_job` tu dien `snapshot_date` bang ngay hien tai neu request khong truyen.
- `TC_JOB_003`: `create_job` map dung `binding_code` cho `CATEGORY` va `COMPETITOR`.
- `TC_JOB_004`: `create_job` nem `ConflictError` khi trung `tracker_type + tracker_code + snapshot_date`.
- `TC_JOB_005`: `create_job` nem `NotFoundError` khi tracker khong ton tai.
- `TC_JOB_006`: `get_job` nem `NotFoundError` khi `job_code` khong ton tai.
- `TC_JOB_007`: `list_jobs` nem `BadRequestError` neu `from_date > to_date`.

## Dashboard And Digest Logic

- `TC_DASHBOARD_001`: `get_dashboard_overview` dem dung so tracker active.
- `TC_DASHBOARD_002`: `get_dashboard_overview` build `top_events` va `top_threats` theo event data.
- `TC_DIGEST_001`: `list_weekly_digests` loc dung theo `week_start`.
- `TC_DIGEST_002`: `get_weekly_digest` tra ve digest da seed.
- `TC_DIGEST_003`: `get_weekly_digest` nem `NotFoundError` khi digest khong ton tai.
