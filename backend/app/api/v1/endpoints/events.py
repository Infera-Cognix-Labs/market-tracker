from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_store
from app.models.api import EventListResponse, EventType, Severity, TrackerType
from app.store import BaseStore

router = APIRouter(prefix="/workspaces/{workspace_id}/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    tracker_type: TrackerType | None = Query(default=None),
    tracker_code: str | None = Query(default=None),
    marketplace: str | None = Query(default=None, pattern=r"^amazon_[a-z]{2}$"),
    asin: str | None = Query(default=None, min_length=10, max_length=12),
    event_type: EventType | None = Query(default=None),
    severity: Severity | None = Query(default=None),
) -> EventListResponse:
    return await store.list_events(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
        tracker_type=tracker_type,
        tracker_code=tracker_code,
        marketplace=marketplace,
        asin=asin,
        event_type=event_type,
        severity=severity,
    )
