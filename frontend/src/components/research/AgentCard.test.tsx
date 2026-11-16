import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetServerClock } from "../../lib/clock";
import type { StageOut } from "../../lib/types";
import { AgentCard } from "./AgentCard";

const NOW = new Date("2026-11-15T12:00:00.000Z");

function stage(overrides: Partial<StageOut> = {}): StageOut {
  return {
    stage: "research",
    agent: "Research Agent",
    status: "pending",
    started_at: null,
    finished_at: null,
    attempts: 0,
    searches: 0,
    llm_calls: 0,
    ...overrides,
  };
}

function valueOf(term: string): string {
  const dt = screen.getByText(term, { selector: "dt" });
  return dt.nextElementSibling?.textContent ?? "";
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
  resetServerClock();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("AgentCard", () => {
  it("shows a waiting agent without inventing timings", () => {
    render(<AgentCard stage={stage()} step={1} />);
    const card = screen.getByRole("article", { name: "Research Agent" });
    expect(within(card).getByText("Waiting")).toBeInTheDocument();
    expect(valueOf("Started")).toBe("Not yet");
    expect(valueOf("Duration")).toBe("—");
    expect(card).toHaveAttribute("data-status", "pending");
  });

  it("shows the elapsed time of a running stage from the server timestamp", () => {
    render(
      <AgentCard
        stage={stage({ status: "running", started_at: "2026-11-15T11:58:55.123456Z", attempts: 1, searches: 2, llm_calls: 3 })}
        step={1}
      />,
    );
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(valueOf("Elapsed")).toBe("1:04");
    expect(valueOf("Web searches")).toBe("2");
    expect(valueOf("Model requests")).toBe("3");
  });

  it("shows the real duration of a completed stage and stops ticking", () => {
    render(
      <AgentCard
        stage={stage({
          stage: "coding",
          agent: "Coding Agent",
          status: "completed",
          started_at: "2026-11-15T11:59:00.000Z",
          finished_at: "2026-11-15T11:59:42.500Z",
          attempts: 1,
          llm_calls: 1,
        })}
        step={2}
      />,
    );
    expect(screen.getByRole("article", { name: "Coding Agent" })).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(valueOf("Took")).toBe("42s");
    vi.advanceTimersByTime(5000);
    expect(valueOf("Took")).toBe("42s");
  });

  it("marks stages that never ran once the job has ended", () => {
    render(<AgentCard stage={stage({ stage: "synthesis", agent: "Manager Agent" })} step={3} jobFinished />);
    expect(screen.getByText("Not run")).toBeInTheDocument();
    expect(screen.queryByText("Waiting")).not.toBeInTheDocument();
  });

  it("labels the run time of a stage that stopped early", () => {
    render(
      <AgentCard
        stage={stage({
          status: "cancelled",
          started_at: "2026-11-15T11:59:00.000Z",
          finished_at: "2026-11-15T11:59:03.000Z",
          attempts: 1,
        })}
        step={1}
        jobFinished
      />,
    );
    expect(screen.getByText("Cancelled")).toBeInTheDocument();
    expect(valueOf("Ran for")).toBe("3.0s");
  });

  it("mentions retries after a provider switch", () => {
    render(<AgentCard stage={stage({ status: "failed", attempts: 2 })} step={1} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText(/Attempt 2/)).toBeInTheDocument();
  });
});
