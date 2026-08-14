import type { components } from "@talaqi/api-client";
import type { TranslationKey } from "@talaqi/translations";

export type ModerationTargetType = "user" | "club" | "event";
export type ModerationCategory =
  | "safety"
  | "harassment"
  | "fraud"
  | "illegal_content"
  | "privacy"
  | "spam"
  | "other";
export type ModerationPriority = "standard" | "high" | "emergency";
export type ModerationCaseStatus =
  "open" | "investigating" | "actioned" | "dismissed";
export type ModerationAction = "suspend" | "unpublish" | "restore";
export type CaseWorkflowAction = "acknowledge" | "dismiss";

export interface ModerationTargetSummary {
  id: string;
  target_type: ModerationTargetType;
  display_name: string;
  secondary_text: string | null;
  status: string;
}

export interface ModerationCaseSummary {
  id: string;
  target: ModerationTargetSummary;
  category: ModerationCategory;
  priority: ModerationPriority;
  status: ModerationCaseStatus;
  is_emergency: boolean;
  available_actions: ModerationAction[];
  created_at: string;
  updated_at: string;
}

export interface ModerationActionRecord {
  id: string;
  action: ModerationAction | null;
  workflow_action: CaseWorkflowAction | null;
  reason: string;
  actor_user_id: string | null;
  created_at: string;
}

export interface ModerationCaseDetail extends ModerationCaseSummary {
  action_history: ModerationActionRecord[];
}

export interface ModerationCasePage {
  items: ModerationCaseSummary[];
  next_cursor: string | null;
}

export interface ModerationTargetPage {
  items: ModerationTargetSummary[];
  next_cursor: string | null;
}

export interface AdminAuditEvent {
  id: string;
  action: string;
  actor_kind: string;
  actor_user_id: string | null;
  target_type: string;
  target_id: string | null;
  reason: string | null;
  request_id: string | null;
  safe_before: Record<string, unknown> | null;
  safe_after: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminAuditEventPage {
  items: AdminAuditEvent[];
  next_cursor: string | null;
}

export type AdminResult<T> =
  | { ok: true; data: T }
  | {
      ok: false;
      key: TranslationKey;
      status: number;
      requestId?: string;
      fieldNames: string[];
    };

export interface ModerationCaseQuery {
  status?: ModerationCaseStatus;
  priority?: ModerationPriority;
  targetType?: ModerationTargetType;
  cursor?: string;
  limit?: number;
}

export interface AdminAuditEventQuery {
  targetType?: ModerationTargetType;
  targetId?: string;
  cursor?: string;
  limit?: number;
}

export interface AdminClientOptions {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
  cookie?: string;
  csrfToken?: string;
}

export interface AdminClient {
  listModerationCases(
    query?: ModerationCaseQuery,
  ): Promise<AdminResult<ModerationCasePage>>;
  getModerationCase(caseId: string): Promise<AdminResult<ModerationCaseDetail>>;
  searchModerationTargets(
    query: string,
    targetType: ModerationTargetType,
  ): Promise<AdminResult<ModerationTargetPage>>;
  submitModerationAction(
    caseId: string,
    action: ModerationAction,
    reason: string,
    idempotencyKey: string,
  ): Promise<AdminResult<ModerationCaseDetail>>;
  transitionModerationCase(
    caseId: string,
    action: CaseWorkflowAction,
    reason: string,
    idempotencyKey: string,
  ): Promise<AdminResult<ModerationCaseDetail>>;
  listAuditEvents(
    query?: AdminAuditEventQuery,
  ): Promise<AdminResult<AdminAuditEventPage>>;
}

type ApiCase = components["schemas"]["CaseResponse"];
type ApiCaseDetail = components["schemas"]["CaseDetailResponse"];
type ApiActionResponse = components["schemas"]["ActionResponse"];
type ApiWorkflowResponse = components["schemas"]["CaseWorkflowResponse"];
type ApiTarget = components["schemas"]["TargetResponse"];
type ApiCasePage = components["schemas"]["CasePageResponse"];
type ApiTargetPage = components["schemas"]["TargetPageResponse"];
type ApiAuditPage = components["schemas"]["AuditPageResponse"];

type ErrorDetails = {
  code?: unknown;
  requestId?: string;
  fieldNames: string[];
};

function errorKey(code: unknown, status: number): TranslationKey {
  if (code === "csrf_failed") return "errors.csrf_failed";
  if (status === 401) return "errors.authentication_required";
  if (status === 403) return "errors.forbidden";
  if (status === 404) return "errors.not_found";
  if (status === 409) return "errors.conflict";
  if (status === 400 || status === 422) return "errors.validation";
  if (status === 429) return "errors.rate_limited";
  return "errors.internal";
}

function errorDetails(value: unknown): ErrorDetails {
  if (
    typeof value !== "object" ||
    value === null ||
    !("error" in value) ||
    typeof value.error !== "object" ||
    value.error === null
  )
    return { fieldNames: [] };
  const error = value.error as Record<string, unknown>;
  const fieldErrors = Array.isArray(error.field_errors)
    ? error.field_errors
    : [];
  const fieldNames = fieldErrors.flatMap((item) => {
    if (
      typeof item !== "object" ||
      item === null ||
      !("field" in item) ||
      typeof item.field !== "string"
    )
      return [];
    return [item.field];
  });
  return {
    code: error.code,
    fieldNames,
    ...(typeof error.request_id === "string"
      ? { requestId: error.request_id }
      : {}),
  };
}

function queryString(values: Record<string, unknown>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== null && value !== "")
      params.set(key, String(value));
  }
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

function targetSummary(value: ApiTarget): ModerationTargetSummary {
  return {
    id: value.id,
    target_type: value.type,
    display_name: value.label,
    secondary_text: value.secondary_label,
    status: value.status,
  };
}

function caseSummary(value: ApiCase): ModerationCaseSummary {
  return {
    id: value.id,
    target: targetSummary(value.target),
    category: value.category as ModerationCategory,
    priority: value.priority,
    status: value.status,
    is_emergency: value.emergency_notice,
    available_actions: value.available_actions,
    created_at: value.created_at,
    updated_at: value.updated_at,
  };
}

function caseDetail(
  value: ApiCaseDetail | ApiActionResponse | ApiWorkflowResponse,
): ModerationCaseDetail {
  return {
    ...caseSummary(value.case),
    action_history: value.events.map((event) => ({
      id: event.id,
      action: event.action as ModerationAction | null,
      workflow_action: event.workflow_action,
      reason: event.reason,
      actor_user_id: event.actor_user_id,
      created_at: event.created_at,
    })),
  };
}

function mapResult<Source, Target>(
  result: AdminResult<Source>,
  mapper: (value: Source) => Target,
): AdminResult<Target> {
  return result.ok ? { ok: true, data: mapper(result.data) } : result;
}

export function createAdminClient(options: AdminClientOptions): AdminClient {
  if (!options.baseUrl) throw new TypeError("baseUrl is required");
  const fetcher = options.fetch ?? globalThis.fetch;
  const baseUrl = options.baseUrl.replace(/\/$/, "");

  async function request<T>(
    path: string,
    init: {
      method?: "GET" | "POST";
      body?: unknown;
      idempotencyKey?: string;
    } = {},
  ): Promise<AdminResult<T>> {
    const headers: Record<string, string> = {};
    if (options.cookie) headers.Cookie = options.cookie;
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    if (init.method === "POST" && options.csrfToken)
      headers["X-CSRF-Token"] = options.csrfToken;
    if (init.idempotencyKey) headers["Idempotency-Key"] = init.idempotencyKey;
    try {
      const response = await fetcher(`${baseUrl}${path}`, {
        method: init.method ?? "GET",
        headers,
        cache: "no-store",
        credentials: "include",
        ...(init.body === undefined ? {} : { body: JSON.stringify(init.body) }),
      });
      if (!response.ok) {
        let parsed: unknown;
        try {
          parsed = await response.json();
        } catch {
          parsed = undefined;
        }
        const details = errorDetails(parsed);
        return {
          ok: false,
          key: errorKey(details.code, response.status),
          status: response.status,
          fieldNames: details.fieldNames,
          ...(details.requestId ? { requestId: details.requestId } : {}),
        };
      }
      if (response.status === 204) return { ok: true, data: undefined as T };
      try {
        return { ok: true, data: (await response.json()) as T };
      } catch {
        return {
          ok: false,
          key: "errors.internal",
          status: response.status,
          fieldNames: [],
        };
      }
    } catch {
      return {
        ok: false,
        key: "errors.internal",
        status: 0,
        fieldNames: [],
      };
    }
  }

  const moderationBase = "/api/v1/admin/moderation";
  const casePath = (caseId: string) =>
    `${moderationBase}/cases/${encodeURIComponent(caseId)}`;
  return {
    listModerationCases: async (query = {}) =>
      mapResult(
        await request<ApiCasePage>(
          `${moderationBase}/cases${queryString({
            status: query.status,
            priority: query.priority,
            target_type: query.targetType,
            cursor: query.cursor,
            limit: query.limit,
          })}`,
        ),
        (page) => ({
          items: page.items.map(caseSummary),
          next_cursor: page.next_cursor,
        }),
      ),
    getModerationCase: async (caseId) =>
      mapResult(await request<ApiCaseDetail>(casePath(caseId)), caseDetail),
    searchModerationTargets: async (query, targetType) =>
      mapResult(
        await request<ApiTargetPage>(
          `${moderationBase}/targets${queryString({
            query,
            target_type: targetType,
          })}`,
        ),
        (page) => ({
          items: page.items.map(targetSummary),
          next_cursor: page.next_cursor ?? null,
        }),
      ),
    submitModerationAction: async (caseId, action, reason, idempotencyKey) =>
      mapResult(
        await request<ApiActionResponse>(`${casePath(caseId)}/actions`, {
          method: "POST",
          body: { action, reason },
          idempotencyKey,
        }),
        caseDetail,
      ),
    transitionModerationCase: async (caseId, action, reason, idempotencyKey) =>
      mapResult(
        await request<ApiWorkflowResponse>(`${casePath(caseId)}/workflow`, {
          method: "POST",
          body: { action, reason },
          idempotencyKey,
        }),
        caseDetail,
      ),
    listAuditEvents: async (query = {}) =>
      mapResult(
        await request<ApiAuditPage>(
          `/api/v1/admin/audit-events${queryString({
            target_type: query.targetType,
            target_id: query.targetId,
            cursor: query.cursor,
            limit: query.limit,
          })}`,
        ),
        (page) => ({ items: page.items, next_cursor: page.next_cursor }),
      ),
  };
}
