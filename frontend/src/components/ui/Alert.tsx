import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

type AlertTone = "info" | "success" | "warning" | "danger";

const STYLES: Record<AlertTone, { box: string; icon: string; Icon: typeof Info }> = {
  info: { box: "border-line bg-surface-muted", icon: "text-accent", Icon: Info },
  success: { box: "border-success-line bg-success-soft", icon: "text-success", Icon: CircleCheck },
  warning: { box: "border-warning-line bg-warning-soft", icon: "text-warning", Icon: TriangleAlert },
  danger: { box: "border-danger-line bg-danger-soft", icon: "text-danger", Icon: CircleAlert },
};

interface AlertProps {
  tone?: AlertTone;
  title?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  className?: string;
  /** "alert" for errors that need attention now, "status" for polite updates. */
  role?: "alert" | "status";
}

export function Alert({ tone = "info", title, children, actions, className, role }: AlertProps) {
  const { box, icon, Icon } = STYLES[tone];
  return (
    <div role={role} className={cn("flex gap-3 rounded-lg border p-4 text-sm", box, className)}>
      <Icon aria-hidden="true" className={cn("mt-0.5 size-5 shrink-0", icon)} />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold text-fg">{title}</p>}
        {children && <div className={cn("text-fg-muted", title ? "mt-1" : undefined)}>{children}</div>}
        {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}
