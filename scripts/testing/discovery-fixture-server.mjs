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

const organizerClubId = "77777777-7777-4777-8777-777777777777";
const secondOrganizerClubId = "66666666-6666-4666-8666-666666666666";
const organizerClub = {
  id: organizerClubId,
  slug: "workspace-runners",
  name: "Workspace Runners",
  description: null,
  category_slug: null,
  country_code: null,
  city_slug: null,
  membership_policy: "approval_required",
  social_links: {},
  logo_media_id: null,
  cover_media_id: null,
  revision: 1,
  status: "draft",
  missing_fields: ["description", "category_slug", "country_code", "city_slug"],
  published_at: null,
  suspended_at: null,
  suspension_reason: null,
  closed_at: null,
  created_at: "2026-07-26T11:00:00Z",
  updated_at: "2026-07-26T11:00:00Z",
};

const secondOrganizerClub = {
  ...organizerClub,
  id: secondOrganizerClubId,
  slug: "safe-switch-club",
  name: "Safe Switch Club",
  description: "A separate fixture used to verify club data isolation.",
  category_slug: "community",
  country_code: "TR",
  city_slug: "istanbul",
  revision: 4,
  status: "published",
  missing_fields: [],
  published_at: "2026-07-26T12:00:00Z",
};

const workspaceMembers = [
  {
    user_id: "88888888-8888-4888-8888-888888888888",
    display_name: "Fixture Owner",
    email: "owner@example.test",
    role: "owner",
    joined_at: "2026-07-26T11:00:00Z",
  },
  {
    user_id: "99999999-9999-4999-8999-999999999999",
    display_name: "Fixture Member",
    email: "member@example.test",
    role: "member",
    joined_at: "2026-07-26T11:30:00Z",
  },
];

const workspaceRequests = [
  {
    id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    user_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    display_name: "Pending Fixture",
    email: "pending@example.test",
    status: "pending",
    message: "I would like to join.",
    decision_reason: null,
    decided_at: null,
    created_at: "2026-07-26T11:45:00Z",
  },
];

const secondWorkspaceMembers = [
  {
    user_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    display_name: "Second Club Owner",
    email: "second-owner@example.test",
    role: "owner",
    joined_at: "2026-07-26T12:00:00Z",
  },
  {
    user_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    display_name: "Second Club Member",
    email: "second-member@example.test",
    role: "member",
    joined_at: "2026-07-26T12:30:00Z",
  },
];

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function fixtureRole(request) {
  const match =
    /(?:^|;\s*)talaqi_access=fixture-(owner|admin|member)(?:;|$)/.exec(
      request.headers.cookie ?? "",
    );
  return match?.[1] ?? "member";
}

function hasCsrf(request) {
  return request.headers["x-csrf-token"] === "fixture-csrf";
}

async function body(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
}

function capabilities(role) {
  if (role === "owner")
    return [
      "edit_profile",
      "manage_members",
      "change_member_roles",
      "transfer_ownership",
      "close_club",
      "preview_profile",
    ];
  if (role === "admin")
    return ["edit_profile", "manage_members", "preview_profile"];
  return [];
}

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

createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://${request.headers.host}`);
  if (url.pathname === "/health") return send(response, 200, { status: "ok" });
  if (url.searchParams.get("search") === "fixture-error") {
    return send(response, 500, {
      error: { code: "fixture_failure", message_key: privateCanary },
    });
  }
  const empty = url.searchParams.get("search") === "fixture-empty";
  const role = fixtureRole(request);
  if (url.pathname === "/api/v1/clubs/managed") {
    return send(
      response,
      200,
      {
        items:
          role === "member"
            ? []
            : [organizerClub, secondOrganizerClub].map((club) => ({
                ...club,
                role,
                capabilities: capabilities(role),
              })),
      },
      "private, no-store",
    );
  }
  if (url.pathname === `/api/v1/clubs/${organizerClubId}/members`) {
    if (role === "member")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    return send(
      response,
      200,
      { items: workspaceMembers },
      "private, no-store",
    );
  }
  if (url.pathname === `/api/v1/clubs/${organizerClubId}/join-requests`) {
    if (role === "member")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    return send(
      response,
      200,
      { items: workspaceRequests },
      "private, no-store",
    );
  }
  if (url.pathname === `/api/v1/clubs/${secondOrganizerClubId}/members`) {
    if (role === "member")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    await delay(500);
    return send(
      response,
      200,
      { items: secondWorkspaceMembers },
      "private, no-store",
    );
  }
  if (url.pathname === `/api/v1/clubs/${secondOrganizerClubId}/join-requests`) {
    if (role === "member")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    await delay(250);
    return send(
      response,
      503,
      { error: { code: "upstream_unavailable" } },
      "private, no-store",
    );
  }
  if (
    url.pathname.startsWith(`/api/v1/clubs/${organizerClubId}`) &&
    request.method !== "GET"
  ) {
    if (!hasCsrf(request))
      return send(
        response,
        403,
        { error: { code: "csrf_failed" } },
        "private, no-store",
      );
    const payload = await body(request);
    const reason =
      typeof payload.reason === "string" ? payload.reason.trim() : "";
    if (
      url.pathname === `/api/v1/clubs/${organizerClubId}` &&
      request.method === "PATCH"
    ) {
      if (role === "member")
        return send(
          response,
          403,
          { error: { code: "forbidden" } },
          "private, no-store",
        );
      if (payload.name === "server-error")
        return send(
          response,
          500,
          { error: { code: "private", message_key: privateCanary } },
          "private, no-store",
        );
      return send(
        response,
        200,
        {
          ...organizerClub,
          ...payload,
          revision: 2,
          status: "published",
          missing_fields: [],
          published_at: "2026-07-26T12:00:00Z",
        },
        "private, no-store",
      );
    }
    const ownerOnly =
      /\/(members\/[0-9a-f-]+\/role|ownership-transfer|close)$/.test(
        url.pathname,
      );
    if (ownerOnly && role !== "owner")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    if (reason.length < 3)
      return send(
        response,
        422,
        { error: { code: "invalid_reason" } },
        "private, no-store",
      );
    return send(response, 200, { status: "completed" }, "private, no-store");
  }
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
