import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { copyText } from "../../lib/clipboard";

/** A shell snippet with a copy button (no highlighting needed for commands). */
export function CodeSnippet({ code, label = "shell" }: { code: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = () => {
    void copyText(code).then((ok) => {
      if (!ok) return;
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div className="overflow-hidden rounded-lg border border-line">
      <div className="flex items-center justify-between border-b border-line bg-surface-muted px-3 py-1">
        <span className="font-mono text-xs text-fg-subtle">{label}</span>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium text-fg-muted transition-colors hover:bg-surface hover:text-fg"
        >
          {copied ? <Check aria-hidden="true" className="size-3.5" /> : <Copy aria-hidden="true" className="size-3.5" />}
          <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="overflow-x-auto bg-code-bg px-4 py-3 font-mono text-[0.8125rem] leading-6 text-code-fg">
        <code>{code}</code>
      </pre>
    </div>
  );
}
