import { ArrowRight, Settings2 } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import type { StartResearch } from "../../hooks/useStartResearch";
import { ApiError } from "../../lib/api";
import { cn } from "../../lib/cn";
import { DEPTH_INFO, REPORT_STYLE_INFO } from "../../lib/labels";
import type { Depth, MetaOut, ReportStyle, UsageOut } from "../../lib/types";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/Skeleton";
import { Spinner } from "../ui/Spinner";
import { inputClasses } from "../ui/styles";
import { ErrorNotice } from "./ErrorNotice";

const DEPTHS: Depth[] = ["quick", "standard", "deep"];
const STYLES: ReportStyle[] = ["technical_report", "executive_brief", "tutorial"];
const MIN_TOPIC_CHARS = 3;
const NOT_CONFIGURED = new ApiError(
  503,
  "not_configured",
  "This server has no language model configured, so research runs cannot start.",
);

interface ResearchFormProps {
  meta: MetaOut | null;
  usage: UsageOut | null;
  starter: StartResearch;
  initialTopic?: string;
}

function CharCount({ id, length, max }: { id: string; length: number; max: number | undefined }) {
  if (!max) return <span id={id} className="text-xs text-fg-subtle tabular-nums">{length}</span>;
  const near = length > max * 0.9;
  return (
    <span id={id} className={cn("text-xs tabular-nums", length > max ? "text-danger" : near ? "text-warning" : "text-fg-subtle")}>
      {length} / {max}
      <span className="sr-only"> characters</span>
    </span>
  );
}

interface OptionCardProps<T extends string> {
  name: string;
  value: T;
  checked: boolean;
  onSelect: (value: T) => void;
  title: string;
  description: string;
}

function OptionCard<T extends string>({ name, value, checked, onSelect, title, description }: OptionCardProps<T>) {
  return (
    <label
      className={cn(
        "relative flex cursor-pointer flex-col gap-1 rounded-lg border p-3 text-sm transition-colors",
        "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-ring",
        checked ? "border-accent-solid bg-accent-soft" : "border-line-strong bg-surface hover:bg-surface-muted",
      )}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => onSelect(value)}
        className="sr-only"
      />
      <span className={cn("font-semibold", checked ? "text-accent-soft-fg" : "text-fg")}>{title}</span>
      <span className="text-xs leading-5 text-fg-muted">{description}</span>
    </label>
  );
}

export function ResearchForm({ meta, usage, starter, initialTopic = "" }: ResearchFormProps) {
  const ids = useId();
  const [topic, setTopic] = useState(initialTopic);
  const [instructions, setInstructions] = useState("");
  const [depth, setDepth] = useState<Depth>("standard");
  const [style, setStyle] = useState<ReportStyle>("technical_report");
  const [model, setModel] = useState<string | null>(null);
  const [attempted, setAttempted] = useState(false);

  const limits = meta?.limits;
  const models = meta?.models ?? [];
  const defaultModel = models.find((item) => item.default)?.id ?? models[0]?.id ?? null;
  const selectedModel = model ?? defaultModel;
  const notConfigured = meta !== null && models.length === 0;

  const trimmedTopic = topic.trim();
  const topicError =
    trimmedTopic.length < MIN_TOPIC_CHARS
      ? `Enter at least ${MIN_TOPIC_CHARS} characters.`
      : limits && trimmedTopic.length > limits.max_topic_chars
        ? `Keep the topic under ${limits.max_topic_chars} characters.`
        : null;
  const instructionsError =
    limits && instructions.trim().length > limits.max_instructions_chars
      ? `Keep instructions under ${limits.max_instructions_chars} characters.`
      : null;
  const remaining = usage ? Math.max(0, usage.jobs_per_ip_per_day - usage.jobs_today) : null;

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAttempted(true);
    if (topicError || instructionsError || starter.submitting || notConfigured) return;
    void starter.start({
      topic: trimmedTopic,
      instructions: instructions.trim() || null,
      depth,
      report_style: style,
      model: selectedModel,
    });
  };

  const showTopicError = attempted && topicError !== null;

  return (
    <form onSubmit={onSubmit} noValidate aria-labelledby={`${ids}-title`} className="space-y-7">
      <div>
        <h1 id={`${ids}-title`} className="text-2xl font-semibold tracking-tight">
          New research
        </h1>
        <p className="mt-1 text-sm text-fg-muted">
          Describe what you want to know. The three agents run one after another and you can watch each step live.
        </p>
      </div>

      {notConfigured && <ErrorNotice error={NOT_CONFIGURED} />}

      <div>
        <div className="flex items-baseline justify-between gap-3">
          <label htmlFor={`${ids}-topic`} className="text-sm font-medium">
            Research topic
          </label>
          <CharCount id={`${ids}-topic-count`} length={topic.length} max={limits?.max_topic_chars} />
        </div>
        <textarea
          id={`${ids}-topic`}
          name="topic"
          rows={3}
          required
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          placeholder="e.g. How do vector databases support retrieval-augmented generation?"
          aria-invalid={showTopicError || undefined}
          aria-describedby={cn(`${ids}-topic-count`, showTopicError && `${ids}-topic-error`)}
          className={cn(inputClasses, "mt-2 resize-y")}
        />
        {showTopicError && (
          <p id={`${ids}-topic-error`} className="mt-1.5 text-sm text-danger">
            {topicError}
          </p>
        )}
      </div>

      <div>
        <div className="flex items-baseline justify-between gap-3">
          <label htmlFor={`${ids}-instructions`} className="text-sm font-medium">
            Instructions <span className="font-normal text-fg-subtle">(optional)</span>
          </label>
          <CharCount id={`${ids}-instructions-count`} length={instructions.length} max={limits?.max_instructions_chars} />
        </div>
        <textarea
          id={`${ids}-instructions`}
          name="instructions"
          rows={2}
          value={instructions}
          onChange={(event) => setInstructions(event.target.value)}
          placeholder="e.g. Focus on open-source options. The audience is a backend team new to the topic."
          aria-invalid={instructionsError !== null || undefined}
          aria-describedby={cn(`${ids}-instructions-count`, instructionsError && `${ids}-instructions-error`)}
          className={cn(inputClasses, "mt-2 resize-y")}
        />
        {instructionsError && (
          <p id={`${ids}-instructions-error`} className="mt-1.5 text-sm text-danger">
            {instructionsError}
          </p>
        )}
      </div>

      <fieldset>
        <legend className="text-sm font-medium">Depth</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {DEPTHS.map((value) => (
            <OptionCard<Depth>
              key={value}
              name={`${ids}-depth`}
              value={value}
              checked={depth === value}
              onSelect={setDepth}
              title={DEPTH_INFO[value].label}
              description={DEPTH_INFO[value].description}
            />
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="text-sm font-medium">Report style</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {STYLES.map((value) => (
            <OptionCard<ReportStyle>
              key={value}
              name={`${ids}-style`}
              value={value}
              checked={style === value}
              onSelect={setStyle}
              title={REPORT_STYLE_INFO[value].label}
              description={REPORT_STYLE_INFO[value].description}
            />
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor={`${ids}-model`} className="flex items-center gap-1.5 text-sm font-medium">
          <Settings2 aria-hidden="true" className="size-4 text-fg-subtle" />
          Model
        </label>
        {meta ? (
          <select
            id={`${ids}-model`}
            name="model"
            value={selectedModel ?? ""}
            onChange={(event) => setModel(event.target.value)}
            disabled={models.length === 0}
            className={cn(inputClasses, "mt-2 sm:max-w-md")}
          >
            {models.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} ({item.provider}){item.default ? " — default" : ""}
              </option>
            ))}
          </select>
        ) : (
          <Skeleton className="mt-2 h-10 w-full sm:max-w-md" />
        )}
      </div>

      {starter.error && <ErrorNotice error={starter.error} />}

      <div className="flex flex-col gap-3 border-t border-line pt-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-fg-muted">
          {remaining !== null && usage ? (
            <>
              <span className="font-medium text-fg">{remaining}</span> of {usage.jobs_per_ip_per_day} research runs
              left for you in the last 24 hours.
            </>
          ) : (
            "Each run counts toward a small per-visitor quota."
          )}
        </p>
        <Button type="submit" size="lg" disabled={starter.submitting || notConfigured} className="w-full sm:w-auto">
          {starter.submitting ? (
            <>
              <Spinner />
              Starting…
            </>
          ) : (
            <>
              Start research
              <ArrowRight aria-hidden="true" className="size-4" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
