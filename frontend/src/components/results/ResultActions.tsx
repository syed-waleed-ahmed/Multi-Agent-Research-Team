import { Braces, Check, Copy, FileDown, Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { copyText } from "../../lib/clipboard";
import { Button } from "../ui/Button";
import { buttonClasses } from "../ui/styles";

type CopyState = "idle" | "copied" | "failed";

interface ResultActionsProps {
  jobId: string;
  reportMarkdown: string;
}

export function ResultActions({ jobId, reportMarkdown }: ResultActionsProps) {
  const [copyState, setCopyState] = useState<CopyState>("idle");

  useEffect(() => {
    if (copyState === "idle") return;
    const timer = window.setTimeout(() => setCopyState("idle"), 2500);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  const onCopy = () => {
    void copyText(reportMarkdown).then((ok) => setCopyState(ok ? "copied" : "failed"));
  };

  return (
    <div className="flex flex-wrap gap-2 print:hidden">
      <Button variant="secondary" size="sm" onClick={onCopy}>
        {copyState === "copied" ? (
          <Check aria-hidden="true" className="size-4 text-success" />
        ) : (
          <Copy aria-hidden="true" className="size-4" />
        )}
        {copyState === "copied" ? "Copied" : "Copy report"}
      </Button>
      <a href={api.downloadUrl(jobId, "md")} download className={buttonClasses("secondary", "sm")}>
        <FileDown aria-hidden="true" className="size-4" />
        Download Markdown
      </a>
      <a href={api.downloadUrl(jobId, "json")} download className={buttonClasses("secondary", "sm")}>
        <Braces aria-hidden="true" className="size-4" />
        Download JSON
      </a>
      <Button variant="secondary" size="sm" onClick={() => window.print()}>
        <Printer aria-hidden="true" className="size-4" />
        Print / Save as PDF
      </Button>
      <p role="status" className="sr-only">
        {copyState === "copied" ? "Report copied to the clipboard." : copyState === "failed" ? "Copying failed." : ""}
      </p>
      {copyState === "failed" && (
        <p className="basis-full text-xs text-danger">Copying is blocked in this browser. Use Download Markdown instead.</p>
      )}
    </div>
  );
}
