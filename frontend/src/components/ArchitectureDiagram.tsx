import { ArrowDown, ArrowRight, Cpu, Database, Globe, Monitor, Search, Server, Workflow } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import { cn } from "../lib/cn";

function Box({ icon, title, text, className }: { icon: ReactNode; title: string; text: string; className?: string }) {
  return (
    <div className={cn("rounded-lg border border-line bg-surface p-4 shadow-xs", className)}>
      <p className="flex items-center gap-2 font-semibold">
        {icon}
        {title}
      </p>
      <p className="mt-1 text-sm leading-6 text-fg-muted">{text}</p>
    </div>
  );
}

function Connector({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-2 text-xs text-fg-subtle" aria-hidden="true">
      <ArrowDown className="size-4" />
      {label}
    </div>
  );
}

const iconClass = "size-4 text-accent";

/**
 * Request flow of the platform, drawn with HTML so it stays readable, themable
 * and accessible (the figure caption and box text carry the full description).
 */
export function ArchitectureDiagram() {
  return (
    <figure className="rounded-xl border border-line bg-page p-4 sm:p-6">
      <div className="mx-auto max-w-3xl">
        <Box
          icon={<Monitor aria-hidden="true" className={iconClass} />}
          title="Browser (React)"
          text="Submits a topic, follows live progress over Server-Sent Events and polls the job status as a fallback."
        />
        <Connector label="HTTPS: JSON API + event stream" />
        <Box
          icon={<Server aria-hidden="true" className={iconClass} />}
          title="FastAPI application"
          text="Validates requests, enforces quotas and rate limits, stores jobs and events, streams progress and serves this interface."
        />
        <Connector label="queued jobs" />
        <Box
          icon={<Workflow aria-hidden="true" className={iconClass} />}
          title="Job runner"
          text="A bounded worker pool with a queue. Supports cooperative cancellation, time limits and recovery after restarts."
        />
        <Connector label="runs the pipeline" />
        <div className="rounded-lg border border-accent-solid/40 bg-accent-soft p-4">
          <p className="text-sm font-semibold text-accent-soft-fg">CrewAI pipeline (sequential)</p>
          <ol className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto_1fr_auto_1fr] sm:items-center">
            {["Research Agent", "Coding Agent", "Manager Agent"].map((name, index) => (
              <Fragment key={name}>
                {index > 0 && (
                  <li aria-hidden="true" className="flex justify-center text-fg-subtle">
                    <ArrowDown className="size-4 sm:hidden" />
                    <ArrowRight className="size-4 max-sm:hidden" />
                  </li>
                )}
                <li className="rounded-md border border-line bg-surface px-3 py-2 text-center text-sm font-medium">
                  {index + 1}. {name}
                </li>
              </Fragment>
            ))}
          </ol>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Box
            icon={<Cpu aria-hidden="true" className={iconClass} />}
            title="LLM provider"
            text="Groq by default; Gemini, OpenRouter, OpenAI-compatible or Ollama as fallbacks."
          />
          <Box
            icon={<Search aria-hidden="true" className={iconClass} />}
            title="Web search"
            text="Serper (Google results) or Tavily, with a per-run search budget."
          />
          <Box
            icon={<Database aria-hidden="true" className={iconClass} />}
            title="Storage"
            text="SQLite or Postgres: jobs, progress events and results, deleted after a retention period."
          />
        </div>
      </div>
      <figcaption className="mt-4 flex items-start justify-center gap-2 text-center text-sm text-fg-muted">
        <Globe aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        One process serves both the website and its API, which fits a single free hosting instance.
      </figcaption>
    </figure>
  );
}
