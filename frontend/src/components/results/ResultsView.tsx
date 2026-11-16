import { useState } from "react";
import { formatDateTime, formatDuration, formatNumber } from "../../lib/format";
import type { ResultOut } from "../../lib/types";
import { Alert } from "../ui/Alert";
import { Tabs, type TabItem } from "../ui/Tabs";
import { cardClasses } from "../ui/styles";
import { CitationPanel } from "./CitationPanel";
import { Markdown } from "./Markdown";
import { ResultActions } from "./ResultActions";
import { SourcesList } from "./SourcesList";

interface ResultsViewProps {
  result: ResultOut;
  jobId: string;
  /** The server stores results on an ephemeral disk. */
  ephemeral: boolean;
}

function totalTokens(usage: Record<string, unknown>): number | null {
  const value = usage.total_tokens;
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null;
}

function EmptyOutput({ label }: { label: string }) {
  return <p className="text-sm text-fg-muted">{label}</p>;
}

/** The finished report and everything behind it. Default export for lazy loading. */
export default function ResultsView({ result, jobId, ephemeral }: ResultsViewProps) {
  const [tab, setTab] = useState("report");
  const tokens = totalTokens(result.token_usage);

  const items: TabItem[] = [
    {
      id: "report",
      label: "Report",
      printable: true,
      content: (
        <div className="space-y-6">
          <CitationPanel check={result.citation_check} />
          <article aria-label="Report">
            <Markdown unverifiedUrls={result.citation_check.unmatched}>{result.report_markdown}</Markdown>
          </article>
        </div>
      ),
    },
    {
      id: "sources",
      label: `Sources (${result.sources.length})`,
      printable: true,
      content: (
        <div className="space-y-6 print:mt-10 print:border-t print:border-line print:pt-6">
          <SourcesList
            sources={result.sources}
            citedUrls={result.citation_check.matched}
            queries={result.search_queries}
          />
        </div>
      ),
    },
    {
      id: "notes",
      label: "Research notes",
      content: result.research_notes.trim() ? (
        <Markdown>{result.research_notes}</Markdown>
      ) : (
        <EmptyOutput label="The Research Agent produced no separate notes." />
      ),
    },
    {
      id: "code",
      label: "Code examples",
      content: result.code_examples.trim() ? (
        <Markdown>{result.code_examples}</Markdown>
      ) : (
        <EmptyOutput label="The Coding Agent produced no code examples." />
      ),
    },
    {
      id: "methodology",
      label: "Methodology",
      content: <Markdown>{result.methodology_markdown}</Markdown>,
    },
  ];

  return (
    <section aria-labelledby="results-heading" className={`${cardClasses} p-5 sm:p-6 print:border-0 print:p-0 print:shadow-none`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between print:hidden">
        <div>
          <h2 id="results-heading" className="text-lg font-semibold">
            Results
          </h2>
          <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-fg-muted">
            <div className="flex gap-1">
              <dt>Model</dt>
              <dd className="font-medium text-fg">
                {result.model} via {result.provider}
              </dd>
            </div>
            <div className="flex gap-1">
              <dt>Duration</dt>
              <dd className="font-medium text-fg">{formatDuration(result.duration_seconds)}</dd>
            </div>
            {tokens !== null && (
              <div className="flex gap-1">
                <dt>Tokens</dt>
                <dd className="font-medium text-fg">{formatNumber(tokens)}</dd>
              </div>
            )}
          </dl>
        </div>
        <ResultActions jobId={jobId} reportMarkdown={result.report_markdown} />
      </div>

      <p className="mb-6 hidden text-xs text-fg-muted print:block">
        Generated {formatDateTime(result.created_at)} by the Multi-Agent Research Team ({result.model} via{" "}
        {result.provider}). AI-generated content; verify important facts before relying on them.
      </p>

      {(result.truncated || ephemeral) && (
        <div className="mt-4 space-y-2 print:hidden">
          {result.truncated && (
            <Alert tone="warning" title="This report was truncated">
              It exceeded the maximum report length on this server, so the end is cut off.
            </Alert>
          )}
          {ephemeral && (
            <p className="text-xs text-fg-subtle" data-testid="ephemeral-notice">
              Results on this instance may be cleared when the server restarts — download them to keep a copy.
            </p>
          )}
        </div>
      )}

      <div className="mt-5 print:mt-0">
        <Tabs items={items} activeId={tab} onChange={setTab} label="Result sections" idPrefix="result" />
      </div>
    </section>
  );
}
