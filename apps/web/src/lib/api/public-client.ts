import type { components, operations } from "@talaqi/api-client";

export type UiErrorKey =
  | "errors.auth_required"
  | "errors.action_unavailable"
  | "errors.not_found"
  | "errors.invalid_filters"
  | "errors.rate_limited"
  | "errors.unavailable";

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; key: UiErrorKey; status: number; requestId?: string };

type EventPage = components["schemas"]["EventPageResponse"];
type EventDetail = components["schemas"]["EventAudienceResponse"];
type ClubPage = components["schemas"]["ClubPageResponse"];
type ClubDetail = components["schemas"]["ClubDetailResponse"];
type SearchPage = components["schemas"]["SearchPageResponse"];
type Metadata = components["schemas"]["DiscoveryMetadataResponse"];
type RegionPolicy = components["schemas"]["RegionPolicyResponse"];
type EventQuery = NonNullable<operations["listEvents"]["parameters"]["query"]>;
type ClubQuery = NonNullable<operations["listClubs"]["parameters"]["query"]>;
type SearchQuery = operations["searchDiscovery"]["parameters"]["query"];
type SavedQuery = NonNullable<
  operations["listSavedEvents"]["parameters"]["query"]
>;

interface NextFetchInit extends RequestInit {
  next?: { revalidate: number; tags: string[] };
}

export interface PublicClientOptions {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
  cookie?: string;
  csrfToken?: string;
}

export interface PublicClient {
  listEvents(query: EventQuery): Promise<ApiResult<EventPage>>;
  getEvent(eventId: string): Promise<ApiResult<EventDetail>>;
  listClubs(query: ClubQuery): Promise<ApiResult<ClubPage>>;
  getClub(slug: string): Promise<ApiResult<ClubDetail>>;
  search(query: SearchQuery): Promise<ApiResult<SearchPage>>;
  getMetadata(): Promise<ApiResult<Metadata>>;
  getRegionPolicy(countryCode: string): Promise<ApiResult<RegionPolicy>>;
  listSavedEvents(query: SavedQuery): Promise<ApiResult<EventPage>>;
  saveEvent(eventId: string): Promise<ApiResult<void>>;
  unsaveEvent(eventId: string): Promise<ApiResult<void>>;
}

function queryString(query: Record<string, unknown>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "")
      params.set(key, String(value));
  }
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

function errorKey(status: number): UiErrorKey {
  if (status === 401) return "errors.auth_required";
  if (status === 403) return "errors.action_unavailable";
  if (status === 404) return "errors.not_found";
  if (status === 422) return "errors.invalid_filters";
  if (status === 429) return "errors.rate_limited";
  return "errors.unavailable";
}

async function requestId(response: Response): Promise<string | undefined> {
  try {
    const body: unknown = await response.json();
    if (typeof body !== "object" || body === null || !("error" in body))
      return undefined;
    const error = body.error;
    if (typeof error !== "object" || error === null || !("request_id" in error))
      return undefined;
    return typeof error.request_id === "string" ? error.request_id : undefined;
  } catch {
    return undefined;
  }
}

export function createPublicClient(options: PublicClientOptions): PublicClient {
  if (!options.baseUrl) throw new TypeError("baseUrl is required");
  const baseUrl = options.baseUrl.replace(/\/$/, "");
  const fetcher = options.fetch ?? globalThis.fetch;

  async function request<T>(
    path: string,
    config: {
      method?: "GET" | "PUT" | "DELETE";
      tag?: string;
      callerAware?: boolean;
      private?: boolean;
    },
  ): Promise<ApiResult<T>> {
    const isPrivate =
      config.private === true ||
      (config.callerAware === true && !!options.cookie);
    const headers: Record<string, string> = {};
    if (isPrivate && options.cookie) headers.Cookie = options.cookie;
    if (
      config.method !== undefined &&
      config.method !== "GET" &&
      options.csrfToken
    ) {
      headers["X-CSRF-Token"] = options.csrfToken;
    }
    const init: NextFetchInit = {
      method: config.method ?? "GET",
      headers,
      ...(isPrivate
        ? { cache: "no-store", credentials: "include" }
        : { next: { revalidate: 60, tags: [config.tag ?? "discovery"] } }),
    };
    try {
      const response = await fetcher(`${baseUrl}${path}`, init);
      if (!response.ok) {
        const id = await requestId(response);
        return {
          ok: false,
          key: errorKey(response.status),
          status: response.status,
          ...(id ? { requestId: id } : {}),
        };
      }
      if (response.status === 204) return { ok: true, data: undefined as T };
      try {
        return { ok: true, data: (await response.json()) as T };
      } catch {
        return {
          ok: false,
          key: "errors.unavailable",
          status: response.status,
        };
      }
    } catch {
      return { ok: false, key: "errors.unavailable", status: 0 };
    }
  }

  return {
    listEvents: (query) =>
      request(`/api/v1/events${queryString(query)}`, {
        tag: "discovery:events",
        callerAware: true,
      }),
    getEvent: (id) =>
      request(`/api/v1/events/${encodeURIComponent(id)}`, {
        tag: `discovery:event:${id}`,
        callerAware: true,
      }),
    listClubs: (query) =>
      request(`/api/v1/clubs${queryString(query)}`, { tag: "discovery:clubs" }),
    getClub: (slug) =>
      request(`/api/v1/clubs/${encodeURIComponent(slug)}`, {
        tag: `discovery:club:${slug}`,
        callerAware: true,
      }),
    search: (query) =>
      request(`/api/v1/search${queryString(query)}`, {
        tag: "discovery:search",
      }),
    getMetadata: () =>
      request("/api/v1/metadata", { tag: "discovery:metadata" }),
    getRegionPolicy: (countryCode) =>
      request(`/api/v1/regions/${encodeURIComponent(countryCode)}/policy`, {
        tag: `region:policy:${countryCode}`,
      }),
    listSavedEvents: (query) =>
      request(`/api/v1/me/saved-events${queryString(query)}`, {
        private: true,
      }),
    saveEvent: (id) =>
      request(`/api/v1/events/${encodeURIComponent(id)}/saved`, {
        method: "PUT",
        private: true,
      }),
    unsaveEvent: (id) =>
      request(`/api/v1/events/${encodeURIComponent(id)}/saved`, {
        method: "DELETE",
        private: true,
      }),
  };
}
