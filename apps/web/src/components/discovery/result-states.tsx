"use client";

import { translate, type LocaleCode } from "@talaqi/translations";
import "./discovery.css";

export type ResultStateLabels = {
  empty: string;
  error: string;
  loading: string;
  retry: string;
};

function defaultLabels(locale: LocaleCode): ResultStateLabels {
  return {
    empty: translate(locale, "states.empty"),
    error: translate(locale, "states.error"),
    loading: translate(locale, "a11y.loadingResults"),
    retry: translate(locale, "states.retry"),
  };
}

export function DiscoveryLoading({
  locale,
  labels,
}: {
  locale: LocaleCode;
  labels?: Partial<ResultStateLabels>;
}) {
  return (
    <p className="tq-result-state" role="status">
      {{ ...defaultLabels(locale), ...labels }.loading}
    </p>
  );
}

export function DiscoveryEmpty({
  locale,
  labels,
}: {
  locale: LocaleCode;
  labels?: Partial<ResultStateLabels>;
}) {
  return (
    <p className="tq-result-state" role="status">
      {{ ...defaultLabels(locale), ...labels }.empty}
    </p>
  );
}

export function DiscoveryError({
  error,
  locale,
  labels: overrides,
  onRetry,
}: {
  error?: unknown;
  locale: LocaleCode;
  labels?: Partial<ResultStateLabels>;
  onRetry?: () => void;
}) {
  const labels = { ...defaultLabels(locale), ...overrides };
  void error;
  return (
    <div className="tq-result-state tq-result-state--error" role="alert">
      <p>{labels.error}</p>
      {onRetry ? (
        <button
          className="tq-discovery-control"
          onClick={onRetry}
          type="button"
        >
          {labels.retry}
        </button>
      ) : null}
    </div>
  );
}
