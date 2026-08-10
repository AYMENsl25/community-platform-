import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "@talaqi/ui/styles.css";
import "../components/admin/admin.css";
import "../components/locale/locale-selector.css";
import "../components/organizer/organizer.css";
import "../components/shell/shells.css";
import "./globals.css";

import { getLocaleDirection, translate } from "@talaqi/translations";
import { LocaleProvider } from "@/lib/locale/locale-context";
import { resolveRequestLocale } from "@/lib/locale/request-locale";
import { PwaManager } from "@/components/pwa/pwa-manager";

export const metadata: Metadata = {
  title: translate("en", "brand.name"),
  description: translate("en", "home.lead"),
  icons: [{ rel: "icon", url: "/brand/talaqi-favicon.png" }],
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = { themeColor: "#166b5c" };

export default async function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const locale = await resolveRequestLocale();
  return (
    <html dir={getLocaleDirection(locale)} lang={locale}>
      <body>
        <LocaleProvider initialLocale={locale}>
          {children}
          <PwaManager />
        </LocaleProvider>
      </body>
    </html>
  );
}
