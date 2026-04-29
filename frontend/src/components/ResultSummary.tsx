import type { SubmitResponse } from "../types";

type ResultSummaryProps = {
  result: SubmitResponse;
};

export function ResultSummary({ result }: ResultSummaryProps) {
  const stats = [
    { label: "Total Questions", value: result.total_questions },
    { label: "Gradable", value: result.gradable_questions },
    { label: "Ungraded", value: result.ungraded_questions },
    { label: "Attempted", value: result.attempted },
    { label: "Correct", value: result.correct },
    { label: "Incorrect", value: result.incorrect },
    { label: "Score", value: result.score },
  ];

  return (
    <section className="panel">
      <h2>Result Summary</h2>
      <div className="stats-grid">
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card">
            <span className="stat-label">{stat.label}</span>
            <strong className="stat-value">{stat.value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
