import { Link } from "react-router";
import { useMeta } from "../../hooks/metaContext";
import { apiUrl } from "../../lib/api";
import { LogoMark } from "./LogoMark";

const linkClass = "text-fg-muted transition-colors hover:text-fg";

export function Footer() {
  const { meta } = useMeta();
  const repo = meta?.repository_url;

  return (
    <footer className="mt-auto border-t border-line bg-surface print:hidden">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.5fr_1fr_1fr] lg:px-8">
        <div className="max-w-sm">
          <div className="flex items-center gap-2.5 font-semibold tracking-tight">
            <LogoMark className="size-6" />
            Multi-Agent Research Team
          </div>
          <p className="mt-3 text-sm leading-6 text-fg-muted">
            Three AI agents that research a topic on the web, write code examples and deliver a cited report.
            Open source and built to run on free tiers.
          </p>
        </div>

        <nav aria-label="Product" className="text-sm">
          <h2 className="font-semibold text-fg">Product</h2>
          <ul className="mt-3 space-y-2">
            <li>
              <Link to="/research" className={linkClass}>
                Research workspace
              </Link>
            </li>
            <li>
              <Link to="/about" className={linkClass}>
                About &amp; architecture
              </Link>
            </li>
            {meta?.api_docs && (
              <li>
                <a href={apiUrl("/api/docs")} className={linkClass}>
                  API documentation
                </a>
              </li>
            )}
          </ul>
        </nav>

        <nav aria-label="Project" className="text-sm">
          <h2 className="font-semibold text-fg">Open source</h2>
          <ul className="mt-3 space-y-2">
            {repo ? (
              <>
                <li>
                  <a href={repo} target="_blank" rel="noopener noreferrer" className={linkClass}>
                    Source code on GitHub
                  </a>
                </li>
                <li>
                  <a
                    href={`${repo}/blob/main/CONTRIBUTING.md`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={linkClass}
                  >
                    Contributing guide
                  </a>
                </li>
                <li>
                  <a href={`${repo}/blob/main/LICENSE`} target="_blank" rel="noopener noreferrer" className={linkClass}>
                    MIT License
                  </a>
                </li>
              </>
            ) : (
              <li className="text-fg-muted">Released under the MIT License</li>
            )}
          </ul>
        </nav>
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-5 text-xs text-fg-subtle sm:px-6 lg:px-8">
          <p>Released under the MIT License. AI-generated content can be wrong; verify it before relying on it.</p>
          {meta && <p>Version {meta.version}</p>}
        </div>
      </div>
    </footer>
  );
}
