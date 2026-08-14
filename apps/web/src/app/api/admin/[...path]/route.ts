import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function allowed(method: string, path: string[]): boolean {
  if (path[0] !== "api" || path[1] !== "v1" || path[2] !== "admin")
    return false;
  if (method === "GET" && path.length === 4 && path[3] === "audit-events")
    return true;
  if (path[3] !== "moderation") return false;
  if (
    method === "GET" &&
    path.length === 5 &&
    (path[4] === "cases" || path[4] === "targets")
  )
    return true;
  if (
    method === "GET" &&
    path.length === 6 &&
    path[4] === "cases" &&
    UUID.test(path[5] ?? "")
  )
    return true;
  return Boolean(
    method === "POST" &&
    path.length === 7 &&
    path[4] === "cases" &&
    UUID.test(path[5] ?? "") &&
    (path[6] === "actions" || path[6] === "workflow"),
  );
}

function privateJson(body: unknown, status: number): Response {
  return Response.json(body, {
    status,
    headers: { "Cache-Control": "private, no-store" },
  });
}

async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  if (!allowed(request.method, path))
    return privateJson({ error: { code: "not_found" } }, 404);

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
  const idempotencyKey = request.headers.get("idempotency-key");
  const contentType = request.headers.get("content-type");
  if (cookie) headers.Cookie = cookie;
  if (csrf) headers["X-CSRF-Token"] = csrf;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  if (contentType) headers["Content-Type"] = contentType;

  try {
    const target = `${baseUrl}/${path.join("/")}${request.nextUrl.search}`;
    const response = await fetch(target, {
      method: request.method,
      headers,
      cache: "no-store",
      ...(request.method === "GET" ? {} : { body: await request.text() }),
    });
    const requestId = response.headers.get("x-request-id");
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "private, no-store",
        ...(requestId ? { "X-Request-ID": requestId } : {}),
      },
    });
  } catch {
    return privateJson({ error: { code: "upstream_unavailable" } }, 502);
  }
}

export const GET = forward;
export const POST = forward;
