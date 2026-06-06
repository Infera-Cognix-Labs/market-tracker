from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.v1.deps import get_store
from app.api.v1.endpoints._tracker_initial_jobs import (
    create_and_dispatch_initial_job,
)
from app.models.api import (
    CompetitorTrackerCreateRequest,
    CompetitorTrackerDetail,
    CompetitorTrackerListResponse,
    CompetitorTrackerUpdateRequest,
    TrackerType,
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


@router.post(
    "", response_model=CompetitorTrackerDetail, status_code=status.HTTP_201_CREATED
)
async def create_competitor_tracker(
    workspace_id: str,
    payload: CompetitorTrackerCreateRequest,
    background_tasks: BackgroundTasks,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CompetitorTrackerDetail:
    tracker = await store.create_competitor_tracker(workspace_id, payload)
    background_tasks.add_task(
        create_and_dispatch_initial_job,
        store=store,
        workspace_id=workspace_id,
        tracker_type=TrackerType.COMPETITOR,
        tracker_code=tracker.tracker_code,
    )
    return tracker


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


@router.delete("/{tracker_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor_tracker(
    workspace_id: str,
    tracker_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> None:
    await store.delete_competitor_tracker(workspace_id, tracker_code)
