import { lazy } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";
import { Layout } from "./components/layout/Layout";
import { MetaProvider } from "./hooks/MetaProvider";
import LandingPage from "./pages/LandingPage";
import RouteErrorPage from "./pages/RouteErrorPage";

// The landing page ships in the main bundle; everything else loads on demand.
const WorkspacePage = lazy(() => import("./pages/WorkspacePage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

const router = createBrowserRouter([
  {
    element: <Layout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: "research", element: <WorkspacePage /> },
      { path: "research/:id", element: <WorkspacePage /> },
      { path: "about", element: <AboutPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function App() {
  return (
    <MetaProvider>
      <RouterProvider router={router} />
    </MetaProvider>
  );
}
