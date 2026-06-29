from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizer_requests.schemas import (
    OrganizerRequestCreate,
    OrganizerRequestReview,
    OrganizerRequestState,
)


ORGANIZER_REQUEST_SELECT = """
SELECT
  org.id::text AS id,
  org.user_id::text AS user_id,
  u.email AS user_email,
  u.display_name AS user_display_name,
  org.status,
  org.reason,
  org.admin_note,
  org.reviewed_by::text AS reviewed_by,
  org.reviewed_at,
  org.created_at,
  org.updated_at
FROM organizer_requests org
JOIN users u ON u.id = org.user_id
"""


async def get_user_organizer_request(
    session: AsyncSession,
    *,
    user_id: str,
) -> OrganizerRequestState | None:
    result = await session.execute(
        text(
            f"""
            {ORGANIZER_REQUEST_SELECT}
            WHERE org.user_id = CAST(:user_id AS uuid)
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    )
    row = result.first()
    return OrganizerRequestState.model_validate(row._mapping) if row else None


async def upsert_user_organizer_request(
    session: AsyncSession,
    *,
    user_id: str,
    payload: OrganizerRequestCreate,
) -> OrganizerRequestState:
    result = await session.execute(
        text(
            """
            INSERT INTO organizer_requests (user_id, status, reason, admin_note, reviewed_by, reviewed_at)
            VALUES (CAST(:user_id AS uuid), 'pending', :reason, NULL, NULL, NULL)
            ON CONFLICT (user_id)
            DO UPDATE SET
              status = CASE
                WHEN organizer_requests.status = 'approved' THEN organizer_requests.status
                ELSE 'pending'
              END,
              reason = EXCLUDED.reason,
              admin_note = CASE
                WHEN organizer_requests.status = 'approved' THEN organizer_requests.admin_note
                ELSE NULL
              END,
              reviewed_by = CASE
                WHEN organizer_requests.status = 'approved' THEN organizer_requests.reviewed_by
                ELSE NULL
              END,
              reviewed_at = CASE
                WHEN organizer_requests.status = 'approved' THEN organizer_requests.reviewed_at
                ELSE NULL
              END
            RETURNING id::text AS id
            """
        ),
        {"user_id": user_id, "reason": payload.reason},
    )
    request_id = str(result.one()._mapping["id"])
    request = await get_organizer_request_by_id(session, request_id=request_id)
    if request is None:
        raise RuntimeError("Organizer request was not returned after upsert.")
    return request


async def list_organizer_requests(
    session: AsyncSession,
    *,
    status_filter: str | None,
    limit: int,
    offset: int,
) -> list[OrganizerRequestState]:
    filters = []
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if status_filter:
        filters.append("org.status = :status_filter")
        params["status_filter"] = status_filter
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    result = await session.execute(
        text(
            f"""
            {ORGANIZER_REQUEST_SELECT}
            {where_clause}
            ORDER BY org.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return [OrganizerRequestState.model_validate(row._mapping) for row in result]


async def get_organizer_request_by_id(
    session: AsyncSession,
    *,
    request_id: str,
) -> OrganizerRequestState | None:
    result = await session.execute(
        text(
            f"""
            {ORGANIZER_REQUEST_SELECT}
            WHERE org.id = CAST(:request_id AS uuid)
            LIMIT 1
            """
        ),
        {"request_id": request_id},
    )
    row = result.first()
    return OrganizerRequestState.model_validate(row._mapping) if row else None


async def review_organizer_request(
    session: AsyncSession,
    *,
    request_id: str,
    reviewer_id: str,
    status: str,
    payload: OrganizerRequestReview,
) -> OrganizerRequestState | None:
    result = await session.execute(
        text(
            """
            UPDATE organizer_requests
            SET status = :status,
                admin_note = :admin_note,
                reviewed_by = CAST(:reviewer_id AS uuid),
                reviewed_at = now()
            WHERE id = CAST(:request_id AS uuid)
            RETURNING id::text AS id
            """
        ),
        {
            "request_id": request_id,
            "reviewer_id": reviewer_id,
            "status": status,
            "admin_note": payload.admin_note,
        },
    )
    row = result.first()
    if not row:
        return None
    return await get_organizer_request_by_id(
        session, request_id=str(row._mapping["id"])
    )


async def user_has_approved_organizer_request(
    session: AsyncSession, *, user_id: str
) -> bool:
    result = await session.execute(
        text(
            """
            SELECT 1
            FROM organizer_requests
            WHERE user_id = CAST(:user_id AS uuid)
              AND status = 'approved'
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    )
    return result.first() is not None
