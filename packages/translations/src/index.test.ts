import { describe, expect, it } from "vitest";

import {
  LOCALE_CODES,
  dictionaries,
  getLocaleDirection,
  translate,
} from "./index";

describe("supported locale codes", () => {
  it("contains the four approved locales in stable order", () => {
    expect(LOCALE_CODES).toEqual(["en", "tr", "fr", "ar"]);
  });
});

describe("shell translations", () => {
  it("keeps every locale in exact key parity", () => {
    const englishKeys = Object.keys(dictionaries.en).sort();

    for (const locale of LOCALE_CODES) {
      expect(Object.keys(dictionaries[locale]).sort()).toEqual(englishKeys);
    }
  });

  it("provides translated shell navigation labels", () => {
    expect(translate("en", "shell.navigation.primary")).toBe(
      "Primary navigation",
    );
    expect(translate("tr", "shell.navigation.primary")).toBe("Ana gezinme");
    expect(translate("fr", "shell.navigation.primary")).toBe(
      "Navigation principale",
    );
    expect(translate("ar", "shell.navigation.primary")).toBe("التنقل الرئيسي");
  });

  it("uses right-to-left direction for Arabic only", () => {
    expect(getLocaleDirection("ar")).toBe("rtl");
    expect(getLocaleDirection("en")).toBe("ltr");
    expect(getLocaleDirection("tr")).toBe("ltr");
    expect(getLocaleDirection("fr")).toBe("ltr");
  });
});
