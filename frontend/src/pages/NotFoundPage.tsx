import { ArrowRight, Compass } from "lucide-react";
import { Link } from "react-router";
import { buttonClasses } from "../components/ui/styles";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export default function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-24 text-center sm:py-32">
      <span className="flex size-12 items-center justify-center rounded-xl bg-surface-muted text-fg-muted">
        <Compass aria-hidden="true" className="size-6" />
      </span>
      <p className="mt-6 text-sm font-semibold text-accent">404</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-3 text-base leading-7 text-fg-muted">
        The page you are looking for does not exist or has moved. Research links stay valid only while the run is
        kept on the server.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link to="/" className={buttonClasses("secondary")}>
          Back to home
        </Link>
        <Link to="/research" className={buttonClasses("primary")}>
          Start research
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </div>
    </div>
  );
}
