from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.core.errors import ConflictError
from app.models.api import Frequency, TriggerMode
from app.services.digest_service import DigestService
from app.services.scheduler_service import SchedulerService


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


def test_scheduler_service_creates_and_dispatches_due_jobs(run_async, monkeypatch):
    now = datetime(2026, 4, 8, 4, 15, tzinfo=UTC)

    category_trackers = [
        SimpleNamespace(
            workspace_id="ws_demo_us",
            tracker_code="ct_due",
            schedule=SimpleNamespace(frequency=Frequency.DAILY, hour_utc=4),
        ),
        SimpleNamespace(
            workspace_id="ws_demo_us",
            tracker_code="ct_not_due",
            schedule=SimpleNamespace(frequency=Frequency.DAILY, hour_utc=8),
        ),
    ]
    competitor_trackers = [
        SimpleNamespace(
            workspace_id="ws_demo_us",
            tracker_code="cmp_due_existing",
            schedule=SimpleNamespace(frequency=Frequency.DAILY, hour_utc=4),
        )
    ]

    monkeypatch.setattr(
        "app.services.scheduler_service.CategoryTrackerDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor(category_trackers)),
    )
    monkeypatch.setattr(
        "app.services.scheduler_service.CompetitorTrackerDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor(competitor_trackers)),
    )

    created_jobs: list[tuple[str, str, date, TriggerMode]] = []
    dispatched_jobs: list[tuple[str, str]] = []

    class FakeJobService:
        async def create_job(self, workspace_id, payload):
            if payload.tracker_code == "cmp_due_existing":
                raise ConflictError("already exists")
            created_jobs.append(
                (
                    workspace_id,
                    payload.tracker_code,
                    payload.snapshot_date,
                    payload.trigger_mode,
                )
            )
            return SimpleNamespace(
                job_code=f"job_{payload.tracker_code}",
                snapshot_date=payload.snapshot_date,
            )

        async def dispatch_job(self, workspace_id, job_code):
            dispatched_jobs.append((workspace_id, job_code))

    result = run_async(
        SchedulerService(FakeJobService()).schedule_due_jobs(reference_time=now)
    )

    assert result.scanned_trackers == 3
    assert result.due_trackers == 2
    assert result.created_jobs == 1
    assert result.dispatched_jobs == 1
    assert result.skipped_existing == 1
    assert result.failed_jobs == 0
    assert created_jobs == [
        ("ws_demo_us", "ct_due", date(2026, 4, 8), TriggerMode.SCHEDULED)
    ]
    assert dispatched_jobs == [("ws_demo_us", "job_ct_due")]


def test_digest_service_generates_weekly_digest(run_async, monkeypatch, seed_data):
    inserted_digests: list[object] = []

    event_docs = [
        FakeDocument(
            workspace_id=seed_data.workspace_id, **event.model_dump(mode="python")
        )
        for event in seed_data.events
    ]
    category_docs = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            tracker_code=seed_data.category_trackers[0].tracker_code,
            name=seed_data.category_trackers[0].name,
        )
    ]
    competitor_docs = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            tracker_code=seed_data.competitor_trackers[0].tracker_code,
            name=seed_data.competitor_trackers[0].name,
        )
    ]

    class FakeWeeklyDigestDocument:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        async def insert(self):
            inserted_digests.append(self)

        @staticmethod
        async def find_one(*args, **kwargs):
            return None

        @staticmethod
        def find(*args, **kwargs):
            return FakeCursor([])

    monkeypatch.setattr(
        "app.services.digest_service.EventDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor(event_docs)),
    )
    monkeypatch.setattr(
        "app.services.digest_service.CategoryTrackerDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor(category_docs)),
    )
    monkeypatch.setattr(
        "app.services.digest_service.CompetitorTrackerDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor(competitor_docs)),
    )
    monkeypatch.setattr(
        "app.services.digest_service.WeeklyDigestDocument",
        FakeWeeklyDigestDocument,
    )

    result = run_async(
        DigestService().generate_weekly_digests(reference_date=date(2026, 4, 3))
    )

    assert result.scanned_workspaces == 1
    assert result.generated_digests == 1
    assert result.skipped_digests == 0
    assert result.failed_digests == 0
    assert len(inserted_digests) == 1

    digest = inserted_digests[0]
    assert digest.digest_code == "wd_2026w14_ws_demo_us"
    assert digest.week_start == date(2026, 3, 28)
    assert digest.week_end == date(2026, 4, 3)
    assert digest.summary.top10_enter_count == 1
    assert digest.summary.price_change_count == 1
    assert len(digest.tracker_refs) == 2
    assert digest.threats


def test_digest_service_skips_when_digest_exists(run_async, monkeypatch):
    workspace_id = "ws_demo_us"

    class FakeWeeklyDigestDocument:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        async def insert(self):
            raise AssertionError("should not insert when digest already exists")

        @staticmethod
        async def find_one(*args, **kwargs):
            return SimpleNamespace(digest_code="wd_2026w14_ws_demo_us")

        @staticmethod
        def find(*args, **kwargs):
            return FakeCursor([SimpleNamespace(workspace_id=workspace_id)])

    monkeypatch.setattr(
        "app.services.digest_service.EventDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor([])),
    )
    monkeypatch.setattr(
        "app.services.digest_service.CategoryTrackerDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor([])),
    )
    monkeypatch.setattr(
        "app.services.digest_service.CompetitorTrackerDocument",
        SimpleNamespace(find=lambda *args, **kwargs: FakeCursor([])),
    )
    monkeypatch.setattr(
        "app.services.digest_service.WeeklyDigestDocument",
        FakeWeeklyDigestDocument,
    )

    result = run_async(
        DigestService().generate_weekly_digests(reference_date=date(2026, 4, 3))
    )

    assert result.scanned_workspaces == 1
    assert result.generated_digests == 0
    assert result.skipped_digests == 1
    assert result.failed_digests == 0
