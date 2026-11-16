import { Menu, Plus, X } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { Link, NavLink, useLocation } from "react-router";
import { useMeta } from "../../hooks/metaContext";
import { cn } from "../../lib/cn";
import { buttonClasses } from "../ui/styles";
import { GitHubMark } from "./GitHubMark";
import { LogoMark } from "./LogoMark";
import { ThemeToggle } from "./ThemeToggle";

const NAV = [
  { to: "/research", label: "Workspace" },
  { to: "/about", label: "About & docs" },
];

function navClass({ isActive }: { isActive: boolean }) {
  return cn(
    "rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "text-fg" : "text-fg-muted hover:text-fg",
  );
}

export function Header() {
  const { meta } = useMeta();
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const location = useLocation();

  // Close the mobile menu after navigating (state derived from the location).
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-page/85 backdrop-blur-md print:hidden">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-2 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="mr-2 flex min-w-0 items-center gap-2.5 rounded-md font-semibold tracking-tight">
          <LogoMark />
          <span className="truncate">
            <span className="hidden sm:inline">Multi-Agent </span>Research Team
          </span>
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={navClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          {meta && (
            <a
              href={meta.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Source code on GitHub (opens in a new tab)"
              title="Source code on GitHub"
              className={buttonClasses("ghost", "icon")}
            >
              <GitHubMark className="size-4.5" />
            </a>
          )}
          <ThemeToggle />
          <Link to="/research" className={buttonClasses("primary", "sm", "ml-2 max-md:hidden")}>
            <Plus aria-hidden="true" className="size-4" />
            New research
          </Link>
          <button
            type="button"
            className={buttonClasses("ghost", "icon", "md:hidden")}
            aria-expanded={open}
            aria-controls={menuId}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X aria-hidden="true" className="size-5" /> : <Menu aria-hidden="true" className="size-5" />}
          </button>
        </div>
      </div>

      <div id={menuId} hidden={!open} className="border-t border-line bg-page md:hidden">
        <nav aria-label="Mobile" className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-3">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={navClass}>
              {item.label}
            </NavLink>
          ))}
          <Link to="/research" className={buttonClasses("primary", "md", "mt-2")}>
            <Plus aria-hidden="true" className="size-4" />
            New research
          </Link>
        </nav>
      </div>
    </header>
  );
}
