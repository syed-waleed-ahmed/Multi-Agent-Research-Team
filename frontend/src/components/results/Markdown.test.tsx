import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("opens http(s) links safely in a new tab", () => {
    render(<Markdown>{"See [the docs](https://docs.example.org/guide)."}</Markdown>);
    const link = screen.getByRole("link", { name: "the docs" });
    expect(link).toHaveAttribute("href", "https://docs.example.org/guide");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer nofollow");
  });

  it("does not render javascript: or relative links", () => {
    render(<Markdown>{"[bad](javascript:alert(1)) and [relative](/admin)"}</Markdown>);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("bad")).toBeInTheDocument();
  });

  it("never renders raw HTML from the model", () => {
    const { container } = render(<Markdown>{'Hello <script>alert(1)</script><img src=x onerror="alert(1)"> world'}</Markdown>);
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });

  it("renders images as links instead of loading them", () => {
    const { container } = render(<Markdown>{"![diagram](https://img.example.com/a.png)"}</Markdown>);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByRole("link", { name: "[Image: diagram]" })).toHaveAttribute("href", "https://img.example.com/a.png");
  });

  it("renders GFM tables, shifted headings and highlighted code", () => {
    const { container } = render(
      <Markdown>{"# Title\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n```python\nprint('hi')\n```"}</Markdown>,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Title" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(container.querySelector("code.hljs.language-python")).not.toBeNull();
    expect(screen.getByText("python")).toBeInTheDocument();
  });

  it("flags links that the citation check could not match", () => {
    render(
      <Markdown unverifiedUrls={["https://unverified.example.net/page"]}>
        {"[ok](https://docs.example.org/guide) and [unverified](https://unverified.example.net/page/)"}
      </Markdown>,
    );
    expect(screen.getAllByText(/not found in retrieved search results/)).toHaveLength(1);
  });
});
