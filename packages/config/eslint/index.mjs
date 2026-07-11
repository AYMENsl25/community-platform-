import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export const javascriptConfig = [eslint.configs.recommended];

export const typescriptConfig = tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strict,
);
