from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.api.v1.router import api_router
from app.config.config import Config, get_settings
from app.core.errors import AppError, app_error_handler, validation_error_handler
from app.core.logging import configure_logging
from app.seed import load_demo_seed
from app.store import build_store


def create_app(settings: Config | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = await build_store(app_settings)
        if app_settings.seed_demo_data:
            await store.seed_demo_data(load_demo_seed())
        app.state.settings = app_settings
        app.state.store = store
        try:
            yield
        finally:
            await store.close()

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request.state.request_id = f"req_{uuid4().hex[:10]}"
        return await call_next(request)

    @app.get("/health")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(api_router, prefix=app_settings.api_prefix)
    return app


app = create_app()
