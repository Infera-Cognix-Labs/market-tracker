from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.v1.deps import get_store
from app.models.api import (
    NotificationRule,
    NotificationRuleCreateRequest,
    NotificationRuleListResponse,
    NotificationRuleUpdateRequest,
)
from app.store import BaseStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/notification-rules",
    tags=["notification-rules"],
)


@router.get("", response_model=NotificationRuleListResponse)
async def list_notification_rules(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> NotificationRuleListResponse:
    return await store.list_notification_rules(workspace_id)


@router.post("", response_model=NotificationRule, status_code=status.HTTP_201_CREATED)
async def create_notification_rule(
    workspace_id: str,
    payload: NotificationRuleCreateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> NotificationRule:
    return await store.create_notification_rule(workspace_id, payload)


@router.patch("/{rule_code}", response_model=NotificationRule)
async def update_notification_rule(
    workspace_id: str,
    rule_code: str,
    payload: NotificationRuleUpdateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> NotificationRule:
    return await store.update_notification_rule(workspace_id, rule_code, payload)


@router.delete("/{rule_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_rule(
    workspace_id: str,
    rule_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> Response:
    await store.delete_notification_rule(workspace_id, rule_code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
