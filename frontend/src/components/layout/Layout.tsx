import { Suspense } from "react";
import { Outlet, ScrollRestoration } from "react-router";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { PageFallback } from "./PageFallback";
import { ServerStatusBanner } from "./ServerStatusBanner";

export function Layout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-accent-solid px-4 py-2 text-sm font-medium text-accent-on focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>
      <Header />
      <ServerStatusBanner />
      <main id="main" tabIndex={-1} className="flex-1 focus:outline-none">
        <Suspense fallback={<PageFallback />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
      <ScrollRestoration />
    </div>
  );
}
