import { useEffect, useMemo, useState } from "react";

import { QuestionCard } from "./QuestionCard";
import type { Paper, QuestionSet } from "../types";

type ExamViewProps = {
  paper: Paper;
  answers: Record<string, string>;
  onAnswerChange: (questionId: string, answer: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
};

export function ExamView({
  paper,
  answers,
  onAnswerChange,
  onSubmit,
  isSubmitting,
}: ExamViewProps) {
  const totalQuestions = paper.sets.reduce(
    (count, questionSet) => count + questionSet.questions.length,
    0,
  );
  const groupedSections = useMemo(
    () =>
      paper.sets.reduce<Record<string, QuestionSet[]>>((grouped, questionSet) => {
        grouped[questionSet.section] ??= [];
        grouped[questionSet.section].push(questionSet);
        return grouped;
      }, {}),
    [paper.sets],
  );
  const sectionOrder = ["VARC", "DILR", "QA"];
  const sections = useMemo(
    () =>
      sectionOrder
        .filter((sectionName) => groupedSections[sectionName]?.length)
        .map((sectionName) => ({
          name: sectionName,
          sets: groupedSections[sectionName],
        })),
    [groupedSections],
  );
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);

  useEffect(() => {
    setActiveSectionIndex(0);
  }, [paper.paper_id]);

  useEffect(() => {
    if (activeSectionIndex > sections.length - 1) {
      setActiveSectionIndex(0);
    }
  }, [activeSectionIndex, sections.length]);

  const activeSection = sections[activeSectionIndex];
  const isFirstSection = activeSectionIndex === 0;
  const isLastSection = activeSectionIndex === sections.length - 1;

  return (
    <section className="exam-layout">
      <header className="panel">
        <div className="exam-header">
          <div>
            <h2>
              CAT {paper.year} Slot {paper.slot}
            </h2>
            <p>{totalQuestions} questions</p>
          </div>
          <div className="section-progress">
            <span>
              Section {activeSectionIndex + 1} of {sections.length}
            </span>
          </div>
        </div>
        <nav className="section-nav" aria-label="Exam sections">
          {sections.map((section, index) => (
            <button
              key={section.name}
              type="button"
              className={`section-tab ${index === activeSectionIndex ? "is-active" : ""}`}
              onClick={() => setActiveSectionIndex(index)}
              aria-current={index === activeSectionIndex ? "page" : undefined}
            >
              {section.name}
            </button>
          ))}
        </nav>
      </header>

      {activeSection ? (
        <section key={activeSection.name} className="section-block">
          <div className="set-list">
            {activeSection.sets.map((questionSet) => (
              <article key={questionSet.set_id} className="set-card">
                {questionSet.shared_context ? (
                  <div className="set-context">
                    <p>{questionSet.shared_context}</p>
                  </div>
                ) : null}
                {questionSet.image_link ? (
                  <img
                    className="set-image"
                    src={questionSet.image_link}
                    alt={`Shared context for ${activeSection.name}`}
                  />
                ) : null}
                <div className="question-list">
                  {questionSet.questions.map((question) => (
                    <QuestionCard
                      key={question.question_id}
                      question={question}
                      value={answers[question.question_id] ?? ""}
                      onChange={onAnswerChange}
                    />
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {activeSection ? (
        <div className="submit-row">
          <div className="section-pager">
            <button
              type="button"
              className="secondary-button"
              onClick={() => setActiveSectionIndex((current) => current - 1)}
              disabled={isFirstSection}
            >
              Previous section
            </button>
            {isLastSection ? (
              <button type="button" onClick={onSubmit} disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Submit Test"}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setActiveSectionIndex((current) => current + 1)}
              >
                Next section
              </button>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
