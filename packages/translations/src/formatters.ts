import type { LocaleCode } from "./types";

type PluralMessages = Partial<Record<Intl.LDMLPluralRule, string>> & {
  other: string;
};

export function formatDate(
  value: Date | number | string,
  locale: LocaleCode,
  timeZone: string,
): string {
  if (!timeZone)
    throw new TypeError("formatDate requires a valid IANA time zone");
  try {
    new Intl.DateTimeFormat(locale, { timeZone }).format(0);
  } catch {
    throw new TypeError("formatDate requires a valid IANA time zone");
  }
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "short",
    timeZone,
    year: "numeric",
  }).format(new Date(value));
}

export function formatNumber(value: number, locale: LocaleCode): string {
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
    useGrouping: true,
  }).format(value);
}

export function formatCurrency(
  value: number,
  locale: LocaleCode,
  currency: string,
): string {
  if (currency !== "TRY" && currency !== "DZD")
    throw new TypeError("formatCurrency requires a supported beta currency");
  return new Intl.NumberFormat(locale, {
    currency,
    currencyDisplay: "symbol",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    style: "currency",
    useGrouping: true,
  }).format(value);
}

export function formatPlural(
  count: number,
  locale: LocaleCode,
  messages: PluralMessages,
): string {
  const category = new Intl.PluralRules(locale).select(count);
  return (messages[category] ?? messages.other).replaceAll(
    "{count}",
    formatNumber(count, locale),
  );
}
