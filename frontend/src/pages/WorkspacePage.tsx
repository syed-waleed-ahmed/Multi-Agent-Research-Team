import { Plus } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { HistoryList } from "../components/research/HistoryList";
import { JobView } from "../components/research/JobView";
import { QuotaCard } from "../components/research/QuotaCard";
import { ResearchForm } from "../components/research/ResearchForm";
import { buttonClasses, cardClasses } from "../components/ui/styles";
import { useMeta } from "../hooks/metaContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useStartResearch } from "../hooks/useStartResearch";
import { useUsage } from "../hooks/useUsage";
import { cn } from "../lib/cn";

interface WorkspaceLocationState {
  topic?: unknown;
  autoStart?: unknown;
}

function NewResearch({ refreshUsage, usage }: { refreshUsage: () => void; usage: ReturnType<typeof useUsage> }) {
  const { meta } = useMeta();
  const location = useLocation();
  const navigate = useNavigate();
  const starter = useStartResearch(refreshUsage);
  useDocumentTitle("New research");

  const state = (location.state ?? null) as WorkspaceLocationState | null;
  const topic = typeof state?.topic === "string" ? state.topic : "";
  const autoStart = state?.autoStart === true && topic.trim().length >= 3;

  // "Start research" on the landing page submits immediately with the default options.
  const started = useRef(false);
  const { start } = starter;
  useEffect(() => {
    if (!autoStart || started.current) return;
    started.current = true;
    // Drop the auto-start flag so a reload or back navigation never submits twice.
    void navigate(location.pathname, { replace: true, state: { topic } });
    void start({ topic: topic.trim(), depth: "standard", report_style: "technical_report" });
  }, [autoStart, location.pathname, navigate, start, topic]);

  return (
    <div className={cn(cardClasses, "p-5 sm:p-8")}>
      <ResearchForm meta={meta} usage={usage.usage} starter={starter} initialTopic={topic} />
    </div>
  );
}

export default function WorkspacePage() {
  const { id } = useParams();
  const { meta } = useMeta();
  const usage = useUsage();

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0">
          {id ? (
            <JobView key={id} jobId={id} meta={meta} onFinished={usage.refresh} />
          ) : (
            <NewResearch refreshUsage={usage.refresh} usage={usage} />
          )}
        </div>
        <aside aria-label="Quota and history" className="min-w-0 space-y-6 print:hidden">
          {id && (
            <Link to="/research" className={buttonClasses("secondary", "md", "w-full")}>
              <Plus aria-hidden="true" className="size-4" />
              New research
            </Link>
          )}
          <QuotaCard usage={usage.usage} error={usage.error} meta={meta} />
          <HistoryList />
        </aside>
      </div>
    </div>
  );
}
