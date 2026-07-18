"use client";

import { translate, type LocaleCode } from "@talaqi/translations";
import { ActionLink, Card, Container } from "@talaqi/ui";
import Image from "next/image";
import { useState } from "react";

import { PublicShell } from "@/components/shell/shells";
import { LocaleSelector } from "./locale-selector";

export function LocalizedHome({
  initialLocale,
}: {
  initialLocale: LocaleCode;
}) {
  const [locale, setLocale] = useState(initialLocale);
  return (
    <PublicShell currentHref="/" locale={locale}>
      <section className="tq-home-hero" id="community">
        <Container className="tq-home-grid">
          <div className="tq-home-copy">
            <LocaleSelector locale={locale} onLocaleChange={setLocale} />
            <p className="tq-home-eyebrow">
              {translate(locale, "home.eyebrow")}
            </p>
            <h1>{translate(locale, "home.title")}</h1>
            <p className="tq-home-lead">{translate(locale, "home.lead")}</p>
            <div className="tq-home-actions">
              <ActionLink href="#foundation">
                {translate(locale, "home.primaryAction")}
              </ActionLink>
              <ActionLink href="#about" variant="secondary">
                {translate(locale, "home.secondaryAction")}
              </ActionLink>
            </div>
          </div>
          <Card
            aria-labelledby="foundation-title"
            className="tq-home-preview"
            id="foundation"
          >
            <Image
              alt=""
              className="tq-home-preview__icon"
              height={98}
              src="/brand/talaqi-icon.png"
              unoptimized
              width={95}
            />
            <h2 id="foundation-title">
              {translate(locale, "home.preview.title")}
            </h2>
            <p id="about">{translate(locale, "home.preview.body")}</p>
          </Card>
        </Container>
      </section>
    </PublicShell>
  );
}
