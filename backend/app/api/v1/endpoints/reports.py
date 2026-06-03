from __future__ import annotations

import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_store
from app.models.api import WeeklyDigest, WeeklyDigestListResponse
from app.services.report_generator import ReportPDFGenerator, ReportExcelGenerator
from app.store import BaseStore

router = APIRouter(prefix="/workspaces/{workspace_id}/reports", tags=["reports"])


@router.get("/weekly-digests", response_model=WeeklyDigestListResponse)
async def list_weekly_digests(
    workspace_id: str,
    store: Annotated[BaseStore, Depends(get_store)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    week_start: date | None = Query(default=None),
) -> WeeklyDigestListResponse:
    return await store.list_weekly_digests(workspace_id, page, page_size, week_start)


@router.get("/weekly-digests/{digest_code}", response_model=WeeklyDigest)
async def get_weekly_digest(
    workspace_id: str,
    digest_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
) -> WeeklyDigest:
    return await store.get_weekly_digest(workspace_id, digest_code)


@router.get("/weekly-digests/{digest_code}/download")
async def download_weekly_digest(
    workspace_id: str,
    digest_code: str,
    store: Annotated[BaseStore, Depends(get_store)],
    format: str = Query(default="pdf", pattern="^(pdf|excel)$"),
):
    digest = await store.get_weekly_digest(workspace_id, digest_code)

    if format == "pdf":
        content = await asyncio.to_thread(ReportPDFGenerator(digest).generate)
        media_type = "application/pdf"
        filename = f"weekly_digest_{digest_code}.pdf"
    else:
        content = await asyncio.to_thread(ReportExcelGenerator(digest).generate)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"weekly_digest_{digest_code}.xlsx"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
