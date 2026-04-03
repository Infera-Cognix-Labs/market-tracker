from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.config.config import Config
from app.integrations.apify_gateway import ApifyBindingResolutionError, ApifyRunLaunch
from app.models.api import (
    CategoryTrackerCreateRequest,
    CategoryTrackingConfigInput,
    JobCreateRequest,
    JobRunStrategy,
    JobStatus,
    JobSummary,
    ProductTimelineResponse,
    Provider,
    Timeframe,
    TrackerScheduleInput,
    TrackerType,
)
from app.services.dashboard_query_service import DashboardQueryService
from app.services.run_orchestrator import RunOrchestrator
from app.store import MongoStore


class FakeCursor:
    def __init__(self, items):
        self.items = items

    async def to_list(self):
        return self.items


class FakeDocument:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def model_dump(self, exclude=None, mode=None):
        exclude = set(exclude or [])
        return {
            key: value
            for key, value in self.__dict__.items()
            if key not in exclude and not key.startswith("_") and not callable(value)
        }

    async def save(self, *args, **kwargs):
        return None


def test_mongo_store_delegates_to_extracted_services(run_async, seed_data):
    class DummyClient:
        def close(self):
            return None

    store = MongoStore(DummyClient(), "market_tracker", Config(seed_demo_data=False))

    captured: dict[str, object] = {}

    class TrackerService:
        async def create_category_tracker(self, workspace_id, payload):
            captured["tracker"] = (workspace_id, payload.name)
            return seed_data.category_trackers[0]

    class QueryService:
        async def get_dashboard_overview(self, workspace_id, timeframe):
            captured["dashboard"] = (workspace_id, timeframe)
            return seed_data.dashboard_overview

    class Jobs:
        async def create_job(self, workspace_id, payload):
            captured["job"] = (workspace_id, payload.tracker_code)
            return seed_data.jobs[0]

        async def dispatch_job(self, workspace_id, job_code):
            captured["dispatch"] = (workspace_id, job_code)

    store.tracker_management = TrackerService()
    store.dashboard_query = QueryService()
    store.job_service = Jobs()

    category = run_async(
        store.create_category_tracker(
            seed_data.workspace_id,
            CategoryTrackerCreateRequest(
                name="New Tracker",
                marketplace="amazon_us",
                scope={"browse_node_id": "node_123"},
                tracking_config=CategoryTrackingConfigInput(top10_alert_enabled=True),
                schedule=TrackerScheduleInput(frequency="DAILY", hour_utc=4),
            ),
        )
    )
    overview = run_async(store.get_dashboard_overview(seed_data.workspace_id, Timeframe.WEEKLY))
    job = run_async(
        store.create_job(
            seed_data.workspace_id,
            JobCreateRequest(
                tracker_type=TrackerType.CATEGORY,
                tracker_code=seed_data.category_trackers[0].tracker_code,
            ),
        )
    )
    run_async(store.dispatch_job(seed_data.workspace_id, seed_data.jobs[0].job_code))

    assert category == seed_data.category_trackers[0]
    assert overview == seed_data.dashboard_overview
    assert job == seed_data.jobs[0]
    assert captured["tracker"] == (seed_data.workspace_id, "New Tracker")
    assert captured["dashboard"] == (seed_data.workspace_id, Timeframe.WEEKLY)
    assert captured["job"] == (seed_data.workspace_id, seed_data.category_trackers[0].tracker_code)
    assert captured["dispatch"] == (seed_data.workspace_id, seed_data.jobs[0].job_code)


def test_dashboard_query_builds_timeline_from_product_snapshots(run_async, monkeypatch, seed_data):
    snapshots = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **snapshot.model_dump(mode="python"),
        )
        for snapshot in seed_data.product_snapshots
    ]
    events = [
        FakeDocument(workspace_id=seed_data.workspace_id, **event.model_dump(mode="python"))
        for event in seed_data.events
        if event.asin == seed_data.products[0].asin
    ]

    monkeypatch.setattr(
        "app.services.dashboard_query_service.ProductSnapshotDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor(snapshots),
            workspace_id="workspace_id",
            marketplace="marketplace",
            asin="asin",
        ),
    )
    monkeypatch.setattr(
        "app.services.dashboard_query_service.EventDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor(events),
            workspace_id="workspace_id",
            marketplace="marketplace",
            asin="asin",
        ),
    )

    response = run_async(
        DashboardQueryService().get_product_timeline(
            workspace_id=seed_data.workspace_id,
            marketplace=seed_data.products[0].marketplace,
            asin=seed_data.products[0].asin,
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 3),
            granularity=Timeframe.DAILY,
        )
    )

    assert isinstance(response, ProductTimelineResponse)
    assert [point.snapshot_date for point in response.points] == [
        date(2026, 4, 1),
        date(2026, 4, 2),
        date(2026, 4, 3),
    ]
    assert response.summary.price_change_count == 1
    assert response.summary.listing_change_count == 1


def test_run_orchestrator_dispatch_job_success(run_async, monkeypatch, seed_data, caplog):
    caplog.set_level("INFO")

    job_document = FakeDocument(
        workspace_id=seed_data.workspace_id,
        job_code="job_cat_20260405_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code=seed_data.category_trackers[0].tracker_code,
        snapshot_date=date(2026, 4, 5),
        trigger_mode="MANUAL",
        status=JobStatus.QUEUED,
        run_strategy=JobRunStrategy(provider=Provider.APIFY, binding_code="bind_category_top50_v1"),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        created_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        error=None,
        external_run=None,
    )
    tracker_document = seed_data.category_trackers[0].model_copy(deep=True)

    saved_statuses: list[JobStatus] = []
    inserted_runs: list[object] = []

    async def fake_save(self, *args, **kwargs):
        saved_statuses.append(JobStatus(self.status))

    async def fake_job_find_one(*args, **kwargs):
        return job_document

    async def fake_tracker_find_one(*args, **kwargs):
        return tracker_document

    class FakeApifyRunDocument:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        async def insert(self):
            inserted_runs.append(self)

    job_document.save = fake_save.__get__(job_document, FakeDocument)

    monkeypatch.setattr(
        "app.services.run_orchestrator.JobDocument",
        SimpleNamespace(
            find_one=fake_job_find_one,
            workspace_id="workspace_id",
            job_code="job_code",
        ),
    )
    monkeypatch.setattr(
        "app.services.run_orchestrator.CategoryTrackerDocument",
        SimpleNamespace(
            find_one=fake_tracker_find_one,
            workspace_id="workspace_id",
            tracker_code="tracker_code",
        ),
    )
    monkeypatch.setattr("app.services.run_orchestrator.ApifyRunDocument", FakeApifyRunDocument)

    class Gateway:
        async def start_run(self, binding_code, run_input):
            assert binding_code == "bind_category_top50_v1"
            assert run_input["tracker_code"] == job_document.tracker_code
            return ApifyRunLaunch(
                provider_run_id="apify_run_test_001",
                default_dataset_id="dataset_test_001",
                status=None,
                raw_status="READY",
                started_at="2026-04-05T02:00:03Z",
                finished_at=None,
                input_hash="hash123",
                binding=SimpleNamespace(
                    binding_code=binding_code,
                    actor_id="owner/category-actor",
                    task_id=None,
                ),
                run_input=run_input,
            )

    orchestrator = RunOrchestrator(Gateway())
    run_async(orchestrator.dispatch_job(seed_data.workspace_id, job_document.job_code))

    assert saved_statuses == [JobStatus.DISPATCHING, JobStatus.RUNNING_EXTERNAL]
    assert job_document.external_run is not None
    assert job_document.external_run.provider_run_id == "apify_run_test_001"
    assert job_document.status == JobStatus.RUNNING_EXTERNAL
    assert inserted_runs[0].apify_run_id == "apify_run_test_001"
    assert any(
        getattr(record, "context", {}).get("apify_run_id") == "apify_run_test_001"
        for record in caplog.records
    )


def test_run_orchestrator_dispatch_job_failure_sets_failed_status_and_logs_context(
    run_async, monkeypatch, seed_data, caplog
):
    caplog.set_level("INFO")

    job_document = FakeDocument(
        workspace_id=seed_data.workspace_id,
        job_code="job_cat_20260405_002",
        tracker_type=TrackerType.CATEGORY,
        tracker_code=seed_data.category_trackers[0].tracker_code,
        snapshot_date=date(2026, 4, 5),
        trigger_mode="MANUAL",
        status=JobStatus.QUEUED,
        run_strategy=JobRunStrategy(provider=Provider.APIFY, binding_code="bind_category_top50_v1"),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        created_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        error=None,
        external_run=None,
    )
    tracker_document = seed_data.category_trackers[0].model_copy(deep=True)

    saved_statuses: list[JobStatus] = []

    async def fake_save(self, *args, **kwargs):
        saved_statuses.append(JobStatus(self.status))

    async def fake_job_find_one(*args, **kwargs):
        return job_document

    async def fake_tracker_find_one(*args, **kwargs):
        return tracker_document

    job_document.save = fake_save.__get__(job_document, FakeDocument)

    monkeypatch.setattr(
        "app.services.run_orchestrator.JobDocument",
        SimpleNamespace(
            find_one=fake_job_find_one,
            workspace_id="workspace_id",
            job_code="job_code",
        ),
    )
    monkeypatch.setattr(
        "app.services.run_orchestrator.CategoryTrackerDocument",
        SimpleNamespace(
            find_one=fake_tracker_find_one,
            workspace_id="workspace_id",
            tracker_code="tracker_code",
        ),
    )

    class Gateway:
        async def start_run(self, binding_code, run_input):
            raise ApifyBindingResolutionError("Missing actor/task configuration for binding.")

    orchestrator = RunOrchestrator(Gateway())
    run_async(orchestrator.dispatch_job(seed_data.workspace_id, job_document.job_code))

    assert saved_statuses == [JobStatus.DISPATCHING, JobStatus.FAILED]
    assert job_document.status == JobStatus.FAILED
    assert job_document.error is not None
    assert "Missing actor/task configuration" in job_document.error.message
    assert any(
        getattr(record, "context", {}).get("job_code") == job_document.job_code
        for record in caplog.records
    )
