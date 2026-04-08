from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from app.config.config import Config
from app.integrations.apify_gateway import (
    ApifyBindingResolutionError,
    ApifyGateway,
    ApifyRunLaunch,
    ApifyRunLookupError,
)
from app.models.api import (
    ApifyWebhookEnvelope,
    CategoryTrackerCreateRequest,
    CategoryTrackingConfigInput,
    ExternalRunStatus,
    ImportWorkerResult,
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
from app.services.apify_run_lifecycle_service import ApifyRunLifecycleService
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

    class Importer:
        async def process_pending_jobs(self):
            captured["import"] = True
            return ImportWorkerResult(
                scanned_jobs=1,
                processed_jobs=1,
                succeeded_jobs=1,
                partial_jobs=0,
                failed_jobs=0,
                skipped_jobs=0,
            )

    store.tracker_management = TrackerService()
    store.dashboard_query = QueryService()
    store.job_service = Jobs()
    store.result_importer = Importer()

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
    overview = run_async(
        store.get_dashboard_overview(seed_data.workspace_id, Timeframe.WEEKLY)
    )
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
    import_result = run_async(store.process_import_jobs())

    assert category == seed_data.category_trackers[0]
    assert overview == seed_data.dashboard_overview
    assert job == seed_data.jobs[0]
    assert captured["tracker"] == (seed_data.workspace_id, "New Tracker")
    assert captured["dashboard"] == (seed_data.workspace_id, Timeframe.WEEKLY)
    assert captured["job"] == (
        seed_data.workspace_id,
        seed_data.category_trackers[0].tracker_code,
    )
    assert captured["dispatch"] == (seed_data.workspace_id, seed_data.jobs[0].job_code)
    assert captured["import"] is True
    assert import_result.succeeded_jobs == 1


def test_apify_gateway_list_dataset_items_maps_response(run_async, monkeypatch):
    gateway = ApifyGateway(Config(apify_config={"token": "token"}).apify_config)

    def fake_list_dataset_items_sync(dataset_id, limit, offset):
        assert dataset_id == "dataset_test_001"
        assert limit == 50
        assert offset == 100
        return {
            "count": 2,
            "total": 300,
            "items": [
                {"asin": "B0BN72FYFG", "title": "One"},
                {"asin": "B09NNBBY8F", "title": "Two"},
            ],
        }

    monkeypatch.setattr(
        gateway, "_list_dataset_items_sync", fake_list_dataset_items_sync
    )

    result = run_async(
        gateway.list_dataset_items("dataset_test_001", limit=50, offset=100)
    )

    assert result.dataset_id == "dataset_test_001"
    assert result.offset == 100
    assert result.limit == 50
    assert result.count == 2
    assert result.total == 300
    assert len(result.items) == 2


def test_dashboard_query_builds_timeline_from_product_snapshots(
    run_async, monkeypatch, seed_data
):
    snapshots = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **snapshot.model_dump(mode="python"),
        )
        for snapshot in seed_data.product_snapshots
    ]
    events = [
        FakeDocument(
            workspace_id=seed_data.workspace_id, **event.model_dump(mode="python")
        )
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


def test_run_orchestrator_dispatch_job_success(
    run_async, monkeypatch, seed_data, caplog
):
    caplog.set_level("INFO")

    job_document = FakeDocument(
        workspace_id=seed_data.workspace_id,
        job_code="job_cat_20260405_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code=seed_data.category_trackers[0].tracker_code,
        snapshot_date=date(2026, 4, 5),
        trigger_mode="MANUAL",
        status=JobStatus.QUEUED,
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY, binding_code="bind_category_top50_v1"
        ),
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
    monkeypatch.setattr(
        "app.services.run_orchestrator.ApifyRunDocument", FakeApifyRunDocument
    )

    class Gateway:
        config = SimpleNamespace(webhook_url=None)

        async def start_run(self, binding_code, run_input, webhooks=None):
            assert binding_code == "bind_category_top50_v1"
            assert run_input["tracker_code"] == job_document.tracker_code
            assert webhooks is None
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


def test_run_orchestrator_dispatch_job_registers_webhook(
    run_async, monkeypatch, seed_data
):
    job_document = FakeDocument(
        workspace_id=seed_data.workspace_id,
        job_code="job_cat_20260405_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code=seed_data.category_trackers[0].tracker_code,
        snapshot_date=date(2026, 4, 5),
        trigger_mode="MANUAL",
        status=JobStatus.QUEUED,
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY, binding_code="bind_category_top50_v1"
        ),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        created_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        error=None,
        external_run=None,
    )
    tracker_document = seed_data.category_trackers[0].model_copy(deep=True)
    captured_webhooks: list[dict[str, object]] | None = None

    async def fake_save(self, *args, **kwargs):
        return None

    async def fake_job_find_one(*args, **kwargs):
        return job_document

    async def fake_tracker_find_one(*args, **kwargs):
        return tracker_document

    class FakeApifyRunDocument:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        async def insert(self):
            return None

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
    monkeypatch.setattr(
        "app.services.run_orchestrator.ApifyRunDocument", FakeApifyRunDocument
    )

    class Gateway:
        config = SimpleNamespace(
            webhook_url="https://example.com/v1/webhooks/apify/runs",
        )

        async def start_run(self, binding_code, run_input, webhooks=None):
            nonlocal captured_webhooks
            captured_webhooks = webhooks
            return ApifyRunLaunch(
                provider_run_id="apify_run_test_001",
                default_dataset_id="dataset_test_001",
                status=ExternalRunStatus.READY,
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

    assert captured_webhooks is not None
    assert (
        captured_webhooks[0]["request_url"]
        == "https://example.com/v1/webhooks/apify/runs"
    )
    assert captured_webhooks[0]["event_types"] == [
        "ACTOR.RUN.SUCCEEDED",
        "ACTOR.RUN.FAILED",
        "ACTOR.RUN.ABORTED",
        "ACTOR.RUN.TIMED_OUT",
    ]


def test_apify_run_lifecycle_webhook_success(run_async, monkeypatch):
    run_document = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_cat_20260405_001",
        apify_run_id="apify_run_test_001",
        status="RUNNING",
        apify_status_raw="RUNNING",
        default_dataset_id=None,
        started_at=None,
        finished_at=None,
        webhook_received_at=None,
        poll_count=0,
        error=None,
        updated_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
    )
    job_document = FakeDocument(
        workspace_id="ws_demo_us",
        job_code="job_cat_20260405_001",
        status=JobStatus.RUNNING_EXTERNAL,
        external_run=None,
        error=SimpleNamespace(code="old", message="old"),
        started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        finished_at=None,
    )

    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.ApifyRunDocument",
        SimpleNamespace(
            find_one=_async_return(run_document),
            find=lambda *args, **kwargs: FakeCursor([run_document]),
            apify_run_id="apify_run_id",
            workspace_id="workspace_id",
        ),
    )
    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.JobDocument",
        SimpleNamespace(
            find_one=_async_return(job_document),
            workspace_id="workspace_id",
            job_code="job_code",
        ),
    )

    service = ApifyRunLifecycleService(
        SimpleNamespace(),
        Config().apify_config,
    )
    ack = run_async(
        service.handle_webhook(
            ApifyWebhookEnvelope(
                eventType="ACTOR.RUN.SUCCEEDED",
                resource={
                    "id": "apify_run_test_001",
                    "status": "SUCCEEDED",
                    "defaultDatasetId": "dataset_test_001",
                    "startedAt": "2026-04-05T02:00:03Z",
                    "finishedAt": "2026-04-05T02:05:00Z",
                },
            )
        )
    )

    assert ack.status == "ACCEPTED"
    assert ack.job_status == JobStatus.IMPORTING
    assert run_document.status == "SUCCEEDED"
    assert run_document.default_dataset_id == "dataset_test_001"
    assert run_document.webhook_received_at is not None
    assert job_document.status == JobStatus.IMPORTING
    assert job_document.external_run.provider_run_id == "apify_run_test_001"
    assert job_document.external_run.status == ExternalRunStatus.SUCCEEDED
    assert job_document.error is None


@pytest.mark.parametrize(
    ("event_type", "raw_status", "expected_status"),
    [
        ("ACTOR.RUN.FAILED", "FAILED", ExternalRunStatus.FAILED),
        ("ACTOR.RUN.ABORTED", "ABORTED", ExternalRunStatus.ABORTED),
        ("ACTOR.RUN.TIMED_OUT", "TIMED-OUT", ExternalRunStatus.TIMED_OUT),
    ],
)
def test_apify_run_lifecycle_webhook_failure(
    run_async,
    monkeypatch,
    event_type,
    raw_status,
    expected_status,
):
    run_document = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_cat_20260405_001",
        apify_run_id="apify_run_test_001",
        status="RUNNING",
        apify_status_raw="RUNNING",
        default_dataset_id="dataset_test_001",
        started_at=None,
        finished_at=None,
        webhook_received_at=None,
        poll_count=0,
        error=None,
        updated_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
    )
    job_document = FakeDocument(
        workspace_id="ws_demo_us",
        job_code="job_cat_20260405_001",
        status=JobStatus.RUNNING_EXTERNAL,
        external_run=None,
        error=None,
        started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        finished_at=None,
    )

    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.ApifyRunDocument",
        SimpleNamespace(
            find_one=_async_return(run_document),
            find=lambda *args, **kwargs: FakeCursor([run_document]),
            apify_run_id="apify_run_id",
            workspace_id="workspace_id",
        ),
    )
    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.JobDocument",
        SimpleNamespace(
            find_one=_async_return(job_document),
            workspace_id="workspace_id",
            job_code="job_code",
        ),
    )

    service = ApifyRunLifecycleService(
        SimpleNamespace(),
        Config().apify_config,
    )
    ack = run_async(
        service.handle_webhook(
            ApifyWebhookEnvelope(
                eventType=event_type,
                resource={
                    "id": "apify_run_test_001",
                    "status": raw_status,
                    "finishedAt": "2026-04-05T02:05:00Z",
                },
            )
        )
    )

    assert ack.status == "ACCEPTED"
    assert ack.provider_status == expected_status
    assert ack.job_status == JobStatus.FAILED
    assert run_document.status == expected_status.value
    assert job_document.status == JobStatus.FAILED
    assert job_document.error.code == expected_status.value


def test_apify_run_lifecycle_webhook_duplicate_is_ignored(run_async, monkeypatch):
    run_document = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_cat_20260405_001",
        apify_run_id="apify_run_test_001",
        status="SUCCEEDED",
        apify_status_raw="SUCCEEDED",
        default_dataset_id="dataset_test_001",
        started_at=None,
        finished_at=datetime(2026, 4, 5, 2, 5, tzinfo=UTC),
        webhook_received_at=None,
        poll_count=0,
        error=None,
        updated_at=datetime(2026, 4, 5, 2, 5, tzinfo=UTC),
    )
    job_document = FakeDocument(
        workspace_id="ws_demo_us",
        job_code="job_cat_20260405_001",
        status=JobStatus.IMPORTING,
        external_run=SimpleNamespace(
            provider_run_id="apify_run_test_001",
            status=ExternalRunStatus.SUCCEEDED,
            started_at=None,
            finished_at=datetime(2026, 4, 5, 2, 5, tzinfo=UTC),
        ),
        error=None,
        started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        finished_at=None,
    )

    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.ApifyRunDocument",
        SimpleNamespace(
            find_one=_async_return(run_document),
            find=lambda *args, **kwargs: FakeCursor([run_document]),
            apify_run_id="apify_run_id",
            workspace_id="workspace_id",
        ),
    )
    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.JobDocument",
        SimpleNamespace(
            find_one=_async_return(job_document),
            workspace_id="workspace_id",
            job_code="job_code",
        ),
    )

    service = ApifyRunLifecycleService(
        SimpleNamespace(),
        Config().apify_config,
    )
    ack = run_async(
        service.handle_webhook(
            ApifyWebhookEnvelope(
                eventType="ACTOR.RUN.SUCCEEDED",
                resource={"id": "apify_run_test_001", "status": "SUCCEEDED"},
            )
        )
    )

    assert ack.status == "IGNORED"
    assert ack.job_status == JobStatus.IMPORTING
    assert run_document.webhook_received_at is not None
    assert job_document.status == JobStatus.IMPORTING


def test_apify_run_lifecycle_poller_counts_and_transitions(run_async, monkeypatch):
    run_one = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_one",
        apify_run_id="run_one",
        status="RUNNING",
        apify_status_raw="RUNNING",
        default_dataset_id=None,
        started_at=None,
        finished_at=None,
        webhook_received_at=None,
        poll_count=0,
        error=None,
        updated_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
    )
    run_two = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_two",
        apify_run_id="run_two",
        status="READY",
        apify_status_raw="READY",
        default_dataset_id=None,
        started_at=None,
        finished_at=None,
        webhook_received_at=None,
        poll_count=0,
        error=None,
        updated_at=datetime(2026, 4, 5, 2, 1, tzinfo=UTC),
    )
    run_three = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_three",
        apify_run_id="run_three",
        status="RUNNING",
        apify_status_raw="RUNNING",
        default_dataset_id=None,
        started_at=None,
        finished_at=None,
        webhook_received_at=None,
        poll_count=0,
        error=None,
        updated_at=datetime(2026, 4, 5, 2, 2, tzinfo=UTC),
    )
    run_four = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_four",
        apify_run_id="run_four",
        status="RUNNING",
        apify_status_raw="RUNNING",
        default_dataset_id=None,
        started_at=None,
        finished_at=None,
        webhook_received_at=None,
        poll_count=0,
        error=None,
        updated_at=datetime(2026, 4, 5, 2, 3, tzinfo=UTC),
    )

    jobs = {
        "job_one": FakeDocument(
            workspace_id="ws_demo_us",
            job_code="job_one",
            status=JobStatus.RUNNING_EXTERNAL,
            external_run=None,
            error=None,
            started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
            finished_at=None,
        ),
        "job_two": FakeDocument(
            workspace_id="ws_demo_us",
            job_code="job_two",
            status=JobStatus.RUNNING_EXTERNAL,
            external_run=None,
            error=None,
            started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
            finished_at=None,
        ),
        "job_three": FakeDocument(
            workspace_id="ws_demo_us",
            job_code="job_three",
            status=JobStatus.IMPORTING,
            external_run=None,
            error=None,
            started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
            finished_at=None,
        ),
        "job_four": FakeDocument(
            workspace_id="ws_demo_us",
            job_code="job_four",
            status=JobStatus.RUNNING_EXTERNAL,
            external_run=None,
            error=None,
            started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
            finished_at=None,
        ),
    }

    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.ApifyRunDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor(
                [run_one, run_two, run_three, run_four]
            ),
            find_one=lambda *args, **kwargs: None,
            apify_run_id="apify_run_id",
            workspace_id="workspace_id",
        ),
    )
    monkeypatch.setattr(
        "app.services.apify_run_lifecycle_service.JobDocument",
        SimpleNamespace(
            find_one=_job_lookup(jobs),
            workspace_id="workspace_id",
            job_code="job_code",
        ),
    )

    class Gateway:
        async def get_run(self, run_id):
            if run_id == "run_one":
                return SimpleNamespace(
                    status=ExternalRunStatus.SUCCEEDED,
                    raw_status="SUCCEEDED",
                    default_dataset_id="dataset_one",
                    started_at="2026-04-05T02:00:01Z",
                    finished_at="2026-04-05T02:05:00Z",
                )
            if run_id == "run_two":
                return SimpleNamespace(
                    status=ExternalRunStatus.FAILED,
                    raw_status="FAILED",
                    default_dataset_id="dataset_two",
                    started_at="2026-04-05T02:00:02Z",
                    finished_at="2026-04-05T02:05:10Z",
                )
            raise ApifyRunLookupError("lookup failed")

    service = ApifyRunLifecycleService(
        Gateway(),
        Config(apify_config={"poll_batch_size": 10}).apify_config,
    )
    service._find_job_document = _find_job_by_run_code(jobs).__get__(
        service,
        ApifyRunLifecycleService,
    )
    result = run_async(service.poll_runs())

    assert result.polled_runs == 3
    assert result.updated_runs == 2
    assert result.jobs_advanced == 1
    assert result.jobs_failed == 1
    assert result.lookup_failures == 1
    assert run_one.poll_count == 1
    assert run_two.poll_count == 1
    assert run_four.poll_count == 0
    assert jobs["job_one"].status == JobStatus.IMPORTING
    assert jobs["job_two"].status == JobStatus.FAILED
    assert jobs["job_three"].status == JobStatus.IMPORTING


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _job_lookup(jobs):
    async def _inner(*args, **kwargs):
        for job in jobs.values():
            if job.job_code in str(args):
                return job
        return None

    return _inner


def _find_job_by_run_code(jobs):
    async def _inner(self, run_document):
        return jobs.get(run_document.tracking_job_code)

    return _inner


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
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY, binding_code="bind_category_top50_v1"
        ),
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
        config = SimpleNamespace(webhook_url=None)

        async def start_run(self, binding_code, run_input, webhooks=None):
            raise ApifyBindingResolutionError(
                "Missing actor/task configuration for binding."
            )

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
