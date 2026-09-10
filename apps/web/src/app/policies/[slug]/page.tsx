import { Container } from "@talaqi/ui";
import { notFound } from "next/navigation";
import { PublicShell } from "@/components/shell/shells";
import { resolveRequestLocale } from "@/lib/locale/request-locale";
import { getPolicy, POLICY_SLUGS, type PolicySlug } from "@/lib/policies";

export default async function PolicyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const [{ slug }, locale] = await Promise.all([
    params,
    resolveRequestLocale(),
  ]);
  if (!POLICY_SLUGS.includes(slug as PolicySlug)) notFound();
  const policy = getPolicy(locale, slug as PolicySlug);
  const draftLabel = {
    en: "Legal review required before launch",
    tr: "Yayın öncesi hukuki inceleme gereklidir",
    fr: "Révision juridique requise avant le lancement",
    ar: "المراجعة القانونية مطلوبة قبل الإطلاق",
  }[locale];
  const versionLabel = {
    en: "Version",
    tr: "Sürüm",
    fr: "Version",
    ar: "الإصدار",
  }[locale];
  return (
    <PublicShell currentHref={`/policies/${slug}`} locale={locale}>
      <Container className="tq-policy-page">
        <p>{policy.legalDraft ? draftLabel : null}</p>
        <h1>{policy.title}</h1>
        <p>{policy.summary}</p>
        <ul>
          {policy.points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
        <p>
          <strong>{versionLabel}:</strong> {policy.version}
        </p>
      </Container>
    </PublicShell>
  );
}
