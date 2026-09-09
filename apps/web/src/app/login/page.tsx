import { LoginForm } from "@/components/auth/login-form";
import { PublicShell } from "@/components/shell/shells";
import { resolveRequestLocale } from "@/lib/locale/request-locale";
import { safeReturnPath } from "@/lib/navigation/safe-return-path";
import { LOCALE_CODES, translate, type LocaleCode } from "@talaqi/translations";
import { Card, Container } from "@talaqi/ui";
import type { Metadata } from "next";

export const metadata: Metadata = {
  robots: { follow: false, index: false },
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ locale?: string; returnTo?: string }>;
}) {
  const [requestLocale, query] = await Promise.all([
    resolveRequestLocale(),
    searchParams,
  ]);
  const locale = LOCALE_CODES.includes(query.locale as LocaleCode)
    ? (query.locale as LocaleCode)
    : requestLocale;
  const returnTo = safeReturnPath(query.returnTo);

  return (
    <PublicShell currentHref="/login" locale={locale}>
      <Container>
        <section className="tq-auth-page" aria-labelledby="login-title">
          <Card>
            <h1 id="login-title">{translate(locale, "auth.login.title")}</h1>
            <p>{translate(locale, "auth.login.description")}</p>
            <LoginForm locale={locale} returnTo={returnTo} />
          </Card>
        </section>
      </Container>
    </PublicShell>
  );
}
