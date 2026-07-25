import { createServer } from "node:http";

const port = Number(process.env.DISCOVERY_FIXTURE_PORT ?? 4100);
const privateCanary = "PRIVATE_EXACT_ADDRESS_CANARY";

const events = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    title: "Istanbul Community Run",
    description: "A welcoming public run beside the park.",
    category_slug: "sports",
    country_code: "TR",
    city_slug: "istanbul",
    district: "Kadikoy",
    public_meeting_area: "Park entrance",
    start_at: "2026-09-20T08:00:00Z",
    end_at: "2026-09-20T10:00:00Z",
    time_zone: "Europe/Istanbul",
    price_type: "free",
    capacity: 30,
    available_places: 12,
    cover_storage_key: null,
    club_name: "Istanbul Neighbours",
    club_slug: "istanbul-neighbours",
    organizer_display_name: "Talaqi Fixtures",
    is_saved: false,
    registration_state: null,
  },
];

const clubs = [
  {
    id: "22222222-2222-4222-8222-222222222222",
    name: "Istanbul Neighbours",
    slug: "istanbul-neighbours",
    description: "Open community activities in Istanbul.",
    category_slug: "community",
    country_code: "TR",
    city_slug: "istanbul",
    cover_storage_key: null,
  },
];

function send(
  response,
  status,
  body,
  cache = "public, max-age=60, s-maxage=300",
) {
  response.writeHead(status, {
    "Content-Type": "application/json",
    "Cache-Control": cache,
    "Access-Control-Allow-Origin": "*",
    "X-Request-ID": "33333333-3333-4333-8333-333333333333",
  });
  response.end(body === undefined ? undefined : JSON.stringify(body));
}

createServer((request, response) => {
  const url = new URL(request.url ?? "/", `http://${request.headers.host}`);
  if (url.pathname === "/health") return send(response, 200, { status: "ok" });
  if (url.searchParams.get("search") === "fixture-error") {
    return send(response, 500, {
      error: { code: "fixture_failure", message_key: privateCanary },
    });
  }
  const empty = url.searchParams.get("search") === "fixture-empty";
  if (url.pathname === "/api/v1/metadata") {
    return send(response, 200, {
      countries: [{ code: "TR", name_key: "countries.TR" }],
      cities: [{ slug: "istanbul", name_key: "cities.istanbul" }],
      categories: [
        { slug: "sports", name_key: "categories.sports" },
        { slug: "community", name_key: "categories.community" },
      ],
      price_types: ["free", "cash"],
      sort: "featured",
    });
  }
  if (url.pathname === "/api/v1/events")
    return send(response, 200, {
      items: empty ? [] : events,
      next_cursor: null,
    });
  if (url.pathname === `/api/v1/events/${events[0].id}`)
    return send(response, 200, events[0]);
  if (url.pathname === "/api/v1/clubs")
    return send(response, 200, {
      items: empty ? [] : clubs,
      next_cursor: null,
    });
  if (url.pathname === `/api/v1/clubs/${clubs[0].slug}`)
    return send(response, 200, { ...clubs[0], events });
  if (url.pathname === "/api/v1/search") {
    return send(response, 200, {
      items: empty
        ? []
        : [
            {
              id: events[0].id,
              kind: "event",
              slug: null,
              title: events[0].title,
              description: events[0].description,
              category_slug: events[0].category_slug,
              country_code: "TR",
              city_slug: "istanbul",
              start_at: events[0].start_at,
            },
            {
              id: clubs[0].id,
              kind: "club",
              slug: clubs[0].slug,
              title: clubs[0].name,
              description: clubs[0].description,
              category_slug: clubs[0].category_slug,
              country_code: "TR",
              city_slug: "istanbul",
              start_at: null,
            },
          ],
      next_cursor: null,
    });
  }
  if (url.pathname === "/api/v1/me/saved-events")
    return send(
      response,
      401,
      { error: { code: "unauthorized", message_key: "errors.auth_required" } },
      "private, no-store",
    );
  return send(response, 404, {
    error: { code: "not_found", message_key: "errors.not_found" },
  });
}).listen(port, "127.0.0.1", () => {
  console.log(`Discovery fixture API listening on http://127.0.0.1:${port}`);
});
