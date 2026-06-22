from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.logging import correlation_context, get_logger
from app.models.api import (
    Event,
    NotificationDeliveryStatus,
    NotificationRule,
    NotificationRuleCreateRequest,
    NotificationRuleListResponse,
    NotificationRuleUpdateRequest,
    NotificationWorkerResult,
)
from app.models.documents import (
    EventDocument,
    NotificationDeliveryDocument,
    NotificationRuleDocument,
    ProductDocument,
)
from app.services.shared import event_doc_to_model

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _rule_effective_since(rule: NotificationRuleDocument) -> datetime:
    return max(_as_utc(rule.created_at), _as_utc(rule.updated_at))


def _build_code(prefix: str, *parts: object) -> str:
    digest = hashlib.sha1(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _rule_doc_to_model(document: NotificationRuleDocument) -> NotificationRule:
    return NotificationRule(
        rule_code=document.rule_code,
        name=document.name,
        enabled=document.enabled,
        webhook_url=document.webhook_url,
        severities=document.severities,
        event_types=document.event_types,
        tracker_type=document.tracker_type,
        tracker_code=document.tracker_code,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


class NotificationService:
    async def list_rules(self, workspace_id: str) -> NotificationRuleListResponse:
        documents = (
            await NotificationRuleDocument.find(
                NotificationRuleDocument.workspace_id == workspace_id
            )
            .sort("+created_at")
            .to_list()
        )
        return NotificationRuleListResponse(
            items=[_rule_doc_to_model(document) for document in documents]
        )

    async def create_rule(
        self, workspace_id: str, payload: NotificationRuleCreateRequest
    ) -> NotificationRule:
        now = _utc_now()
        document = NotificationRuleDocument(
            workspace_id=workspace_id,
            rule_code=_build_code("nr", workspace_id, payload.name, now.isoformat()),
            name=payload.name,
            enabled=payload.enabled,
            webhook_url=payload.webhook_url,
            severities=[item.value for item in payload.severities],
            event_types=[item.value for item in payload.event_types],
            tracker_type=payload.tracker_type.value if payload.tracker_type else None,
            tracker_code=payload.tracker_code or None,
            created_at=now,
            updated_at=now,
        )
        await document.insert()
        return _rule_doc_to_model(document)

    async def update_rule(
        self,
        workspace_id: str,
        rule_code: str,
        payload: NotificationRuleUpdateRequest,
    ) -> NotificationRule:
        document = await self._get_rule_document(workspace_id, rule_code)
        update_data = payload.model_dump(exclude_unset=True)

        if "name" in update_data:
            document.name = payload.name or document.name
        if "enabled" in update_data and payload.enabled is not None:
            document.enabled = payload.enabled
        if "webhook_url" in update_data and payload.webhook_url is not None:
            document.webhook_url = payload.webhook_url
        if "severities" in update_data and payload.severities is not None:
            document.severities = [item.value for item in payload.severities]
        if "event_types" in update_data and payload.event_types is not None:
            document.event_types = [item.value for item in payload.event_types]
        if "tracker_type" in update_data:
            document.tracker_type = (
                payload.tracker_type.value if payload.tracker_type else None
            )
        if "tracker_code" in update_data:
            document.tracker_code = payload.tracker_code or None

        document.updated_at = _utc_now()
        await document.save()
        return _rule_doc_to_model(document)

    async def delete_rule(self, workspace_id: str, rule_code: str) -> None:
        document = await self._get_rule_document(workspace_id, rule_code)
        await document.delete()

    async def process_pending_notifications(
        self, *, batch_size: int = 100
    ) -> NotificationWorkerResult:
        batch_size = max(1, batch_size)
        rules = (
            await NotificationRuleDocument.find({"enabled": True})
            .sort("+created_at")
            .to_list()
        )
        if not rules:
            return NotificationWorkerResult(
                scanned_events=0,
                matched_deliveries=0,
                sent=0,
                failed=0,
                skipped_existing=0,
            )

        scanned_events = 0
        sent = 0
        failed = 0
        matched = 0
        skipped_existing = 0

        for rule in rules:
            effective_since = _rule_effective_since(rule)
            attempted_for_rule = 0
            offset = 0
            while attempted_for_rule < batch_size:
                event_documents = (
                    await EventDocument.find(
                        self._build_event_query(rule, effective_since)
                    )
                    .sort("-event_time")
                    .skip(offset)
                    .limit(batch_size)
                    .to_list()
                )
                if not event_documents:
                    break

                scanned_events += len(event_documents)
                offset += len(event_documents)

                for event_document in event_documents:
                    if attempted_for_rule >= batch_size:
                        break

                    if _as_utc(event_document.event_time) < effective_since:
                        continue
                    event = event_doc_to_model(event_document)
                    if not self._matches_rule(event, rule):
                        continue

                    delivery = await self._claim_delivery(rule, event)
                    if delivery is None:
                        skipped_existing += 1
                        continue

                    matched += 1
                    attempted_for_rule += 1
                    ok, error = await self._send_slack(rule, event)
                    now = _utc_now()
                    delivery.attempts += 1
                    delivery.updated_at = now
                    delivery.status = (
                        NotificationDeliveryStatus.SUCCESS.value
                        if ok
                        else NotificationDeliveryStatus.FAILED.value
                    )
                    delivery.error = error
                    delivery.delivered_at = now if ok else None
                    await delivery.save()
                    if ok:
                        sent += 1
                    else:
                        failed += 1

        return NotificationWorkerResult(
            scanned_events=scanned_events,
            matched_deliveries=matched,
            sent=sent,
            failed=failed,
            skipped_existing=skipped_existing,
        )

    def _build_event_query(
        self, rule: NotificationRuleDocument, effective_since: datetime
    ) -> dict[str, Any]:
        query: dict[str, Any] = {
            "workspace_id": rule.workspace_id,
            "event_time": {"$gte": effective_since},
        }
        if rule.severities:
            query["severity"] = {"$in": rule.severities}
        if rule.event_types:
            query["event_type"] = {"$in": rule.event_types}
        if rule.tracker_type:
            query["tracker_type"] = rule.tracker_type
        if rule.tracker_code:
            query["tracker_code"] = rule.tracker_code
        return query

    async def _get_rule_document(
        self, workspace_id: str, rule_code: str
    ) -> NotificationRuleDocument:
        document = await NotificationRuleDocument.find_one(
            NotificationRuleDocument.workspace_id == workspace_id,
            NotificationRuleDocument.rule_code == rule_code,
        )
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "NOTIFICATION_RULE_NOT_FOUND",
                    "message": "Rule not found.",
                },
            )
        return document

    def _matches_rule(self, event: Event, rule: NotificationRuleDocument) -> bool:
        if rule.severities and event.severity.value not in rule.severities:
            return False
        if rule.event_types and event.event_type.value not in rule.event_types:
            return False
        if rule.tracker_type and event.tracker_type.value != rule.tracker_type:
            return False
        if rule.tracker_code and event.tracker_code != rule.tracker_code:
            return False
        return True

    async def _claim_delivery(
        self, rule: NotificationRuleDocument, event: Event
    ) -> NotificationDeliveryDocument | None:
        now = _utc_now()
        delivery = NotificationDeliveryDocument(
            workspace_id=rule.workspace_id,
            delivery_code=_build_code(
                "nd", rule.workspace_id, rule.rule_code, event.event_code
            ),
            rule_code=rule.rule_code,
            event_code=event.event_code,
            status=NotificationDeliveryStatus.PENDING.value,
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        try:
            await delivery.insert()
        except DuplicateKeyError:
            existing = await NotificationDeliveryDocument.find_one(
                NotificationDeliveryDocument.workspace_id == rule.workspace_id,
                NotificationDeliveryDocument.rule_code == rule.rule_code,
                NotificationDeliveryDocument.event_code == event.event_code,
            )
            if (
                existing is not None
                and existing.status == NotificationDeliveryStatus.FAILED.value
                and existing.attempts < 3
            ):
                return existing
            return None
        return delivery

    async def _send_slack(
        self,
        rule: NotificationRuleDocument,
        event: Event,
    ) -> tuple[bool, str | None]:
        product = await self._get_product_document(rule.workspace_id, event)
        payload = self._build_slack_payload(rule, event, product)
        try:
            await asyncio.to_thread(self._post_json, rule.webhook_url, payload)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            logger.warning(
                "Failed to deliver event notification to Slack.",
                extra={
                    "context": correlation_context(
                        workspace_id=rule.workspace_id,
                        rule_code=rule.rule_code,
                        event_code=event.event_code,
                        error=str(exc),
                    )
                },
            )
            return False, str(exc)[:500]
        return True, None

    def _post_json(self, url: str, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            response.read()

    async def _get_product_document(
        self, workspace_id: str, event: Event
    ) -> ProductDocument | None:
        return await ProductDocument.find_one(
            ProductDocument.workspace_id == workspace_id,
            ProductDocument.marketplace == event.marketplace,
            ProductDocument.asin == event.asin,
        )

    def _event_product_image_url(self, event: Event) -> str | None:
        current = event.payload.current
        if current and current.main_image_url:
            return current.main_image_url
        previous = event.payload.previous
        if previous and previous.main_image_url:
            return previous.main_image_url
        return None

    def _event_product_url(
        self, event: Event, product: ProductDocument | None = None
    ) -> str:
        if product and product.product_url:
            return product.product_url
        return f"https://www.amazon.com/dp/{event.asin}"

    def _build_slack_payload(
        self,
        rule: NotificationRuleDocument,
        event: Event,
        product: ProductDocument | None = None,
    ) -> dict[str, Any]:
        color = {
            "HIGH": "#dc2626",
            "MEDIUM": "#d97706",
            "LOW": "#16a34a",
        }.get(event.severity.value, "#64748b")
        product_url = self._event_product_url(event, product)
        image_url = (
            product.main_image_url_latest
            if product and product.main_image_url_latest
            else self._event_product_image_url(event)
        )
        attachment: dict[str, Any] = {
            "color": color,
            "fields": [
                {
                    "title": "Type",
                    "value": event.event_type.value,
                    "short": True,
                },
                {
                    "title": "Severity",
                    "value": event.severity.value,
                    "short": True,
                },
                {
                    "title": "ASIN",
                    "value": f"<{product_url}|{event.asin}>",
                    "short": True,
                },
                {
                    "title": "Tracker",
                    "value": (f"{event.tracker_code} ({event.tracker_type.value})"),
                    "short": True,
                },
                {"title": "Product", "value": event.title, "short": False},
                {
                    "title": "Summary",
                    "value": event.summary or "N/A",
                    "short": False,
                },
                {
                    "title": "Time",
                    "value": event.event_time.isoformat(),
                    "short": True,
                },
                {
                    "title": "Marketplace",
                    "value": event.marketplace,
                    "short": True,
                },
            ],
        }
        if image_url:
            attachment["image_url"] = image_url
        return {
            "text": f"[{rule.name}] {event.title}",
            "attachments": [attachment],
        }
