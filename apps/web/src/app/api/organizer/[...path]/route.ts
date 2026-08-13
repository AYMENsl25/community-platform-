import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function allowed(method: string, path: string[]): boolean {
  if (path[0] !== "api" || path[1] !== "v1") return false;
  const resource = path[2];
  if (
    method === "GET" &&
    path.length === 4 &&
    ((resource === "me" && path[3] === "dashboard") ||
      (resource === "organizer" && path[3] === "dashboard"))
  )
    return true;
  if (
    resource === "profiles" &&
    method === "GET" &&
    path.length === 4 &&
    path[3] === "capabilities"
  )
    return true;
  if (
    resource === "regions" &&
    method === "GET" &&
    path.length === 5 &&
    /^[a-z]{2}$/i.test(path[3] ?? "") &&
    path[4] === "policy"
  )
    return true;
  if (resource === "media") {
    if (method === "POST" && path.length === 4 && path[3] === "uploads")
      return true;
    return Boolean(
      method === "POST" &&
      path.length === 6 &&
      path[3] === "uploads" &&
      UUID.test(path[4] ?? "") &&
      path[5] === "complete",
    );
  }
  if (resource === "events") {
    if (method === "GET" && path.length === 4 && path[3] === "managed")
      return true;
    if (method === "POST" && path.length === 3) return true;
    const eventId = path[3];
    if (!eventId || !UUID.test(eventId)) return false;
    if (path.length === 4 && (method === "PATCH" || method === "DELETE"))
      return true;
    if (method === "GET" && path.length === 5 && path[4] === "managed")
      return true;
    if (
      (method === "GET" || method === "POST") &&
      path.length === 5 &&
      path[4] === "updates"
    )
      return true;
    if (
      method === "GET" &&
      ((path.length === 5 && path[4] === "attendees") ||
        (path.length === 6 && path[4] === "attendees" && path[5] === "summary"))
    )
      return true;
    if (
      method === "POST" &&
      ((path.length === 6 && path[4] === "attendees" && path[5] === "export") ||
        (path.length === 7 &&
          path[4] === "registrations" &&
          UUID.test(path[5] ?? "") &&
          path[6] === "confirm-cash"))
    )
      return true;
    return Boolean(
      method === "POST" &&
      path.length === 5 &&
      (path[4] === "duplicate" ||
        path[4] === "cancel" ||
        path[4] === "complete"),
    );
  }
  if (resource !== "clubs") return false;
  if (method === "GET" && path.length === 4 && path[3] === "managed")
    return true;
  const clubId = path[3];
  if (!clubId || !UUID.test(clubId)) return false;
  if (method === "PATCH" && path.length === 4) return true;
  if (
    (method === "GET" || method === "POST") &&
    path.length === 5 &&
    path[4] === "announcements"
  )
    return true;
  if (
    method === "GET" &&
    path.length === 5 &&
    (path[4] === "members" || path[4] === "join-requests")
  )
    return true;
  if (
    method === "POST" &&
    path.length === 5 &&
    (path[4] === "ownership-transfer" || path[4] === "close")
  )
    return true;
  if (
    method === "PATCH" &&
    path.length === 7 &&
    path[4] === "members" &&
    UUID.test(path[5] ?? "") &&
    path[6] === "role"
  )
    return true;
  return Boolean(
    method === "POST" &&
    path.length === 7 &&
    path[4] === "join-requests" &&
    UUID.test(path[5] ?? "") &&
    (path[6] === "approve" || path[6] === "reject"),
  );
}

async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  if (!allowed(request.method, path))
    return Response.json({ error: { code: "not_found" } }, { status: 404 });
  const baseUrl = (
    process.env.API_PUBLIC_URL ?? "http://localhost:8000"
  ).replace(/\/$/, "");
  const headers: Record<string, string> = {};
  const access = request.cookies.get("talaqi_access")?.value;
  const csrfCookie = request.cookies.get("talaqi_csrf")?.value;
  const cookie = [
    access ? `talaqi_access=${access}` : undefined,
    csrfCookie ? `talaqi_csrf=${csrfCookie}` : undefined,
  ]
    .filter(Boolean)
    .join("; ");
  const csrf = request.headers.get("x-csrf-token");
  const contentType = request.headers.get("content-type");
  if (cookie) headers.Cookie = cookie;
  if (csrf) headers["X-CSRF-Token"] = csrf;
  if (contentType) headers["Content-Type"] = contentType;
  const idempotencyKey = request.headers.get("idempotency-key");
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  try {
    const response = await fetch(
      `${baseUrl}/${path.join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        cache: "no-store",
        ...(request.method === "GET" ? {} : { body: await request.text() }),
      },
    );
    const responseRequestId = response.headers.get("x-request-id");
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "private, no-store",
        ...(responseRequestId ? { "X-Request-ID": responseRequestId } : {}),
      },
    });
  } catch {
    return Response.json(
      { error: { code: "upstream_unavailable" } },
      {
        status: 502,
        headers: { "Cache-Control": "private, no-store" },
      },
    );
  }
}

export const GET = forward;
export const PATCH = forward;
export const POST = forward;
export const DELETE = forward;
