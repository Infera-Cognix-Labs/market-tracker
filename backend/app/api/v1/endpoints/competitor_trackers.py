from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_store
from app.models.api import (
    CompetitorTrackerCreateRequest,
    CompetitorTrackerDetail,
    CompetitorTrackerListResponse,
    CompetitorTrackerUpdateRequest,
    TrackedAsinReplacementRequest,
)
from app.store import BaseStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/competitor-trackers",
    tags=["competitor-trackers"],
)


@router.get("", response_model=CompetitorTrackerListResponse)
async def list_competitor_trackers(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> CompetitorTrackerListResponse:
    return await store.list_competitor_trackers(workspace_id, page, page_size)


@router.post("", response_model=CompetitorTrackerDetail, status_code=status.HTTP_201_CREATED)
async def create_competitor_tracker(
    workspace_id: str,
    payload: CompetitorTrackerCreateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CompetitorTrackerDetail:
    return await store.create_competitor_tracker(workspace_id, payload)


@router.get("/{tracker_code}", response_model=CompetitorTrackerDetail)
async def get_competitor_tracker(
    workspace_id: str,
    tracker_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CompetitorTrackerDetail:
    return await store.get_competitor_tracker(workspace_id, tracker_code)


@router.patch("/{tracker_code}", response_model=CompetitorTrackerDetail)
async def update_competitor_tracker(
    workspace_id: str,
    tracker_code: str,
    payload: CompetitorTrackerUpdateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CompetitorTrackerDetail:
    return await store.update_competitor_tracker(workspace_id, tracker_code, payload)


@router.put("/{tracker_code}/tracked-asins", response_model=CompetitorTrackerDetail)
async def replace_tracked_asins(
    workspace_id: str,
    tracker_code: str,
    payload: TrackedAsinReplacementRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CompetitorTrackerDetail:
    return await store.replace_tracked_asins(workspace_id, tracker_code, payload)
