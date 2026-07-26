import type { components } from "@talaqi/api-client";
import type { TranslationKey } from "@talaqi/translations";

export type ManagedClub = components["schemas"]["ManagedClubResponse"];
export type ClubMember = components["schemas"]["MemberResponse"];
export type ClubJoinRequest = components["schemas"]["JoinRequestResponse"];
export type ClubPatch = components["schemas"]["ClubPatchRequest"];

export type OrganizerResult<T> =
  | { ok: true; data: T }
  | {
      ok: false;
      key: TranslationKey;
      status: number;
      requestId?: string;
      fieldNames: string[];
    };

type ManagedClubPage = components["schemas"]["ManagedClubPageResponse"];
type MemberPage = components["schemas"]["MemberPageResponse"];
type JoinRequestPage = components["schemas"]["JoinRequestPageResponse"];
type ClubResponse = components["schemas"]["ClubResponse"];

type ErrorBody = {
  error?: {
    code?: unknown;
    request_id?: unknown;
    field_errors?: unknown;
  };
};

export interface OrganizerClientOptions {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
  cookie?: string;
  csrfToken?: string;
}

export interface OrganizerClient {
  listManagedClubs(): Promise<OrganizerResult<ManagedClubPage>>;
  listMembers(clubId: string): Promise<OrganizerResult<MemberPage>>;
  listRequests(clubId: string): Promise<OrganizerResult<JoinRequestPage>>;
  updateClub(
    clubId: string,
    patch: ClubPatch,
  ): Promise<OrganizerResult<ClubResponse>>;
  approveRequest(
    clubId: string,
    requestId: string,
    reason: string,
  ): Promise<OrganizerResult<void>>;
  rejectRequest(
    clubId: string,
    requestId: string,
    reason: string,
  ): Promise<OrganizerResult<void>>;
  changeRole(
    clubId: string,
    userId: string,
    role: "admin" | "member",
    reason: string,
  ): Promise<OrganizerResult<void>>;
  transferOwnership(
    clubId: string,
    userId: string,
    reason: string,
  ): Promise<OrganizerResult<void>>;
  closeClub(clubId: string, reason: string): Promise<OrganizerResult<void>>;
}

function mappedErrorKey(code: unknown, status: number): TranslationKey {
  if (code === "stale_revision") return "organizer.errors.staleRevision";
  if (code === "duplicate_slug") return "organizer.errors.duplicateSlug";
  if (code === "invalid_reason") return "organizer.errors.reason";
  if (code === "csrf_failed") return "errors.csrf_failed";
  if (code === "forbidden" || status === 403) return "errors.forbidden";
  if (status === 401) return "errors.authentication_required";
  if (status === 404) return "errors.not_found";
  if (status === 409) return "errors.conflict";
  if (status === 400 || status === 422) return "errors.validation";
  return "errors.internal";
}

function fieldNames(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (typeof item !== "object" || item === null || !("field" in item))
      return [];
    return typeof item.field === "string" ? [item.field] : [];
  });
}

export function createOrganizerClient(
  options: OrganizerClientOptions,
): OrganizerClient {
  const fetcher = options.fetch ?? globalThis.fetch;
  const baseUrl = options.baseUrl.replace(/\/$/, "");

  async function request<T>(
    path: string,
    init: { method?: "GET" | "PATCH" | "POST"; body?: unknown } = {},
  ): Promise<OrganizerResult<T>> {
    const headers: Record<string, string> = {};
    if (options.cookie) headers.Cookie = options.cookie;
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    if (init.method && init.method !== "GET" && options.csrfToken)
      headers["X-CSRF-Token"] = options.csrfToken;
    try {
      const response = await fetcher(`${baseUrl}${path}`, {
        method: init.method ?? "GET",
        headers,
        cache: "no-store",
        credentials: "include",
        ...(init.body === undefined ? {} : { body: JSON.stringify(init.body) }),
      });
      if (!response.ok) {
        let body: ErrorBody = {};
        try {
          body = (await response.json()) as ErrorBody;
        } catch {
          body = {};
        }
        const code = body.error?.code;
        const requestId = body.error?.request_id;
        return {
          ok: false,
          key: mappedErrorKey(code, response.status),
          status: response.status,
          fieldNames: fieldNames(body.error?.field_errors),
          ...(typeof requestId === "string" ? { requestId } : {}),
        };
      }
      if (response.status === 204) return { ok: true, data: undefined as T };
      return { ok: true, data: (await response.json()) as T };
    } catch {
      return {
        ok: false,
        key: "errors.internal",
        status: 0,
        fieldNames: [],
      };
    }
  }

  const clubPath = (clubId: string) =>
    `/api/v1/clubs/${encodeURIComponent(clubId)}`;
  return {
    listManagedClubs: () => request("/api/v1/clubs/managed"),
    listMembers: (clubId) => request(`${clubPath(clubId)}/members`),
    listRequests: (clubId) => request(`${clubPath(clubId)}/join-requests`),
    updateClub: (clubId, patch) =>
      request(clubPath(clubId), { method: "PATCH", body: patch }),
    approveRequest: (clubId, requestId, reason) =>
      request(`${clubPath(clubId)}/join-requests/${requestId}/approve`, {
        method: "POST",
        body: { reason },
      }),
    rejectRequest: (clubId, requestId, reason) =>
      request(`${clubPath(clubId)}/join-requests/${requestId}/reject`, {
        method: "POST",
        body: { reason },
      }),
    changeRole: (clubId, userId, role, reason) =>
      request(`${clubPath(clubId)}/members/${userId}/role`, {
        method: "PATCH",
        body: { role, reason },
      }),
    transferOwnership: (clubId, userId, reason) =>
      request(`${clubPath(clubId)}/ownership-transfer`, {
        method: "POST",
        body: { target_user_id: userId, reason },
      }),
    closeClub: (clubId, reason) =>
      request(`${clubPath(clubId)}/close`, {
        method: "POST",
        body: { reason },
      }),
  };
}
