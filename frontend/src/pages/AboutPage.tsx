import { BookOpen, ExternalLink } from "lucide-react";
import type { ReactNode } from "react";
import { ArchitectureDiagram } from "../components/ArchitectureDiagram";
import { GitHubMark } from "../components/layout/GitHubMark";
import { CodeSnippet } from "../components/ui/CodeSnippet";
import { buttonClasses, cardClasses } from "../components/ui/styles";
import { useMeta } from "../hooks/metaContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { apiUrl } from "../lib/api";
import { cn } from "../lib/cn";
import type { LimitsOut } from "../lib/types";

const SECTIONS = [
  { id: "architecture", label: "Architecture" },
  { id: "agents", label: "Agents" },
  { id: "stack", label: "Tech stack" },
  { id: "self-hosting", label: "Self-hosting" },
  { id: "limits", label: "Free-tier limits" },
  { id: "api", label: "API" },
  { id: "license", label: "License & contributing" },
];

const AGENT_DETAILS = [
  {
    name: "Research Agent",
    points: [
      "Plans and runs web searches within a per-run budget: up to 2 (Quick), 4 (Standard) or 6 (Deep).",
      "Writes research notes that keep the URL of every source it relies on.",
      "Every search query and its result count is recorded and shown in the activity log.",
    ],
  },
  {
    name: "Coding Agent",
    points: [
      "Reads the research notes and writes practical code examples and implementation notes.",
      "Its output is passed to the Manager Agent and is also available on its own in the Code examples tab.",
    ],
  },
  {
    name: "Manager Agent",
    points: [
      "Reviews the notes and code and writes the final Markdown report in the chosen style.",
      "Links in the report are then compared with the URLs search actually returned; unretrieved links are flagged.",
      "Python code blocks in the final report are syntax-checked (parsed, never executed); the result is noted in the methodology.",
      "A factual methodology section (model, queries, timings, citation check) is generated from recorded data, not by the model.",
    ],
  },
];

const STACK = [
  ["CrewAI", "Defines the three agents and runs their tasks in sequence."],
  ["Groq", "Default LLM provider (free tier). Others can be configured as fallbacks via LiteLLM."],
  ["Serper / Tavily", "Web search APIs with free tiers; Serper returns Google results."],
  ["FastAPI + Uvicorn", "HTTP API, Server-Sent Events, quotas, security headers and static hosting."],
  ["SQLAlchemy + Alembic", "Persistence on SQLite (default) or Postgres, with migrations."],
  ["React + TypeScript", "This interface, built with Vite and styled with Tailwind CSS."],
] as const;

const ENV_VARS = [
  ["GROQ_API_KEY", "Required", "Groq API key (free at console.groq.com)."],
  ["SERPER_API_KEY", "Required*", "Serper key; or set TAVILY_API_KEY instead."],
  ["DATABASE_URL", "Optional", "Defaults to a local SQLite file. Use Postgres for persistent hosting."],
  ["JOBS_PER_IP_PER_HOUR / _PER_DAY", "Optional", "Per-visitor quotas (defaults 5 and 10)."],
  ["GLOBAL_JOBS_PER_DAY", "Optional", "Instance-wide daily cap (default 100)."],
  ["MAX_CONCURRENT_JOBS", "Optional", "Parallel runs (default 1; free LLM quotas are per account)."],
  ["CORS_ORIGINS", "Optional", "Only for split hosting of the frontend on another origin."],
] as const;

const DEFAULT_REPO = "https://github.com/syed-waleed-ahmed/Multi-Agent-Research-Team";

function installSnippet(repo: string): string {
  const folder = repo.replace(/\/+$/, "").split("/").pop() || "Multi-Agent-Research-Team";
  return `git clone ${repo}.git
cd ${folder}
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -e ".[web]"
cp .env.example .env               # then add GROQ_API_KEY and SERPER_API_KEY`;
}

const BUILD = `cd frontend
npm ci
npm run build                      # writes frontend/dist, served by the backend
cd ..
research-team-web                  # http://localhost:8000`;

const DEV = `research-team-web                                   # API on :8000
cd frontend
API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev  # UI with hot reload`;

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-heading`} className="scroll-mt-24">
      <h2 id={`${id}-heading`} className="text-xl font-semibold tracking-tight sm:text-2xl">
        {title}
      </h2>
      <div className="mt-4 space-y-4 text-base leading-7 text-fg-muted">{children}</div>
    </section>
  );
}

function LimitsList({ limits, persistence }: { limits: LimitsOut | null; persistence: string | null }) {
  const minutes = limits ? Math.round(limits.job_timeout_seconds / 60) : null;
  return (
    <ul className="list-disc space-y-2 pl-5">
      <li>
        {limits ? (
          <>
            Each visitor can start up to <strong className="text-fg">{limits.jobs_per_ip_per_hour} runs per hour</strong> and{" "}
            <strong className="text-fg">{limits.jobs_per_ip_per_day} per day</strong>; the whole instance accepts up to{" "}
            {limits.global_jobs_per_day} runs per day.
          </>
        ) : (
          "Runs are limited per visitor (per hour and per day) and per instance (per day)."
        )}{" "}
        Repeating a recent identical request reuses its report without using quota.
      </li>
      <li>
        {limits
          ? `${limits.max_concurrent_jobs} ${limits.max_concurrent_jobs === 1 ? "run executes" : "runs execute"} at a time; others wait in a short queue, and each run stops after ${minutes} minute${minutes === 1 ? "" : "s"}.`
          : "A limited number of runs execute at a time; others wait in a short queue, and each run has a time limit."}
      </li>
      <li>
        The language-model provider's free tier has its own per-minute token limits. At busy times a run can stop with a
        rate-limit error — waiting a minute and trying again usually works.
      </li>
      <li>
        Free hosting instances sleep when idle. The first request after a pause can take up to a minute while the server
        wakes up.
      </li>
      <li>
        {persistence === "ephemeral"
          ? "This instance stores results on an ephemeral disk: they are cleared when the server restarts. Download reports you want to keep."
          : "Finished research is deleted after a retention period. Download reports you want to keep."}
      </li>
      <li>There is no uptime guarantee, and AI-generated reports can contain mistakes. Verify important facts.</li>
    </ul>
  );
}

export default function AboutPage() {
  const { meta } = useMeta();
  useDocumentTitle("About & docs");
  const repo = meta?.repository_url ?? null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold text-accent">About &amp; documentation</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">How the research team works</h1>
        <p className="mt-4 text-lg leading-8 text-fg-muted">
          An open-source platform where three AI agents research a topic on the web, write code examples and deliver a
          cited Markdown report. This page explains the architecture, what each agent does, how to run your own instance
          and what the free-tier limits mean.
        </p>
      </div>

      <div className="mt-12 grid gap-12 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <nav aria-label="On this page" className="lg:sticky lg:top-24 lg:self-start">
          <p className="text-sm font-semibold">On this page</p>
          <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm lg:flex-col">
            {SECTIONS.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`} className="text-fg-muted hover:text-fg">
                  {section.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="min-w-0 space-y-16">
          <Section id="architecture" title="Architecture">
            <p>
              A single FastAPI process serves the API and this interface. Submitted topics become persisted jobs that a
              bounded worker pool runs one by one. As the CrewAI pipeline executes, the engine emits real progress events
              — stage changes, searches, model requests, retries — which are stored and streamed to the browser.
            </p>
            <ArchitectureDiagram />
          </Section>

          <Section id="agents" title="Agent responsibilities">
            <div className="grid gap-4 md:grid-cols-3">
              {AGENT_DETAILS.map((agent, index) => (
                <div key={agent.name} className={cn(cardClasses, "p-5")}>
                  <p className="text-xs font-medium text-fg-subtle">Step {index + 1}</p>
                  <h3 className="font-semibold text-fg">{agent.name}</h3>
                  <ul className="mt-3 list-disc space-y-2 pl-4 text-sm leading-6">
                    {agent.points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </Section>

          <Section id="stack" title="Tech stack">
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-muted text-fg">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      Component
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      Role
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line bg-surface">
                  {STACK.map(([name, role]) => (
                    <tr key={name}>
                      <th scope="row" className="px-4 py-2.5 font-medium whitespace-nowrap text-fg">
                        {name}
                      </th>
                      <td className="px-4 py-2.5">{role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section id="self-hosting" title="Self-hosting quick start">
            <p>
              You need Python 3.10+, Node.js 22+, a free{" "}
              <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer" className="text-accent underline underline-offset-2">
                Groq API key
              </a>{" "}
              and a free{" "}
              <a href="https://serper.dev" target="_blank" rel="noopener noreferrer" className="text-accent underline underline-offset-2">
                Serper API key
              </a>
              .
            </p>
            <h3 className="text-base font-semibold text-fg">1. Install the backend</h3>
            <CodeSnippet code={installSnippet(repo ?? DEFAULT_REPO)} />
            <h3 className="text-base font-semibold text-fg">2. Build the interface and start the server</h3>
            <CodeSnippet code={BUILD} />
            <h3 className="text-base font-semibold text-fg">Developing the interface</h3>
            <CodeSnippet code={DEV} />
            <h3 className="text-base font-semibold text-fg">Main settings</h3>
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-muted text-fg">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      Variable
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      Needed
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      Purpose
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line bg-surface">
                  {ENV_VARS.map(([name, needed, purpose]) => (
                    <tr key={name}>
                      <th scope="row" className="px-4 py-2.5 font-mono text-xs font-medium text-fg">
                        {name}
                      </th>
                      <td className="px-4 py-2.5 whitespace-nowrap">{needed}</td>
                      <td className="px-4 py-2.5">{purpose}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm">
              The full list, including fallback providers and every abuse limit, is documented in{" "}
              <code className="rounded bg-surface-muted px-1 py-0.5 font-mono text-[0.85em] text-fg">.env.example</code>.
            </p>
          </Section>

          <Section id="limits" title="Free-tier limits, honestly">
            <p>
              This public instance runs on free tiers of hosting, model inference and web search. To keep it available for
              everyone, it enforces limits:
            </p>
            <LimitsList limits={meta?.limits ?? null} persistence={meta?.persistence ?? null} />
          </Section>

          <Section id="api" title="API">
            <p>
              Everything the interface does is available over a versioned JSON API under{" "}
              <code className="rounded bg-surface-muted px-1 py-0.5 font-mono text-[0.85em] text-fg">/api/v1</code>: submit a
              topic, follow its events, read the result and download it as Markdown or JSON. Errors always use the same
              envelope with a stable code and a user-safe message.
            </p>
            {meta?.api_docs && (
              <a href={apiUrl("/api/docs")} className={buttonClasses("secondary")}>
                <BookOpen aria-hidden="true" className="size-4" />
                Interactive API docs
              </a>
            )}
          </Section>

          <Section id="license" title="License & contributing">
            <p>
              The project is released under the MIT License. Bug reports, ideas and pull requests are welcome — the
              contributing guide explains the development setup and checks.
            </p>
            {repo && (
              <div className="flex flex-wrap gap-3">
                <a href={repo} target="_blank" rel="noopener noreferrer" className={buttonClasses("primary")}>
                  <GitHubMark className="size-4" />
                  Repository
                </a>
                <a
                  href={`${repo}/blob/main/CONTRIBUTING.md`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={buttonClasses("secondary")}
                >
                  Contributing guide
                  <ExternalLink aria-hidden="true" className="size-4" />
                </a>
                <a
                  href={`${repo}/blob/main/LICENSE`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={buttonClasses("secondary")}
                >
                  MIT License
                  <ExternalLink aria-hidden="true" className="size-4" />
                </a>
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
