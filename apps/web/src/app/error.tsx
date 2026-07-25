"use client";
import { DiscoveryError } from "@/components/discovery/result-states";
import { useLocale } from "@/lib/locale/locale-context";
export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { locale, t } = useLocale();
  return (
    <DiscoveryError
      labels={{ error: t("states.error"), retry: t("states.retry") }}
      locale={locale}
      onRetry={reset}
    />
  );
}
