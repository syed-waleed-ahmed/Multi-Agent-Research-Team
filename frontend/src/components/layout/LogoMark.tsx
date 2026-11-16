import { cn } from "../../lib/cn";

/** Three connected nodes: the three agents working in sequence. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className={cn("size-7", className)}>
      <rect width="32" height="32" rx="8" className="fill-accent-solid" />
      <circle cx="10" cy="11" r="3" fill="#fff" />
      <circle cx="22" cy="11" r="3" fill="#fff" fillOpacity=".8" />
      <circle cx="16" cy="22" r="3.5" fill="#fff" />
      <path d="M12.4 13.2 14.6 19M19.6 13.2 17.4 19M13 11h6" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
