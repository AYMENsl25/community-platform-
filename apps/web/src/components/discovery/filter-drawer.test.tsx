import type { components } from "@talaqi/api-client";
import { translate } from "@talaqi/translations";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FilterDrawer } from "./filter-drawer";

const metadata = {
  countries: [{ code: "TR", name_key: "regions.country.tr" }],
  cities: [{ slug: "istanbul", name_key: "regions.city.istanbul" }],
  categories: [{ slug: "sports", name_key: "categories.sports" }],
  price_types: ["free", "cash"],
  sort: "featured",
} satisfies components["schemas"]["DiscoveryMetadataResponse"];

describe("FilterDrawer", () => {
  it.each(["en", "tr", "fr", "ar"] as const)(
    "derives %s labels and keeps a no-JS GET form",
    (locale) => {
      render(
        <FilterDrawer
          filters={{ country: "TR", search: "run" }}
          locale={locale}
          metadata={metadata}
        />,
      );
      const form = screen.getByRole("form", {
        name: translate(locale, "filters.title"),
      });
      expect(form).toHaveAttribute("method", "get");
      expect(form).toHaveAttribute("action", "/explore");
      expect(
        screen.getByLabelText(translate(locale, "filters.search")),
      ).toHaveValue("run");
    },
  );

  it("focuses the first dialog control, traps both directions, and restores trigger", () => {
    render(<FilterDrawer filters={{}} locale="en" metadata={metadata} />);
    const trigger = screen.getByRole("button", { name: "Open filters" });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Filters" });
    const close = screen.getByRole("button", { name: "Close filters" });
    expect(close).toHaveFocus();
    fireEvent.keyDown(dialog, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("button", { name: "Apply filters" })).toHaveFocus();
    fireEvent.keyDown(dialog, { key: "Tab" });
    expect(close).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(trigger).toHaveFocus();
    expect(screen.getAllByLabelText("Search")).toHaveLength(1);
  });
});
