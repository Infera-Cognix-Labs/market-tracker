from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    category_trackers,
    competitor_trackers,
    dashboard,
    events,
    jobs,
    products,
    reports,
)

api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(category_trackers.router)
api_router.include_router(competitor_trackers.router)
api_router.include_router(products.router)
api_router.include_router(events.router)
api_router.include_router(jobs.router)
api_router.include_router(reports.router)
