import { CircleCheck, Link2, TriangleAlert } from "lucide-react";
import { cn } from "../../lib/cn";
import { domainOf, safeHttpUrl } from "../../lib/format";
import type { CitationCheckOut } from "../../lib/types";

export const UNVERIFIED_LABEL = "Not found in retrieved search results — verify before relying on them";

/**
 * Result of the backend's citation check: which links in the report appeared
 * in the URLs the Research Agent actually retrieved. A match means the source
 * was retrieved, not that each claim was fact-checked.
 */
export function CitationPanel({ check }: { check: CitationCheckOut }) {
  const matched = check.matched.length;
  const unmatched = check.unmatched.length;
  const total = matched + unmatched;

  const tone = total === 0 ? "neutral" : unmatched > 0 ? "warning" : "success";
  const Icon = unmatched > 0 ? TriangleAlert : total === 0 ? Link2 : CircleCheck;

  return (
    <section
      aria-labelledby="citation-heading"
      data-testid="citation-panel"
      className={cn(
        "rounded-lg border p-4 text-sm",
        tone === "warning" && "border-warning-line bg-warning-soft",
        tone === "success" && "border-success-line bg-success-soft",
        tone === "neutral" && "border-line bg-surface-muted",
      )}
    >
      <div className="flex gap-3">
        <Icon
          aria-hidden="true"
          className={cn(
            "mt-0.5 size-5 shrink-0",
            tone === "warning" ? "text-warning" : tone === "success" ? "text-success" : "text-fg-subtle",
          )}
        />
        <div className="min-w-0 flex-1">
          <h3 id="citation-heading" className="font-semibold text-fg">
            Citation check
          </h3>
          <p className="mt-1 text-fg-muted">
            {total === 0 ? (
              "The report contains no links to check against the retrieved search results."
            ) : (
              <>
                <span className="font-semibold text-fg">
                  {matched} of {total}
                </span>{" "}
                {total === 1 ? "link" : "links"} in the report{" "}
                {matched === 1 && total === 1 ? "was" : "were"} found in the search results retrieved during this run.
              </>
            )}
          </p>

          {unmatched > 0 && (
            <div className="mt-3">
              <p className="font-medium text-warning">{UNVERIFIED_LABEL}:</p>
              <ul className="mt-2 space-y-1.5">
                {check.unmatched.map((url) => {
                  const safe = safeHttpUrl(url);
                  return (
                    <li key={url} className="flex min-w-0 items-start gap-2">
                      <TriangleAlert aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-warning" />
                      {safe ? (
                        <a
                          href={safe}
                          target="_blank"
                          rel="noopener noreferrer nofollow"
                          className="min-w-0 break-all text-fg underline decoration-warning/60 underline-offset-2 hover:decoration-warning"
                        >
                          {url}
                        </a>
                      ) : (
                        <span className="min-w-0 break-all text-fg">{url}</span>
                      )}
                      {domainOf(url) && <span className="sr-only">({domainOf(url)})</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <p className="mt-3 text-xs leading-5 text-fg-muted">
            A match means the page was retrieved by web search, not that every claim was independently fact-checked.
          </p>
        </div>
      </div>
    </section>
  );
}
