import { render, screen } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it } from "vitest";

import {
  ActionLink,
  Button,
  Card,
  Container,
  SkipLink,
  Stack,
  VisuallyHidden,
} from "./index";

describe("interactive primitives", () => {
  it("keeps Button native semantics, attributes, and refs", () => {
    const reference = createRef<HTMLButtonElement>();

    render(
      <Button ref={reference} type="submit" disabled data-purpose="save">
        Save changes
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Save changes" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("type", "submit");
    expect(button).toHaveAttribute("data-purpose", "save");
    expect(reference.current).toBe(button);
  });

  it("keeps ActionLink as a real named link", () => {
    render(<ActionLink href="/community">Explore community</ActionLink>);

    expect(
      screen.getByRole("link", { name: "Explore community" }),
    ).toHaveAttribute("href", "/community");
  });

  it("targets main content with a native skip link", () => {
    render(<SkipLink href="#main-content">Skip to main content</SkipLink>);

    expect(
      screen.getByRole("link", { name: "Skip to main content" }),
    ).toHaveAttribute("href", "#main-content");
  });
});

describe("layout primitives", () => {
  it("renders Card with a section semantic when labelled", () => {
    render(<Card aria-label="Community preview">Preview</Card>);
    expect(
      screen.getByRole("region", { name: "Community preview" }),
    ).toHaveTextContent("Preview");
  });

  it("forwards layout attributes without changing native elements", () => {
    const { container } = render(
      <Container data-testid="container">
        <Stack gap="large" data-testid="stack">
          Content
        </Stack>
      </Container>,
    );

    expect(screen.getByTestId("container").tagName).toBe("DIV");
    expect(screen.getByTestId("stack")).toHaveAttribute("data-gap", "large");
    expect(container.querySelectorAll("div")).toHaveLength(2);
  });

  it("provides screen-reader-only content without ARIA hiding it", () => {
    render(<VisuallyHidden>Opens in a new window</VisuallyHidden>);
    expect(screen.getByText("Opens in a new window")).not.toHaveAttribute(
      "aria-hidden",
    );
  });
});
