import { DiscoveryLoading } from "@/components/discovery/result-states";
import { translate } from "@talaqi/translations";
import { resolveRequestLocale } from "@/lib/locale/request-locale";
export default async function Loading() {
  const locale = await resolveRequestLocale();
  return (
    <DiscoveryLoading
      labels={{ loading: translate(locale, "states.loading") }}
      locale={locale}
    />
  );
}
