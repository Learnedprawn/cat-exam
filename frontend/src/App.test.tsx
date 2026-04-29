import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const { fetchPapersMock, fetchPaperMock, submitPaperMock } = vi.hoisted(() => ({
  fetchPapersMock: vi.fn(),
  fetchPaperMock: vi.fn(),
  submitPaperMock: vi.fn(),
}));

vi.mock("./api", () => ({
  fetchPapers: fetchPapersMock,
  fetchPaper: fetchPaperMock,
  submitPaper: submitPaperMock,
}));

describe("App theme mode", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    fetchPapersMock.mockResolvedValue([
      { paper_id: "cat-2024-slot-1", year: 2024, slot: 1 },
    ]);
    fetchPaperMock.mockReset();
    submitPaperMock.mockReset();
    document.documentElement.removeAttribute("data-theme");
  });

  it("always initializes in light mode", async () => {
    render(<App />);

    await screen.findByText("Select paper");

    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });
});
