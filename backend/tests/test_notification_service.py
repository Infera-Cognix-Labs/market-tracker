from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models.api import (
    Event,
    EventPayload,
    EventType,
    Severity,
    TrackerType,
)
from app.services import notification_service as module
from app.services.notification_service import NotificationService


class _Query:
    def __init__(self, items):
        self._items = list(items)
        self._skip = 0
        self._limit = None

    def sort(self, field):
        reverse = field.startswith("-")
        name = field[1:] if field[0] in "+-" else field
        self._items.sort(key=lambda item: getattr(item, name), reverse=reverse)
        return self

    def skip(self, count):
        self._skip = count
        return self

    def limit(self, count):
        self._limit = count
        return self

    async def to_list(self):
        items = self._items[self._skip :]
        if self._limit is not None:
            items = items[: self._limit]
        return items


class _RuleDocument:
    rules = []

    @classmethod
    def find(cls, query):
        assert query == {"enabled": True}
        return _Query(cls.rules)


class _EventDocument:
    events = []
    queries = []

    @classmethod
    def find(cls, query):
        cls.queries.append(query)
        return _Query([event for event in cls.events if _matches_query(event, query)])


class _Delivery:
    def __init__(self):
        self.attempts = 0
        self.updated_at = None
        self.status = None
        self.error = None
        self.delivered_at = None

    async def save(self):
        return None


def _matches_query(document, query):
    for key, expected in query.items():
        actual = getattr(document, key)
        if isinstance(expected, dict):
            if "$gte" in expected and actual < expected["$gte"]:
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
            continue
        if actual != expected:
            return False
    return True


def _rule(**overrides):
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    values = {
        "workspace_id": "ws_1",
        "rule_code": "rule_1",
        "name": "High alerts",
        "enabled": True,
        "webhook_url": "https://hooks.slack.test/services/example",
        "severities": ["HIGH"],
        "event_types": [],
        "tracker_type": None,
        "tracker_code": None,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _event_document(index: int, *, severity: Severity, event_time: datetime):
    event = Event(
        event_code=f"ev_{index}",
        tracker_type=TrackerType.CATEGORY,
        tracker_code="cat_1",
        marketplace="amazon_us",
        asin=f"B000000{index:03d}"[:10],
        event_type=EventType.ENTER_TOP10,
        event_time=event_time,
        snapshot_date=date(2026, 6, 19),
        severity=severity,
        title=f"Product {index}",
        summary="Entered top 10",
        payload=EventPayload(),
    )
    return SimpleNamespace(
        workspace_id="ws_1",
        event_code=event.event_code,
        event_time=event_time,
        severity=severity.value,
        event_type=event.event_type.value,
        tracker_type=event.tracker_type.value,
        tracker_code=event.tracker_code,
        event=event,
    )


@pytest.fixture(autouse=True)
def patch_documents(monkeypatch):
    _RuleDocument.rules = []
    _EventDocument.events = []
    _EventDocument.queries = []
    monkeypatch.setattr(module, "NotificationRuleDocument", _RuleDocument)
    monkeypatch.setattr(module, "EventDocument", _EventDocument)
    monkeypatch.setattr(module, "event_doc_to_model", lambda document: document.event)


@pytest.mark.asyncio
async def test_process_pending_notifications_filters_events_before_batch_limit():
    created_at = datetime(2026, 6, 19, tzinfo=timezone.utc)
    _RuleDocument.rules = [_rule(created_at=created_at)]
    _EventDocument.events = [
        *[
            _event_document(
                index,
                severity=Severity.LOW,
                event_time=created_at + timedelta(minutes=200 - index),
            )
            for index in range(100)
        ],
        *[
            _event_document(
                100 + index,
                severity=Severity.HIGH,
                event_time=created_at + timedelta(minutes=99 - index),
            )
            for index in range(9)
        ],
    ]

    sent = []
    service = NotificationService()

    async def claim_delivery(rule, event):
        return _Delivery()

    async def send_slack(rule, event):
        sent.append(event.event_code)
        return True, None

    service._claim_delivery = claim_delivery
    service._send_slack = send_slack

    result = await service.process_pending_notifications(batch_size=100)

    assert result.sent == 9
    assert sent == [f"ev_{100 + index}" for index in range(9)]
    assert _EventDocument.queries == [
        {
            "workspace_id": "ws_1",
            "event_time": {"$gte": created_at},
            "severity": {"$in": ["HIGH"]},
        },
        {
            "workspace_id": "ws_1",
            "event_time": {"$gte": created_at},
            "severity": {"$in": ["HIGH"]},
        },
    ]


@pytest.mark.asyncio
async def test_process_pending_notifications_pages_past_existing_deliveries():
    created_at = datetime(2026, 6, 19, tzinfo=timezone.utc)
    _RuleDocument.rules = [_rule(created_at=created_at)]
    _EventDocument.events = [
        _event_document(
            index,
            severity=Severity.HIGH,
            event_time=created_at + timedelta(minutes=200 - index),
        )
        for index in range(109)
    ]

    sent = []
    service = NotificationService()

    async def claim_delivery(rule, event):
        if int(event.event_code.removeprefix("ev_")) < 100:
            return None
        return _Delivery()

    async def send_slack(rule, event):
        sent.append(event.event_code)
        return True, None

    service._claim_delivery = claim_delivery
    service._send_slack = send_slack

    result = await service.process_pending_notifications(batch_size=100)

    assert result.skipped_existing == 100
    assert result.sent == 9
    assert result.matched_deliveries == 9
    assert sent == [f"ev_{100 + index}" for index in range(9)]
    assert result.failed == 0
