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
    AvailabilityStatus,
    ApifyWebhookEnvelope,
    BuyBoxStatus,
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
    TrackerRef,
    TrackerScheduleInput,
    TrackerType,
)
from app.services.apify_run_lifecycle_service import ApifyRunLifecycleService
from app.services.dashboard_query_service import DashboardQueryService
from app.services.normalization_service import (
    NormalizationResult,
    NormalizedProductRecord,
)
from app.services.result_importer_service import ResultImporterService, TrackerContext
from app.services.run_orchestrator import RunOrchestrator
from app.services.shared import product_snapshot_doc_to_model, snapshot_doc_to_model
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




@pytest.mark.skip(
    reason="Internal implementation details changed after module refactoring"
)
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


@pytest.mark.skip(
    reason="Internal implementation details changed after module refactoring"
)
def test_mongo_store_forwards_airflow_reference_inputs(run_async):
    class DummyClient:
        def close(self):
            return None

    store = MongoStore(DummyClient(), "market_tracker", Config(seed_demo_data=False))
    captured: dict[str, object] = {}

    class SchedulerService:
        async def schedule_due_jobs(self, *, reference_time=None):
            captured["schedule_reference_time"] = reference_time
            return SimpleNamespace(model_dump=lambda: {"created_jobs": 0})

    class DigestService:
        async def generate_weekly_digests(self, *, reference_date=None):
            captured["digest_reference_date"] = reference_date
            return SimpleNamespace(model_dump=lambda: {"generated_digests": 0})

    schedule_reference_time = datetime(2026, 4, 8, 4, 15, tzinfo=UTC)
    digest_reference_date = date(2026, 4, 3)

    store.scheduler_service = SchedulerService()
    store.digest_service = DigestService()

    run_async(store.schedule_jobs(reference_time=schedule_reference_time))
    run_async(store.process_digest_jobs(reference_date=digest_reference_date))

    assert captured["schedule_reference_time"] == schedule_reference_time
    assert captured["digest_reference_date"] == digest_reference_date


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


def test_dashboard_query_filters_product_timeline_by_tracker_code(
    run_async, monkeypatch, seed_data
):
    target_tracker_code = "cmp_target_tracker"
    other_tracker_code = "ct_other_tracker"
    snapshots = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **snapshot.model_dump(mode="python", exclude={"tracker_refs"}),
            tracker_refs=[
                TrackerRef(
                    tracker_type=TrackerType.COMPETITOR,
                    tracker_code=target_tracker_code,
                    tracker_name="Target Tracker",
                )
            ],
            created_at=datetime(2026, 4, 1, tzinfo=UTC),
        )
        for snapshot in seed_data.product_snapshots[:2]
    ] + [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **seed_data.product_snapshots[2].model_dump(
                mode="python", exclude={"tracker_refs"}
            ),
            tracker_refs=[
                TrackerRef(
                    tracker_type=TrackerType.CATEGORY,
                    tracker_code=other_tracker_code,
                    tracker_name="Other Tracker",
                )
            ],
            created_at=datetime(2026, 4, 3, tzinfo=UTC),
        )
    ]
    events = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **seed_data.events[0].model_dump(mode="python", exclude={"tracker_code"}),
            tracker_code=target_tracker_code,
        ),
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **seed_data.events[1].model_dump(mode="python", exclude={"tracker_code"}),
            tracker_code=other_tracker_code,
        ),
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
            from_date=None,
            to_date=None,
            granularity=Timeframe.DAILY,
            tracker_code=target_tracker_code,
        )
    )

    assert [point.snapshot_date for point in response.points] == [
        seed_data.product_snapshots[0].snapshot_date,
        seed_data.product_snapshots[1].snapshot_date,
    ]
    assert [event.tracker_code for event in response.events] == [target_tracker_code]


def test_product_snapshot_doc_to_model_ignores_created_at():
    document = FakeDocument(
        workspace_id="ws_test",
        marketplace="amazon_de",
        asin="B08TSF3MRG",
        snapshot_date=date(2026, 4, 13),
        captured_at=datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
        tracker_refs=[],
        parent_asin=None,
        brand="Philips",
        title="Philips Steamer",
        title_hash="title_hash",
        product_url="https://www.amazon.de/dp/B08TSF3MRG",
        main_image_url="https://images.example.com/B08TSF3MRG.jpg",
        main_image_hash="image_hash",
        bsr_position=10,
        price_current=39.99,
        price_original=49.99,
        currency="EUR",
        coupon_text=None,
        availability_status=AvailabilityStatus.IN_STOCK,
        buy_box_status=BuyBoxStatus.HAS_BUY_BOX,
        buy_box_seller_name="Amazon",
        rating_value=4.5,
        review_count=100,
        variation_count=2,
        source_refs={"provider": "APIFY"},
        created_at=datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
    )

    model = product_snapshot_doc_to_model(document)

    assert model.asin == "B08TSF3MRG"
    assert model.price_current == 39.99


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


def test_run_orchestrator_builds_category_run_input_with_marketplace_domain():
    tracker_document = SimpleNamespace(
        marketplace="amazon_de",
        scope=SimpleNamespace(browse_node_id="3098778031", browse_node_url=None),
        tracking_config=SimpleNamespace(top_n=50),
    )
    job_document = FakeDocument(
        job_code="job_cat_20260413_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code="ct_kaffeekannen",
        snapshot_date=date(2026, 4, 13),
        trigger_mode="MANUAL",
        status=JobStatus.QUEUED,
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY, binding_code="bind_category_top50_v1"
        ),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        created_at=datetime(2026, 4, 13, tzinfo=UTC),
    )

    run_input = RunOrchestrator(SimpleNamespace())._build_run_input(
        job_document, tracker_document
    )

    assert run_input["amazon_domain"] == "www.amazon.de"
    assert (
        run_input["search_url"]
        == "https://www.amazon.de/s?i=specialty-aps&rh=n%3A3098778031"
    )
    assert run_input["max_pages"] == 4


def test_run_orchestrator_dispatch_job_advances_terminal_success_runs_to_importing(
    run_async, monkeypatch, seed_data
):
    job_document = FakeDocument(
        workspace_id=seed_data.workspace_id,
        job_code="job_cat_20260405_003",
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
    inserted_runs: list[object] = []
    saved_statuses: list[JobStatus] = []

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
            return ApifyRunLaunch(
                provider_run_id="apify_run_test_003",
                default_dataset_id="dataset_test_003",
                status=ExternalRunStatus.SUCCEEDED,
                raw_status="SUCCEEDED",
                started_at=datetime(2026, 4, 5, 2, 0, 3),
                finished_at=datetime(2026, 4, 5, 2, 5, 0),
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

    assert saved_statuses == [JobStatus.DISPATCHING, JobStatus.IMPORTING]
    assert job_document.status == JobStatus.IMPORTING
    assert job_document.error is None
    assert job_document.external_run is not None
    assert job_document.external_run.status == ExternalRunStatus.SUCCEEDED
    assert job_document.external_run.started_at.tzinfo == UTC
    assert job_document.external_run.finished_at.tzinfo == UTC
    assert inserted_runs[0].status == ExternalRunStatus.SUCCEEDED.value
    assert inserted_runs[0].started_at.tzinfo == UTC
    assert inserted_runs[0].finished_at.tzinfo == UTC


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


def test_result_importer_process_pending_jobs_handles_naive_run_finished_at(
    run_async, monkeypatch
):
    job_document = FakeDocument(
        workspace_id="ws_demo_us",
        job_code="job_import_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code="ct_demo",
        snapshot_date=date(2026, 4, 5),
        status=JobStatus.IMPORTING,
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        error=None,
        created_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        started_at=datetime(2026, 4, 5, 2, 0, tzinfo=UTC),
        finished_at=None,
    )
    run_document = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_import_001",
        apify_run_id="apify_run_test_004",
        status=ExternalRunStatus.SUCCEEDED.value,
        default_dataset_id="dataset_test_004",
        finished_at=datetime(2026, 4, 5, 2, 5, 0),
    )

    saved_statuses: list[JobStatus] = []
    saved_finished_at_values: list[datetime] = []
    tracker_updates: list[JobStatus] = []

    async def fake_job_save(self, *args, **kwargs):
        saved_statuses.append(JobStatus(self.status))

    async def fake_run_save(self, *args, **kwargs):
        saved_finished_at_values.append(self.finished_at)

    job_document.save = fake_job_save.__get__(job_document, FakeDocument)
    run_document.save = fake_run_save.__get__(run_document, FakeDocument)

    monkeypatch.setattr(
        "app.services.result_importer_service.JobDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor([job_document]),
            status="status",
        ),
    )
    monkeypatch.setattr(
        "app.services.result_importer_service.ApifyRunDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor([run_document]),
            workspace_id="workspace_id",
            tracking_job_code="tracking_job_code",
        ),
    )

    normalization_service = SimpleNamespace(
        normalize_items=lambda **kwargs: NormalizationResult(
            records=[], invalid_count=0
        )
    )
    service = ResultImporterService(
        gateway=SimpleNamespace(),
        normalization_service=normalization_service,
        snapshot_service=SimpleNamespace(),
        event_engine=SimpleNamespace(),
        config=Config().apify_config,
        storage_config=Config().storage_config,
    )

    async def fake_load_or_import_raw_items(**kwargs):
        return [], 0

    async def fake_load_tracker_context(**kwargs):
        return TrackerContext(
            tracker_type=TrackerType.CATEGORY,
            marketplace="amazon_de",
        )

    async def fake_update_tracker_stats(**kwargs):
        tracker_updates.append(kwargs["final_status"])

    service._load_or_import_raw_items = fake_load_or_import_raw_items
    service._load_tracker_context = fake_load_tracker_context
    service._update_tracker_stats = fake_update_tracker_stats

    result = run_async(service.process_pending_jobs())

    assert result.succeeded_jobs == 1
    assert job_document.status == JobStatus.SUCCESS
    assert saved_statuses == [JobStatus.PROCESSING, JobStatus.SUCCESS]
    assert run_document.finished_at.tzinfo == UTC
    assert saved_finished_at_values[0].tzinfo == UTC
    assert tracker_updates == [JobStatus.SUCCESS]


def test_result_importer_redispatches_category_run_when_unique_coverage_is_low(
    run_async, monkeypatch
):
    job_document = FakeDocument(
        workspace_id="ws_demo_us",
        job_code="job_import_coverage_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code="ct_demo",
        snapshot_date=date(2026, 4, 6),
        status=JobStatus.IMPORTING,
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY,
            binding_code="bind_category_top50_v1",
        ),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        error=None,
        created_at=datetime(2026, 4, 6, 2, 0, tzinfo=UTC),
        started_at=datetime(2026, 4, 6, 2, 0, tzinfo=UTC),
        finished_at=None,
        external_run=None,
    )
    latest_run_document = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_import_coverage_001",
        apify_run_id="apify_run_test_010",
        status=ExternalRunStatus.SUCCEEDED.value,
        default_dataset_id="dataset_test_010",
        run_input={"max_pages": 4, "top_n": 50, "search_url": "https://example.com"},
        created_at=datetime(2026, 4, 6, 2, 5, tzinfo=UTC),
        updated_at=datetime(2026, 4, 6, 2, 5, tzinfo=UTC),
        finished_at=datetime(2026, 4, 6, 2, 10, tzinfo=UTC),
    )
    older_run_document = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_import_coverage_001",
        apify_run_id="apify_run_test_009",
        status=ExternalRunStatus.SUCCEEDED.value,
        default_dataset_id="dataset_test_009",
        run_input={"max_pages": 3, "top_n": 50, "search_url": "https://example.com"},
        created_at=datetime(2026, 4, 6, 2, 4, tzinfo=UTC),
        updated_at=datetime(2026, 4, 6, 2, 4, tzinfo=UTC),
        finished_at=datetime(2026, 4, 6, 2, 9, tzinfo=UTC),
    )

    saved_statuses: list[JobStatus] = []
    inserted_runs: list[object] = []

    async def fake_job_save(self, *args, **kwargs):
        saved_statuses.append(JobStatus(self.status))

    job_document.save = fake_job_save.__get__(job_document, FakeDocument)

    class FakeApifyRunDocument:
        workspace_id = "workspace_id"
        tracking_job_code = "tracking_job_code"

        @staticmethod
        def find(*args, **kwargs):
            return FakeCursor([older_run_document, latest_run_document])

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        async def insert(self):
            inserted_runs.append(self)

    monkeypatch.setattr(
        "app.services.result_importer_service.JobDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor([job_document]),
            status="status",
        ),
    )
    monkeypatch.setattr(
        "app.services.result_importer_service.ApifyRunDocument",
        FakeApifyRunDocument,
    )

    normalization_service = SimpleNamespace(
        normalize_items=lambda **kwargs: NormalizationResult(
            records=[
                NormalizedProductRecord(
                    marketplace="amazon_de",
                    asin=f"B0UNIQUE{i:04d}",
                    rank_position=i,
                    captured_at=datetime(2026, 4, 6, 2, 10, tzinfo=UTC),
                    brand="Brand",
                    title=f"Product {i}",
                    product_url=f"https://www.amazon.de/dp/B0UNIQUE{i:04d}",
                    main_image_url=f"https://images.example.com/B0UNIQUE{i:04d}.jpg",
                    title_hash=f"title_hash_{i}",
                    main_image_hash=f"image_hash_{i}",
                    bsr_position=i,
                    price_current=19.99,
                    price_original=None,
                    currency="EUR",
                    coupon_text=None,
                    availability_status=AvailabilityStatus.IN_STOCK,
                    buy_box_status=BuyBoxStatus.HAS_BUY_BOX,
                    buy_box_seller_name="Seller",
                    rating_value=4.5,
                    review_count=42,
                    variation_count=1,
                    source_batch_no=1,
                    source_item_index=i,
                )
                for i in range(1, 41)
            ],
            invalid_count=0,
        )
    )

    dispatched_inputs: list[dict[str, object]] = []

    class Gateway:
        async def start_run(self, binding_code, run_input, webhooks=None):
            dispatched_inputs.append(
                {
                    "binding_code": binding_code,
                    "run_input": run_input,
                    "webhooks": webhooks,
                }
            )
            return ApifyRunLaunch(
                provider_run_id="apify_run_test_011",
                default_dataset_id="dataset_test_011",
                status=ExternalRunStatus.READY,
                raw_status="READY",
                started_at="2026-04-06T02:10:30Z",
                finished_at=None,
                input_hash="hash_retry_011",
                binding=SimpleNamespace(
                    binding_code=binding_code,
                    actor_id="owner/category-actor",
                    task_id=None,
                ),
                run_input=run_input,
            )

    snapshot_service = SimpleNamespace(
        persist_snapshots=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError(
                "should not persist snapshots before expanded crawl finishes"
            )
        )
    )
    event_engine = SimpleNamespace(
        generate_events_for_job=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("should not emit events before expanded crawl finishes")
        )
    )

    service = ResultImporterService(
        gateway=Gateway(),
        normalization_service=normalization_service,
        snapshot_service=snapshot_service,
        event_engine=event_engine,
        config=Config().apify_config,
        storage_config=Config().storage_config,
    )

    async def fake_load_or_import_raw_items(**kwargs):
        return [SimpleNamespace(payload={"asin": "B0UNIQUE0001"})], 40

    async def fake_load_tracker_context(**kwargs):
        return TrackerContext(
            tracker_type=TrackerType.CATEGORY,
            marketplace="amazon_de",
            category_top_n=50,
        )

    async def fake_update_tracker_stats(**kwargs):
        raise AssertionError(
            "tracker stats should not be updated while crawl is expanding"
        )

    service._load_or_import_raw_items = fake_load_or_import_raw_items
    service._load_tracker_context = fake_load_tracker_context
    service._update_tracker_stats = fake_update_tracker_stats

    result = run_async(service.process_pending_jobs())

    assert result.processed_jobs == 1
    assert result.succeeded_jobs == 0
    assert result.partial_jobs == 0
    assert result.failed_jobs == 0
    assert dispatched_inputs[0]["binding_code"] == "bind_category_top50_v1"
    assert dispatched_inputs[0]["run_input"]["max_pages"] == 5
    assert inserted_runs[0].origin == "IMPORT_RETRY"
    assert inserted_runs[0].apify_run_id == "apify_run_test_011"
    assert job_document.status == JobStatus.RUNNING_EXTERNAL
    assert job_document.external_run.provider_run_id == "apify_run_test_011"
    assert job_document.summary.expected_items == 40
    assert job_document.summary.imported_items == 40
    assert saved_statuses == [JobStatus.PROCESSING, JobStatus.RUNNING_EXTERNAL]


def test_result_importer_marks_partial_success_when_category_unique_coverage_stays_low(
    run_async, monkeypatch
):
    job_document = FakeDocument(
        workspace_id="ws_demo_us",
        job_code="job_import_coverage_002",
        tracker_type=TrackerType.CATEGORY,
        tracker_code="ct_demo",
        snapshot_date=date(2026, 4, 7),
        status=JobStatus.IMPORTING,
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY,
            binding_code="bind_category_top50_v1",
        ),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        error=None,
        created_at=datetime(2026, 4, 7, 2, 0, tzinfo=UTC),
        started_at=datetime(2026, 4, 7, 2, 0, tzinfo=UTC),
        finished_at=None,
        external_run=None,
    )
    run_document = FakeDocument(
        workspace_id="ws_demo_us",
        tracking_job_code="job_import_coverage_002",
        apify_run_id="apify_run_test_012",
        status=ExternalRunStatus.SUCCEEDED.value,
        default_dataset_id="dataset_test_012",
        run_input={"max_pages": 10, "top_n": 50, "search_url": "https://example.com"},
        created_at=datetime(2026, 4, 7, 2, 5, tzinfo=UTC),
        updated_at=datetime(2026, 4, 7, 2, 5, tzinfo=UTC),
        finished_at=datetime(2026, 4, 7, 2, 10, tzinfo=UTC),
    )

    saved_statuses: list[JobStatus] = []
    tracker_updates: list[JobStatus] = []
    persisted_snapshots: list[str] = []
    generated_events: list[str] = []

    async def fake_job_save(self, *args, **kwargs):
        saved_statuses.append(JobStatus(self.status))

    job_document.save = fake_job_save.__get__(job_document, FakeDocument)

    monkeypatch.setattr(
        "app.services.result_importer_service.JobDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor([job_document]),
            status="status",
        ),
    )
    monkeypatch.setattr(
        "app.services.result_importer_service.ApifyRunDocument",
        SimpleNamespace(
            find=lambda *args, **kwargs: FakeCursor([run_document]),
            workspace_id="workspace_id",
            tracking_job_code="tracking_job_code",
        ),
    )

    normalization_service = SimpleNamespace(
        normalize_items=lambda **kwargs: NormalizationResult(
            records=[
                NormalizedProductRecord(
                    marketplace="amazon_de",
                    asin=f"B0LOWUNIQ{i:04d}",
                    rank_position=i,
                    captured_at=datetime(2026, 4, 7, 2, 10, tzinfo=UTC),
                    brand="Brand",
                    title=f"Product {i}",
                    product_url=f"https://www.amazon.de/dp/B0LOWUNIQ{i:04d}",
                    main_image_url=f"https://images.example.com/B0LOWUNIQ{i:04d}.jpg",
                    title_hash=f"title_hash_{i}",
                    main_image_hash=f"image_hash_{i}",
                    bsr_position=i,
                    price_current=19.99,
                    price_original=None,
                    currency="EUR",
                    coupon_text=None,
                    availability_status=AvailabilityStatus.IN_STOCK,
                    buy_box_status=BuyBoxStatus.HAS_BUY_BOX,
                    buy_box_seller_name="Seller",
                    rating_value=4.5,
                    review_count=42,
                    variation_count=1,
                    source_batch_no=1,
                    source_item_index=i,
                )
                for i in range(1, 39)
            ],
            invalid_count=0,
        )
    )

    async def fake_persist_snapshots(**kwargs):
        persisted_snapshots.append(kwargs["apify_run_id"])

    async def fake_generate_events_for_job(**kwargs):
        generated_events.append(kwargs["job_document"].job_code)
        return 0

    service = ResultImporterService(
        gateway=SimpleNamespace(),
        normalization_service=normalization_service,
        snapshot_service=SimpleNamespace(persist_snapshots=fake_persist_snapshots),
        event_engine=SimpleNamespace(
            generate_events_for_job=fake_generate_events_for_job
        ),
        config=Config().apify_config,
        storage_config=Config().storage_config,
    )

    async def fake_load_or_import_raw_items(**kwargs):
        return [SimpleNamespace(payload={"asin": "B0LOWUNIQ0001"})], 38

    async def fake_load_tracker_context(**kwargs):
        return TrackerContext(
            tracker_type=TrackerType.CATEGORY,
            marketplace="amazon_de",
            category_top_n=50,
        )

    async def fake_update_tracker_stats(**kwargs):
        tracker_updates.append(kwargs["final_status"])

    service._load_or_import_raw_items = fake_load_or_import_raw_items
    service._load_tracker_context = fake_load_tracker_context
    service._update_tracker_stats = fake_update_tracker_stats

    result = run_async(service.process_pending_jobs())

    assert result.partial_jobs == 1
    assert job_document.status == JobStatus.PARTIAL_SUCCESS
    assert job_document.error.code == "CATEGORY_UNIQUE_INSUFFICIENT"
    assert persisted_snapshots == ["apify_run_test_012"]
    assert generated_events == ["job_import_coverage_002"]
    assert tracker_updates == [JobStatus.PARTIAL_SUCCESS]
    assert saved_statuses == [JobStatus.PROCESSING, JobStatus.PARTIAL_SUCCESS]




def test_snapshot_doc_to_model_dedupes_existing_duplicate_snapshot_products():
    snapshot = snapshot_doc_to_model(
        FakeDocument(
            tracker_code="ct_elektrische_zitruspressen",
            marketplace="amazon_de",
            browse_node_id="3169451",
            snapshot_date=date(2026, 4, 13),
            captured_at=datetime(2026, 4, 13, 19, 34, tzinfo=UTC),
            top_n=50,
            products=[
                {
                    "asin": "B0FIRST123",
                    "rank_position": 1,
                    "title": "First product",
                    "brand": "Brand A",
                    "product_url": "https://www.amazon.de/dp/B0FIRST123",
                    "price_current": 79.99,
                    "price_original": None,
                    "currency": "EUR",
                    "rating_value": 4.7,
                    "review_count": 120,
                    "image_url": "https://images.example.com/B0FIRST123.jpg",
                    "availability_status": AvailabilityStatus.IN_STOCK,
                    "buy_box_status": BuyBoxStatus.HAS_BUY_BOX,
                    "coupon_text": None,
                },
                {
                    "asin": "B0FIRST123",
                    "rank_position": 2,
                    "title": "First product duplicate",
                    "brand": "Brand A",
                    "product_url": "https://www.amazon.de/dp/B0FIRST123",
                    "price_current": 79.99,
                    "price_original": None,
                    "currency": "EUR",
                    "rating_value": 4.7,
                    "review_count": 120,
                    "image_url": "https://images.example.com/B0FIRST123.jpg",
                    "availability_status": AvailabilityStatus.IN_STOCK,
                    "buy_box_status": BuyBoxStatus.HAS_BUY_BOX,
                    "coupon_text": None,
                },
                {
                    "asin": "B0SECOND12",
                    "rank_position": 3,
                    "title": "Second product",
                    "brand": "Brand B",
                    "product_url": "https://www.amazon.de/dp/B0SECOND12",
                    "price_current": 69.99,
                    "price_original": None,
                    "currency": "EUR",
                    "rating_value": 4.6,
                    "review_count": 80,
                    "image_url": "https://images.example.com/B0SECOND12.jpg",
                    "availability_status": AvailabilityStatus.IN_STOCK,
                    "buy_box_status": BuyBoxStatus.HAS_BUY_BOX,
                    "coupon_text": None,
                },
            ],
            summary={
                "asin_count": 3,
                "new_entrant_count": 0,
                "returning_count": 0,
                "exit_count": 0,
                "enter_top10_count": 0,
                "exit_top10_count": 0,
            },
            source_refs={"provider": "APIFY"},
        )
    )

    assert [product.asin for product in snapshot.products] == [
        "B0FIRST123",
        "B0SECOND12",
    ]
    assert [product.rank_position for product in snapshot.products] == [1, 2]
    assert snapshot.summary.asin_count == 2


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
