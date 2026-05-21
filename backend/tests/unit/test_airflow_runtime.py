from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.airflow_runtime import (
    resolve_airflow_reference_date,
    resolve_airflow_reference_time,
    run_apify_poller_batch_task,
    run_importer_batch_task,
    run_schedule_batch_task,
    run_weekly_digest_batch_task,
)
from app.config.config import Config


class FakeResult:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self):
        return self.payload


def test_resolve_airflow_reference_time_prefers_interval_end():
    logical_date = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)
    data_interval_end = datetime(2026, 4, 10, 10, 15, tzinfo=UTC)

    resolved = resolve_airflow_reference_time(
        {
            "dag_run": SimpleNamespace(logical_date=logical_date),
            "data_interval_end": data_interval_end,
        }
    )

    assert resolved == data_interval_end


def test_resolve_airflow_reference_date_uses_resolved_time():
    logical_date = datetime(2026, 4, 3, 10, 0, tzinfo=UTC)

    resolved = resolve_airflow_reference_date(
        {"dag_run": SimpleNamespace(logical_date=logical_date)}
    )

    assert resolved == date(2026, 4, 3)


def test_run_schedule_batch_task_forwards_reference_time_and_closes_store(monkeypatch):
    captured: dict[str, object] = {}

    class FakeStore:
        async def schedule_jobs(self, reference_time=None):
            captured["reference_time"] = reference_time
            return FakeResult({"created_jobs": 0, "dispatched_jobs": 0})

        async def close(self):
            captured["closed"] = True

    async def fake_build_store(settings):
        captured["settings"] = settings
        return FakeStore()

    monkeypatch.setattr("app.airflow_runtime.get_settings", lambda: Config())
    monkeypatch.setattr("app.airflow_runtime.configure_logging", lambda: None)
    monkeypatch.setattr("app.airflow_runtime.build_store", fake_build_store)

    reference_time = datetime(2026, 4, 8, 4, 15, tzinfo=UTC)
    payload = run_schedule_batch_task(reference_time=reference_time)

    assert payload == {"created_jobs": 0, "dispatched_jobs": 0}
    assert captured["reference_time"] == reference_time
    assert captured["closed"] is True
    assert isinstance(captured["settings"], Config)


def test_run_apify_poller_batch_task_executes_and_closes_store(monkeypatch):
    captured: dict[str, object] = {}

    class FakeStore:
        async def poll_apify_runs(self):
            captured["polled"] = True
            return FakeResult({"polled_runs": 0, "updated_runs": 0})

        async def close(self):
            captured["closed"] = True

    async def fake_build_store(settings):
        return FakeStore()

    monkeypatch.setattr("app.airflow_runtime.get_settings", lambda: Config())
    monkeypatch.setattr("app.airflow_runtime.configure_logging", lambda: None)
    monkeypatch.setattr("app.airflow_runtime.build_store", fake_build_store)

    payload = run_apify_poller_batch_task()

    assert payload == {"polled_runs": 0, "updated_runs": 0}
    assert captured["polled"] is True
    assert captured["closed"] is True


def test_run_importer_batch_task_executes_and_closes_store(monkeypatch):
    captured: dict[str, object] = {}

    class FakeStore:
        async def process_import_jobs(self):
            captured["imported"] = True
            return FakeResult({"processed_jobs": 0, "skipped_jobs": 0})

        async def close(self):
            captured["closed"] = True

    async def fake_build_store(settings):
        return FakeStore()

    monkeypatch.setattr("app.airflow_runtime.get_settings", lambda: Config())
    monkeypatch.setattr("app.airflow_runtime.configure_logging", lambda: None)
    monkeypatch.setattr("app.airflow_runtime.build_store", fake_build_store)

    payload = run_importer_batch_task()

    assert payload == {"processed_jobs": 0, "skipped_jobs": 0}
    assert captured["imported"] is True
    assert captured["closed"] is True


def test_run_weekly_digest_batch_task_forwards_reference_date(monkeypatch):
    captured: dict[str, object] = {}

    class FakeStore:
        async def process_digest_jobs(self, reference_date=None):
            captured["reference_date"] = reference_date
            return FakeResult({"generated_digests": 1, "failed_digests": 0})

        async def close(self):
            captured["closed"] = True

    async def fake_build_store(settings):
        return FakeStore()

    monkeypatch.setattr("app.airflow_runtime.get_settings", lambda: Config())
    monkeypatch.setattr("app.airflow_runtime.configure_logging", lambda: None)
    monkeypatch.setattr("app.airflow_runtime.build_store", fake_build_store)

    reference_date = date(2026, 4, 3)
    payload = run_weekly_digest_batch_task(reference_date=reference_date)

    assert payload == {"generated_digests": 1, "failed_digests": 0}
    assert captured["reference_date"] == reference_date
    assert captured["closed"] is True
