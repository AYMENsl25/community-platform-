"use client";

import {
  applyDocumentLocale,
  LOCALE_CODES,
  translate,
  type LocaleCode,
} from "@talaqi/translations";

export function LocaleSelector({
  locale,
  onLocaleChange,
}: {
  locale: LocaleCode;
  onLocaleChange: (locale: LocaleCode) => void;
}) {
  function selectLocale(nextLocale: LocaleCode) {
    applyDocumentLocale(nextLocale);
    document.cookie = `talaqi_locale=${nextLocale}; Path=/; Max-Age=31536000; SameSite=Lax`;
    onLocaleChange(nextLocale);
  }
  return (
    <label className="tq-locale-selector">
      <span>{translate(locale, "locale.label")}</span>
      <select
        aria-label={translate(locale, "a11y.localeSelector")}
        onChange={(event) =>
          selectLocale(event.currentTarget.value as LocaleCode)
        }
        value={locale}
      >
        {LOCALE_CODES.map((code) => (
          <option key={code} value={code}>
            {translate(locale, `locale.${code}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
