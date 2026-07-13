import { spawnSync } from "node:child_process";
import console from "node:console";
import { existsSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import process from "node:process";
import { fileURLToPath, URL } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const root = fileURLToPath(new URL("../../../", import.meta.url));
const check = process.argv.includes("--check");
const python = findPython();
const pythonArguments = [
  join(root, "apps", "api", "scripts", "generate_openapi.py"),
];
if (check) pythonArguments.push("--check");

const openapiResult = spawnSync(python, pythonArguments, {
  cwd: root,
  encoding: "utf8",
  stdio: "inherit",
});
if (openapiResult.error) throw openapiResult.error;
if (openapiResult.status !== 0) process.exit(openapiResult.status ?? 1);

const schemaPath = join(root, "openapi", "talaqi-v1.json");
const outputPath = join(
  root,
  "packages",
  "api-client",
  "src",
  "schema.generated.ts",
);
const schema = JSON.parse(await readFile(schemaPath, "utf8"));
const generated = astToString(await openapiTS(schema, { alphabetize: true }));

if (check) {
  const existing = existsSync(outputPath)
    ? await readFile(outputPath, "utf8")
    : "";
  if (existing !== generated) {
    console.error("checked-in generated API client is out of date");
    process.exit(1);
  }
} else {
  await writeFile(outputPath, generated, { encoding: "utf8" });
}

function findPython() {
  const candidates =
    process.platform === "win32"
      ? [join(root, ".venv", "Scripts", "python.exe")]
      : [
          join(root, ".venv", "bin", "python3"),
          join(root, ".venv", "bin", "python"),
        ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return (
    process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3")
  );
}
