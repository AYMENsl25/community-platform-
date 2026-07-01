from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.events.service import get_event_detail
from app.modules.payments.schemas import EventCheckoutRequest, EventCheckoutSession
from app.modules.payments.schemas import MoyasarWebhookPayload, MoyasarWebhookResult
from app.modules.payments.service import (
    CheckoutNotRequiredError,
    CheckoutProviderError,
    InvalidWebhookSecretError,
    WebhookProcessingError,
    create_event_checkout,
    process_moyasar_webhook,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/events/{event_id}/checkout", response_model=EventCheckoutSession)
async def create_event_payment_checkout(
    event_id: str,
    payload: EventCheckoutRequest,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> EventCheckoutSession:
    event = await get_event_detail(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    try:
        return await create_event_checkout(
            event,
            user_id=current_user.id,
            return_path=payload.return_path,
        )
    except CheckoutNotRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout is only required for paid events.",
        ) from exc
    except CheckoutProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment checkout provider failed.",
        ) from exc


@router.post("/moyasar/webhook", response_model=MoyasarWebhookResult)
async def handle_moyasar_webhook(
    payload: MoyasarWebhookPayload,
    session: AsyncSession = Depends(get_db_session),
) -> MoyasarWebhookResult:
    try:
        return await process_moyasar_webhook(session, payload)
    except InvalidWebhookSecretError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Moyasar webhook secret.",
        ) from exc
    except WebhookProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Moyasar webhook could not be processed.",
        ) from exc
