import { ExternalLink, Search } from "lucide-react";
import { domainOf, formatPublished, normalizeUrl, safeHttpUrl } from "../../lib/format";
import type { SourceOut } from "../../lib/types";
import { Badge } from "../ui/Badge";

interface SourcesListProps {
  sources: SourceOut[];
  /** Report links that matched a retrieved source (citation check). */
  citedUrls: readonly string[];
  queries: readonly string[];
}

/** Every source the Research Agent retrieved, with the query that found it. */
export function SourcesList({ sources, citedUrls, queries }: SourcesListProps) {
  const cited = new Set(citedUrls.map(normalizeUrl));

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold">Sources retrieved during research</h3>
        <p className="mt-1 text-sm text-fg-muted">
          Results returned by web search for this run. They were not independently fact-checked.
        </p>
      </div>

      {sources.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line-strong px-4 py-6 text-center text-sm text-fg-muted">
          No web sources were retrieved for this report.
        </p>
      ) : (
        <ol className="space-y-3">
          {sources.map((source, index) => {
            const url = safeHttpUrl(source.url);
            const domain = domainOf(source.url);
            const published = formatPublished(source.published);
            const isCited = cited.has(normalizeUrl(source.url));
            return (
              <li key={`${source.url}-${index}`} className="rounded-lg border border-line bg-surface p-4 break-inside-avoid">
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-surface-muted text-xs font-semibold text-fg-muted tabular-nums">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      {url ? (
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer nofollow"
                          className="print-url inline-flex min-w-0 items-center gap-1 font-medium break-words text-accent hover:underline"
                        >
                          {source.title || domain || source.url}
                          <ExternalLink aria-hidden="true" className="size-3.5 shrink-0 print:hidden" />
                          <span className="sr-only">(opens in a new tab)</span>
                        </a>
                      ) : (
                        <span className="font-medium break-words">{source.title || source.url}</span>
                      )}
                      {isCited && <Badge tone="success">Cited in report</Badge>}
                    </div>
                    <p className="mt-1 flex flex-wrap gap-x-2 text-xs text-fg-subtle">
                      {domain && <span>{domain}</span>}
                      {published && (
                        <>
                          <span aria-hidden="true">·</span>
                          <span>{published}</span>
                        </>
                      )}
                      {source.provider && (
                        <>
                          <span aria-hidden="true">·</span>
                          <span>via {source.provider}</span>
                        </>
                      )}
                    </p>
                    {source.snippet && <p className="mt-2 text-sm leading-6 break-words text-fg-muted">{source.snippet}</p>}
                    {source.query && (
                      <p className="mt-2 inline-flex max-w-full items-center gap-1.5 text-xs text-fg-subtle">
                        <Search aria-hidden="true" className="size-3.5 shrink-0" />
                        <span className="break-words">Found by the query “{source.query}”</span>
                      </p>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {queries.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold">Search queries executed ({queries.length})</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {queries.map((query, index) => (
              <li key={`${query}-${index}`}>
                <Badge className="max-w-full">
                  <span className="break-words">{query}</span>
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
