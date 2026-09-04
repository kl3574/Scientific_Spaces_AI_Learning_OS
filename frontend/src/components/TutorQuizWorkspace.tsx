"use client";

import { useEffect, useRef } from "react";

import type { QuizQuestion } from "@/lib/tutor";
import {
  getTutorQuizChoices,
  scoreTutorQuiz,
  type TutorQuizAnswers,
} from "@/lib/tutorWorkspace";

import { TutorSourceList } from "./TutorSourceList";

export function TutorQuizWorkspace({
  questions,
  answers,
  submitted,
  onAnswer,
  onSubmit,
  onReset,
}: Readonly<{
  questions: QuizQuestion[];
  answers: TutorQuizAnswers;
  submitted: boolean;
  onAnswer: (index: number, answer: string) => void;
  onSubmit: () => void;
  onReset: () => void;
}>) {
  const score = scoreTutorQuiz(questions, answers);
  const workspaceRef = useRef<HTMLElement>(null);
  const scoreRef = useRef<HTMLDivElement>(null);
  const previousSubmittedRef = useRef(submitted);

  useEffect(() => {
    const focusFrame = window.requestAnimationFrame(() => {
      workspaceRef.current?.focus({ preventScroll: true });
      workspaceRef.current?.scrollIntoView({ behavior: "auto", block: "nearest" });
    });
    return () => window.cancelAnimationFrame(focusFrame);
  }, []);

  useEffect(() => {
    const previousSubmitted = previousSubmittedRef.current;
    previousSubmittedRef.current = submitted;
    if (previousSubmitted === submitted) {
      return;
    }
    const focusFrame = window.requestAnimationFrame(() => {
      if (submitted) {
        scoreRef.current?.focus({ preventScroll: true });
        scoreRef.current?.scrollIntoView({ behavior: "auto", block: "nearest" });
        return;
      }
      const firstAnswer = workspaceRef.current?.querySelector<HTMLElement>(
        'input:not([disabled]), textarea:not([disabled])',
      );
      firstAnswer?.focus({ preventScroll: true });
      firstAnswer?.scrollIntoView({ behavior: "auto", block: "nearest" });
    });
    return () => window.cancelAnimationFrame(focusFrame);
  }, [submitted]);

  return (
    <section
      ref={workspaceRef}
      aria-labelledby="tutor-quiz-heading"
      className="grid min-w-0 scroll-mt-24 gap-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
      data-testid="tutor-quiz-workspace"
      tabIndex={-1}
    >
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold" id="tutor-quiz-heading">Quiz</h2>
          <p className="mt-1 text-sm text-slate-600">
            {submitted ? "Review each grounded answer and its source." : "Answer every question before checking your score."}
          </p>
        </div>
        {submitted ? (
          <div
            ref={scoreRef}
            aria-atomic="true"
            aria-live="polite"
            className="max-w-full shrink-0 scroll-mt-24 border-l-4 border-emerald-600 bg-emerald-50 px-3 py-2 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
            data-testid="tutor-quiz-score"
            role="status"
            tabIndex={-1}
          >
            <p className="text-xs font-semibold uppercase text-emerald-800">Score</p>
            <p className="text-lg font-semibold text-emerald-950">{score.correct} / {score.total}</p>
            <p className="sr-only">Quiz submitted. Review each grounded answer and its source below.</p>
          </div>
        ) : null}
      </div>

      {questions.map((item, index) => {
        const choices = getTutorQuizChoices(questions, index);
        const selected = answers[index] ?? "";
        const correct = selected.trim().toLocaleLowerCase("zh-CN") === item.correct_answer.trim().toLocaleLowerCase("zh-CN");
        return (
          <article key={`${item.question}-${index}`} className="min-w-0 border-b border-slate-200 bg-white py-4 text-sm last:border-b-0">
            <fieldset className="min-w-0" disabled={submitted}>
              <legend className="max-w-full break-words font-semibold leading-6 [overflow-wrap:anywhere]">{index + 1}. {item.question}</legend>
              {choices.length ? (
                <div className="mt-3 grid min-w-0 gap-2">
                  {choices.map((choice, choiceIndex) => (
                    <label key={choice} className="flex min-w-0 max-w-full cursor-pointer items-start gap-3 rounded border border-slate-200 px-3 py-2 hover:border-emerald-700">
                      <input
                        className="mt-1"
                        checked={selected === choice}
                        name={`tutor-quiz-${index}`}
                        onChange={() => onAnswer(index, choice)}
                        type="radio"
                        value={choice}
                      />
                      <span className="min-w-0 break-words [overflow-wrap:anywhere]"><span className="font-semibold">{String.fromCharCode(65 + choiceIndex)}.</span> {choice}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <label className="mt-3 grid gap-1">
                  <span className="text-xs font-semibold text-slate-600">Your answer</span>
                  <textarea
                    className="min-h-20 rounded border border-slate-300 px-3 py-2"
                    onChange={(event) => onAnswer(index, event.target.value)}
                    value={selected}
                  />
                </label>
              )}
            </fieldset>

            {submitted ? (
              <div className={`mt-4 border-l-4 px-3 py-2 ${correct ? "border-emerald-600 bg-emerald-50" : "border-amber-500 bg-amber-50"}`} data-testid={`tutor-quiz-review-${index}`}>
                <p className="font-semibold">{correct ? "Correct" : "Review needed"}</p>
                <p className="mt-2 break-words text-slate-800"><span className="font-semibold">Correct answer:</span> {item.correct_answer}</p>
                <p className="mt-2 break-words text-slate-700 [overflow-wrap:anywhere]">{item.explanation}</p>
                <TutorSourceList compact title="题目来源" sources={item.sources} />
              </div>
            ) : null}
          </article>
        );
      })}

      <div className="flex flex-wrap gap-2">
        {submitted ? (
          <button className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white" onClick={onReset} type="button">
            Try again
          </button>
        ) : (
          <button className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400" disabled={!score.complete} onClick={onSubmit} type="button">
            Check answers
          </button>
        )}
      </div>
    </section>
  );
}
