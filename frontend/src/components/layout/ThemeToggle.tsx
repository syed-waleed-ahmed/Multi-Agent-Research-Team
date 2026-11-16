import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { applyTheme, saveTheme, storedTheme, systemTheme, type Theme } from "../../lib/theme";
import { buttonClasses } from "../ui/styles";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => storedTheme() ?? systemTheme());

  // Follow the operating system until the visitor picks a theme explicitly.
  useEffect(() => {
    let query: MediaQueryList;
    try {
      query = window.matchMedia("(prefers-color-scheme: dark)");
    } catch {
      return;
    }
    const onChange = (event: MediaQueryListEvent) => {
      if (storedTheme()) return;
      const next: Theme = event.matches ? "dark" : "light";
      applyTheme(next);
      setTheme(next);
    };
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const next: Theme = theme === "dark" ? "light" : "dark";
  const toggle = () => {
    applyTheme(next);
    saveTheme(next);
    setTheme(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
      className={buttonClasses("ghost", "icon")}
    >
      {theme === "dark" ? <Sun aria-hidden="true" className="size-4.5" /> : <Moon aria-hidden="true" className="size-4.5" />}
    </button>
  );
}
