import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const repositoryRoot = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const sourcePath = resolve(
  repositoryRoot,
  "assets/brand/source/talaqi-logo-source.png",
);
const destination = resolve(repositoryRoot, "apps/web/public/brand");
const expectedChecksum =
  "0380136a1d394beb063d4955677201a4d405ee4b5bc9f3c4adaef7bd8ef8365c";
const checking = process.argv.includes("--check");
const background = { r: 252, g: 247, b: 239 };

const source = await readFile(sourcePath);
const checksum = createHash("sha256").update(source).digest("hex");
if (checksum !== expectedChecksum) {
  throw new Error(
    `Brand source checksum mismatch: expected ${expectedChecksum}, received ${checksum}`,
  );
}

const pngOptions = {
  compressionLevel: 9,
  adaptiveFiltering: false,
  palette: false,
};

async function crop(bounds) {
  return sharp(source).extract(bounds).png(pngOptions).toBuffer();
}

async function monochromeWordmark() {
  const { data, info } = await sharp(source)
    .extract({ left: 350, top: 144, width: 993, height: 351 })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  const brand = { r: 24, g: 79, b: 67 };

  for (let index = 0; index < data.length; index += info.channels) {
    const distance = Math.max(
      Math.abs(data[index] - background.r),
      Math.abs(data[index + 1] - background.g),
      Math.abs(data[index + 2] - background.b),
    );
    const coverage = Math.min(1, Math.max(0, (distance - 3) / 64));
    data[index] = Math.round(
      background.r + (brand.r - background.r) * coverage,
    );
    data[index + 1] = Math.round(
      background.g + (brand.g - background.g) * coverage,
    );
    data[index + 2] = Math.round(
      background.b + (brand.b - background.b) * coverage,
    );
  }

  return sharp(data, {
    raw: { width: info.width, height: info.height, channels: info.channels },
  })
    .png(pngOptions)
    .toBuffer();
}

const icon = await crop({ left: 728, top: 606, width: 237, height: 245 });
const assets = new Map([
  [
    "talaqi-wordmark.png",
    await crop({ left: 350, top: 144, width: 993, height: 351 }),
  ],
  ["talaqi-icon.png", icon],
  [
    "talaqi-favicon.png",
    await sharp(icon)
      .resize(64, 64, {
        fit: "contain",
        background,
        withoutEnlargement: true,
      })
      .png(pngOptions)
      .toBuffer(),
  ],
  ["talaqi-wordmark-monochrome.png", await monochromeWordmark()],
]);

await mkdir(destination, { recursive: true });

for (const [name, generated] of assets) {
  const target = resolve(destination, name);
  if (checking) {
    const checkedIn = await readFile(target).catch(() => undefined);
    if (!checkedIn?.equals(generated)) {
      throw new Error(
        `${name} is missing or differs from deterministic output`,
      );
    }
  } else {
    await writeFile(target, generated);
  }
}

console.log(
  checking
    ? `Verified ${assets.size} deterministic Talaqi brand assets.`
    : `Generated ${assets.size} deterministic Talaqi brand assets.`,
);
