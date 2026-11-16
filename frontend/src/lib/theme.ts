import { browserStorage, safeGet, safeSet } from "./storage";

export type Theme = "light" | "dark";

/** Must match the key read by `public/theme-init.js`. */
export const THEME_KEY = "mart:theme";

export function storedTheme(): Theme | null {
  const value = safeGet(browserStorage, THEME_KEY);
  return value === "light" || value === "dark" ? value : null;
}

export function systemTheme(): Theme {
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
}

export function saveTheme(theme: Theme): void {
  safeSet(browserStorage, THEME_KEY, theme);
}
