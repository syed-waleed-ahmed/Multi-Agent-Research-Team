import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig([
  globalIgnores(["dist", "coverage", "playwright-report", "test-results", "blob-report"]),
  {
    files: ["src/**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommendedTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      jsxA11y.flatConfigs.recommended,
    ],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", ignoreRestSiblings: true },
      ],
      "react-refresh/only-export-components": ["error", { allowConstantExport: true }],
    },
  },
  {
    files: ["src/**/*.test.{ts,tsx}", "src/test/**/*.{ts,tsx}"],
    rules: { "react-refresh/only-export-components": "off" },
  },
  {
    files: ["e2e/**/*.ts", "*.config.ts"],
    extends: [js.configs.recommended, tseslint.configs.recommendedTypeChecked],
    languageOptions: {
      globals: globals.node,
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
  },
  {
    files: ["eslint.config.js"],
    extends: [js.configs.recommended],
    languageOptions: { globals: globals.node },
  },
  {
    files: ["public/**/*.js"],
    extends: [js.configs.recommended],
    languageOptions: { sourceType: "script", globals: globals.browser },
  },
]);
