import type { Question } from "../types";

type QuestionCardProps = {
  question: Question;
  value: string;
  onChange: (questionId: string, answer: string) => void;
};

export function QuestionCard({
  question,
  value,
  onChange,
}: QuestionCardProps) {
  return (
    <article className="question-card">
      <div className="question-meta">
        <span>Q{question.question_number}</span>
        <span className="question-type">{question.question_type.toUpperCase()}</span>
      </div>
      <p className="question-text">{question.question_text}</p>
      {question.question_type === "mcq" ? (
        <div className="options">
          {(question.options ?? []).map((option) => (
            <label key={option.option_id} className="option">
              <input
                type="radio"
                name={question.question_id}
                value={option.option_id}
                checked={value === option.option_id}
                onChange={(event) =>
                  onChange(question.question_id, event.target.value)
                }
              />
              <span>
                <strong>{option.option_id}.</strong> {option.option_text}
              </span>
            </label>
          ))}
        </div>
      ) : (
        <label className="field">
          <span className="field-label">Enter answer</span>
          <input
            type="text"
            inputMode="numeric"
            value={value}
            onChange={(event) => onChange(question.question_id, event.target.value)}
            placeholder="Type a numeric answer"
          />
        </label>
      )}
    </article>
  );
}
