# Airflow 3 Orchestration

Repo này có sẵn 4 DAG Airflow 3 để thay thế các loop worker nội bộ:

- `market_tracker_schedule_reconcile`
- `market_tracker_apify_poller`
- `market_tracker_importer`
- `market_tracker_weekly_digest`

Các DAG nằm trong [`backend/dags`](/home/duncan-nguyen/workspace/infera/market-tracker/backend/dags) và chỉ gọi lại business logic hiện có trong `app.store`.

## Mô hình chạy

- Tracker schedule vẫn được giữ trong MongoDB qua `schedule.frequency` và `schedule.hour_utc`.
- Airflow không tạo DAG riêng cho từng tracker.
- Mỗi DAG chạy một batch rồi thoát; retry, scheduling, pause/unpause do Airflow quản lý.

## Lịch mặc định

- Scheduler reconcile: `0 0 * * *`
- Apify poller: `* * * * *`
- Importer: `* * * * *`
- Weekly digest: `0 0 * * 1`

Scheduler reconcile mặc định chạy vào `00:00 UTC` mỗi ngày.
Weekly digest mặc định chạy vào `00:00 UTC` mỗi thứ Hai.

## Biến môi trường DAG

- `AIRFLOW_MARKET_TRACKER_SCHEDULE_RECONCILE_ENABLED=true`
- `AIRFLOW_MARKET_TRACKER_SCHEDULE_RECONCILE_CRON=0 0 * * *`
- `AIRFLOW_MARKET_TRACKER_APIFY_POLLER_ENABLED=true`
- `AIRFLOW_MARKET_TRACKER_APIFY_POLLER_CRON=* * * * *`
- `AIRFLOW_MARKET_TRACKER_IMPORTER_ENABLED=true`
- `AIRFLOW_MARKET_TRACKER_IMPORTER_CRON=* * * * *`
- `AIRFLOW_MARKET_TRACKER_WEEKLY_DIGEST_ENABLED=true`
- `AIRFLOW_MARKET_TRACKER_WEEKLY_DIGEST_CRON=0 0 * * 1`

## Deploy

Airflow worker/scheduler cần có cùng runtime context với backend:

- source code `backend/app`
- source code `backend/dags`
- `app-config.yaml`
- secrets/env cho MongoDB, Apify, storage

Neu deploy dung external MongoDB, hay truyen cung mot `MONGO_URI` cho backend va Airflow. Neu khong dung `MONGO_URI`, can dam bao `MONGO_HOST`/`MONGO_PORT` cua Airflow trung voi backend thay vi hardcode hostname noi bo nhu `mongodb`.

Không cần thêm `apache-airflow` vào dependency runtime của API service. Airflow dependency chỉ cần có trong image hoặc environment của Airflow.

## Cutover đề xuất

1. Deploy DAGs ở trạng thái paused.
2. Manual trigger từng DAG và kiểm tra log/task result.
3. Tắt worker loop cũ tương ứng.
4. Unpause DAG tương ứng trong Airflow.
5. Sau khi toàn bộ DAG ổn định, gỡ `worker_pool` khỏi process manager production.
