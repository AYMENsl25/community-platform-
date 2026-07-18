import { globSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  API_MESSAGE_KEYS,
  LOCALE_CODES,
  dictionaries,
  type TranslationKey,
} from "./index";

const identicalValueAllowlist = new Set<TranslationKey>(["brand.name"]);

describe("complete Phase 1 dictionaries", () => {
  it("has exact key parity across all locales", () => {
    const englishKeys = Object.keys(dictionaries.en).sort();
    for (const locale of LOCALE_CODES)
      expect(Object.keys(dictionaries[locale]).sort()).toEqual(englishKeys);
  });
  it("uses localized values outside the explicit narrow allowlist", () => {
    for (const locale of LOCALE_CODES.filter((value) => value !== "en")) {
      for (const key of Object.keys(dictionaries.en) as TranslationKey[]) {
        if (!identicalValueAllowlist.has(key))
          expect(dictionaries[locale][key], `${locale}:${key}`).not.toBe(
            dictionaries.en[key],
          );
      }
    }
  });
  it("catalogs every stable API message key emitted by production Python", () => {
    const apiRoot = new URL("../../../apps/api/src/", import.meta.url);
    const emitted = new Set<string>(
      globSync("**/*.py", { cwd: apiRoot }).flatMap((file) => {
        const source = readFileSync(new URL(file, apiRoot), "utf8");
        return [...source.matchAll(/["'](errors\.[a-z0-9_.]+)["']/gu)]
          .map((match) => match[1])
          .filter((key): key is string => Boolean(key));
      }),
    );
    expect(emitted.size).toBeGreaterThan(10);
    for (const key of emitted) {
      expect(API_MESSAGE_KEYS, key).toContain(key);
      expect(dictionaries.en).toHaveProperty(key);
    }
  });
  it("contains native UTF-8 text instead of mojibake", () => {
    const values = LOCALE_CODES.flatMap((locale) =>
      Object.values(dictionaries[locale]),
    );
    expect(values).toContain("Türkçe");
    expect(values).toContain("Événements");
    expect(values).toContain("العربية");
    expect(values.join(" ")).not.toMatch(/(?:Ãƒ.|Ã‚.|Ã˜.|Ã™.)/u);
  });
});
