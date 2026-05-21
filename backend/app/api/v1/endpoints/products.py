from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_store
from app.models.api import ProductDetail, ProductTimelineResponse, Timeframe
from app.store import BaseStore

router = APIRouter(prefix="/workspaces/{workspace_id}/products", tags=["products"])


@router.get("/{marketplace}/{asin}", response_model=ProductDetail)
async def get_product_detail(
    workspace_id: str,
    marketplace: str,
    asin: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> ProductDetail:
    return await store.get_product_detail(workspace_id, marketplace, asin)


@router.get("/{marketplace}/{asin}/timeline", response_model=ProductTimelineResponse)
async def get_product_timeline(
    workspace_id: str,
    marketplace: str,
    asin: str,
    store: Annotated[BaseStore, Depends(get_store)],
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    granularity: Timeframe = Query(default=Timeframe.DAILY),
    tracker_code: str | None = Query(default=None),
) -> ProductTimelineResponse:
    return await store.get_product_timeline(
        workspace_id=workspace_id,
        marketplace=marketplace,
        asin=asin,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        tracker_code=tracker_code,
    )
