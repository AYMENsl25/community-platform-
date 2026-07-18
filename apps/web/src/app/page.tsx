import { LocalizedHome } from "@/components/locale/localized-home";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export default async function Home() {
  return <LocalizedHome initialLocale={await resolveRequestLocale()} />;
}
