import { translate } from "@talaqi/translations";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  DiscoveryEmpty,
  DiscoveryError,
  DiscoveryLoading,
} from "./result-states";

describe("discovery result states", () => {
  it.each(["en", "tr", "fr", "ar"] as const)(
    "localizes %s defaults",
    (locale) => {
      const { rerender } = render(<DiscoveryLoading locale={locale} />);
      expect(screen.getByRole("status")).toHaveTextContent(
        translate(locale, "a11y.loadingResults"),
      );
      rerender(<DiscoveryEmpty locale={locale} />);
      expect(screen.getByRole("status")).toHaveTextContent(
        translate(locale, "states.empty"),
      );
      rerender(<DiscoveryError locale={locale} />);
      expect(screen.getByRole("alert")).toHaveTextContent(
        translate(locale, "states.error"),
      );
    },
  );

  it("preserves safe overrides and retry", () => {
    const retry = vi.fn();
    render(
      <DiscoveryError
        error={new Error("secret")}
        labels={{ error: "Safe", retry: "Again" }}
        locale="en"
        onRetry={retry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Safe");
    fireEvent.click(screen.getByRole("button", { name: "Again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
