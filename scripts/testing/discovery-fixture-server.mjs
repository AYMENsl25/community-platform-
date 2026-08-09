import { createServer } from "node:http";

const port = Number(process.env.DISCOVERY_FIXTURE_PORT ?? 4100);
const privateCanary = "PRIVATE_EXACT_ADDRESS_CANARY";
const memberVenue = "Moda Community Hall, Kadikoy";
const memberRegistrations = new Map();

const events = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    title: "Istanbul Community Run",
    description: "A welcoming public run beside the park.",
    category_slug: "sports",
    country_code: "TR",
    city_slug: "istanbul",
    district: "Kadikoy",
    exact_address: null,
    latitude: null,
    longitude: null,
    public_meeting_area: "Park entrance",
    start_at: "2026-09-20T08:00:00Z",
    end_at: "2026-09-20T10:00:00Z",
    time_zone: "Europe/Istanbul",
    ownership_type: "club",
    cancellation_cutoff_minutes: 60,
    price_type: "free",
    capacity: 30,
    available_places: 12,
    cover_media_id: null,
    club_name: "Istanbul Neighbours",
    club_slug: "istanbul-neighbours",
    organizer_display_name: "Talaqi Fixtures",
    is_saved: false,
    registration_id: null,
    registration_method: null,
    registration_state: null,
    registration_cash_expires_at: null,
    registration_confirmed_at: null,
  },
];

events.push({
  ...events[0],
  id: "11111111-1111-4111-8111-111111111112",
  title: "Istanbul Park Yoga",
  description: "A related public activity selected by city and category.",
  start_at: "2026-09-21T08:00:00Z",
  end_at: "2026-09-21T09:00:00Z",
});

const clubs = [
  {
    id: "22222222-2222-4222-8222-222222222222",
    name: "Istanbul Neighbours",
    slug: "istanbul-neighbours",
    description: "Open community activities in Istanbul.",
    category_slug: "community",
    country_code: "TR",
    city_slug: "istanbul",
    cover_media_id: null,
    member_count: 42,
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

const organizerEvent = {
  id: "55555555-5555-4555-8555-555555555555",
  ownership_type: "independent",
  club_id: null,
  owner_user_id: "88888888-8888-4888-8888-888888888888",
  title: "Organizer fixture event",
  description: "A safe organizer event.",
  category_slug: "sports",
  country_code: "TR",
  city_slug: "istanbul",
  start_at: "2026-09-20T08:00:00Z",
  end_at: "2026-09-20T10:00:00Z",
  time_zone: "Europe/Istanbul",
  capacity: 30,
  visibility: "public",
  status: "draft",
  registration_method: "free",
  cash_expiry_minutes: null,
  cancellation_cutoff_minutes: 60,
  district: "Kadikoy",
  public_meeting_area: "Park entrance",
  exact_address: privateCanary,
  latitude: 40.99,
  longitude: 29.02,
  exact_venue_is_public: false,
  cover_media_id: null,
  revision: 1,
  published_at: null,
  cancelled_at: null,
  completed_at: null,
  suspended_at: null,
  suspension_reason: null,
  created_at: "2026-08-02T08:00:00Z",
  updated_at: "2026-08-02T08:00:00Z",
  capabilities: ["edit", "duplicate", "delete_draft", "preview"],
  validation_blockers: [],
};

let organizerAttendees = [
  {
    registration_id: "44444444-4444-4444-8444-444444444441",
    user_id: "44444444-4444-4444-8444-444444444451",
    username: "cash-member",
    display_name: "Cash Fixture Member",
    method: "cash_organizer_confirmed",
    state: "cash_pending",
    waitlist_sequence: null,
    cash_expires_at: "2036-09-20T07:30:00Z",
    confirmed_at: null,
    created_at: "2026-08-09T10:00:00Z",
  },
  {
    registration_id: "44444444-4444-4444-8444-444444444442",
    user_id: "44444444-4444-4444-8444-444444444452",
    username: "waiting-member",
    display_name: "Waiting Fixture Member",
    method: "free",
    state: "waitlisted",
    waitlist_sequence: 1,
    cash_expires_at: null,
    confirmed_at: null,
    created_at: "2026-08-09T09:00:00Z",
  },
];

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

const adminCaseId = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
let adminTargetStatus = "published";
let adminActionHistory = [];
let adminAuditEvents = [];

function adminTarget() {
  return {
    id: clubs[0].id,
    type: "club",
    label: clubs[0].name,
    secondary_label: "Istanbul",
    status: adminTargetStatus,
  };
}

function adminCase() {
  const actioned = adminActionHistory.length > 0;
  return {
    id: adminCaseId,
    target: adminTarget(),
    category: "safety",
    priority: "emergency",
    status: actioned ? "actioned" : "open",
    assigned_admin_user_id: null,
    resolution_reason: actioned
      ? adminActionHistory[adminActionHistory.length - 1].reason
      : null,
    acknowledged_at: actioned ? "2026-07-27T01:00:00Z" : null,
    resolved_at: actioned ? "2026-07-27T01:00:00Z" : null,
    emergency_notice: true,
    available_actions:
      adminTargetStatus === "published"
        ? ["suspend", "unpublish"]
        : ["restore"],
    created_at: "2026-07-27T00:00:00Z",
    updated_at: "2026-07-27T01:00:00Z",
  };
}

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

function adminKind(request) {
  const match =
    /(?:^|;\s*)talaqi_access=fixture-(platform-admin|platform-admin-no-mfa)(?:;|$)/.exec(
      request.headers.cookie ?? "",
    );
  return match?.[1] ?? null;
}

function hasCsrf(request) {
  return request.headers["x-csrf-token"] === "fixture-csrf";
}

function accessToken(request) {
  return /(?:^|;\s*)talaqi_access=([^;]+)/.exec(
    request.headers.cookie ?? "",
  )?.[1];
}

function memberEvent(request) {
  const token = accessToken(request);
  const registration = token ? memberRegistrations.get(token) : undefined;
  return {
    ...events[0],
    ...(token?.includes("full") ? { available_places: 0 } : {}),
    ...(token?.includes("cash") ? { price_type: "cash" } : {}),
    ...(registration ?? {}),
    exact_address:
      registration?.registration_state === "confirmed" ||
      registration?.registration_state === "cash_pending"
        ? memberVenue
        : null,
  };
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
  const platformAdmin = adminKind(request);
  if (url.pathname === "/api/v1/admin/moderation/cases") {
    if (!platformAdmin)
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    return send(
      response,
      200,
      { items: [adminCase()], next_cursor: null },
      "private, no-store",
    );
  }
  if (url.pathname === `/api/v1/admin/moderation/cases/${adminCaseId}`) {
    if (!platformAdmin)
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    return send(
      response,
      200,
      { case: adminCase(), events: adminActionHistory },
      "private, no-store",
    );
  }
  if (url.pathname === "/api/v1/admin/moderation/targets") {
    if (!platformAdmin)
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    const type = url.searchParams.get("target_type");
    const item =
      type === "club"
        ? adminTarget()
        : {
            id: type === "event" ? events[0].id : workspaceMembers[1].user_id,
            type,
            label:
              type === "event"
                ? events[0].title
                : workspaceMembers[1].display_name,
            secondary_label: "Fixture result",
            status: "active",
          };
    return send(
      response,
      200,
      { items: [item], next_cursor: null },
      "private, no-store",
    );
  }
  if (
    url.pathname === `/api/v1/admin/moderation/cases/${adminCaseId}/actions` &&
    request.method === "POST"
  ) {
    if (platformAdmin !== "platform-admin")
      return send(
        response,
        403,
        { error: { code: "admin_mfa_required" } },
        "private, no-store",
      );
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
    if (reason.length < 3)
      return send(
        response,
        422,
        { error: { code: "invalid_reason" } },
        "private, no-store",
      );
    const previousTargetStatus = adminTargetStatus;
    adminTargetStatus =
      payload.action === "restore"
        ? "published"
        : payload.action === "unpublish"
          ? "unpublished"
          : "suspended";
    const record = {
      id: crypto.randomUUID(),
      actor_user_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
      action: payload.action,
      from_status: adminActionHistory.length ? "actioned" : "open",
      to_status: "actioned",
      reason,
      created_at: "2026-07-27T01:00:00Z",
    };
    adminActionHistory = [...adminActionHistory, record];
    adminAuditEvents = [
      {
        id: crypto.randomUUID(),
        actor_user_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
        actor_kind: "admin",
        action: `moderation.target.${payload.action}`,
        target_type: "club",
        target_id: clubs[0].id,
        reason,
        safe_before: { status: previousTargetStatus },
        safe_after: { status: adminTargetStatus, case_id: adminCaseId },
        request_id: request.headers["idempotency-key"] ?? null,
        created_at: "2026-07-27T01:00:00Z",
      },
      ...adminAuditEvents,
    ];
    return send(
      response,
      200,
      {
        action: payload.action,
        status: "actioned",
        case: adminCase(),
        events: adminActionHistory,
      },
      "private, no-store",
    );
  }
  if (url.pathname === "/api/v1/admin/audit-events") {
    if (!platformAdmin)
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    return send(
      response,
      200,
      { items: adminAuditEvents, next_cursor: null },
      "private, no-store",
    );
  }
  if (url.pathname === "/api/v1/profiles/capabilities") {
    return send(
      response,
      200,
      {
        create_club: role !== "member",
        create_independent_event: role === "owner",
        save_event: true,
        register_event: true,
        access_admin: false,
        blockers: role === "member" ? ["rules_acceptance_required"] : [],
      },
      "private, no-store",
    );
  }
  if (url.pathname === "/api/v1/regions/TR/policy") {
    return send(response, 200, {
      country_code: "TR",
      default_locale: "tr",
      default_currency: "TRY",
      allowed_registration_methods: ["free", "cash_organizer_confirmed"],
      cash_default_minutes: 1440,
      cash_bounds: [120, 4320],
      cancellation_default_minutes: 1440,
      cancellation_bounds: [0, 10080],
      club_limit: 3,
      independent_event_limit: 3,
      exact_venue_public_by_default: false,
      revision: 1,
    });
  }
  if (url.pathname === "/api/v1/events/managed") {
    return send(
      response,
      200,
      { items: role === "member" ? [] : [organizerEvent] },
      "private, no-store",
    );
  }
  const attendeePath = `/api/v1/events/${organizerEvent.id}/attendees`;
  if (url.pathname === attendeePath && request.method === "GET") {
    if (role === "member")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    const state = url.searchParams.get("state");
    const search = (url.searchParams.get("search") ?? "").toLowerCase();
    const items = organizerAttendees.filter(
      (item) =>
        (!state || item.state === state) &&
        (!search ||
          item.username.toLowerCase().includes(search) ||
          item.display_name.toLowerCase().includes(search)),
    );
    return send(
      response,
      200,
      { items, next_cursor: null },
      "private, no-store",
    );
  }
  if (url.pathname === `${attendeePath}/summary` && request.method === "GET") {
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
      {
        held: organizerAttendees.filter((item) =>
          ["confirmed", "cash_pending"].includes(item.state),
        ).length,
        confirmed: organizerAttendees.filter(
          (item) => item.state === "confirmed",
        ).length,
        cash_pending: organizerAttendees.filter(
          (item) => item.state === "cash_pending",
        ).length,
        waitlisted: organizerAttendees.filter(
          (item) => item.state === "waitlisted",
        ).length,
        cancelled: 0,
        expired: 0,
      },
      "private, no-store",
    );
  }
  if (url.pathname === `${attendeePath}/export` && request.method === "POST") {
    if (role === "member")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    if (!hasCsrf(request))
      return send(
        response,
        403,
        { error: { code: "csrf_failed" } },
        "private, no-store",
      );
    return send(
      response,
      202,
      { request_id: "44444444-4444-4444-8444-444444444499", status: "queued" },
      "private, no-store",
    );
  }
  const cashConfirmPath = `${attendeePath.replace("/attendees", "/registrations")}/${organizerAttendees[0].registration_id}/confirm-cash`;
  if (url.pathname === cashConfirmPath && request.method === "POST") {
    if (role === "member")
      return send(
        response,
        403,
        { error: { code: "forbidden" } },
        "private, no-store",
      );
    if (!hasCsrf(request))
      return send(
        response,
        403,
        { error: { code: "csrf_failed" } },
        "private, no-store",
      );
    organizerAttendees = organizerAttendees.map((item) =>
      item.registration_id === organizerAttendees[0].registration_id
        ? { ...item, state: "confirmed", confirmed_at: "2026-08-10T00:00:00Z" }
        : item,
    );
    return send(response, 200, organizerAttendees[0], "private, no-store");
  }
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
  const targetIsPublic = adminTargetStatus === "published";
  const savedPath = `/api/v1/events/${events[0].id}/saved`;
  const registrationPath = `/api/v1/events/${events[0].id}/registrations`;
  const cancellationPath = `${registrationPath}/me`;
  if (url.pathname === registrationPath && request.method === "POST") {
    const token = accessToken(request);
    if (!token)
      return send(
        response,
        401,
        { error: { code: "unauthorized", message_key: "errors.unauthorized" } },
        "private, no-store",
      );
    if (!hasCsrf(request))
      return send(
        response,
        403,
        { error: { code: "csrf_failed" } },
        "private, no-store",
      );
    const state = token.includes("cash")
      ? "cash_pending"
      : token.includes("full")
        ? "waitlisted"
        : "confirmed";
    const registration = {
      registration_id: "33333333-3333-4333-8333-333333333333",
      registration_method:
        state === "cash_pending" ? "cash_organizer_confirmed" : "free",
      registration_state: state,
      registration_cash_expires_at:
        state === "cash_pending" ? "2036-09-20T07:30:00Z" : null,
      registration_confirmed_at:
        state === "confirmed" ? "2026-08-10T00:00:00Z" : null,
      available_places: state === "waitlisted" ? 0 : 11,
    };
    memberRegistrations.set(token, registration);
    return send(
      response,
      201,
      { id: registration.registration_id, state },
      "private, no-store",
    );
  }
  if (url.pathname === cancellationPath && request.method === "DELETE") {
    const token = accessToken(request);
    if (!token)
      return send(
        response,
        401,
        { error: { code: "unauthorized" } },
        "private, no-store",
      );
    if (!hasCsrf(request))
      return send(
        response,
        403,
        { error: { code: "csrf_failed" } },
        "private, no-store",
      );
    memberRegistrations.delete(token);
    return send(response, 200, { state: "cancelled" }, "private, no-store");
  }
  if (
    url.pathname === savedPath &&
    ["PUT", "DELETE"].includes(request.method)
  ) {
    if (!(request.headers.cookie ?? "").includes("talaqi_access="))
      return send(
        response,
        401,
        { error: { code: "unauthorized" } },
        "private, no-store",
      );
    if (!hasCsrf(request))
      return send(
        response,
        403,
        { error: { code: "csrf_failed" } },
        "private, no-store",
      );
    return send(response, 204, undefined, "private, no-store");
  }
  if (url.pathname === "/api/v1/events")
    return send(response, 200, {
      items: empty || !targetIsPublic ? [] : events,
      next_cursor: null,
    });
  if (url.pathname === `/api/v1/events/${events[0].id}`)
    return targetIsPublic
      ? send(response, 200, memberEvent(request), "private, no-store")
      : send(response, 404, { error: { code: "not_found" } });
  if (url.pathname === "/api/v1/clubs")
    return send(response, 200, {
      items: empty || !targetIsPublic ? [] : clubs,
      next_cursor: null,
    });
  if (url.pathname === `/api/v1/clubs/${clubs[0].slug}`)
    return targetIsPublic
      ? send(response, 200, { ...clubs[0], events })
      : send(response, 404, { error: { code: "not_found" } });
  if (url.pathname === "/api/v1/search") {
    return send(response, 200, {
      items:
        empty || !targetIsPublic
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
