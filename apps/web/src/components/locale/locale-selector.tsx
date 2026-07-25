"use client";

import { LOCALE_CODES, type LocaleCode } from "@talaqi/translations";

import { useLocale } from "@/lib/locale/locale-context";

export function LocaleSelector() {
  const { locale, setLocale, t } = useLocale();
  return (
    <label className="tq-locale-selector">
      <span>{t("locale.label")}</span>
      <select
        aria-label={t("a11y.localeSelector")}
        onChange={(event) => setLocale(event.currentTarget.value as LocaleCode)}
        value={locale}
      >
        {LOCALE_CODES.map((code) => (
          <option key={code} value={code}>
            {t(`locale.${code}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
