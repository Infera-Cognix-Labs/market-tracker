from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.v1.deps import get_store
from app.models.api import (
    Job,
    JobCreateRequest,
    JobListResponse,
    JobStatus,
    TrackerType,
)
from app.store import BaseStore

router = APIRouter(prefix="/workspaces/{workspace_id}/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    tracker_type: TrackerType | None = Query(default=None),
    tracker_code: str | None = Query(default=None),
    status_value: JobStatus | None = Query(default=None, alias="status"),
) -> JobListResponse:
    return await store.list_jobs(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
        tracker_type=tracker_type,
        tracker_code=tracker_code,
        status=status_value,
    )


@router.post("", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    workspace_id: str,
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    store: Annotated[BaseStore, Depends(get_store)],
) -> Job:
    job = await store.create_job(workspace_id, payload)
    background_tasks.add_task(store.dispatch_job, workspace_id, job.job_code)
    return job


@router.get("/{job_code}", response_model=Job)
async def get_job(
    workspace_id: str,
    job_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> Job:
    return await store.get_job(workspace_id, job_code)
