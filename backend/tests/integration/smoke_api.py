from __future__ import annotations

import json
import os
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

BASE_URL = os.getenv("MARKET_TRACKER_BASE_URL", "http://127.0.0.1:8001")
WORKSPACE_ID_BASE = os.getenv("MARKET_TRACKER_WORKSPACE_ID", "ws_sample")
SAMPLE_XLSX_PATH = os.getenv("MARKET_TRACKER_SAMPLE_XLSX", "docs/.data/sample.xlsx")
_XML_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_ASIN_RE = re.compile(r"^(?=.*\d)[A-Z0-9]{10,12}$")


def _check(response: httpx.Response, expected_statuses: set[int]) -> dict:
    if response.status_code not in expected_statuses:
        raise AssertionError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}, expected {sorted(expected_statuses)}: {response.text}"
        )
    if not response.content:
        return {}
    return response.json()


def _print_response(label: str, status_code: int, payload: object) -> None:
    print(f"\n=== {label} ({status_code}) ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _read_sample_rows(path: str) -> list[dict[str, object]]:
    xlsx_path = Path(path)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Sample file not found: {xlsx_path}")

    with zipfile.ZipFile(xlsx_path, "r") as workbook:
        shared_xml = workbook.read("xl/sharedStrings.xml")
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml")

    shared_root = ET.fromstring(shared_xml)
    shared_values: list[str] = []
    for item in shared_root.findall("x:si", _XML_NS):
        parts = [node.text or "" for node in item.findall(".//x:t", _XML_NS)]
        shared_values.append("".join(parts))

    sheet_root = ET.fromstring(sheet_xml)
    structured_rows: list[dict[str, object]] = []
    top10_asins: list[str] = []

    for row in sheet_root.findall("x:sheetData/x:row", _XML_NS):
        row_no = int(row.attrib["r"])
        values: dict[str, str] = {}
        for cell in row.findall("x:c", _XML_NS):
            ref = cell.attrib["r"]
            col = "".join(ch for ch in ref if ch.isalpha())
            value_node = cell.find("x:v", _XML_NS)
            if value_node is None or value_node.text is None:
                continue
            raw = value_node.text
            if cell.attrib.get("t") == "s":
                values[col] = shared_values[int(raw)]
            else:
                values[col] = raw

        if 2 <= row_no <= 5:
            competitor_asins = [
                values[col]
                for col in ("D", "E", "F", "G", "H", "I")
                if values.get(col)
            ]
            keywords = [
                values[col]
                for col in ("J", "K", "L", "M", "N", "O")
                if values.get(col)
            ]
            structured_rows.append(
                {
                    "category_name": values.get("A", "UNKNOWN_CATEGORY"),
                    "browse_node_id": str(values.get("B", "")),
                    "our_asin": values.get("C", ""),
                    "competitor_asins": competitor_asins,
                    "keywords": keywords,
                }
            )

        candidate = values.get("A")
        if candidate and _ASIN_RE.fullmatch(candidate.strip().upper()):
            top10_asins.append(candidate.strip().upper())

    if len(structured_rows) < 4:
        raise RuntimeError("Expected at least 4 structured sample rows in sample.xlsx")

    if not top10_asins:
        raise RuntimeError("Expected at least 1 TOP10 ASIN in sample.xlsx")

    derived_row = {
        "category_name": "TOP10_ASIN_SAMPLE",
        "browse_node_id": f"{structured_rows[0]['browse_node_id']}_top10",
        "our_asin": top10_asins[0],
        "competitor_asins": [top10_asins[0], *structured_rows[0]["competitor_asins"][:5]],
        "keywords": [],
    }
    return [*structured_rows, derived_row]


def main() -> None:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    workspace_id = f"{WORKSPACE_ID_BASE}_{suffix}"
    samples = _read_sample_rows(SAMPLE_XLSX_PATH)

    print("\n=== Extracted 5 Samples ===")
    print(json.dumps(samples, ensure_ascii=False, indent=2))

    created_category_codes: list[str] = []

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        health_response = client.get("/health")
        health = _check(health_response, {200})
        _print_response("GET /health", health_response.status_code, health)
        assert health["status"] == "ok"

        dashboard_response = client.get(
            f"/v1/workspaces/{workspace_id}/dashboard/overview",
            params={"timeframe": "WEEKLY"},
        )
        dashboard = _check(dashboard_response, {200})
        _print_response(
            "GET /v1/workspaces/{workspace_id}/dashboard/overview",
            dashboard_response.status_code,
            dashboard,
        )
        assert "summary" in dashboard

        category_list_response = client.get(
            f"/v1/workspaces/{workspace_id}/category-trackers"
        )
        category_list = _check(category_list_response, {200})
        _print_response(
            "GET /v1/workspaces/{workspace_id}/category-trackers",
            category_list_response.status_code,
            category_list,
        )
        assert "items" in category_list

        for index, sample in enumerate(samples, start=1):
            category_name = f"{sample['category_name']} {suffix} #{index}"
            category_create_response = client.post(
                f"/v1/workspaces/{workspace_id}/category-trackers",
                json={
                    "name": category_name,
                    "marketplace": "amazon_de",
                    "scope": {
                        "browse_node_id": sample["browse_node_id"],
                        "browse_node_url": (
                            "https://www.amazon.de/s"
                            f"?i=specialty-aps&rh=n%3A{sample['browse_node_id']}"
                        ),
                    },
                    "schedule": {"frequency": "DAILY", "hour_utc": (3 + index) % 24},
                },
            )
            created_category = _check(category_create_response, {201})
            _print_response(
                f"POST /v1/workspaces/{{workspace_id}}/category-trackers [sample {index}]",
                category_create_response.status_code,
                created_category,
            )
            category_code = created_category["tracker_code"]
            created_category_codes.append(category_code)

            category_detail_response = client.get(
                f"/v1/workspaces/{workspace_id}/category-trackers/{category_code}"
            )
            category_detail = _check(category_detail_response, {200})
            _print_response(
                f"GET /v1/workspaces/{{workspace_id}}/category-trackers/{category_code}",
                category_detail_response.status_code,
                category_detail,
            )
            assert category_detail["name"] == category_name

            category_update_response = client.patch(
                f"/v1/workspaces/{workspace_id}/category-trackers/{category_code}",
                json={
                    "status": "PAUSED",
                    "tracking_config": {"top10_alert_enabled": False},
                    "schedule": {"frequency": "DAILY", "hour_utc": (8 + index) % 24},
                },
            )
            updated_category = _check(category_update_response, {200})
            _print_response(
                f"PATCH /v1/workspaces/{{workspace_id}}/category-trackers/{category_code}",
                category_update_response.status_code,
                updated_category,
            )
            assert updated_category["status"] == "PAUSED"

            latest_snapshot_response = client.get(
                f"/v1/workspaces/{workspace_id}/category-trackers/{category_code}/snapshots/latest"
            )
            latest_snapshot = _check(latest_snapshot_response, {404})
            _print_response(
                (
                    "GET /v1/workspaces/{workspace_id}/category-trackers/"
                    f"{category_code}/snapshots/latest"
                ),
                latest_snapshot_response.status_code,
                latest_snapshot,
            )

        competitor_list_response = client.get(
            f"/v1/workspaces/{workspace_id}/competitor-trackers"
        )
        competitor_list = _check(competitor_list_response, {200})
        _print_response(
            "GET /v1/workspaces/{workspace_id}/competitor-trackers",
            competitor_list_response.status_code,
            competitor_list,
        )
        assert "items" in competitor_list

        tracked_asins = []
        for sample in samples:
            our_asin = sample["our_asin"]
            if our_asin and isinstance(our_asin, str):
                tracked_asins.append({"asin": our_asin, "enabled": True})
        tracked_asins.extend(
            {"asin": asin, "enabled": True}
            for asin in samples[0]["competitor_asins"]
            if isinstance(asin, str)
        )

        # Keep order while de-duplicating ASINs.
        deduped: dict[str, dict[str, object]] = {}
        for item in tracked_asins:
            deduped[item["asin"]] = item
        tracked_asins = list(deduped.values())[:12]

        competitor_name = f"API Smoke Competitor {suffix}"
        competitor_create_response = client.post(
            f"/v1/workspaces/{workspace_id}/competitor-trackers",
            json={
                "name": competitor_name,
                "marketplace": "amazon_de",
                "tracked_asins": tracked_asins,
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
        )
        created_competitor = _check(competitor_create_response, {201})
        _print_response(
            "POST /v1/workspaces/{workspace_id}/competitor-trackers",
            competitor_create_response.status_code,
            created_competitor,
        )
        competitor_code = created_competitor["tracker_code"]

        competitor_detail_response = client.get(
            f"/v1/workspaces/{workspace_id}/competitor-trackers/{competitor_code}"
        )
        competitor_detail = _check(competitor_detail_response, {200})
        _print_response(
            f"GET /v1/workspaces/{{workspace_id}}/competitor-trackers/{competitor_code}",
            competitor_detail_response.status_code,
            competitor_detail,
        )
        assert competitor_detail["name"] == competitor_name

        competitor_update_response = client.patch(
            f"/v1/workspaces/{workspace_id}/competitor-trackers/{competitor_code}",
            json={
                "status": "PAUSED",
                "schedule": {"frequency": "DAILY", "hour_utc": 8},
            },
        )
        updated_competitor = _check(competitor_update_response, {200})
        _print_response(
            f"PATCH /v1/workspaces/{{workspace_id}}/competitor-trackers/{competitor_code}",
            competitor_update_response.status_code,
            updated_competitor,
        )
        assert updated_competitor["status"] == "PAUSED"

        replace_asins_response = client.put(
            f"/v1/workspaces/{workspace_id}/competitor-trackers/{competitor_code}/tracked-asins",
            json={"tracked_asins": tracked_asins[:3]},
        )
        replaced_asins = _check(replace_asins_response, {200})
        _print_response(
            (
                "PUT /v1/workspaces/{workspace_id}/competitor-trackers/"
                f"{competitor_code}/tracked-asins"
            ),
            replace_asins_response.status_code,
            replaced_asins,
        )
        assert replaced_asins["stats"]["tracked_asin_count"] == 3

        target_marketplace = "amazon_de"
        target_asin = samples[4]["our_asin"]
        product_detail_response = client.get(
            f"/v1/workspaces/{workspace_id}/products/{target_marketplace}/{target_asin}"
        )
        product_detail = _check(product_detail_response, {404})
        _print_response(
            f"GET /v1/workspaces/{{workspace_id}}/products/{target_marketplace}/{target_asin}",
            product_detail_response.status_code,
            product_detail,
        )

        product_timeline_response = client.get(
            f"/v1/workspaces/{workspace_id}/products/{target_marketplace}/{target_asin}/timeline",
            params={
                "from_date": "2026-04-01",
                "to_date": "2026-04-03",
                "granularity": "DAILY",
            },
        )
        product_timeline = _check(product_timeline_response, {404})
        _print_response(
            (
                "GET /v1/workspaces/{workspace_id}/products/"
                f"{target_marketplace}/{target_asin}/timeline"
            ),
            product_timeline_response.status_code,
            product_timeline,
        )

        events_response = client.get(f"/v1/workspaces/{workspace_id}/events")
        events = _check(events_response, {200})
        _print_response(
            "GET /v1/workspaces/{workspace_id}/events",
            events_response.status_code,
            events,
        )
        assert "items" in events

        jobs_list_response = client.get(f"/v1/workspaces/{workspace_id}/jobs")
        jobs = _check(jobs_list_response, {200})
        _print_response(
            "GET /v1/workspaces/{workspace_id}/jobs",
            jobs_list_response.status_code,
            jobs,
        )
        assert "items" in jobs

        create_job_response = client.post(
            f"/v1/workspaces/{workspace_id}/jobs",
            json={
                "tracker_type": "CATEGORY",
                "tracker_code": created_category_codes[0],
                "trigger_mode": "MANUAL",
            },
        )
        created_job = _check(create_job_response, {202})
        _print_response(
            "POST /v1/workspaces/{workspace_id}/jobs",
            create_job_response.status_code,
            created_job,
        )
        job_code = created_job["job_code"]

        job_detail_response = client.get(
            f"/v1/workspaces/{workspace_id}/jobs/{job_code}"
        )
        job_detail = _check(job_detail_response, {200})
        _print_response(
            f"GET /v1/workspaces/{{workspace_id}}/jobs/{job_code}",
            job_detail_response.status_code,
            job_detail,
        )
        assert job_detail["job_code"] == job_code

        digest_list_response = client.get(
            f"/v1/workspaces/{workspace_id}/reports/weekly-digests"
        )
        digest_list = _check(digest_list_response, {200})
        _print_response(
            "GET /v1/workspaces/{workspace_id}/reports/weekly-digests",
            digest_list_response.status_code,
            digest_list,
        )
        assert "items" in digest_list

        digest_detail_response = client.get(
            f"/v1/workspaces/{workspace_id}/reports/weekly-digests/wd_2099w01_{workspace_id}"
        )
        digest_detail = _check(digest_detail_response, {404})
        _print_response(
            "GET /v1/workspaces/{workspace_id}/reports/weekly-digests/{digest_code}",
            digest_detail_response.status_code,
            digest_detail,
        )

        webhook_response = client.post(
            "/v1/webhooks/apify/runs",
            json={
                "eventType": "ACTOR.RUN.SUCCEEDED",
                "resource": {
                    "id": "run_non_existing",
                    "status": "SUCCEEDED",
                },
            },
        )
        webhook_ack = _check(webhook_response, {202})
        _print_response(
            "POST /v1/webhooks/apify/runs",
            webhook_response.status_code,
            webhook_ack,
        )

    print("\nAll sample-driven API smoke checks passed.")


if __name__ == "__main__":
    main()
