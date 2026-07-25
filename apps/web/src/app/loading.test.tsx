import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/locale/request-locale", () => ({
  resolveRequestLocale: async () => "en",
}));
import Loading from "./loading";

describe("route loading state", () => {
  it("announces a localized loading state", async () => {
    render(await Loading());
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });
});
