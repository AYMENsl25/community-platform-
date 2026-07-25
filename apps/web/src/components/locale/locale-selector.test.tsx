import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LocaleProvider } from "@/lib/locale/locale-context";
import { LocaleSelector } from "./locale-selector";

describe("LocaleSelector", () => {
  it("updates direction and persists the explicit choice immediately", () => {
    render(
      <LocaleProvider initialLocale="en">
        <LocaleSelector />
      </LocaleProvider>,
    );
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "ar" },
    });
    expect(document.documentElement).toHaveAttribute("lang", "ar");
    expect(document.documentElement).toHaveAttribute("dir", "rtl");
    expect(document.cookie).toContain("talaqi_locale=ar");
    expect(screen.getByRole("combobox")).toHaveValue("ar");
  });
});
