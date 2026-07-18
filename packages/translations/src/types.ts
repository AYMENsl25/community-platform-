export const LOCALE_CODES = ["en", "tr", "fr", "ar"] as const;
export type LocaleCode = (typeof LOCALE_CODES)[number];

export function getLocaleDirection(locale: LocaleCode): "ltr" | "rtl" {
  return locale === "ar" ? "rtl" : "ltr";
}
