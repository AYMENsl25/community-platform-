import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function allowed(method: string, path: string[]): boolean {
  if (path[0] !== "api" || path[1] !== "v1" || path[2] !== "clubs")
    return false;
  if (method === "GET" && path.length === 4 && path[3] === "managed")
    return true;
  const clubId = path[3];
  if (!clubId || !UUID.test(clubId)) return false;
  if (method === "PATCH" && path.length === 4) return true;
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
  try {
    const response = await fetch(`${baseUrl}/${path.join("/")}`, {
      method: request.method,
      headers,
      cache: "no-store",
      ...(request.method === "GET" ? {} : { body: await request.text() }),
    });
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
