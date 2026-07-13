import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const repositoryRoot = resolve(import.meta.dirname, "../../..");
const sourcePath = resolve(
  repositoryRoot,
  "assets/brand/source/talaqi-logo-source.png",
);
const publicBrandPath = resolve(repositoryRoot, "apps/web/public/brand");

function pngDimensions(path: string) {
  const bytes = readFileSync(path);
  expect(bytes.subarray(1, 4).toString("ascii")).toBe("PNG");
  return {
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
  };
}

describe("Talaqi brand asset provenance", () => {
  it("keeps an immutable copy of the approved source", () => {
    const checksum = createHash("sha256")
      .update(readFileSync(sourcePath))
      .digest("hex");

    expect(checksum).toBe(
      "0380136a1d394beb063d4955677201a4d405ee4b5bc9f3c4adaef7bd8ef8365c",
    );
  });

  it.each([
    ["talaqi-wordmark.png", 993, 351],
    ["talaqi-icon.png", 237, 245],
    ["talaqi-favicon.png", 64, 64],
    ["talaqi-wordmark-monochrome.png", 993, 351],
  ])("creates %s at its undistorted contract size", (name, width, height) => {
    const assetPath = resolve(publicBrandPath, name);
    expect(existsSync(assetPath)).toBe(true);
    expect(pngDimensions(assetPath)).toEqual({ width, height });
  });

  it("regenerates every checked-in derivative byte-for-byte", () => {
    expect(() =>
      execFileSync(
        process.execPath,
        ["scripts/brand/generate-assets.mjs", "--check"],
        {
          cwd: repositoryRoot,
          stdio: "pipe",
        },
      ),
    ).not.toThrow();
  });
});
