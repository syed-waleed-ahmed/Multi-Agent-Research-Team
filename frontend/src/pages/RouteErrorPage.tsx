import { RefreshCw } from "lucide-react";
import { isRouteErrorResponse, Link, useRouteError } from "react-router";
import { Button } from "../components/ui/Button";
import { buttonClasses } from "../components/ui/styles";

/**
 * Last-resort screen for unexpected rendering errors (for example a failed
 * download of a page bundle after a redeploy). Keeps its own minimal layout.
 */
export default function RouteErrorPage() {
  const error = useRouteError();
  const status = isRouteErrorResponse(error) ? error.status : null;

  return (
    <div className="flex min-h-dvh items-center justify-center bg-page px-4">
      <div role="alert" className="max-w-md text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Something went wrong</h1>
        <p className="mt-3 text-base leading-7 text-fg-muted">
          {status
            ? `The page could not be loaded (error ${status}).`
            : "The page failed to load. Reloading usually fixes this, especially right after the site was updated."}
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button onClick={() => window.location.reload()}>
            <RefreshCw aria-hidden="true" className="size-4" />
            Reload page
          </Button>
          <Link to="/" reloadDocument className={buttonClasses("secondary")}>
            Go to home
          </Link>
        </div>
      </div>
    </div>
  );
}
