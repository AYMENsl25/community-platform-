"use client";

import type { components } from "@talaqi/api-client";
import {
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";
import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import "./discovery.css";

type Metadata = components["schemas"]["DiscoveryMetadataResponse"];
export type DiscoveryFilters = Partial<
  Record<
    | "category"
    | "city"
    | "country"
    | "date_from"
    | "date_to"
    | "price"
    | "search",
    string | null
  >
>;
export type FilterDrawerLabels = {
  apply: string;
  category: string;
  city: string;
  close: string;
  country: string;
  dateFrom: string;
  dateTo: string;
  filters: string;
  open: string;
  price: string;
  search: string;
  any: string;
  clear: string;
};

function defaultLabels(locale: LocaleCode): FilterDrawerLabels {
  return {
    any: "—",
    clear: translate(locale, "filters.clear"),
    apply: translate(locale, "filters.apply"),
    category: translate(locale, "filters.category"),
    city: translate(locale, "filters.city"),
    close: translate(locale, "filters.close"),
    country: translate(locale, "filters.country"),
    dateFrom: translate(locale, "filters.date"),
    dateTo: translate(locale, "filters.date"),
    filters: translate(locale, "filters.title"),
    open: translate(locale, "filters.open"),
    price: translate(locale, "filters.price"),
    search: translate(locale, "filters.search"),
  };
}

function Fields({
  filters,
  labels,
  locale,
  metadata,
}: {
  filters: DiscoveryFilters;
  labels: FilterDrawerLabels;
  locale: LocaleCode;
  metadata: Metadata;
}) {
  const named = (item: Record<string, string>, fallback: string) =>
    item.name_key
      ? translate(locale, item.name_key as TranslationKey)
      : humanize(fallback);
  return (
    <>
      <label>
        {labels.search}
        <input
          autoComplete="off"
          defaultValue={filters.search ?? undefined}
          name="search"
          placeholder={labels.search}
          type="search"
        />
      </label>
      <label>
        {labels.country}
        <select defaultValue={filters.country ?? ""} name="country">
          <option value="">{labels.any}</option>
          {metadata.countries.map((item) => (
            <option key={item.code} value={item.code}>
              {named(item, item.code ?? "")}
            </option>
          ))}
        </select>
      </label>
      <label>
        {labels.city}
        <select defaultValue={filters.city ?? ""} name="city">
          <option value="">{labels.any}</option>
          {metadata.cities.map((item) => (
            <option key={item.slug} value={item.slug}>
              {named(item, item.slug ?? "")}
            </option>
          ))}
        </select>
      </label>
      <label>
        {labels.category}
        <select defaultValue={filters.category ?? ""} name="category">
          <option value="">{labels.any}</option>
          {metadata.categories.map((item) => (
            <option key={item.slug} value={item.slug}>
              {named(item, item.slug ?? "")}
            </option>
          ))}
        </select>
      </label>
      <label>
        {labels.dateFrom}
        <input
          defaultValue={filters.date_from ?? undefined}
          name="date_from"
          type="date"
        />
      </label>
      <label>
        {labels.dateTo}
        <input
          defaultValue={filters.date_to ?? undefined}
          name="date_to"
          type="date"
        />
      </label>
      <label>
        {labels.price}
        <select defaultValue={filters.price ?? ""} name="price">
          <option value="">{labels.any}</option>
          {metadata.price_types.map((price) => (
            <option key={price} value={price}>
              {translate(
                locale,
                price === "free" ? "filters.free" : "filters.cash",
              )}
            </option>
          ))}
        </select>
      </label>
      <button className="tq-discovery-control" type="submit">
        {labels.apply}
      </button>
    </>
  );
}

export function FilterDrawer({
  filters,
  labels: overrides,
  locale,
  metadata,
}: {
  filters: DiscoveryFilters;
  labels?: Partial<FilterDrawerLabels>;
  locale: LocaleCode;
  metadata: Metadata;
}) {
  const labels = { ...defaultLabels(locale), ...overrides };
  const [open, setOpen] = useState(false);
  const activeCount = Object.values(filters).filter(Boolean).length;
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const close = () => {
    triggerRef.current?.focus();
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("keydown", escape);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  const trapFocus = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab") return;
    const controls = dialogRef.current?.querySelectorAll<HTMLElement>(
      "button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href]",
    );
    if (!controls?.length) return;
    const first = controls[0],
      last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  };

  return (
    <div className="tq-filter-drawer">
      <button
        aria-controls="discovery-filters"
        aria-expanded={open}
        className="tq-discovery-control"
        onClick={() => setOpen(true)}
        ref={triggerRef}
        type="button"
      >
        {labels.open}
        {activeCount ? <span aria-hidden="true"> ({activeCount})</span> : null}
      </button>
      <form
        action="/explore"
        aria-hidden={open || undefined}
        aria-label={labels.filters}
        className="tq-filter-form tq-filter-form--fallback"
        method="get"
      >
        <Fields
          filters={filters}
          labels={labels}
          locale={locale}
          metadata={metadata}
        />
      </form>
      {open ? (
        <div
          className="tq-filter-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) close();
          }}
        >
          <div
            aria-labelledby="discovery-filters-title"
            aria-modal="true"
            className="tq-filter-dialog"
            id="discovery-filters"
            onKeyDown={trapFocus}
            ref={dialogRef}
            role="dialog"
          >
            <header className="tq-filter-dialog__header">
              <div>
                <h2 id="discovery-filters-title">{labels.filters}</h2>
                {activeCount ? <p>{activeCount}</p> : null}
              </div>
              <button
                aria-label={labels.close}
                className="tq-discovery-control tq-filter-dialog__close"
                onClick={close}
                ref={closeRef}
                type="button"
              >
                {String.fromCharCode(215)}
              </button>
            </header>
            <form action="/explore" method="get">
              <a className="tq-filter-dialog__clear" href="/explore">
                {labels.clear}
              </a>
              <Fields
                filters={filters}
                labels={labels}
                locale={locale}
                metadata={metadata}
              />
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function humanize(value: string): string {
  return value
    .replaceAll("-", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
