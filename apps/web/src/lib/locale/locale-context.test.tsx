import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LocaleProvider, useLocale } from "./locale-context";

const refresh = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

function Consumer() {
  const { direction, locale, setLocale, t } = useLocale();
  return (
    <div>
      <output>{`${locale}:${direction}:${t("shell.navigation.explore")}`}</output>
      <button onClick={() => setLocale("ar")} type="button">
        Arabic
      </button>
    </div>
  );
}

describe("LocaleProvider", () => {
  it("persists locale, updates the document, and refreshes server content", () => {
    render(
      <LocaleProvider initialLocale="en">
        <Consumer />
      </LocaleProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Arabic" }));
    expect(document.documentElement).toHaveAttribute("lang", "ar");
    expect(document.documentElement).toHaveAttribute("dir", "rtl");
    expect(document.cookie).toContain("talaqi_locale=ar");
    expect(screen.getByText(/ar:rtl:/)).toBeInTheDocument();
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("rejects use outside the provider", () => {
    expect(() => render(<Consumer />)).toThrow(
      "useLocale must be used within LocaleProvider",
    );
  });
});
