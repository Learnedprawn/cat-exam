import type { Paper, PaperSummary, SubmitResponse } from "./types";

const rawApiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const API_BASE = rawApiBase.replace(/\/+$/, "");

export async function fetchPapers(): Promise<PaperSummary[]> {
  const response = await fetch(`${API_BASE}/papers`);
  if (!response.ok) {
    throw new Error("Failed to load papers");
  }
  return response.json();
}

export async function fetchPaper(paperId: string): Promise<Paper> {
  const response = await fetch(`${API_BASE}/papers/${paperId}`);
  if (!response.ok) {
    throw new Error("Failed to load paper");
  }
  return response.json();
}

export async function submitPaper(
  paperId: string,
  answers: Record<string, string>,
): Promise<SubmitResponse> {
  const response = await fetch(`${API_BASE}/papers/${paperId}/submit`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ answers }),
  });

  if (!response.ok) {
    throw new Error("Failed to submit paper");
  }

  return response.json();
}
