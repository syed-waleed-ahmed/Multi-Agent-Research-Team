import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CitationPanel } from "./CitationPanel";

describe("CitationPanel", () => {
  it("reports the matched count and flags unmatched links", () => {
    render(
      <CitationPanel
        check={{
          matched: ["https://docs.example.org/guide"],
          unmatched: ["https://unverified.example.net/page"],
        }}
      />,
    );
    const panel = screen.getByTestId("citation-panel");
    expect(panel).toHaveTextContent("1 of 2 links in the report were found in the search results");
    expect(within(panel).getByText(/Not found in retrieved search results — verify before relying on them/)).toBeInTheDocument();

    const link = within(panel).getByRole("link", { name: "https://unverified.example.net/page" });
    expect(link).toHaveAttribute("href", "https://unverified.example.net/page");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer nofollow");
  });

  it("confirms when every link was retrieved", () => {
    render(<CitationPanel check={{ matched: ["https://a.example/1", "https://b.example/2"], unmatched: [] }} />);
    const panel = screen.getByTestId("citation-panel");
    expect(panel).toHaveTextContent("2 of 2 links");
    expect(panel).not.toHaveTextContent("Not found in retrieved search results");
  });

  it("explains when the report has no links", () => {
    render(<CitationPanel check={{ matched: [], unmatched: [] }} />);
    expect(screen.getByTestId("citation-panel")).toHaveTextContent("The report contains no links to check");
  });

  it("never renders unsafe URLs as links", () => {
    render(<CitationPanel check={{ matched: [], unmatched: ["javascript:alert(1)"] }} />);
    const panel = screen.getByTestId("citation-panel");
    expect(within(panel).queryByRole("link")).not.toBeInTheDocument();
    expect(panel).toHaveTextContent("javascript:alert(1)");
  });
});
