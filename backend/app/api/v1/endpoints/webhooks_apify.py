from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.api.v1.deps import get_store
from app.models.api import ApifyWebhookAck, ApifyWebhookEnvelope
from app.store import BaseStore

router = APIRouter(prefix="/webhooks/apify", tags=["webhooks"])


@router.post("/runs", response_model=ApifyWebhookAck, status_code=status.HTTP_202_ACCEPTED)
async def receive_apify_run_webhook(
    payload: ApifyWebhookEnvelope,
    store: Annotated[BaseStore, Depends(get_store)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> ApifyWebhookAck:
    return await store.handle_apify_webhook(payload, authorization)
