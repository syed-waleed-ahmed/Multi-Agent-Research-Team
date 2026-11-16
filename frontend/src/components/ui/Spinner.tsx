import { LoaderCircle } from "lucide-react";
import { cn } from "../../lib/cn";

/** Decorative spinner; pair it with visible or screen-reader text. */
export function Spinner({ className }: { className?: string }) {
  return <LoaderCircle aria-hidden="true" className={cn("size-4 motion-safe:animate-spin", className)} />;
}
