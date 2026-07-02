from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.events.service import get_event_detail
from app.modules.payments.schemas import (
    EventCheckoutRequest,
    EventCheckoutSession,
    MoyasarWebhookPayload,
    MoyasarWebhookResult,
    PaymentAdminActionResult,
    PaymentAdminRecord,
    PaymentDisputeRequest,
    PaymentRefundRequest,
)
from app.modules.payments.service import (
    AdminRequiredError,
    CheckoutNotRequiredError,
    CheckoutProviderError,
    InvalidWebhookSecretError,
    PaymentAdminActionError,
    PaymentNotFoundError,
    WebhookProcessingError,
    create_event_checkout,
    list_admin_payment_records,
    process_moyasar_webhook,
    record_admin_payment_dispute,
    refund_admin_payment,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/events/{event_id}/checkout", response_model=EventCheckoutSession)
async def create_event_payment_checkout(
    event_id: str,
    payload: EventCheckoutRequest,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> EventCheckoutSession:
    event = await get_event_detail(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    try:
        return await create_event_checkout(
            session,
            event,
            user_id=current_user.id,
            return_path=payload.return_path,
            idempotency_key=payload.idempotency_key or idempotency_key,
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


@router.get("/admin/payments", response_model=list[PaymentAdminRecord])
async def list_payment_admin_records(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> list[PaymentAdminRecord]:
    try:
        return await list_admin_payment_records(
            session,
            current_user=current_user,
            status_filter=status_filter,
            limit=min(max(limit, 1), 100),
            offset=max(offset, 0),
        )
    except AdminRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        ) from exc


@router.post(
    "/admin/payments/{payment_id}/refund",
    response_model=PaymentAdminActionResult,
)
async def refund_payment_admin_record(
    payment_id: str,
    payload: PaymentRefundRequest,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> PaymentAdminActionResult:
    try:
        return await refund_admin_payment(
            session,
            current_user=current_user,
            payment_id=payment_id,
            payload=payload,
        )
    except AdminRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        ) from exc
    except PaymentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        ) from exc
    except PaymentAdminActionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc) or "Payment refund could not be recorded.",
        ) from exc


@router.post(
    "/admin/payments/{payment_id}/disputes",
    response_model=PaymentAdminActionResult,
)
async def record_payment_dispute_admin_record(
    payment_id: str,
    payload: PaymentDisputeRequest,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> PaymentAdminActionResult:
    try:
        return await record_admin_payment_dispute(
            session,
            current_user=current_user,
            payment_id=payment_id,
            payload=payload,
        )
    except AdminRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        ) from exc
    except PaymentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        ) from exc
    except PaymentAdminActionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc) or "Payment dispute could not be recorded.",
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
