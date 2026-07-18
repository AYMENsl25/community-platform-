import { dictionaries } from "./catalog";
import type { TranslationKey } from "./dictionaries/en";
import { getLocaleDirection, LOCALE_CODES, type LocaleCode } from "./types";

export function normalizeLocale(value?: string | null): LocaleCode | undefined {
  if (!value || !/^[A-Za-z]{2}(?:-[A-Za-z0-9]{2,8})*$/.test(value.trim()))
    return undefined;
  const primary = (value.trim().split("-", 1)[0] ?? "").toLowerCase();
  return LOCALE_CODES.find((locale) => locale === primary);
}

function requestLocale(header?: string | null): LocaleCode | undefined {
  return (header ?? "")
    .split(",")
    .map((entry, position) => {
      const [range, ...parameters] = entry.trim().split(";");
      const locale = normalizeLocale(range);
      let quality = 1;
      if (parameters.length > 1) return undefined;
      if (parameters.length === 1) {
        const match = /^q=(0(?:\.\d{0,3})?|1(?:\.0{0,3})?|\.\d{1,3})$/i.exec(
          (parameters[0] ?? "").trim(),
        );
        if (!match) return undefined;
        quality = Number(match[1]);
      }
      return locale && quality > 0 ? { locale, position, quality } : undefined;
    })
    .filter(
      (
        item,
      ): item is { locale: LocaleCode; position: number; quality: number } =>
        Boolean(item),
    )
    .sort((a, b) => b.quality - a.quality || a.position - b.position)[0]
    ?.locale;
}

export function resolveLocale(options: {
  profile?: string | null;
  explicit?: string | null;
  acceptLanguage?: string | null;
  regionalDefault?: string | null;
}): LocaleCode {
  return (
    normalizeLocale(options.profile) ??
    normalizeLocale(options.explicit) ??
    requestLocale(options.acceptLanguage) ??
    normalizeLocale(options.regionalDefault) ??
    "en"
  );
}

export function resolveMessage(locale: LocaleCode, key: string): string {
  return Object.prototype.hasOwnProperty.call(dictionaries.en, key)
    ? dictionaries[locale][key as TranslationKey]
    : dictionaries[locale]["errors.unknown"];
}

export function applyDocumentLocale(locale: LocaleCode): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = getLocaleDirection(locale);
}

export { getLocaleDirection };
