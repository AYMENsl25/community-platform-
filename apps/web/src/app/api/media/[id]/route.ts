const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await context.params;
  if (!UUID.test(id)) return new Response(null, { status: 404 });
  const baseUrl = (
    process.env.API_PUBLIC_URL ?? "http://localhost:8000"
  ).replace(/\/$/, "");
  try {
    const response = await fetch(
      `${baseUrl}/api/v1/media/public/${encodeURIComponent(id)}`,
      { next: { revalidate: 60, tags: [`public-media:${id}`] } },
    );
    if (!response.ok)
      return new Response(null, {
        status: response.status === 404 ? 404 : 502,
        headers: { "Cache-Control": "no-store" },
      });
    if (response.headers.get("content-type") !== "image/webp")
      return new Response(null, {
        status: 502,
        headers: { "Cache-Control": "no-store" },
      });
    return new Response(response.body, {
      status: 200,
      headers: {
        "Content-Type": "image/webp",
        "Cache-Control":
          response.headers.get("cache-control") ??
          "public, max-age=60, s-maxage=300, must-revalidate",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return new Response(null, {
      status: 502,
      headers: { "Cache-Control": "no-store" },
    });
  }
}
