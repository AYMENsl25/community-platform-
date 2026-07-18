import { translate } from "@talaqi/translations";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LocalizedHome } from "@/components/locale/localized-home";

describe("localized home", () => {
  it("renders translated English content inside the public shell", () => {
    const { container } = render(<LocalizedHome initialLocale="en" />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: translate("en", "home.title"),
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(screen.getByAltText("Talaqi")).toHaveAttribute(
      "src",
      "/brand/talaqi-wordmark.png",
    );
  });
  it("rerenders visible content and shell direction when locale changes", () => {
    const { container } = render(<LocalizedHome initialLocale="en" />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "ar" } });
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: translate("ar", "home.title"),
      }),
    ).toBeInTheDocument();
    expect(container.querySelector(".tq-public-shell")).toHaveAttribute(
      "lang",
      "ar",
    );
    expect(container.querySelector(".tq-public-shell")).toHaveAttribute(
      "dir",
      "rtl",
    );
  });
});
