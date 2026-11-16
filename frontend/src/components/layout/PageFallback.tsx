import { Skeleton } from "../ui/Skeleton";

/** Placeholder while a page's code is loading. */
export function PageFallback() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8" aria-busy="true">
      <span className="sr-only">Loading…</span>
      <Skeleton className="h-8 w-64 max-w-full" />
      <Skeleton className="mt-4 h-4 w-full max-w-xl" />
      <Skeleton className="mt-2 h-4 w-full max-w-lg" />
      <Skeleton className="mt-8 h-48 w-full" />
    </div>
  );
}
