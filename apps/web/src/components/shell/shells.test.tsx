import { readFileSync } from "node:fs";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AdminShell, MemberShell, OrganizerShell, PublicShell } from "./shells";

describe("public shell", () => {
  it("provides one skip target and semantic landmarks", () => {
    const { container } = render(
      <PublicShell locale="en" currentHref="/">
        <h1>Foundation preview</h1>
      </PublicShell>,
    );

    const focusable = container.querySelectorAll(
      "a[href], button:not([disabled])",
    );
    expect(focusable[0]).toHaveTextContent("Skip to main content");
    expect(focusable[0]).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("marks only the current navigation link", () => {
    render(
      <PublicShell locale="en" currentHref="/">
        Content
      </PublicShell>,
    );

    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Community" })).not.toHaveAttribute(
      "aria-current",
    );
  });
  it("links to Explore and marks it on discovery routes", () => {
    render(
      <PublicShell locale="en" currentHref="/explore">
        Content
      </PublicShell>,
    );

    expect(screen.getByRole("link", { name: "Explore" })).toHaveAttribute(
      "href",
      "/explore",
    );
    expect(screen.getByRole("link", { name: "Explore" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("allows the first focusable skip link to receive keyboard focus", () => {
    const { container } = render(
      <PublicShell locale="en" currentHref="/">
        Content
      </PublicShell>,
    );
    const skipLink = container.querySelector<HTMLAnchorElement>("a[href]");

    skipLink?.focus();
    expect(skipLink).toHaveFocus();
  });
});

describe("workspace shells", () => {
  it.each([
    [MemberShell, "Member workspace"],
    [OrganizerShell, "Organizer workspace"],
    [AdminShell, "Platform administration"],
  ])("renders an accessible %s structure", (Shell, label) => {
    const { container } = render(
      <Shell locale="en" currentHref="/overview">
        Workspace content
      </Shell>,
    );

    expect(
      screen.getByRole("complementary", { name: label }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Workspace navigation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveTextContent("Workspace content");
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("applies Arabic language and right-to-left direction", () => {
    const { container } = render(
      <MemberShell locale="ar" currentHref="/overview">
        محتوى
      </MemberShell>,
    );

    const shell = container.firstElementChild;
    expect(shell).toHaveAttribute("lang", "ar");
    expect(shell).toHaveAttribute("dir", "rtl");
    expect(
      screen.getByRole("navigation", { name: "التنقل في مساحة العمل" }),
    ).toBeInTheDocument();
  });
});

describe("shell CSS contract", () => {
  const styles = readFileSync("src/components/shell/shells.css", "utf8");

  it("uses logical directional declarations and a compact-width layout", () => {
    expect(styles).not.toMatch(
      /^\s*(margin|padding|border|inset)-(left|right)\s*:/gim,
    );
    expect(styles).toContain("padding-inline");
    expect(styles).toContain("@media (max-width: 48rem)");
  });

  it("keeps primary action text high-contrast inside the shell", () => {
    expect(styles).toMatch(
      /\.tq-shell \.tq-action-link--primary\s*\{[^}]*color:\s*var\(--tq-color-on-brand\)/s,
    );
  });
});
