import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@talaqi/ui/styles.css";
import "../components/locale/locale-selector.css";
import "../components/shell/shells.css";
import "./globals.css";

import { getLocaleDirection, translate } from "@talaqi/translations";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export const metadata: Metadata = {
  title: translate("en", "brand.name"),
  description: translate("en", "home.lead"),
  icons: [{ rel: "icon", url: "/brand/talaqi-favicon.png" }],
};

export default async function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const locale = await resolveRequestLocale();
  return (
    <html dir={getLocaleDirection(locale)} lang={locale}>
      <body>{children}</body>
    </html>
  );
}
