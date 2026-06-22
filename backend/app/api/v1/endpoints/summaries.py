from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_store
from app.models.api import (
    CategoryInsights,
    CompetitorAlertCounts,
    CompetitorInsights,
    KeywordInsights,
    Timeframe,
)
from app.store import BaseStore

router = APIRouter(prefix="/workspaces/{workspace_id}/summaries", tags=["summaries"])


@router.get("/category-insights", response_model=CategoryInsights)
async def get_category_insights(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    timeframe: Timeframe = Query(default=Timeframe.WEEKLY),
) -> CategoryInsights:
    return await store.get_category_insights(workspace_id, timeframe)


@router.get("/competitor-insights", response_model=CompetitorInsights)
async def get_competitor_insights(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    timeframe: Timeframe = Query(default=Timeframe.WEEKLY),
) -> CompetitorInsights:
    return await store.get_competitor_insights(workspace_id, timeframe)


@router.get("/competitor-alerts", response_model=CompetitorAlertCounts)
async def get_competitor_alerts(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> CompetitorAlertCounts:
    return await store.get_competitor_alerts(workspace_id)


@router.get("/keyword-insights", response_model=KeywordInsights)
async def get_keyword_insights(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    timeframe: Timeframe = Query(default=Timeframe.WEEKLY),
) -> KeywordInsights:
    return await store.get_keyword_insights(workspace_id, timeframe)
