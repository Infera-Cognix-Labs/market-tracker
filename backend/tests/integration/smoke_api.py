from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx


BASE_URL = os.getenv("MARKET_TRACKER_BASE_URL", "http://127.0.0.1:8001")
WORKSPACE_ID = os.getenv("MARKET_TRACKER_WORKSPACE_ID", "ws_demo_us")


def _check(response: httpx.Response, expected_status: int) -> dict:
    if response.status_code != expected_status:
        raise AssertionError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}, expected {expected_status}: {response.text}"
        )
    if not response.content:
        return {}
    return response.json()


def main() -> None:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    category_name = f"API Smoke Category {suffix}"
    competitor_name = f"API Smoke Competitor {suffix}"

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        health = _check(client.get("/health"), 200)
        assert health["status"] == "ok"

        dashboard = _check(
            client.get(
                f"/v1/workspaces/{WORKSPACE_ID}/dashboard/overview",
                params={"timeframe": "WEEKLY"},
            ),
            200,
        )
        assert "summary" in dashboard

        category_list = _check(
            client.get(f"/v1/workspaces/{WORKSPACE_ID}/category-trackers"),
            200,
        )
        assert "items" in category_list

        created_category = _check(
            client.post(
                f"/v1/workspaces/{WORKSPACE_ID}/category-trackers",
                json={
                    "name": category_name,
                    "marketplace": "amazon_us",
                    "scope": {
                        "browse_node_id": f"node_{suffix}",
                        "browse_node_url": f"https://www.amazon.com/example/{suffix}",
                    },
                    "schedule": {"frequency": "DAILY", "hour_utc": 4},
                },
            ),
            201,
        )
        category_code = created_category["tracker_code"]

        category_detail = _check(
            client.get(
                f"/v1/workspaces/{WORKSPACE_ID}/category-trackers/{category_code}"
            ),
            200,
        )
        assert category_detail["name"] == category_name

        updated_category = _check(
            client.patch(
                f"/v1/workspaces/{WORKSPACE_ID}/category-trackers/{category_code}",
                json={
                    "status": "PAUSED",
                    "tracking_config": {"top10_alert_enabled": False},
                    "schedule": {"frequency": "DAILY", "hour_utc": 7},
                },
            ),
            200,
        )
        assert updated_category["status"] == "PAUSED"
        assert updated_category["schedule"]["hour_utc"] == 7

        latest_snapshot = _check(
            client.get(
                f"/v1/workspaces/{WORKSPACE_ID}/category-trackers/ct_baby_bottle_warmers_us/snapshots/latest"
            ),
            200,
        )
        assert latest_snapshot["tracker_code"] == "ct_baby_bottle_warmers_us"

        competitor_list = _check(
            client.get(f"/v1/workspaces/{WORKSPACE_ID}/competitor-trackers"),
            200,
        )
        assert "items" in competitor_list

        created_competitor = _check(
            client.post(
                f"/v1/workspaces/{WORKSPACE_ID}/competitor-trackers",
                json={
                    "name": competitor_name,
                    "marketplace": "amazon_us",
                    "tracked_asins": [
                        {"asin": "B0ABC12345", "enabled": True},
                        {"asin": "B0XYZ67890", "enabled": True},
                    ],
                    "track_fields": {
                        "bsr": True,
                        "price": True,
                        "buy_box": True,
                        "availability": True,
                        "promotions": True,
                        "title_change": True,
                        "main_image_change": True,
                        "variation_change": True,
                        "content_change": True,
                    },
                    "schedule": {"frequency": "DAILY", "hour_utc": 5},
                },
            ),
            201,
        )
        competitor_code = created_competitor["tracker_code"]

        competitor_detail = _check(
            client.get(
                f"/v1/workspaces/{WORKSPACE_ID}/competitor-trackers/{competitor_code}"
            ),
            200,
        )
        assert competitor_detail["name"] == competitor_name

        updated_competitor = _check(
            client.patch(
                f"/v1/workspaces/{WORKSPACE_ID}/competitor-trackers/{competitor_code}",
                json={
                    "status": "PAUSED",
                    "schedule": {"frequency": "DAILY", "hour_utc": 8},
                },
            ),
            200,
        )
        assert updated_competitor["status"] == "PAUSED"
        assert updated_competitor["schedule"]["hour_utc"] == 8

        replaced_asins = _check(
            client.put(
                f"/v1/workspaces/{WORKSPACE_ID}/competitor-trackers/{competitor_code}/tracked-asins",
                json={"tracked_asins": [{"asin": "B0ABC12345", "enabled": True}]},
            ),
            200,
        )
        assert replaced_asins["stats"]["tracked_asin_count"] == 1

        product_detail = _check(
            client.get(f"/v1/workspaces/{WORKSPACE_ID}/products/amazon_us/B0ABC12345"),
            200,
        )
        assert product_detail["asin"] == "B0ABC12345"

        product_timeline = _check(
            client.get(
                f"/v1/workspaces/{WORKSPACE_ID}/products/amazon_us/B0ABC12345/timeline",
                params={
                    "from_date": "2026-04-01",
                    "to_date": "2026-04-03",
                    "granularity": "DAILY",
                },
            ),
            200,
        )
        assert len(product_timeline["points"]) == 3

        events = _check(
            client.get(
                f"/v1/workspaces/{WORKSPACE_ID}/events",
                params={"event_type": "PRICE_CHANGED"},
            ),
            200,
        )
        assert events["items"]

        jobs = _check(
            client.get(f"/v1/workspaces/{WORKSPACE_ID}/jobs"),
            200,
        )
        assert "items" in jobs

        created_job = _check(
            client.post(
                f"/v1/workspaces/{WORKSPACE_ID}/jobs",
                json={
                    "tracker_type": "CATEGORY",
                    "tracker_code": category_code,
                    "trigger_mode": "MANUAL",
                },
            ),
            202,
        )
        job_code = created_job["job_code"]

        job_detail = _check(
            client.get(f"/v1/workspaces/{WORKSPACE_ID}/jobs/{job_code}"),
            200,
        )
        assert job_detail["job_code"] == job_code

        digest_list = _check(
            client.get(f"/v1/workspaces/{WORKSPACE_ID}/reports/weekly-digests"),
            200,
        )
        assert digest_list["items"]

        digest_detail = _check(
            client.get(
                f"/v1/workspaces/{WORKSPACE_ID}/reports/weekly-digests/wd_2026w14_ws_demo_us"
            ),
            200,
        )
        assert digest_detail["digest_code"] == "wd_2026w14_ws_demo_us"

    print("All API smoke checks passed.")


if __name__ == "__main__":
    main()
