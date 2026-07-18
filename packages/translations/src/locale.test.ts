// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { dictionaries } from "./catalog";
import {
  applyDocumentLocale,
  getLocaleDirection,
  normalizeLocale,
  resolveLocale,
  resolveMessage,
} from "./locale";

describe("locale resolution", () => {
  it("uses profile, explicit, weighted request, region, then English", () => {
    expect(
      resolveLocale({
        profile: "ar",
        explicit: "tr",
        acceptLanguage: "fr;q=1",
        regionalDefault: "en",
      }),
    ).toBe("ar");
    expect(
      resolveLocale({
        explicit: "tr-TR",
        acceptLanguage: "fr;q=1",
        regionalDefault: "ar",
      }),
    ).toBe("tr");
    expect(
      resolveLocale({
        acceptLanguage: "de;q=1, fr-FR;q=.7, ar-DZ;q=.9, tr;q=0",
        regionalDefault: "tr",
      }),
    ).toBe("ar");
    expect(resolveLocale({ regionalDefault: "fr-FR" })).toBe("fr");
    expect(resolveLocale({ acceptLanguage: "*;q=1, de;q=.8" })).toBe("en");
  });
  it("normalizes supported language subtags only", () => {
    expect(normalizeLocale("AR-dz")).toBe("ar");
    expect(normalizeLocale(" tr_TR ")).toBeUndefined();
    expect(normalizeLocale("de-DE")).toBeUndefined();
  });
});

describe("safe messages and document state", () => {
  it("falls back to the localized unknown error without exposing a raw key", () => {
    expect(resolveMessage("fr", "errors.not_found")).toBe(
      dictionaries.fr["errors.not_found"],
    );
    expect(resolveMessage("fr", "private.internal.secret")).toBe(
      dictionaries.fr["errors.unknown"],
    );
    expect(resolveMessage("fr", "private.internal.secret")).not.toContain(
      "private.internal.secret",
    );
  });
  it("updates html language and direction synchronously", () => {
    applyDocumentLocale("ar");
    expect(document.documentElement.lang).toBe("ar");
    expect(document.documentElement.dir).toBe("rtl");
    applyDocumentLocale("tr");
    expect(document.documentElement.lang).toBe("tr");
    expect(document.documentElement.dir).toBe("ltr");
    expect(getLocaleDirection("ar")).toBe("rtl");
  });
});
