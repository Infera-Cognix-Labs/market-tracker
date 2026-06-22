from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.config.config import LLMConfig
from app.core.logging import correlation_context, get_logger
from app.models.api import DigestInsights, Event, EventType, Severity, WeeklyDigest

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are an Amazon marketplace analyst. Given structured market tracking data, \
produce a concise analytical summary. Output valid JSON only, no markdown."""

_USER_PROMPT_TEMPLATE = """\
Analyze the following weekly marketplace tracking data.

Period: {week_start} to {week_end}
Trackers monitored: {tracker_count} ({tracker_names})

Event Summary:
- New entrants to Top 50: {new_entrant_count}
- Returning to Top 50: {returning_count}
- Entered Top 10: {top10_enter_count}
- Price changes: {price_change_count}
- Listing changes: {listing_change_count}

Top Threats Detected ({threat_count}):
{threats_text}

Notable Events (top {event_count} by severity):
{events_text}

Produce a JSON object with exactly these fields:
- "executive_summary": 2-3 sentence overview of the week's most significant developments
- "key_trends": array of {trend_count} concise bullet points identifying notable patterns
- "risk_assessment": 1-2 sentence evaluation of competitive risk level

Rules:
- Be specific: reference actual ASINs, marketplaces, and event types from the data
- Focus on patterns across multiple signals, not isolated events
- Use factual language based on the data provided — do not speculate
- If data is sparse, reduce key_trends accordingly (minimum 2)"""

_SEVERITY_WEIGHT = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
}

_LISTING_EVENT_TYPES = {
    EventType.TITLE_CHANGED,
    EventType.MAIN_IMAGE_CHANGED,
    EventType.VARIATIONS_ADDED,
}


def _build_event_digest(events: list[Event]) -> list[dict[str, str]]:
    sorted_events = sorted(
        events,
        key=lambda e: (_SEVERITY_WEIGHT.get(e.severity, 2), -e.event_time.timestamp()),
    )
    top_events = sorted_events[:10]
    result: list[dict[str, str]] = []
    for event in top_events:
        entry: dict[str, str] = {
            "severity": event.severity.value,
            "marketplace": event.marketplace,
            "asin": event.asin,
            "event_type": event.event_type.value,
            "summary": event.summary,
        }
        if event.payload and event.payload.delta:
            delta = event.payload.delta
            parts: list[str] = []
            if delta.price_current_pct is not None:
                parts.append(f"{delta.price_current_pct:+.1f}%")
            if delta.price_current_abs is not None:
                parts.append(f"abs {delta.price_current_abs:+.2f}")
            if parts:
                entry["delta"] = ", ".join(parts)
        result.append(entry)
    return result


def _format_events_text(digest_events: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for entry in digest_events:
        delta_str = f" ({entry['delta']})" if "delta" in entry else ""
        lines.append(
            f"- [{entry['severity']}] {entry['marketplace']} | {entry['asin']} "
            f'| {entry["event_type"]}: "{entry["summary"]}"{delta_str}'
        )
    return "\n".join(lines) if lines else "No notable events."


def _format_threats_text(digest: WeeklyDigest) -> str:
    lines: list[str] = []
    for threat in digest.threats:
        event_types = ", ".join(et.value for et in threat.event_types)
        lines.append(
            f"- {threat.asin} ({threat.marketplace}): "
            f"event types [{event_types}] — {threat.reason}"
        )
    return "\n".join(lines) if lines else "No threats detected."


def _count_trends(events: list[Event]) -> int:
    event_count = len(events)
    if event_count < 10:
        return 2
    if event_count < 50:
        return 4
    return 6


class LLMService:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout_secs,
        )

    async def generate_digest_insights(
        self,
        *,
        digest: WeeklyDigest,
        events: list[Event],
    ) -> DigestInsights | None:
        event_digest = _build_event_digest(events)
        trend_count = _count_trends(events)

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            week_start=digest.week_start,
            week_end=digest.week_end,
            tracker_count=len(digest.tracker_refs),
            tracker_names=", ".join(tr.tracker_name for tr in digest.tracker_refs),
            new_entrant_count=digest.summary.new_entrant_count,
            returning_count=digest.summary.returning_count,
            top10_enter_count=digest.summary.top10_enter_count,
            price_change_count=digest.summary.price_change_count,
            listing_change_count=digest.summary.listing_change_count,
            threat_count=len(digest.threats),
            threats_text=_format_threats_text(digest),
            event_count=len(event_digest),
            events_text=_format_events_text(event_digest),
            trend_count=trend_count,
        )

        last_error: Exception | None = None
        for attempt in range(self._config.retry_attempts + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._config.model,
                    max_tokens=self._config.max_tokens,
                    temperature=self._config.temperature,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = response.choices[0].message.content or ""
                parsed = json.loads(
                    content.strip().removeprefix("```json").removesuffix("```").strip()
                )
                return DigestInsights(
                    executive_summary=str(parsed.get("executive_summary", "")),
                    key_trends=[str(t) for t in parsed.get("key_trends", [])],
                    risk_assessment=str(parsed.get("risk_assessment", "")),
                )
            except json.JSONDecodeError as exc:
                last_error = exc
                logger.warning(
                    "LLM response was not valid JSON, retrying.",
                    extra={
                        "context": correlation_context(
                            attempt=attempt + 1,
                            error_type="json_decode",
                        )
                    },
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM API call failed, retrying.",
                    extra={
                        "context": correlation_context(
                            attempt=attempt + 1,
                            error_type=type(exc).__name__,
                        )
                    },
                )

        logger.warning(
            "LLM insight generation failed after all retries.",
            extra={
                "context": correlation_context(
                    error_type=type(last_error).__name__ if last_error else "unknown",
                    retry_attempts=self._config.retry_attempts,
                )
            },
        )
        return None
