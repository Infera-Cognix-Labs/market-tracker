from __future__ import annotations

from fastapi import Request

from app.store import BaseStore


def get_store(request: Request) -> BaseStore:
    return request.app.state.store
