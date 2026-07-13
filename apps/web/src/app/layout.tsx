import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@talaqi/ui/styles.css";
import "../components/shell/shells.css";
import "./globals.css";

import { translate } from "@talaqi/translations";

export const metadata: Metadata = {
  title: translate("en", "brand.name"),
  description: translate("en", "home.lead"),
  icons: [{ rel: "icon", url: "/brand/talaqi-favicon.png" }],
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
