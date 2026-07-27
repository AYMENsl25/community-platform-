"use client";

import type { TranslationKey } from "@talaqi/translations";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import {
  createAdminClient,
  type AdminResult,
  type ModerationAction,
  type ModerationCaseDetail,
} from "@/lib/api/admin-client";
import { useLocale } from "@/lib/locale/locale-context";

type Feedback = { key: TranslationKey; requestId?: string };

function csrfToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const value = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("talaqi_csrf="));
  return value
    ? decodeURIComponent(value.slice("talaqi_csrf=".length))
    : undefined;
}

export function AdminCaseDetail({
  initialCase,
  initialError,
}: {
  initialCase?: ModerationCaseDetail;
  initialError?: Feedback;
}) {
  const { t } = useLocale();
  const [moderationCase, setModerationCase] = useState(initialCase);
  const [feedback, setFeedback] = useState<Feedback | undefined>(initialError);
  const [notice, setNotice] = useState(false);
  const [action, setAction] = useState<ModerationAction>();
  const [reason, setReason] = useState("");
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const triggerRef = useRef<HTMLElement | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const dialogRef = useRef<HTMLFormElement>(null);
  const idempotencyRef = useRef<string | undefined>(undefined);
  const client = useMemo(
    () => createAdminClient({ baseUrl: "/api/admin", csrfToken: csrfToken() }),
    [],
  );

  useEffect(() => {
    if (action) reasonRef.current?.focus();
  }, [action]);

  function fail(result: Extract<AdminResult<unknown>, { ok: false }>) {
    setNotice(false);
    setFeedback({
      key: result.key,
      ...(result.requestId ? { requestId: result.requestId } : {}),
    });
  }

  function openAction(nextAction: ModerationAction, trigger: HTMLElement) {
    triggerRef.current = trigger;
    idempotencyRef.current = crypto.randomUUID();
    setReason("");
    setUnderstood(false);
    setAction(nextAction);
  }

  function closeDialog() {
    if (busy) return;
    setAction(undefined);
    idempotencyRef.current = undefined;
    requestAnimationFrame(() => triggerRef.current?.focus());
  }

  function onDialogKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeDialog();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        "textarea:not([disabled]), input:not([disabled]), button:not([disabled])",
      ) ?? [],
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!moderationCase || !action || !understood || !idempotencyRef.current)
      return;
    setBusy(true);
    setFeedback(undefined);
    const result = await client.submitModerationAction(
      moderationCase.id,
      action,
      reason,
      idempotencyRef.current,
    );
    setBusy(false);
    if (!result.ok) return fail(result);
    setModerationCase(result.data);
    setNotice(true);
    setAction(undefined);
    idempotencyRef.current = undefined;
    requestAnimationFrame(() =>
      document.querySelector<HTMLElement>("[data-admin-case-title]")?.focus(),
    );
  }

  if (!moderationCase)
    return (
      <div className="tq-admin-alert" role="alert">
        {feedback ? t(feedback.key) : t("errors.not_found")}
      </div>
    );
  const actions =
    (
      moderationCase as ModerationCaseDetail & {
        available_actions?: ModerationAction[];
      }
    ).available_actions ?? [];

  return (
    <section className="tq-admin" aria-labelledby="admin-case-title">
      <header className="tq-admin__header">
        <div>
          <h1 data-admin-case-title id="admin-case-title" tabIndex={-1}>
            {t("admin.case.title")}
          </h1>
          <p>{moderationCase.target.display_name}</p>
        </div>
        <span className="tq-admin-badge">
          {t(`admin.priority.${moderationCase.priority}` as TranslationKey)}
        </span>
      </header>
      {moderationCase.is_emergency ? (
        <aside className="tq-admin-emergency" role="alert">
          <strong>{t("admin.emergency.title")}</strong>
          <p>{t("admin.emergency.notice")}</p>
        </aside>
      ) : null}
      {feedback ? (
        <div className="tq-admin-alert" role="alert">
          <p>{t(feedback.key)}</p>
          {feedback.requestId ? <code>{feedback.requestId}</code> : null}
        </div>
      ) : null}
      {notice ? (
        <p className="tq-admin-notice" role="status">
          {t("admin.action.completed")}
        </p>
      ) : null}
      <section className="tq-admin-card" aria-labelledby="case-summary-title">
        <h2 id="case-summary-title">{t("admin.case.summary")}</h2>
        <dl>
          <dt>{t("admin.case.category")}</dt>
          <dd>
            {t(`admin.category.${moderationCase.category}` as TranslationKey)}
          </dd>
          <dt>{t("admin.case.status")}</dt>
          <dd>
            {t(`admin.status.${moderationCase.status}` as TranslationKey)}
          </dd>
        </dl>
        {actions.length ? (
          <div className="tq-admin-actions">
            {actions.map((item) => (
              <button
                className={
                  item === "restore" ? undefined : "tq-admin-button--danger"
                }
                data-action={item}
                key={item}
                onClick={(event) => openAction(item, event.currentTarget)}
                type="button"
              >
                {t(`admin.action.${item}` as TranslationKey)}
              </button>
            ))}
          </div>
        ) : null}
      </section>
      <section className="tq-admin-card" aria-labelledby="action-history-title">
        <h2 id="action-history-title">{t("admin.audit.history")}</h2>
        {moderationCase.action_history.length ? (
          <ul className="tq-admin-history">
            {moderationCase.action_history.map((record) => (
              <li key={record.id}>
                <strong>
                  {t(`admin.action.${record.action}` as TranslationKey)}
                </strong>
                <p>{record.reason}</p>
                <small>
                  {record.actor_user_id ?? "system"}
                  {" — "}
                  {record.created_at}
                </small>
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("admin.audit.empty")}</p>
        )}
      </section>
      {action ? (
        <div
          aria-labelledby="admin-dialog-title"
          aria-modal="true"
          className="tq-admin-dialog-backdrop"
          onKeyDown={onDialogKeyDown}
          role="alertdialog"
        >
          <form className="tq-admin-dialog" onSubmit={confirm} ref={dialogRef}>
            <h2 id="admin-dialog-title">
              {t(`admin.dialog.${action}` as TranslationKey)}
            </h2>
            <p>{moderationCase.target.display_name}</p>
            <p>{t("admin.dialog.warning")}</p>
            <label>
              {t("admin.dialog.reason")}
              <textarea
                minLength={3}
                onChange={(event) => setReason(event.target.value)}
                ref={reasonRef}
                required
                value={reason}
              />
            </label>
            <label>
              <input
                checked={understood}
                onChange={(event) => setUnderstood(event.target.checked)}
                required
                type="checkbox"
              />
              {t("admin.dialog.understand")}
            </label>
            <div className="tq-admin-actions">
              <button disabled={busy} onClick={closeDialog} type="button">
                {t("common.cancel")}
              </button>
              <button
                className="tq-admin-button--danger"
                disabled={busy || !understood || reason.trim().length < 3}
                type="submit"
              >
                {t(`admin.action.${action}` as TranslationKey)}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  );
}
