from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.config import config as config_module
from app.config.config import ApifyConfig, StorageConfig
from app.models.api import (
    Job,
    JobRunStrategy,
    JobStatus,
    JobSummary,
    Provider,
    TrackerRef,
    TrackerType,
    TriggerMode,
)
from app.services.object_storage_service import LocalObjectStorageService
from app.services.result_importer_service import ResultImporterService
from app.services.run_orchestrator import RunOrchestrator
from app.services.snapshot_service import SnapshotService


def test_apify_actor_config_and_secret_file_helpers(monkeypatch, tmp_path):
    apify_config_file = tmp_path / "apify-config.yaml"
    apify_config_file.write_text(
        """
bindings:
  category:
    name: "Category Runner"
    actor_id: "owner/category-actor"
    build: "v2"
        input_adapter: "saswave_category"
  competitor:
    task_id: "task_competitor"
    memory_mbytes: 4096
        input_adapter: "saswave_competitor"
""".strip(),
        encoding="utf-8",
    )
    token_file = tmp_path / "apify.token"
    token_file.write_text("token-from-file", encoding="utf-8")

    monkeypatch.setenv("APIFY_CONFIG_FILE", str(apify_config_file))
    monkeypatch.setenv("APIFY_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("APIFY_TOKEN", raising=False)

    config_module._load_apify_file_config.cache_clear()

    assert config_module._binding_str("category", "name") == "Category Runner"
    assert config_module._binding_str("category", "actor_id") == "owner/category-actor"
    assert config_module._binding_str("category", "input_adapter") == "saswave_category"
    assert config_module._binding_str("competitor", "task_id") == "task_competitor"
    assert config_module._binding_int("competitor", "memory_mbytes") == 4096
    assert (
        config_module._binding_str("competitor", "input_adapter")
        == "saswave_competitor"
    )
    assert (
        config_module._read_secret(
            env_name="APIFY_TOKEN", file_env_name="APIFY_TOKEN_FILE"
        )
        == "token-from-file"
    )


def test_importer_replays_batches_from_object_storage(run_async, tmp_path):
    storage_root = tmp_path / "object-store"
    object_storage = LocalObjectStorageService(str(storage_root))

    importer = ResultImporterService(
        gateway=SimpleNamespace(),
        normalization_service=SimpleNamespace(),
        snapshot_service=SimpleNamespace(),
        event_engine=SimpleNamespace(),
        config=ApifyConfig(token="token"),
        storage_config=StorageConfig(
            raw_batch_offload_enabled=True,
            raw_batch_offload_min_items=1,
            local_object_store_root=str(storage_root),
        ),
        object_storage=object_storage,
    )

    storage_uri = run_async(
        importer._offload_raw_items(
            workspace_id="ws_demo_us",
            apify_run_id="run_001",
            batch_no=1,
            items=[{"asin": "B0AAA11111"}, {"asin": "B0BBB22222"}],
        )
    )

    batch_doc = SimpleNamespace(
        batch_no=1,
        raw_items=[],
        raw_storage_uri=storage_uri,
        source_item_count=2,
    )

    flattened_items, expected_items = run_async(
        importer._flatten_raw_batches([batch_doc])
    )

    assert expected_items == 2
    assert len(flattened_items) == 2
    assert flattened_items[0].payload["asin"] == "B0AAA11111"
    assert flattened_items[1].payload["asin"] == "B0BBB22222"


def test_snapshot_service_append_only_does_not_overwrite_existing_payload(
    run_async, monkeypatch
):
    service = SnapshotService()

    tracker_ref = TrackerRef(
        tracker_type=TrackerType.COMPETITOR,
        tracker_code="cmp_demo",
        tracker_name="Competitor Demo",
    )

    existing_snapshot = SimpleNamespace(
        tracker_refs=[tracker_ref],
        title="Original Title",
        created_at=datetime(2026, 4, 7, 3, 0, tzinfo=UTC),
        save_called=False,
    )

    async def fake_save(self):
        self.save_called = True

    existing_snapshot.save = fake_save.__get__(existing_snapshot, SimpleNamespace)

    async def fake_find_one(*args, **kwargs):
        return existing_snapshot

    monkeypatch.setattr(
        "app.services.snapshot_service.ProductSnapshotDocument",
        SimpleNamespace(
            find_one=fake_find_one,
            workspace_id="workspace_id",
            marketplace="marketplace",
            asin="asin",
            snapshot_date="snapshot_date",
        ),
    )

    inserted = run_async(
        service._upsert_product_snapshot(
            workspace_id="ws_demo_us",
            snapshot_date=date(2026, 4, 8),
            tracker_ref=tracker_ref,
            record=SimpleNamespace(
                marketplace="amazon_us",
                asin="B0AAA11111",
                captured_at=datetime(2026, 4, 8, 3, 0, tzinfo=UTC),
                brand="Brand",
                title="Changed Title",
                title_hash="new_title_hash",
                product_url="https://example.com/product",
                main_image_url="https://example.com/image.jpg",
                main_image_hash="new_image_hash",
                bsr_position=12,
                price_current=29.99,
                price_original=39.99,
                currency="USD",
                coupon_text="10% off",
                availability_status="IN_STOCK",
                buy_box_status="HAS_BUY_BOX",
                buy_box_seller_name="Amazon",
                rating_value=4.7,
                review_count=128,
                variation_count=3,
            ),
            source_refs={"provider": "APIFY"},
        )
    )

    assert inserted is False
    assert existing_snapshot.title == "Original Title"
    assert existing_snapshot.save_called is False


def test_run_orchestrator_build_run_input_uses_saswave_adapters():
    gateway = SimpleNamespace(
        config=SimpleNamespace(
            webhook_url=None,
            webhook_secret=None,
            category_input_adapter="saswave_category",
            category_amazon_domain="www.amazon.com",
            competitor_input_adapter="saswave_competitor",
            competitor_amazon_domain="www.amazon.com",
        )
    )
    orchestrator = RunOrchestrator(gateway)

    category_job = Job(
        job_code="job_cat_20260408_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code="ct_demo",
        snapshot_date=date(2026, 4, 8),
        trigger_mode=TriggerMode.MANUAL,
        status=JobStatus.QUEUED,
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY,
            binding_code="bind_category_top50_v1",
        ),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        created_at=datetime(2026, 4, 8, 2, 0, tzinfo=UTC),
    )
    category_tracker = SimpleNamespace(
        marketplace="amazon_us",
        scope=SimpleNamespace(
            browse_node_id="123456",
            browse_node_url="https://www.amazon.com/s?i=specialty-aps&rh=n%3A123456",
        ),
        tracking_config=SimpleNamespace(top_n=50),
    )
    category_payload = orchestrator._build_run_input(category_job, category_tracker)

    assert category_payload["search_url"] == category_tracker.scope.browse_node_url
    assert category_payload["max_pages"] == 1
    assert category_payload["amazon_domain"] == "www.amazon.com"

    competitor_job = Job(
        job_code="job_cmp_20260408_001",
        tracker_type=TrackerType.COMPETITOR,
        tracker_code="cmp_demo",
        snapshot_date=date(2026, 4, 8),
        trigger_mode=TriggerMode.MANUAL,
        status=JobStatus.QUEUED,
        run_strategy=JobRunStrategy(
            provider=Provider.APIFY,
            binding_code="bind_competitor_tracking_v1",
        ),
        summary=JobSummary(expected_items=0, imported_items=0, events_emitted=0),
        created_at=datetime(2026, 4, 8, 2, 0, tzinfo=UTC),
    )
    competitor_tracker = SimpleNamespace(
        marketplace="amazon_us",
        tracked_asins=[
            SimpleNamespace(asin="B0BN72FYFG", enabled=True),
            SimpleNamespace(asin="B09NNBBY8F", enabled=False),
        ],
    )
    competitor_payload = orchestrator._build_run_input(
        competitor_job,
        competitor_tracker,
    )

    assert competitor_payload == {
        "asins": ["B0BN72FYFG"],
        "amazon_domain": "www.amazon.com",
    }
