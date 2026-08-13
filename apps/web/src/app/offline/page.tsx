import { translate } from "@talaqi/translations";
import { Container } from "@talaqi/ui";
import { PublicShell } from "@/components/shell/shells";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export default async function OfflinePage() {
  const locale = await resolveRequestLocale();
  return (
    <PublicShell currentHref="" locale={locale}>
      <Container className="tq-offline-shell">
        <h1>{translate(locale, "pwa.offline.title")}</h1>
        <p>{translate(locale, "pwa.offline.body")}</p>
        <a className="tq-action-link" href="/explore">
          {translate(locale, "pwa.offline.retry")}
        </a>
      </Container>
    </PublicShell>
  );
}
