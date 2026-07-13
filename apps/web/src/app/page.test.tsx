import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "@/app/page";

describe("home foundation preview", () => {
  it("renders translated content inside the public shell", () => {
    const { container } = render(<Home />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Find your people. Build something together.",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(screen.getByAltText("Talaqi")).toHaveAttribute(
      "src",
      "/brand/talaqi-wordmark.png",
    );
  });
});
