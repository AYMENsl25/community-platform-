import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ErrorPage from "./error";
import { LocaleProvider } from "@/lib/locale/locale-context";

describe("route error state", () => {
  it("hides raw failures and offers recovery", () => {
    const reset = vi.fn();
    const { container } = render(
      <LocaleProvider initialLocale="en">
        <ErrorPage error={new Error("database secret")} reset={reset} />
      </LocaleProvider>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("database secret");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
