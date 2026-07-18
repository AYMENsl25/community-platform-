import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatPlural,
} from "./formatters";

describe("deterministic Intl formatters", () => {
  it("formats dates with an explicit valid IANA time zone", () => {
    const instant = new Date("2026-07-14T18:30:00Z");
    expect(formatDate(instant, "tr", "Europe/Istanbul")).toBe(
      new Intl.DateTimeFormat("tr", {
        day: "2-digit",
        hour: "2-digit",
        hourCycle: "h23",
        minute: "2-digit",
        month: "short",
        timeZone: "Europe/Istanbul",
        year: "numeric",
      }).format(instant),
    );
    expect(() => formatDate(instant, "en", "Mars/Olympus")).toThrow(
      "valid IANA time zone",
    );
    expect(() => formatDate(instant, "en", "")).toThrow("valid IANA time zone");
  });

  it("formats numbers and only beta currencies", () => {
    expect(formatNumber(1234.5, "fr")).toBe(
      new Intl.NumberFormat("fr", {
        maximumFractionDigits: 2,
        minimumFractionDigits: 0,
        useGrouping: true,
      }).format(1234.5),
    );
    expect(formatCurrency(1250, "tr", "TRY")).toBe(
      new Intl.NumberFormat("tr", {
        currency: "TRY",
        currencyDisplay: "symbol",
        maximumFractionDigits: 2,
        minimumFractionDigits: 2,
        style: "currency",
        useGrouping: true,
      }).format(1250),
    );
    expect(formatCurrency(500, "ar", "DZD")).toBe(
      new Intl.NumberFormat("ar", {
        currency: "DZD",
        currencyDisplay: "symbol",
        maximumFractionDigits: 2,
        minimumFractionDigits: 2,
        style: "currency",
        useGrouping: true,
      }).format(500),
    );
    expect(() => formatCurrency(10, "en", "USD")).toThrow(
      "supported beta currency",
    );
  });

  it("supports every Intl plural category and falls back to other", () => {
    const messages = {
      zero: "zero:{count}",
      one: "one:{count}",
      two: "two:{count}",
      few: "few:{count}",
      many: "many:{count}",
      other: "other:{count}",
    } as const;

    expect(formatPlural(0, "ar", messages)).toMatch(/^zero:/);
    expect(formatPlural(1, "ar", messages)).toMatch(/^one:/);
    expect(formatPlural(2, "ar", messages)).toMatch(/^two:/);
    expect(formatPlural(3, "ar", messages)).toMatch(/^few:/);
    expect(formatPlural(11, "ar", messages)).toMatch(/^many:/);
    expect(formatPlural(100, "ar", messages)).toMatch(/^other:/);
    expect(formatPlural(2, "ar", { other: "fallback:{count}" })).toMatch(
      /^fallback:/,
    );
  });
});
