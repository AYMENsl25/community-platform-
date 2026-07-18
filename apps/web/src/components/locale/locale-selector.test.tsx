import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LocaleSelector } from "./locale-selector";

describe("LocaleSelector", () => {
  it("updates direction, persists, and reports the explicit choice immediately", () => {
    const onLocaleChange = vi.fn();
    render(<LocaleSelector locale="en" onLocaleChange={onLocaleChange} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "ar" } });
    expect(document.documentElement).toHaveAttribute("lang", "ar");
    expect(document.documentElement).toHaveAttribute("dir", "rtl");
    expect(document.cookie).toContain("talaqi_locale=ar");
    expect(onLocaleChange).toHaveBeenCalledWith("ar");
  });
});
