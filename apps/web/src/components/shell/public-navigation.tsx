"use client";

import {
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";
import { useEffect, useState } from "react";

type Item = { href: string; label: TranslationKey };

export function PublicNavigation({
  currentHref,
  items,
  locale,
}: {
  currentHref: string;
  items: Item[];
  locale: LocaleCode;
}) {
  const [open, setOpen] = useState(false);
  const menuLabel = { en: "Menu", tr: "Menü", fr: "Menu", ar: "القائمة" }[
    locale
  ];
  useEffect(() => {
    if (!open) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [open]);
  return (
    <div className="tq-public-menu">
      <button
        aria-controls="public-navigation"
        aria-expanded={open}
        className="tq-public-menu__trigger"
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        {menuLabel}
      </button>
      <nav
        aria-label={translate(locale, "shell.navigation.primary")}
        className="tq-navigation tq-navigation--public"
        data-open={open || undefined}
        id="public-navigation"
      >
        <ul>
          {items.map((item) => (
            <li key={item.href}>
              <a
                aria-current={currentHref === item.href ? "page" : undefined}
                href={item.href}
                onClick={() => setOpen(false)}
              >
                {translate(locale, item.label)}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
