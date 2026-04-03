from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_store
from app.models.api import DashboardOverview, Timeframe
from app.store import BaseStore

router = APIRouter(prefix="/workspaces/{workspace_id}/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    timeframe: Timeframe = Query(default=Timeframe.WEEKLY),
) -> DashboardOverview:
    return await store.get_dashboard_overview(workspace_id, timeframe)
