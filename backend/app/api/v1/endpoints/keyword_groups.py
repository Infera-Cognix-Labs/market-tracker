from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_store
from app.models.api import (
    KeywordGroup,
    KeywordGroupCreateRequest,
    KeywordGroupListResponse,
    KeywordGroupSnapshot,
    KeywordGroupUpdateRequest,
    TrackedKeywordReplacementRequest,
)
from app.store import BaseStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/keyword-groups",
    tags=["keyword-groups"],
)


@router.get("", response_model=KeywordGroupListResponse)
async def list_keyword_groups(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> KeywordGroupListResponse:
    return await store.list_keyword_groups(workspace_id, page, page_size)


@router.post("", response_model=KeywordGroup, status_code=status.HTTP_201_CREATED)
async def create_keyword_group(
    workspace_id: str,
    payload: KeywordGroupCreateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordGroup:
    return await store.create_keyword_group(workspace_id, payload)


@router.get("/{group_code}", response_model=KeywordGroup)
async def get_keyword_group(
    workspace_id: str,
    group_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordGroup:
    return await store.get_keyword_group(workspace_id, group_code)


@router.patch("/{group_code}", response_model=KeywordGroup)
async def update_keyword_group(
    workspace_id: str,
    group_code: str,
    payload: KeywordGroupUpdateRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordGroup:
    return await store.update_keyword_group(workspace_id, group_code, payload)


@router.put(
    "/{group_code}/tracked-keywords", response_model=KeywordGroup
)
async def replace_tracked_keywords(
    workspace_id: str,
    group_code: str,
    payload: TrackedKeywordReplacementRequest,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordGroup:
    return await store.replace_tracked_keywords(workspace_id, group_code, payload)


@router.get(
    "/{group_code}/snapshots/latest", response_model=KeywordGroupSnapshot
)
async def get_latest_keyword_group_snapshot(
    workspace_id: str,
    group_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> KeywordGroupSnapshot:
    return await store.get_latest_keyword_group_snapshot(workspace_id, group_code)


@router.delete("/{group_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword_group(
    workspace_id: str,
    group_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> None:
    await store.delete_keyword_group(workspace_id, group_code)
