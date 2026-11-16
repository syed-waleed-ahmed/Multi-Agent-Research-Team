import { ChevronRight } from "lucide-react";
import { Fragment } from "react";
import { JOB_STATUS_LABEL, STAGE_STATUS_LABEL } from "../../lib/labels";
import { STAGE_ORDER, isTerminal, type JobOut, type StageOut } from "../../lib/types";
import { AgentCard } from "./AgentCard";

function orderedStages(stages: StageOut[]): StageOut[] {
  const rank = (stage: StageOut) => {
    const index = STAGE_ORDER.indexOf(stage.stage as (typeof STAGE_ORDER)[number]);
    return index === -1 ? STAGE_ORDER.length : index;
  };
  return [...stages].sort((a, b) => rank(a) - rank(b));
}

/** Sentence announced to screen readers whenever the pipeline state changes. */
function announcement(job: JobOut, stages: StageOut[]): string {
  if (job.status === "queued") {
    return job.queue_position ? `Waiting in the queue, position ${job.queue_position}.` : "Waiting in the queue.";
  }
  if (job.status === "running") {
    const parts = stages
      .filter((stage) => stage.status !== "pending")
      .map((stage) => `${stage.agent} ${STAGE_STATUS_LABEL[stage.status].toLowerCase()}`);
    return parts.length ? `${parts.join(". ")}.` : "Starting the first agent.";
  }
  if (job.status === "succeeded") return "All three agents completed. The report is ready.";
  return `Research ${JOB_STATUS_LABEL[job.status].toLowerCase()}.`;
}

export function AgentPipeline({ job }: { job: JobOut }) {
  const stages = orderedStages(job.stages);

  return (
    <section aria-labelledby="pipeline-heading" className="print:hidden">
      <h2 id="pipeline-heading" className="sr-only">
        Agents
      </h2>
      <p role="status" className="sr-only">
        {announcement(job, stages)}
      </p>
      <ol className="grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch">
        {stages.map((stage, index) => (
          <Fragment key={stage.stage}>
            {index > 0 && (
              <li aria-hidden="true" className="hidden items-center text-fg-subtle md:flex">
                <ChevronRight className="size-4" />
              </li>
            )}
            <li className="min-w-0">
              <AgentCard stage={stage} step={index + 1} jobFinished={isTerminal(job.status)} />
            </li>
          </Fragment>
        ))}
      </ol>
    </section>
  );
}
