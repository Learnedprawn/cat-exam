import { useEffect, useState } from "react";

import { fetchPaper, fetchPapers, submitPaper } from "./api";
import { ExamView } from "./components/ExamView";
import { PaperPicker } from "./components/PaperPicker";
import { ResultSummary } from "./components/ResultSummary";
import type { Paper, PaperSummary, SubmitResponse } from "./types";

import "./styles.css";

export default function App() {
  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState("");
  const [paper, setPaper] = useState<Paper | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SubmitResponse | null>(null);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [loadingPaper, setLoadingPaper] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadPapers() {
      try {
        const fetchedPapers = await fetchPapers();
        setPapers(fetchedPapers);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load papers");
      } finally {
        setLoadingPapers(false);
      }
    }

    void loadPapers();
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = "light";
  }, []);

  useEffect(() => {
    if (!selectedPaperId) {
      setPaper(null);
      setAnswers({});
      setResult(null);
      return;
    }

    async function loadPaper() {
      setLoadingPaper(true);
      setError("");

      try {
        const fetchedPaper = await fetchPaper(selectedPaperId);
        setPaper(fetchedPaper);
        setAnswers({});
        setResult(null);
      } catch (loadError) {
        setPaper(null);
        setError(loadError instanceof Error ? loadError.message : "Failed to load paper");
      } finally {
        setLoadingPaper(false);
      }
    }

    void loadPaper();
  }, [selectedPaperId]);

  function handleAnswerChange(questionId: string, answer: string) {
    setAnswers((current) => ({
      ...current,
      [questionId]: answer,
    }));
  }

  async function handleSubmit() {
    if (!paper) {
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const submitResult = await submitPaper(paper.paper_id, answers);
      setResult(submitResult);
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Failed to submit paper",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <h1 className="eyebrow">CAT Practice</h1>
        {/* <h1>Practice in a clean exam reading view</h1> */}
        <p className="app-intro">
          Select a paper, move section by section, and answer questions in a
          free layout.
        </p>
      </header>

      <PaperPicker
        papers={papers}
        selectedPaperId={selectedPaperId}
        onChange={setSelectedPaperId}
        disabled={loadingPapers}
      />

      {error ? <div className="error-banner">{error}</div> : null}

      {loadingPapers ? <div className="panel">Loading papers...</div> : null}
      {loadingPaper ? <div className="panel">Loading paper...</div> : null}
      {result ? <ResultSummary result={result} /> : null}

      {paper && !loadingPaper ? (
        <ExamView
          paper={paper}
          answers={answers}
          onAnswerChange={handleAnswerChange}
          onSubmit={handleSubmit}
          isSubmitting={submitting}
        />
      ) : null}
    </main>
  );
}
