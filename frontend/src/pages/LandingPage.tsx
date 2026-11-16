import {
  ArrowRight,
  BadgeCheck,
  Braces,
  ClipboardCheck,
  CodeXml,
  Eye,
  FileDown,
  Gauge,
  Printer,
  Radio,
  Scale,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { GitHubMark } from "../components/layout/GitHubMark";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { buttonClasses, cardClasses } from "../components/ui/styles";
import { useMeta } from "../hooks/metaContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { cn } from "../lib/cn";

const SUGGESTIONS = [
  "How do vector databases support retrieval-augmented generation?",
  "Event sourcing vs. CRUD for an order-management service",
  "Practical patterns for rate limiting a public REST API",
];

const AGENTS = [
  {
    Icon: Search,
    name: "Research Agent",
    output: "Sourced research notes",
    text: "Plans targeted web searches (2, 4 or 6 depending on depth), reads the results and writes notes that keep every source URL.",
  },
  {
    Icon: CodeXml,
    name: "Coding Agent",
    output: "Code examples",
    text: "Turns the findings into practical code and implementation notes, so the report is something you can act on.",
  },
  {
    Icon: ClipboardCheck,
    name: "Manager Agent",
    output: "Final cited report",
    text: "Reviews the notes and code, resolves gaps and writes the final Markdown report in the style you chose, with references.",
  },
];

const VALUE = [
  {
    Icon: BadgeCheck,
    title: "Sourced, not just generated",
    text: "Every link in the report is checked against the pages search actually returned. Links that were not retrieved are flagged so you know what to verify.",
  },
  {
    Icon: Braces,
    title: "Practical by default",
    text: "A dedicated agent writes code examples and implementation notes instead of leaving you with a summary of a summary.",
  },
  {
    Icon: Eye,
    title: "Transparent while it works",
    text: "Watch each agent start and finish, every search query and model request, retries and provider fallbacks — as they really happen.",
  },
];

const STEPS = [
  { title: "Describe your topic", text: "Add optional instructions, pick a depth and a report style." },
  { title: "Agents run in sequence", text: "Research, then code, then review — streamed live to your browser." },
  { title: "Review with evidence", text: "Read the report next to its sources and the citation check." },
  { title: "Keep it", text: "Copy it, download Markdown or JSON, or print it to PDF." },
];

const FEATURES = [
  { Icon: Radio, title: "Live agent view", text: "Real progress events over Server-Sent Events, with a polling fallback." },
  { Icon: ShieldCheck, title: "Cited sources with citation check", text: "Retrieved sources listed with their queries; unretrieved links flagged." },
  { Icon: CodeXml, title: "Code examples", text: "Highlighted, copyable code blocks from the Coding Agent." },
  { Icon: FileDown, title: "Markdown & JSON download", text: "The report with sources and methodology, or the full structured result." },
  { Icon: Printer, title: "Print to PDF", text: "A print layout with just the report and its sources." },
  { Icon: Scale, title: "Open source (MIT)", text: "Read the code, self-host it, change it." },
  { Icon: Gauge, title: "Free-tier friendly", text: "Per-visitor quotas, a job queue and reuse of identical recent requests." },
];

const STACK = [
  { name: "CrewAI", role: "Agent orchestration" },
  { name: "Groq", role: "LLM inference" },
  { name: "Serper / Tavily", role: "Web search" },
  { name: "FastAPI", role: "API and live event stream" },
  { name: "React", role: "This interface" },
  { name: "SQLite / Postgres", role: "Job and result storage" },
];

function SectionHeading({ eyebrow, title, text, id }: { eyebrow: string; title: string; text?: string; id: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-sm font-semibold text-accent">{eyebrow}</p>
      <h2 id={id} className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
        {title}
      </h2>
      {text && <p className="mt-3 text-base leading-7 text-fg-muted">{text}</p>}
    </div>
  );
}

function HeroForm() {
  const navigate = useNavigate();
  const { meta } = useMeta();
  const ids = useId();
  const [topic, setTopic] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = topic.trim();
    if (trimmed.length < 3) {
      setError("Enter a topic of at least 3 characters.");
      return;
    }
    void navigate("/research", { state: { topic: trimmed, autoStart: true } });
  };

  return (
    <form onSubmit={onSubmit} noValidate className="mt-8">
      <label htmlFor={`${ids}-topic`} className="sr-only">
        Research topic
      </label>
      <div className="flex flex-col gap-2 rounded-xl border border-line-strong bg-surface p-2 shadow-sm transition-shadow focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/25 sm:flex-row">
        <input
          id={`${ids}-topic`}
          type="text"
          name="topic"
          value={topic}
          maxLength={meta?.limits.max_topic_chars}
          onChange={(event) => {
            setTopic(event.target.value);
            if (error) setError(null);
          }}
          placeholder="What do you want to research?"
          aria-invalid={error !== null || undefined}
          aria-describedby={error ? `${ids}-error` : undefined}
          className="h-12 w-full min-w-0 flex-1 rounded-lg bg-transparent px-3 text-base text-fg placeholder:text-fg-subtle focus:outline-none"
        />
        <Button type="submit" size="lg" className="sm:w-auto">
          Start research
          <ArrowRight aria-hidden="true" className="size-4" />
        </Button>
      </div>
      {error && (
        <p id={`${ids}-error`} className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-fg-subtle">Try:</span>
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => {
              setTopic(suggestion);
              setError(null);
            }}
            className="max-w-full truncate rounded-full border border-line bg-surface px-3 py-1 text-fg-muted transition-colors hover:border-line-strong hover:text-fg"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </form>
  );
}

function PipelineIllustration() {
  return (
    <div className={cn(cardClasses, "p-5 sm:p-6")} aria-labelledby="flow-heading" role="group">
      <p id="flow-heading" className="text-sm font-semibold">
        How a run flows
      </p>
      <ol className="mt-5 space-y-4">
        {AGENTS.map(({ Icon, name, output }, index) => (
          <li key={name} className="relative flex gap-4">
            {index < AGENTS.length - 1 && (
              <span aria-hidden="true" className="absolute top-11 bottom-[-1rem] left-5 w-px bg-line" />
            )}
            <span className="relative flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-soft-fg">
              <Icon aria-hidden="true" className="size-5" />
            </span>
            <div className="min-w-0 flex-1 rounded-lg border border-line bg-page px-4 py-3">
              <p className="text-xs font-medium text-fg-subtle">Step {index + 1}</p>
              <p className="font-semibold">{name}</p>
              <p className="mt-0.5 text-sm text-fg-muted">Produces: {output}</p>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-5 flex items-start gap-2 border-t border-line pt-4 text-sm text-fg-muted">
        <Sparkles aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-accent" />
        You follow every step live, then get the report with its sources, citation check and methodology.
      </p>
    </div>
  );
}

export default function LandingPage() {
  const { meta } = useMeta();
  useDocumentTitle(null);

  return (
    <>
      <section aria-labelledby="hero-heading" className="border-b border-line bg-surface">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 md:py-20 lg:grid-cols-[1.15fr_1fr] lg:items-center lg:px-8 lg:py-24">
          <div className="min-w-0">
            <p className="inline-flex items-center gap-2 rounded-full border border-line bg-page px-3 py-1 text-xs font-medium text-fg-muted">
              <Scale aria-hidden="true" className="size-3.5" />
              Open source · MIT licensed · free to use
            </p>
            <h1
              id="hero-heading"
              className="mt-6 text-4xl font-semibold tracking-tight text-balance sm:text-5xl lg:text-[3.4rem] lg:leading-[1.08]"
            >
              Research any topic with a team of AI agents
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-fg-muted">
              A Research Agent searches the web and takes sourced notes, a Coding Agent writes practical examples, and
              a Manager Agent turns it all into a cited report. You watch every step as it happens.
            </p>
            <HeroForm />
          </div>
          <PipelineIllustration />
        </div>
      </section>

      <section aria-labelledby="value-heading" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <SectionHeading
          id="value-heading"
          eyebrow="Why it's useful"
          title="A research assistant that shows its work"
          text="Language models write fluent text whether or not they know the answer. This platform keeps the evidence next to the answer, so you can judge it."
        />
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {VALUE.map(({ Icon, title, text }) => (
            <div key={title} className={cn(cardClasses, "p-6")}>
              <Icon aria-hidden="true" className="size-6 text-accent" />
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-fg-muted">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="agents-heading" className="border-y border-line bg-surface">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <SectionHeading
            id="agents-heading"
            eyebrow="The team"
            title="Three specialists, one after another"
            text="Each agent has one job and passes its output to the next. Running them in sequence keeps runs predictable and easy to follow."
          />
          <ol className="mt-10 grid gap-5 md:grid-cols-3">
            {AGENTS.map(({ Icon, name, text, output }, index) => (
              <li key={name} className="rounded-xl border border-line bg-page p-6">
                <div className="flex items-center gap-3">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-accent-soft text-accent-soft-fg">
                    <Icon aria-hidden="true" className="size-5" />
                  </span>
                  <div>
                    <p className="text-xs font-medium text-fg-subtle">Agent {index + 1}</p>
                    <h3 className="font-semibold">{name}</h3>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-fg-muted">{text}</p>
                <p className="mt-4 text-xs font-medium text-fg-subtle">Output: {output}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="how-heading" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <SectionHeading id="how-heading" eyebrow="How it works" title="From question to report in four steps" />
        <ol className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li key={step.title} className="relative">
              <span className="flex size-8 items-center justify-center rounded-full border border-line-strong text-sm font-semibold tabular-nums">
                {index + 1}
              </span>
              <h3 className="mt-4 font-semibold">{step.title}</h3>
              <p className="mt-1.5 text-sm leading-6 text-fg-muted">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="features-heading" className="border-y border-line bg-surface">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <SectionHeading id="features-heading" eyebrow="Features" title="What you get with every run" />
          <ul className="mt-10 grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ Icon, title, text }) => (
              <li key={title} className="flex gap-4">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-page">
                  <Icon aria-hidden="true" className="size-4.5 text-accent" />
                </span>
                <div>
                  <h3 className="font-semibold">{title}</h3>
                  <p className="mt-1 text-sm leading-6 text-fg-muted">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="stack-heading" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <SectionHeading
          id="stack-heading"
          eyebrow="Technology"
          title="Built on open, swappable components"
          text="Free tiers of hosted services by default. Model and search providers can be swapped through configuration."
        />
        <ul className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STACK.map((item) => (
            <li key={item.name} className={cn(cardClasses, "flex items-baseline justify-between gap-3 px-5 py-4")}>
              <span className="font-semibold">{item.name}</span>
              <span className="text-right text-sm text-fg-muted">{item.role}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="oss-heading" className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
        <div className="rounded-2xl border border-line bg-surface px-6 py-12 text-center shadow-xs sm:px-12">
          <h2 id="oss-heading" className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Open source and self-hostable
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-base leading-7 text-fg-muted">
            This instance runs on free tiers with shared quotas. Run your own with free Groq and Serper keys — the
            backend, the agents and this interface are all MIT licensed.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {meta ? (
              <a href={meta.repository_url} target="_blank" rel="noopener noreferrer" className={buttonClasses("primary", "lg")}>
                <GitHubMark className="size-4.5" />
                View on GitHub
              </a>
            ) : (
              <Skeleton className="h-12 w-44 rounded-lg" />
            )}
            <Link to="/about" className={buttonClasses("secondary", "lg")}>
              Self-hosting guide
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
