import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const styles = readFileSync("src/styles.css", "utf8");

function relativeLuminance(hex: string) {
  const pairs = hex.slice(1).match(/.{2}/g);
  if (pairs?.length !== 3) {
    throw new Error(`Expected a six-digit hexadecimal color, received ${hex}`);
  }

  const channels = pairs.map((channel) => {
    const value = Number.parseInt(channel, 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  const [red, green, blue] = channels;
  if (red === undefined || green === undefined || blue === undefined) {
    throw new Error(`Could not parse hexadecimal color ${hex}`);
  }

  return red * 0.2126 + green * 0.7152 + blue * 0.0722;
}

function contrastRatio(first: string, second: string) {
  const luminances = [relativeLuminance(first), relativeLuminance(second)].sort(
    (a, b) => b - a,
  );
  const [lighter, darker] = luminances;
  if (lighter === undefined || darker === undefined) {
    throw new Error("Expected two luminance values");
  }

  return (lighter + 0.05) / (darker + 0.05);
}

function token(name: string) {
  const value = styles.match(
    new RegExp(`${name}:\\s*(#[0-9a-f]{6})`, "i"),
  )?.[1];
  if (value === undefined) {
    throw new Error(`Missing six-digit color token ${name}`);
  }

  return value;
}

describe("Talaqi design tokens", () => {
  it("defines the locked brand anchors and accessibility values", () => {
    expect(styles).toContain("--tq-color-brand: #184f43");
    expect(styles).toContain("--tq-color-canvas: #fcf7ef");
    expect(styles).toContain("--tq-color-accent: #d87050");
    expect(styles).toContain("--tq-touch-target: 2.75rem");
    expect(styles).toContain("--tq-focus-ring-width: 0.1875rem");
  });

  it("keeps text and UI boundary tokens at their WCAG contrast thresholds", () => {
    expect(
      contrastRatio(token("--tq-color-text"), token("--tq-color-canvas")),
    ).toBeGreaterThanOrEqual(4.5);
    expect(
      contrastRatio(token("--tq-color-border"), token("--tq-color-surface")),
    ).toBeGreaterThanOrEqual(3);
  });

  it("preserves visible focus and reduced-motion preferences", () => {
    expect(styles).toMatch(/:focus-visible\s*\{/);
    expect(styles).toMatch(
      /\.tq-skip-link:focus(?:\s*,|\s*\{)[^}]*transform:\s*translateY\(0\)/s,
    );
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
  });

  it("uses logical properties for directional layout", () => {
    const declaration = /^\s*(margin|padding|border|inset)-(left|right)\s*:/gim;
    expect(styles).not.toMatch(declaration);
    expect(styles).toContain("padding-inline");
  });
});
