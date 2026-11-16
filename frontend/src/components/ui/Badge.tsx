import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

export type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

const TONES: Record<Tone, string> = {
  neutral: "border-line bg-surface-muted text-fg-muted",
  accent: "border-transparent bg-accent-soft text-accent-soft-fg",
  success: "border-success-line bg-success-soft text-success",
  warning: "border-warning-line bg-warning-soft text-warning",
  danger: "border-danger-line bg-danger-soft text-danger",
};

interface BadgeProps {
  tone?: Tone;
  size?: "sm" | "md";
  children: ReactNode;
  className?: string;
}

export function Badge({ tone = "neutral", size = "sm", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1 rounded-full border font-medium",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
