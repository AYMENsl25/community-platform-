"use client";

import { useMemo, useState } from "react";

import {
  createAdminClient,
  type FeatureFlag,
  type OperationalOutboxEvent,
  type RegionPolicy,
} from "@/lib/api/admin-client";
import { useLocale } from "@/lib/locale/locale-context";

function csrfToken() {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("talaqi_csrf="))
    ?.slice("talaqi_csrf=".length);
}
function operationKey() {
  return crypto.randomUUID() + crypto.randomUUID();
}

export function AdminOperations({
  initialFlags,
  initialPolicy,
  initialOutbox,
}: {
  initialFlags: FeatureFlag[];
  initialPolicy: RegionPolicy;
  initialOutbox: OperationalOutboxEvent[];
}) {
  const { t } = useLocale();
  const client = useMemo(
    () => createAdminClient({ baseUrl: "/api/admin", csrfToken: csrfToken() }),
    [],
  );
  const [flags, setFlags] = useState(initialFlags);
  const [policy, setPolicy] = useState(initialPolicy);
  const [outbox, setOutbox] = useState(initialOutbox);
  const [reason, setReason] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function previewFlag(flag: FeatureFlag) {
    const result = await client.previewFeatureFlag(
      flag.key,
      !flag.enabled,
      flag.revision,
      reason,
    );
    if (result.ok) {
      setPreview(flag.key);
      setFeedback(t("admin.operations.previewReady"));
    } else setFeedback(t(result.key));
  }
  async function applyFlag(flag: FeatureFlag) {
    if (preview !== flag.key) return;
    const result = await client.updateFeatureFlag(
      flag.key,
      !flag.enabled,
      flag.revision,
      reason,
      operationKey(),
    );
    if (result.ok) {
      setFlags((items) =>
        items.map((item) =>
          item.key === flag.key ? result.data.setting : item,
        ),
      );
      setPreview(null);
      setFeedback(t("admin.operations.updated"));
    } else setFeedback(t(result.key));
  }
  async function previewPolicy() {
    const result = await client.previewRegionPolicy(policy.country_code, {
      revision: policy.revision,
      reason,
      club_limit: policy.club_limit + 1,
    });
    if (result.ok) {
      setPreview("policy");
      setFeedback(t("admin.operations.previewReady"));
    } else setFeedback(t(result.key));
  }
  async function applyPolicy() {
    if (preview !== "policy") return;
    const result = await client.updateRegionPolicy(
      policy.country_code,
      { revision: policy.revision, reason, club_limit: policy.club_limit + 1 },
      operationKey(),
    );
    if (result.ok) {
      setPolicy(result.data.policy);
      setPreview(null);
      setFeedback(t("admin.operations.updated"));
    } else setFeedback(t(result.key));
  }
  async function retry(event: OperationalOutboxEvent) {
    const result = await client.retryOutboxEvent(
      event.id,
      reason,
      operationKey(),
    );
    if (result.ok) {
      setOutbox((items) =>
        items.map((item) => (item.id === event.id ? result.data.event : item)),
      );
      setFeedback(t("admin.operations.retried"));
    } else setFeedback(t(result.key));
  }

  return (
    <section className="tq-admin" aria-labelledby="operations-title">
      <header className="tq-admin__header">
        <div>
          <h1 id="operations-title">{t("admin.operations.title")}</h1>
          <p>{t("admin.operations.lead")}</p>
        </div>
      </header>
      {feedback ? (
        <p role="status" className="tq-admin-notice">
          {feedback}
        </p>
      ) : null}
      <label>
        {t("admin.operations.reason")}
        <textarea
          value={reason}
          onChange={(event) => {
            setReason(event.target.value);
            setPreview(null);
          }}
        />
      </label>
      <div className="tq-admin__grid">
        <article className="tq-admin-card">
          <h2>{t("admin.operations.flags")}</h2>
          <ul className="tq-admin-list">
            {flags.map((flag) => (
              <li key={flag.key}>
                <strong>{flag.key}</strong>{" "}
                <span className="tq-admin-badge">
                  {flag.enabled
                    ? t("admin.operations.enabled")
                    : t("admin.operations.disabled")}
                </span>
                <div className="tq-admin-actions">
                  <button
                    disabled={reason.trim().length < 3}
                    onClick={() => void previewFlag(flag)}
                  >
                    {t("admin.operations.preview")}
                  </button>
                  <button
                    disabled={preview !== flag.key}
                    onClick={() => void applyFlag(flag)}
                  >
                    {t("admin.operations.apply")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </article>
        <article className="tq-admin-card">
          <h2>{t("admin.operations.region")}</h2>
          <p>
            {policy.country_code}: {t("admin.operations.clubLimit")}{" "}
            {policy.club_limit}
          </p>
          <div className="tq-admin-actions">
            <button
              disabled={reason.trim().length < 3}
              onClick={() => void previewPolicy()}
            >
              {t("admin.operations.preview")}
            </button>
            <button
              disabled={preview !== "policy"}
              onClick={() => void applyPolicy()}
            >
              {t("admin.operations.apply")}
            </button>
          </div>
        </article>
        <article className="tq-admin-card">
          <h2>{t("admin.operations.outbox")}</h2>
          <ul className="tq-admin-list">
            {outbox.map((event) => (
              <li key={event.id}>
                <strong>{event.event_type}</strong>{" "}
                <span className="tq-admin-badge">{event.status}</span>
                <p>
                  {t("admin.operations.attempts")}: {event.attempt_count}
                </p>
                {event.last_error_code ? (
                  <code>{event.last_error_code}</code>
                ) : null}
                {event.status === "permanent_failed" ? (
                  <button
                    disabled={reason.trim().length < 3}
                    onClick={() => void retry(event)}
                  >
                    {t("admin.operations.retry")}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}
