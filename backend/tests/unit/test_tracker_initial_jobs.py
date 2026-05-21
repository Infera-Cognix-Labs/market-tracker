from __future__ import annotations

from types import SimpleNamespace

from fastapi import BackgroundTasks

from app.api.v1.endpoints._tracker_initial_jobs import create_and_dispatch_initial_job
from app.api.v1.endpoints.category_trackers import create_category_tracker
from app.api.v1.endpoints.competitor_trackers import create_competitor_tracker
from app.core.errors import ConflictError
from app.models.api import (
    CategoryScope,
    CategoryTrackerCreateRequest,
    CompetitorTrackerCreateRequest,
    CompetitorTrackFields,
    TrackerScheduleInput,
    TrackerType,
    TrackedAsinWrite,
    TriggerMode,
)


def test_create_and_dispatch_initial_job_runs_immediately(run_async):
    captured: dict[str, object] = {}

    class FakeStore:
        async def create_job(self, workspace_id, payload):
            captured["create_job"] = (
                workspace_id,
                payload.tracker_type,
                payload.tracker_code,
                payload.trigger_mode,
            )
            return SimpleNamespace(job_code="job_ct_new_001")

        async def dispatch_job(self, workspace_id, job_code):
            captured["dispatch_job"] = (workspace_id, job_code)

    run_async(
        create_and_dispatch_initial_job(
            store=FakeStore(),
            workspace_id="ws_demo_us",
            tracker_type=TrackerType.CATEGORY,
            tracker_code="ct_new",
        )
    )

    assert captured["create_job"] == (
        "ws_demo_us",
        TrackerType.CATEGORY,
        "ct_new",
        TriggerMode.MANUAL,
    )
    assert captured["dispatch_job"] == ("ws_demo_us", "job_ct_new_001")


def test_create_and_dispatch_initial_job_skips_conflict(run_async):
    captured: dict[str, object] = {"dispatched": False}

    class FakeStore:
        async def create_job(self, workspace_id, payload):
            raise ConflictError("already exists")

        async def dispatch_job(self, workspace_id, job_code):
            captured["dispatched"] = True

    run_async(
        create_and_dispatch_initial_job(
            store=FakeStore(),
            workspace_id="ws_demo_us",
            tracker_type=TrackerType.COMPETITOR,
            tracker_code="cmp_new",
        )
    )

    assert captured["dispatched"] is False


def test_create_category_tracker_enqueues_initial_fetch(run_async):
    captured: dict[str, object] = {}

    class FakeStore:
        async def create_category_tracker(self, workspace_id, payload):
            captured["create_tracker"] = (workspace_id, payload.name)
            return SimpleNamespace(tracker_code="ct_new", name=payload.name)

        async def create_job(self, workspace_id, payload):
            captured["create_job"] = (
                workspace_id,
                payload.tracker_type,
                payload.tracker_code,
                payload.trigger_mode,
            )
            return SimpleNamespace(job_code="job_ct_new_001")

        async def dispatch_job(self, workspace_id, job_code):
            captured["dispatch_job"] = (workspace_id, job_code)

    payload = CategoryTrackerCreateRequest(
        name="New Category",
        marketplace="amazon_us",
        scope=CategoryScope(browse_node_id="123"),
        schedule=TrackerScheduleInput(frequency="DAILY", hour_utc=0),
    )
    background_tasks = BackgroundTasks()

    tracker = run_async(
        create_category_tracker(
            workspace_id="ws_demo_us",
            payload=payload,
            background_tasks=background_tasks,
            store=FakeStore(),
        )
    )
    run_async(background_tasks())

    assert tracker.tracker_code == "ct_new"
    assert captured["create_tracker"] == ("ws_demo_us", "New Category")
    assert captured["create_job"] == (
        "ws_demo_us",
        TrackerType.CATEGORY,
        "ct_new",
        TriggerMode.MANUAL,
    )
    assert captured["dispatch_job"] == ("ws_demo_us", "job_ct_new_001")


def test_create_competitor_tracker_enqueues_initial_fetch(run_async):
    captured: dict[str, object] = {}

    class FakeStore:
        async def create_competitor_tracker(self, workspace_id, payload):
            captured["create_tracker"] = (workspace_id, payload.name)
            return SimpleNamespace(tracker_code="cmp_new", name=payload.name)

        async def create_job(self, workspace_id, payload):
            captured["create_job"] = (
                workspace_id,
                payload.tracker_type,
                payload.tracker_code,
                payload.trigger_mode,
            )
            return SimpleNamespace(job_code="job_cmp_new_001")

        async def dispatch_job(self, workspace_id, job_code):
            captured["dispatch_job"] = (workspace_id, job_code)

    payload = CompetitorTrackerCreateRequest(
        name="New Competitor",
        marketplace="amazon_us",
        tracked_asins=[TrackedAsinWrite(asin="B0ABC12345", enabled=True)],
        track_fields=CompetitorTrackFields(
            bsr=True,
            price=True,
            buy_box=True,
            availability=True,
            promotions=True,
            title_change=True,
            main_image_change=True,
            variation_change=True,
            content_change=True,
        ),
        schedule=TrackerScheduleInput(frequency="DAILY", hour_utc=0),
    )
    background_tasks = BackgroundTasks()

    tracker = run_async(
        create_competitor_tracker(
            workspace_id="ws_demo_us",
            payload=payload,
            background_tasks=background_tasks,
            store=FakeStore(),
        )
    )
    run_async(background_tasks())

    assert tracker.tracker_code == "cmp_new"
    assert captured["create_tracker"] == ("ws_demo_us", "New Competitor")
    assert captured["create_job"] == (
        "ws_demo_us",
        TrackerType.COMPETITOR,
        "cmp_new",
        TriggerMode.MANUAL,
    )
    assert captured["dispatch_job"] == ("ws_demo_us", "job_cmp_new_001")
