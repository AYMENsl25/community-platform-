import { defineConfig, globalIgnores } from "eslint/config";
import { typescriptConfig } from "@talaqi/config/eslint";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

export default defineConfig([
  ...typescriptConfig,
  ...nextVitals,
  ...nextTypescript,
  globalIgnores([".next/**", "coverage/**", "next-env.d.ts"]),
]);
