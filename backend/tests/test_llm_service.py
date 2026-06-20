from __future__ import annotations

import json
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.config.config import LLMConfig
from app.models.api import (
    Event,
    EventPayload,
    EventType,
    Severity,
    TrackerRef,
    TrackerType,
    WeeklyDigest,
    WeeklyDigestSummary,
)
from app.services.llm_service import (
    LLMService,
    _build_event_digest,
    _count_trends,
    _format_events_text,
    _format_threats_text,
)


def _make_event(
    *,
    event_type: EventType = EventType.PRICE_CHANGED,
    severity: Severity = Severity.MEDIUM,
    marketplace: str = "amazon_us",
    asin: str = "B0ABC12345",
    summary: str = "price changed",
    event_time: datetime | None = None,
) -> Event:
    return Event(
        event_code="evt_001",
        tracker_type=TrackerType.COMPETITOR,
        tracker_code="trk_001",
        marketplace=marketplace,
        asin=asin,
        event_type=event_type,
        event_time=event_time or datetime(2025, 6, 15, tzinfo=timezone.utc),
        snapshot_date=date(2025, 6, 15),
        severity=severity,
        title="Test Product",
        summary=summary,
        payload=EventPayload(),
    )


def _make_digest(
    *,
    threats: list | None = None,
    summary: WeeklyDigestSummary | None = None,
) -> WeeklyDigest:
    return WeeklyDigest(
        digest_code="wd_2025w25_ws1",
        week_start=date(2025, 6, 9),
        week_end=date(2025, 6, 15),
        tracker_refs=[
            TrackerRef(
                tracker_type=TrackerType.COMPETITOR,
                tracker_code="trk_001",
                tracker_name="Test Tracker",
            )
        ],
        summary=summary
        or WeeklyDigestSummary(
            new_entrant_count=3,
            returning_count=1,
            top10_enter_count=2,
            price_change_count=5,
            listing_change_count=2,
        ),
        threats=threats or [],
        created_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
    )


def _make_config(**overrides: object) -> LLMConfig:
    defaults = {
        "enabled": True,
        "api_key": "sk-test-key",
        "model": "gpt-4o-mini",
        "max_tokens": 2500,
        "temperature": 0.3,
        "timeout_secs": 30,
        "retry_attempts": 2,
    }
    defaults.update(overrides)
    return LLMConfig(**defaults)


class TestBuildEventDigest:
    def test_orders_by_severity(self) -> None:
        events = [
            _make_event(severity=Severity.LOW),
            _make_event(severity=Severity.HIGH, asin="B0HIGH12345"),
            _make_event(severity=Severity.MEDIUM, asin="B0MEDS12345"),
        ]
        result = _build_event_digest(events)
        assert result[0]["severity"] == "HIGH"
        assert result[1]["severity"] == "MEDIUM"
        assert result[2]["severity"] == "LOW"

    def test_limits_to_10_events(self) -> None:
        events = [_make_event(asin=f"B0NUM{i:07d}") for i in range(15)]
        result = _build_event_digest(events)
        assert len(result) == 10

    def test_empty_events(self) -> None:
        result = _build_event_digest([])
        assert result == []


class TestFormatEventsText:
    def test_formats_correctly(self) -> None:
        digest_events = [
            {
                "severity": "HIGH",
                "marketplace": "amazon_us",
                "asin": "B0ABC12345",
                "event_type": "PRICE_CHANGED",
                "summary": "price dropped from $29.99 to $24.99",
            }
        ]
        result = _format_events_text(digest_events)
        assert "[HIGH]" in result
        assert "amazon_us" in result
        assert "B0ABC12345" in result
        assert "PRICE_CHANGED" in result

    def test_empty_events(self) -> None:
        result = _format_events_text([])
        assert result == "No notable events."


class TestFormatThreatsText:
    def test_formats_threats(self) -> None:
        from app.models.api import Threat, EventType as ET

        threat = Threat(
            asin="B0ABC12345",
            marketplace="amazon_us",
            reason="Observed PRICE_CHANGED during the selected timeframe.",
            event_types=[ET.PRICE_CHANGED],
            tracker_refs=[],
        )
        digest = _make_digest(threats=[threat])
        result = _format_threats_text(digest)
        assert "B0ABC12345" in result
        assert "amazon_us" in result

    def test_no_threats(self) -> None:
        digest = _make_digest(threats=[])
        result = _format_threats_text(digest)
        assert result == "No threats detected."


class TestCountTrends:
    def test_sparse_data(self) -> None:
        events = [_make_event() for _ in range(5)]
        assert _count_trends(events) == 2

    def test_medium_data(self) -> None:
        events = [_make_event() for _ in range(25)]
        assert _count_trends(events) == 4

    def test_large_data(self) -> None:
        events = [_make_event() for _ in range(100)]
        assert _count_trends(events) == 6


class TestLLMService:
    @pytest.mark.asyncio
    async def test_successful_insights(self) -> None:
        config = _make_config()
        service = LLMService(config)

        mock_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "executive_summary": "Test summary.",
                                "key_trends": ["Trend 1", "Trend 2"],
                                "risk_assessment": "Low risk.",
                            }
                        )
                    )
                )
            ]
        )

        with patch.object(
            service._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await service.generate_digest_insights(
                digest=_make_digest(),
                events=[_make_event()],
            )

        assert result is not None
        assert result.executive_summary == "Test summary."
        assert result.key_trends == ["Trend 1", "Trend 2"]
        assert result.risk_assessment == "Low risk."

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self) -> None:
        config = _make_config(retry_attempts=0)
        service = LLMService(config)

        mock_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
        )

        with patch.object(
            service._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await service.generate_digest_insights(
                digest=_make_digest(),
                events=[_make_event()],
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self) -> None:
        config = _make_config(retry_attempts=0)
        service = LLMService(config)

        with patch.object(
            service._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=Exception("API error"),
        ):
            result = await service.generate_digest_insights(
                digest=_make_digest(),
                events=[_make_event()],
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_retry_on_failure(self) -> None:
        config = _make_config(retry_attempts=1)
        service = LLMService(config)

        success_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "executive_summary": "Success after retry.",
                                "key_trends": ["Trend A"],
                                "risk_assessment": "Medium.",
                            }
                        )
                    )
                )
            ]
        )

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call fails")
            return success_response

        with patch.object(
            service._client.chat.completions, "create", side_effect=side_effect
        ):
            result = await service.generate_digest_insights(
                digest=_make_digest(),
                events=[_make_event()],
            )

        assert result is not None
        assert result.executive_summary == "Success after retry."
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_empty_content_returns_none(self) -> None:
        config = _make_config(retry_attempts=0)
        service = LLMService(config)

        mock_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
        )

        with patch.object(
            service._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await service.generate_digest_insights(
                digest=_make_digest(),
                events=[_make_event()],
            )

        assert result is None
