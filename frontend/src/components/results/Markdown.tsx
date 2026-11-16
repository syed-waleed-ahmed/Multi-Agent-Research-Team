import { Check, Copy, TriangleAlert } from "lucide-react";
import { createContext, useContext, useMemo, useState, type ComponentPropsWithoutRef, type ReactNode } from "react";
import ReactMarkdown, { type Components, type Options } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { copyText } from "../../lib/clipboard";
import { cn } from "../../lib/cn";
import { normalizeUrl, safeHttpUrl } from "../../lib/format";

/** Normalized URLs of report links that were not among the retrieved search results. */
const UnverifiedContext = createContext<ReadonlySet<string>>(new Set());

interface HastNode {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

function hastText(node: HastNode | undefined): string {
  if (!node) return "";
  if (node.type === "text") return node.value ?? "";
  return (node.children ?? []).map(hastText).join("");
}

function codeLanguage(pre: HastNode | undefined): string | null {
  const code = pre?.children?.find((child) => child.tagName === "code");
  const className = code?.properties?.className;
  const classes = Array.isArray(className) ? className.map(String) : [];
  const language = classes.find((name) => name.startsWith("language-"));
  return language ? language.slice("language-".length) : null;
}

function CopyCodeButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const onClick = () => {
    void copyText(text).then((ok) => {
      if (!ok) return;
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium text-fg-muted transition-colors hover:bg-surface hover:text-fg print:hidden"
    >
      {copied ? <Check aria-hidden="true" className="size-3.5" /> : <Copy aria-hidden="true" className="size-3.5" />}
      <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

type Level = 1 | 2 | 3 | 4 | 5 | 6;

/** Report headings are rendered one level down so the page keeps a single h1. */
function heading(level: Level) {
  const Tag = `h${Math.min(level + 1, 6)}` as "h2" | "h3" | "h4" | "h5" | "h6";
  function Heading({ node: _node, className, ...props }: ComponentPropsWithoutRef<"h1"> & { node?: unknown }) {
    return <Tag className={cn(`md-h${level}`, className)} {...props} />;
  }
  return Heading;
}

function SafeLink({ node: _node, href, children, ...props }: ComponentPropsWithoutRef<"a"> & { node?: unknown }) {
  const unverified = useContext(UnverifiedContext);
  const safe = safeHttpUrl(href);
  if (!safe) return <span>{children}</span>;
  const flagged = unverified.has(normalizeUrl(safe));
  return (
    <>
      <a {...props} href={safe} target="_blank" rel="noopener noreferrer nofollow" className="print-url">
        {children}
      </a>
      {flagged && (
        <span
          className="ml-0.5 inline-flex translate-y-0.5 text-warning"
          title="Not found in retrieved search results — verify before relying on it"
        >
          <TriangleAlert aria-hidden="true" className="size-3.5" />
          <span className="sr-only"> (not found in retrieved search results; verify before relying on it)</span>
        </span>
      )}
    </>
  );
}

function SafeImage({ node: _node, src, alt }: ComponentPropsWithoutRef<"img"> & { node?: unknown }) {
  // External images are not loaded (privacy and Content-Security-Policy); link to them instead.
  const safe = typeof src === "string" ? safeHttpUrl(src) : null;
  const label = alt?.trim() ? `Image: ${alt}` : "Image";
  if (!safe) return <span className="text-fg-muted">[{label}]</span>;
  return (
    <a href={safe} target="_blank" rel="noopener noreferrer nofollow">
      [{label}]
    </a>
  );
}

function CodeBlock({ node, children }: ComponentPropsWithoutRef<"pre"> & { node?: unknown }) {
  const hast = node as HastNode | undefined;
  const language = codeLanguage(hast);
  return (
    <div className="code-block overflow-hidden rounded-lg border border-line">
      <div className="flex items-center justify-between gap-2 border-b border-line bg-surface-muted px-3 py-1">
        <span className="font-mono text-xs text-fg-subtle">{language ?? "code"}</span>
        <CopyCodeButton text={hastText(hast).replace(/\n$/, "")} />
      </div>
      <pre>{children}</pre>
    </div>
  );
}

function Table({ node: _node, ...props }: ComponentPropsWithoutRef<"table"> & { node?: unknown }) {
  return (
    <div className="table-wrap">
      <table {...props} />
    </div>
  );
}

const COMPONENTS: Components = {
  h1: heading(1),
  h2: heading(2),
  h3: heading(3),
  h4: heading(4),
  h5: heading(5),
  h6: heading(6),
  a: SafeLink,
  img: SafeImage,
  pre: CodeBlock,
  table: Table,
};

/** Only absolute http(s) links survive; everything else renders as plain text. */
function urlTransform(url: string): string {
  return safeHttpUrl(url) ?? "";
}

const REMARK_PLUGINS: Options["remarkPlugins"] = [remarkGfm];
const REHYPE_PLUGINS: Options["rehypePlugins"] = [[rehypeHighlight, { detect: false }]];

interface MarkdownProps {
  children: string;
  /** Links to flag as unverified (from the citation check). */
  unverifiedUrls?: readonly string[];
  className?: string;
}

/**
 * Renders model-written Markdown safely: raw HTML is never rendered (no
 * rehype-raw), links open in a new tab with `noopener noreferrer nofollow`.
 */
export function Markdown({ children, unverifiedUrls, className }: MarkdownProps): ReactNode {
  const unverified = useMemo(() => new Set((unverifiedUrls ?? []).map(normalizeUrl)), [unverifiedUrls]);
  return (
    <UnverifiedContext.Provider value={unverified}>
      <div className={cn("markdown", className)}>
        <ReactMarkdown
          remarkPlugins={REMARK_PLUGINS}
          rehypePlugins={REHYPE_PLUGINS}
          components={COMPONENTS}
          urlTransform={urlTransform}
        >
          {children}
        </ReactMarkdown>
      </div>
    </UnverifiedContext.Provider>
  );
}
