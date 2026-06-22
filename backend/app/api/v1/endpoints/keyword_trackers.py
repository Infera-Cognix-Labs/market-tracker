from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.v1.deps import get_store
from app.api.v1.endpoints._tracker_initial_jobs import (
    create_and_dispatch_initial_job,
)
from app.models.api import (
    KeywordSnapshot,
    KeywordTracker,
    KeywordTrackerCreateRequest,
    KeywordTrackerListResponse,
    KeywordTrackerUpdateRequest,
    Timeframe,
    TrackerType,
)
from app.store import BaseStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/keyword-trackers", tags=["keyword-trackers"]
)


@router.get("", response_model=KeywordTrackerListResponse)
async def list_keyword_trackers(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> KeywordTrackerListResponse:
    return await store.list_keyword_trackers(workspace_id, page, page_size)


@router.post("", response_model=KeywordTracker, status_code=status.HTTP_201_CREATED)
async def create_keyword_tracker(
    workspace_id: str,
    payload: KeywordTrackerCreateRequest,
    background_tasks: BackgroundTasks,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordTracker:
    tracker = await store.create_keyword_tracker(workspace_id, payload)
    background_tasks.add_task(
        create_and_dispatch_initial_job,
        store=store,
        workspace_id=workspace_id,
        tracker_type=TrackerType.KEYWORD,
        tracker_code=tracker.tracker_code,
    )
    return tracker


@router.get("/{tracker_code}", response_model=KeywordTracker)
async def get_keyword_tracker(
    workspace_id: str,
    tracker_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordTracker:
    return await store.get_keyword_tracker(workspace_id, tracker_code)


@router.patch("/{tracker_code}", response_model=KeywordTracker)
async def update_keyword_tracker(
    workspace_id: str,
    tracker_code: str,
    payload: KeywordTrackerUpdateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordTracker:
    return await store.update_keyword_tracker(workspace_id, tracker_code, payload)


@router.get("/{tracker_code}/snapshots/latest", response_model=KeywordSnapshot)
async def get_latest_keyword_snapshot(
    workspace_id: str,
    tracker_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
    timeframe: Timeframe = Query(default=Timeframe.WEEKLY),
) -> KeywordSnapshot:
    return await store.get_latest_keyword_snapshot(
        workspace_id, tracker_code, timeframe
    )


@router.delete("/{tracker_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword_tracker(
    workspace_id: str,
    tracker_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> None:
    await store.delete_keyword_tracker(workspace_id, tracker_code)
