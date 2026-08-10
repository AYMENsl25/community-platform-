import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isSafePublicGet(method: string, path: string[]): boolean {
  if (method !== "GET" || path[0] !== "api" || path[1] !== "v1") return false;
  if (path.length === 3)
    return ["clubs", "search", "metadata"].includes(path[2] ?? "");
  return path.length === 5 && path[2] === "regions" && path[4] === "policy";
}

function allowed(method: string, path: string[]): boolean {
  if (isSafePublicGet(method, path)) return true;
  if (
    method === "POST" &&
    path.length === 4 &&
    path[0] === "api" &&
    path[1] === "v1" &&
    path[2] === "auth" &&
    path[3] === "logout"
  )
    return true;
  if (
    path[0] !== "api" ||
    path[1] !== "v1" ||
    path[2] !== "events" ||
    !UUID.test(path[3] ?? "")
  )
    return false;
  if (method === "GET") return path.length === 4;
  if (method === "POST")
    return path.length === 5 && path[4] === "registrations";
  if (method === "PUT") return path.length === 5 && path[4] === "saved";
  if (method === "DELETE")
    return (
      (path.length === 5 && path[4] === "saved") ||
      (path.length === 6 && path[4] === "registrations" && path[5] === "me")
    );
  return false;
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
  const access = request.cookies.get("talaqi_access")?.value;
  const csrfCookie = request.cookies.get("talaqi_csrf")?.value;
  const csrf = request.headers.get("x-csrf-token");
  const idempotencyKey = request.headers.get("idempotency-key");
  const safePublicGet = isSafePublicGet(request.method, path);
  const cookie = safePublicGet ? "" : [
    access ? `talaqi_access=${access}` : undefined,
    csrfCookie ? `talaqi_csrf=${csrfCookie}` : undefined,
  ]
    .filter(Boolean)
    .join("; ");
  const headers: Record<string, string> = {};
  if (cookie) headers.Cookie = cookie;
  if (csrf) headers["X-CSRF-Token"] = csrf;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  try {
    const response = await fetch(`${baseUrl}/${path.join("/")}`, {
      method: request.method,
      headers,
      cache: "no-store",
    });
    const outgoingHeaders = new Headers({
      "Content-Type": response.headers.get("content-type") ?? "application/json",
      "Cache-Control": safePublicGet ? "public, max-age=60" : "private, no-store",
    });
    if (path[2] === "auth" && path[3] === "logout") {
      for (const cookie of response.headers.getSetCookie())
        outgoingHeaders.append("Set-Cookie", cookie);
    }
    return new Response(response.body, {
      status: response.status,
      headers: outgoingHeaders,
    });
  } catch {
    return Response.json(
      { error: { code: "upstream_unavailable" } },
      { status: 502, headers: { "Cache-Control": "private, no-store" } },
    );
  }
}

export const PUT = forward;
export const DELETE = forward;
export const GET = forward;
export const POST = forward;
