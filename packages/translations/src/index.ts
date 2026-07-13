export const LOCALE_CODES = ["en", "tr", "fr", "ar"] as const;
export type LocaleCode = (typeof LOCALE_CODES)[number];
