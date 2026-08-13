from __future__ import annotations

# ruff: noqa: RUF001 -- localized copy intentionally contains non-ASCII glyphs.
import asyncio
import logging
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Literal, Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from talaqi.identity.outbox import RecoveryEmailIntent, RecoveryEmailLinkAdapter
from talaqi.identity.tokens import AuthTokenCodec

Locale = Literal["ar", "en", "fr", "tr"]
SUPPORTED_LOCALES: tuple[Locale, ...] = ("ar", "en", "fr", "tr")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


@dataclass(frozen=True, slots=True)
class EmailMessageRequest:
    recipient: str
    rendered: RenderedEmail
    idempotency_key: str


class EmailProvider(Protocol):
    async def send(self, message: EmailMessageRequest) -> str: ...


class ConsoleEmailProvider:
    def __init__(self) -> None:
        self.messages: list[EmailMessageRequest] = []
        self._provider_ids: dict[str, str] = {}

    async def send(self, message: EmailMessageRequest) -> str:
        existing = self._provider_ids.get(message.idempotency_key)
        if existing is not None:
            return existing
        self.messages.append(message)
        provider_id = f"console:{message.idempotency_key}"
        self._provider_ids[message.idempotency_key] = provider_id
        return provider_id


class ProviderApiTransport(Protocol):
    async def deliver(
        self,
        *,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str,
        idempotency_key: str,
    ) -> str: ...


class ProductionEmailProvider:
    """Production API adapter; transport must enforce the supplied idempotency key."""

    def __init__(self, transport: ProviderApiTransport) -> None:
        self._transport = transport

    async def send(self, message: EmailMessageRequest) -> str:
        provider_id = await self._transport.deliver(
            recipient=message.recipient,
            subject=message.rendered.subject,
            text_body=message.rendered.text,
            html_body=message.rendered.html,
            idempotency_key=message.idempotency_key,
        )
        if not provider_id.strip():
            raise RuntimeError("provider_message_id_missing")
        return provider_id


class SmtpEmailProvider:
    """TLS SMTP adapter for local/private relays; API providers are preferred in production."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._starttls = starttls

    async def send(self, message: EmailMessageRequest) -> str:
        value = EmailMessage()
        value["From"] = self._sender
        value["To"] = message.recipient
        value["Subject"] = message.rendered.subject
        value["X-Idempotency-Key"] = message.idempotency_key
        value["Message-ID"] = make_msgid(domain=self._sender.rsplit("@", 1)[-1])
        value.set_content(message.rendered.text)
        value.add_alternative(message.rendered.html, subtype="html")

        def deliver() -> None:
            with smtplib.SMTP(self._host, self._port, timeout=15) as client:
                if self._starttls:
                    client.starttls()
                if self._username is not None:
                    client.login(self._username, self._password or "")
                client.send_message(value)

        await asyncio.to_thread(deliver)
        return str(value["Message-ID"])


_COPY: dict[Locale, dict[str, tuple[str, str]]] = {
    "en": {
        "email_verification": (
            "Verify your Talaqi email",
            "Use the secure link to verify your email.",
        ),
        "password_reset": (
            "Reset your Talaqi password",
            "Use the secure link to reset your password.",
        ),
        "security": ("Talaqi security notice", "A security change was made to your account."),
        "membership": ("Talaqi community update", "Your club membership has an update."),
        "registration": ("Talaqi registration update", "Your event registration has an update."),
        "cash_expiry": ("Cash reservation expired", "Your cash reservation expired."),
        "promotion": ("You have a place", "You were promoted from the waitlist."),
        "cancellation": ("Cancellation update", "An event or registration was cancelled."),
        "event_change": ("Event details changed", "Review the latest event details."),
    },
    "fr": {
        "email_verification": (
            "Vérifiez votre e-mail Talaqi",
            "Utilisez le lien sécurisé pour vérifier votre e-mail.",
        ),
        "password_reset": (
            "Réinitialisez votre mot de passe Talaqi",
            "Utilisez le lien sécurisé pour réinitialiser votre mot de passe.",
        ),
        "security": (
            "Avis de sécurité Talaqi",
            "Une modification de sécurité a été effectuée sur votre compte.",
        ),
        "membership": (
            "Actualité de la communauté Talaqi",
            "Votre adhésion au club a été mise à jour.",
        ),
        "registration": (
            "Actualité de votre inscription",
            "Votre inscription à l’événement a été mise à jour.",
        ),
        "cash_expiry": ("Réservation en espèces expirée", "Votre réservation en espèces a expiré."),
        "promotion": ("Une place est disponible", "Vous avez quitté la liste d’attente."),
        "cancellation": ("Actualité d’annulation", "Un événement ou une inscription a été annulé."),
        "event_change": (
            "Détails de l’événement modifiés",
            "Consultez les derniers détails de l’événement.",
        ),
    },
    "tr": {
        "email_verification": (
            "Talaqi e-postanızı doğrulayın",
            "E-postanızı doğrulamak için güvenli bağlantıyı kullanın.",
        ),
        "password_reset": (
            "Talaqi parolanızı sıfırlayın",
            "Parolanızı sıfırlamak için güvenli bağlantıyı kullanın.",
        ),
        "security": ("Talaqi güvenlik bildirimi", "Hesabınızda bir güvenlik değişikliği yapıldı."),
        "membership": ("Talaqi topluluk güncellemesi", "Kulüp üyeliğiniz güncellendi."),
        "registration": ("Talaqi kayıt güncellemesi", "Etkinlik kaydınız güncellendi."),
        "cash_expiry": ("Nakit rezervasyonu sona erdi", "Nakit rezervasyonunuz sona erdi."),
        "promotion": ("Yeriniz hazır", "Bekleme listesinden yükseltildiniz."),
        "cancellation": ("İptal güncellemesi", "Bir etkinlik veya kayıt iptal edildi."),
        "event_change": (
            "Etkinlik ayrıntıları değişti",
            "Güncel etkinlik ayrıntılarını inceleyin.",
        ),
    },
    "ar": {
        "email_verification": (
            "تحقق من بريدك في تلاقي",
            "استخدم الرابط الآمن للتحقق من بريدك الإلكتروني.",
        ),
        "password_reset": (
            "أعد تعيين كلمة مرور تلاقي",
            "استخدم الرابط الآمن لإعادة تعيين كلمة المرور.",
        ),
        "security": ("تنبيه أمان من تلاقي", "تم إجراء تغيير أمني على حسابك."),
        "membership": ("تحديث مجتمع تلاقي", "طرأ تحديث على عضويتك في النادي."),
        "registration": ("تحديث تسجيل تلاقي", "طرأ تحديث على تسجيلك في الفعالية."),
        "cash_expiry": ("انتهت مهلة الحجز النقدي", "انتهت مهلة حجزك النقدي."),
        "promotion": ("أصبح لديك مقعد", "تمت ترقيتك من قائمة الانتظار."),
        "cancellation": ("تحديث إلغاء", "تم إلغاء فعالية أو تسجيل."),
        "event_change": ("تغيرت تفاصيل الفعالية", "راجع أحدث تفاصيل الفعالية."),
    },
}


def render_email(template: str, locale: str, *, action_url: str | None = None) -> RenderedEmail:
    selected: Locale = locale if locale in SUPPORTED_LOCALES else "en"  # type: ignore[assignment]
    subject, body = _COPY[selected][template]
    direction = "rtl" if selected == "ar" else "ltr"
    link_text = f"\n{action_url}" if action_url else ""
    link_html = f'<p><a href="{action_url}">{action_url}</a></p>' if action_url else ""
    return RenderedEmail(
        subject=subject,
        text=f"{body}{link_text}\n\nTalaqi",
        html=(
            f'<div lang="{selected}" dir="{direction}"><p>{body}</p>{link_html}<p>Talaqi</p></div>'
        ),
    )


@dataclass(frozen=True, slots=True)
class PendingEmail:
    delivery_id: UUID
    notification_id: UUID
    recipient_user_id: UUID
    recipient: str
    locale: str
    event_type: str
    parameters: dict[str, object]
    action_path: str | None
    auth_token_id: UUID | None
    attempt_count: int


class EmailDeliveryWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        provider: EmailProvider,
        *,
        session_secret: str,
        web_public_url: str,
        daily_recipient_quota: int = 20,
        max_attempts: int = 5,
        processing_lease: timedelta = timedelta(minutes=5),
    ) -> None:
        self._factory = session_factory
        self._provider = provider
        self._links = RecoveryEmailLinkAdapter(AuthTokenCodec(session_secret), web_public_url)
        self._web_base = web_public_url.rstrip("/")
        self._quota = daily_recipient_quota
        self._max_attempts = max_attempts
        self._processing_lease = processing_lease

    async def run_once(self, *, now: datetime | None = None, limit: int = 100) -> int:
        current = (now or datetime.now(UTC)).astimezone(UTC)
        async with self._factory() as session, session.begin():
            items = await self._claim(session, now=current, limit=limit)
        delivered = 0
        for item in items:
            try:
                if not _is_security_event(item.event_type) and not await self._reserve_quota(
                    item, now=current
                ):
                    await self._defer_quota(item, now=current)
                    continue
                action_url = self._action_url(item)
                rendered = render_email(
                    template_for(item.event_type, item.parameters),
                    item.locale,
                    action_url=action_url,
                )
                provider_id = await self._provider.send(
                    EmailMessageRequest(
                        recipient=item.recipient,
                        rendered=rendered,
                        idempotency_key=f"notification-email:{item.delivery_id}",
                    )
                )
                async with self._factory() as session, session.begin():
                    changed = await session.scalar(
                        text(
                            """
                            UPDATE talaqi.notification_deliveries
                            SET status = 'delivered', provider_message_id = :provider_id,
                                delivered_at = :now, processing_started_at = NULL,
                                last_error_code = NULL
                            WHERE id = :id AND channel = 'email' AND status = 'processing'
                              AND attempt_count = :attempt_count
                            RETURNING id
                            """
                        ),
                        {
                            "id": item.delivery_id,
                            "attempt_count": item.attempt_count,
                            "provider_id": provider_id[:500],
                            "now": current,
                        },
                    )
                delivered += int(changed is not None)
            except Exception as error:
                LOGGER.error(
                    "email delivery failed",
                    extra={
                        "delivery_id": str(item.delivery_id),
                        "event_type": item.event_type,
                        "error_code": type(error).__name__.lower(),
                    },
                )
                permanent = _is_permanent(error)
                await self._fail(
                    item,
                    type(error).__name__.lower(),
                    now=current,
                    permanent=permanent or item.attempt_count >= self._max_attempts,
                )
        return delivered

    async def _claim(
        self, session: AsyncSession, *, now: datetime, limit: int
    ) -> tuple[PendingEmail, ...]:
        claimed = (
            (
                await session.execute(
                    text(
                        """
                        WITH candidates AS (
                            SELECT delivery.id
                            FROM talaqi.notification_deliveries AS delivery
                            WHERE delivery.channel = 'email'
                              AND (
                                (delivery.status IN ('pending', 'retryable_failed')
                                 AND (delivery.next_attempt_at IS NULL
                                      OR delivery.next_attempt_at <= :now))
                                OR (delivery.status = 'processing'
                                    AND delivery.processing_started_at <= :lease_expired_at)
                              )
                            ORDER BY delivery.created_at, delivery.id
                            FOR UPDATE SKIP LOCKED
                            LIMIT :limit
                        )
                        UPDATE talaqi.notification_deliveries AS delivery
                        SET status = 'processing',
                            attempt_count = delivery.attempt_count + 1,
                            processing_started_at = :now, next_attempt_at = NULL
                        FROM candidates
                        WHERE delivery.id = candidates.id
                        RETURNING delivery.id, delivery.attempt_count
                        """
                    ),
                    {
                        "now": now,
                        "lease_expired_at": now - self._processing_lease,
                        "limit": limit,
                    },
                )
            )
            .tuples()
            .all()
        )
        items: list[PendingEmail] = []
        for delivery_id, attempt_count in claimed:
            row = (
                (
                    await session.execute(
                        text(
                            """
                            SELECT delivery.id, delivery.notification_id,
                                   notification.recipient_user_id, user_account.email,
                                   COALESCE(intent.locale_hint, profile.locale, 'en') AS locale,
                                   notification.type_key, notification.parameters,
                                   notification.action_path, intent.auth_token_id,
                                   CAST(:attempt_count AS integer) AS attempt_count
                            FROM talaqi.notification_deliveries AS delivery
                            JOIN talaqi.notifications AS notification
                              ON notification.id = delivery.notification_id
                            JOIN talaqi.users AS user_account
                              ON user_account.id = notification.recipient_user_id
                            LEFT JOIN talaqi.profiles AS profile
                              ON profile.user_id = user_account.id
                            JOIN talaqi.email_delivery_intents AS intent
                              ON intent.delivery_id = delivery.id
                            WHERE delivery.id = :delivery_id
                            """
                        ),
                        {
                            "delivery_id": delivery_id,
                            "attempt_count": attempt_count,
                        },
                    )
                )
                .mappings()
                .one()
            )
            items.append(
                PendingEmail(
                    delivery_id=cast(UUID, row["id"]),
                    notification_id=cast(UUID, row["notification_id"]),
                    recipient_user_id=cast(UUID, row["recipient_user_id"]),
                    recipient=cast(str, row["email"]),
                    locale=cast(str, row["locale"]),
                    event_type=cast(str, row["type_key"]),
                    parameters=cast(dict[str, object], row["parameters"]),
                    action_path=cast(str | None, row["action_path"]),
                    auth_token_id=cast(UUID | None, row["auth_token_id"]),
                    attempt_count=cast(int, row["attempt_count"]),
                )
            )
        return tuple(items)

    async def _reserve_quota(self, item: PendingEmail, *, now: datetime) -> bool:
        async with self._factory() as session, session.begin():
            existing = await session.scalar(
                text(
                    "SELECT slot FROM talaqi.email_quota_reservations "
                    "WHERE delivery_id = :delivery_id"
                ),
                {"delivery_id": item.delivery_id},
            )
            if existing is not None:
                return True
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:user_id AS text), 0))"),
                {"user_id": str(item.recipient_user_id)},
            )
            count = await session.scalar(
                text(
                    """
                    SELECT count(*) FROM talaqi.email_quota_reservations
                    WHERE recipient_user_id = :user_id
                      AND quota_date = CAST(
                          CAST(:now AS timestamptz) AT TIME ZONE 'UTC' AS date
                      )
                    """
                ),
                {"user_id": item.recipient_user_id, "now": now},
            )
            slot = int(count or 0) + 1
            if slot > self._quota:
                return False
            await session.execute(
                text(
                    """
                    INSERT INTO talaqi.email_quota_reservations (
                        delivery_id, recipient_user_id, quota_date, slot
                    ) VALUES (
                        :delivery_id, :user_id,
                        CAST(CAST(:now AS timestamptz) AT TIME ZONE 'UTC' AS date), :slot
                    )
                    """
                ),
                {
                    "delivery_id": item.delivery_id,
                    "user_id": item.recipient_user_id,
                    "now": now,
                    "slot": slot,
                },
            )
            return True

    async def _defer_quota(self, item: PendingEmail, *, now: datetime) -> None:
        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        async with self._factory() as session, session.begin():
            await session.execute(
                text(
                    """
                    UPDATE talaqi.notification_deliveries
                    SET status = 'retryable_failed', next_attempt_at = :retry_at,
                        last_error_code = 'daily_recipient_quota',
                        processing_started_at = NULL
                    WHERE id = :id AND status = 'processing'
                      AND attempt_count = :attempt_count
                    """
                ),
                {
                    "id": item.delivery_id,
                    "attempt_count": item.attempt_count,
                    "retry_at": next_day,
                },
            )

    def _action_url(self, item: PendingEmail) -> str | None:
        if item.event_type in {
            "identity.email_verification_requested",
            "identity.password_reset_requested",
        }:
            if item.auth_token_id is None:
                raise ValueError("recovery_token_missing")
            kind = (
                "email_verification"
                if item.event_type == "identity.email_verification_requested"
                else "password_reset"
            )
            return self._links.link(
                RecoveryEmailIntent(
                    user_id=item.recipient_user_id,
                    auth_token_id=item.auth_token_id,
                    locale_hint=item.locale,
                    template=kind,
                )
            )
        return f"{self._web_base}{item.action_path}" if item.action_path else None

    async def _fail(
        self,
        item: PendingEmail,
        code: str,
        *,
        now: datetime,
        permanent: bool,
    ) -> None:
        status = "permanent_failed" if permanent else "retryable_failed"
        retry_at = None if permanent else now + timedelta(minutes=2 ** min(item.attempt_count, 8))
        async with self._factory() as session, session.begin():
            await session.execute(
                text(
                    """
                    UPDATE talaqi.notification_deliveries
                    SET status = CAST(:status AS talaqi.delivery_status),
                        next_attempt_at = :retry_at, last_error_code = :code,
                        processing_started_at = NULL
                    WHERE id = :id AND status = 'processing'
                      AND attempt_count = :attempt_count
                    """
                ),
                {
                    "id": item.delivery_id,
                    "attempt_count": item.attempt_count,
                    "status": status,
                    "retry_at": retry_at,
                    "code": code[:120],
                },
            )


def template_for(event_type: str, parameters: dict[str, object]) -> str:
    if event_type == "identity.email_verification_requested":
        return "email_verification"
    if event_type == "identity.password_reset_requested":
        return "password_reset"
    if event_type.startswith(("identity.", "moderation.")):
        return "security"
    if event_type.startswith(("membership.", "club.")):
        return "membership"
    if event_type == "registration.expired":
        return "cash_expiry"
    if event_type in {"registration.confirmed", "registration.cash_pending"} and (
        parameters.get("previous_state") == "waitlisted"
    ):
        return "promotion"
    if event_type.endswith("cancelled"):
        return "cancellation"
    if event_type.startswith("event."):
        return "event_change"
    if event_type.startswith("registration."):
        return "registration"
    raise ValueError("unsupported_email_template")


def _is_permanent(error: Exception) -> bool:
    if isinstance(error, (KeyError, ValueError, smtplib.SMTPRecipientsRefused)):
        return True
    return isinstance(error, smtplib.SMTPResponseException) and error.smtp_code >= 500


def _is_security_event(event_type: str) -> bool:
    return event_type.startswith(("identity.", "moderation."))


__all__ = [
    "SUPPORTED_LOCALES",
    "ConsoleEmailProvider",
    "EmailDeliveryWorker",
    "EmailMessageRequest",
    "EmailProvider",
    "ProductionEmailProvider",
    "ProviderApiTransport",
    "RenderedEmail",
    "SmtpEmailProvider",
    "render_email",
    "template_for",
]
