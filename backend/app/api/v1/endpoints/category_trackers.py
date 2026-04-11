from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.v1.deps import get_store
from app.api.v1.endpoints._tracker_initial_jobs import (
    create_and_dispatch_initial_job,
)
from app.models.api import (
    CategorySnapshot,
    CategoryTracker,
    CategoryTrackerCreateRequest,
    CategoryTrackerListResponse,
    CategoryTrackerUpdateRequest,
    TrackerType,
)
from app.store import BaseStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/category-trackers", tags=["category-trackers"]
)


@router.get("", response_model=CategoryTrackerListResponse)
async def list_category_trackers(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> CategoryTrackerListResponse:
    return await store.list_category_trackers(workspace_id, page, page_size)


@router.post("", response_model=CategoryTracker, status_code=status.HTTP_201_CREATED)
async def create_category_tracker(
    workspace_id: str,
    payload: CategoryTrackerCreateRequest,
    background_tasks: BackgroundTasks,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CategoryTracker:
    tracker = await store.create_category_tracker(workspace_id, payload)
    background_tasks.add_task(
        create_and_dispatch_initial_job,
        store=store,
        workspace_id=workspace_id,
        tracker_type=TrackerType.CATEGORY,
        tracker_code=tracker.tracker_code,
    )
    return tracker


@router.get("/{tracker_code}", response_model=CategoryTracker)
async def get_category_tracker(
    workspace_id: str,
    tracker_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CategoryTracker:
    return await store.get_category_tracker(workspace_id, tracker_code)


@router.patch("/{tracker_code}", response_model=CategoryTracker)
async def update_category_tracker(
    workspace_id: str,
    tracker_code: str,
    payload: CategoryTrackerUpdateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CategoryTracker:
    return await store.update_category_tracker(workspace_id, tracker_code, payload)


@router.get("/{tracker_code}/snapshots/latest", response_model=CategorySnapshot)
async def get_latest_category_snapshot(
    workspace_id: str,
    tracker_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CategorySnapshot:
    return await store.get_latest_category_snapshot(workspace_id, tracker_code)
