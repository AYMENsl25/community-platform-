import { describe, expect, it } from "vitest";

import { LOCALE_CODES } from "./index";

describe("supported locale codes", () => {
  it("contains the four approved locales in stable order", () => {
    expect(LOCALE_CODES).toEqual(["en", "tr", "fr", "ar"]);
  });
});
