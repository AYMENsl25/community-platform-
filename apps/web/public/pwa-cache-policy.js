const SENSITIVE_SEGMENTS = [
  "/me",
  "/invitations",
  "/registrations",
  "/notifications",
  "/attendees",
  "/admin",
];

export function cacheCategory(request) {
  if (request.method !== "GET") return "bypass";
  const url = new URL(request.url);
  const path = url.pathname;
  if (
    path.startsWith("/api/admin/") ||
    path.startsWith("/api/organizer/") ||
    SENSITIVE_SEGMENTS.some((segment) =>
      path.split("/").includes(segment.slice(1)),
    )
  ) {
    return "bypass";
  }
  if (path.startsWith("/_next/static/")) {
    return "static";
  }
  if (
    path === "/api/public/api/v1/clubs" ||
    path === "/api/public/api/v1/search" ||
    path === "/api/public/api/v1/metadata" ||
    /^\/api\/public\/api\/v1\/regions\/[^/]+\/policy$/.test(path)
  ) {
    return "public";
  }
  return "bypass";
}
