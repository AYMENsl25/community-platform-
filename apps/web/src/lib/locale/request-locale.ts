import { resolveLocale, type LocaleCode } from "@talaqi/translations";
import { cookies, headers } from "next/headers";

export async function resolveRequestLocale(): Promise<LocaleCode> {
  const [cookieStore, headerStore] = await Promise.all([cookies(), headers()]);
  return resolveLocale({
    explicit: cookieStore.get("talaqi_locale")?.value,
    acceptLanguage: headerStore.get("accept-language"),
  });
}
