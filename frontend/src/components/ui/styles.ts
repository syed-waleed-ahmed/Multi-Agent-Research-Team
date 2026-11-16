import { cn } from "../../lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-accent-solid text-accent-on shadow-sm hover:bg-accent-solid-hover disabled:hover:bg-accent-solid",
  secondary:
    "border border-line-strong bg-surface text-fg shadow-xs hover:bg-surface-muted disabled:hover:bg-surface",
  ghost: "text-fg-muted hover:bg-surface-muted hover:text-fg",
  danger:
    "border border-danger-line bg-danger-soft text-danger hover:border-danger disabled:hover:border-danger-line",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 gap-1.5 rounded-md px-2.5 text-sm",
  md: "h-10 gap-2 rounded-lg px-4 text-sm",
  lg: "h-12 gap-2 rounded-lg px-5 text-base",
  icon: "size-9 rounded-md",
};

/** Shared button look, also used for links styled as buttons. */
export function buttonClasses(variant: ButtonVariant = "primary", size: ButtonSize = "md", extra?: string) {
  return cn(
    "inline-flex shrink-0 items-center justify-center font-medium whitespace-nowrap transition-colors duration-150",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
    "disabled:cursor-not-allowed disabled:opacity-60",
    VARIANTS[variant],
    SIZES[size],
    extra,
  );
}

export const cardClasses = "rounded-xl border border-line bg-surface shadow-xs";

export const inputClasses = cn(
  "block w-full rounded-lg border border-line-strong bg-surface px-3 py-2.5 text-base text-fg shadow-xs sm:text-sm",
  "placeholder:text-fg-subtle",
  "focus:border-ring focus:outline-2 focus:outline-offset-0 focus:outline-ring/40",
  "disabled:cursor-not-allowed disabled:opacity-60",
  "aria-invalid:border-danger",
);
