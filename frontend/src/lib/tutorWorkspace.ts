import type { ArticleMetadata, ArticleSummary } from "./articles";
import type { QuizQuestion, TutorMode, TutorSession } from "./tutor";
import { getSafeExternalUrl } from "./tutorPresentation";

export const MAX_TUTOR_ARTICLE_RESULTS = 6;
export const MAX_TUTOR_ACTIVITY_ITEMS = 5;

export type TutorArticleSelection = {
  id: string;
  title: string;
  metadata: ArticleMetadata;
};

export type TutorQuizAnswers = Record<number, string>;

export type TutorQuizScore = {
  answered: number;
  correct: number;
  total: number;
  complete: boolean;
};

export type TutorActivityItem = {
  key: string;
  modeLabel: string;
  articleTitle: string;
  prompt: string;
  updatedAt: string;
};

const MODE_LABELS: Record<TutorMode, string> = {
  explain: "Explain",
  derive: "Derive",
  qa: "Q&A",
  quiz: "Quiz",
  research: "Research",
};

const MODE_ACTIVITY_LABELS: Record<TutorMode, string> = {
  explain: "Concept explanation",
  derive: "Derivation practice",
  qa: "Question and answer",
  quiz: "Knowledge check",
  research: "Research exploration",
};

export function createTutorArticleSelection(article: ArticleSummary): TutorArticleSelection {
  return {
    id: article.id,
    title: normalizeDisplayText(article.title) || "Untitled article",
    metadata: article.metadata ?? {},
  };
}

export function getTutorModeLabel(mode: TutorMode): string {
  return MODE_LABELS[mode];
}

export function getTutorQuizChoices(questions: readonly QuizQuestion[], index: number): string[] {
  const question = questions[index];
  if (!question) {
    return [];
  }

  const supplied = dedupeAnswers([...(question.options ?? []), question.correct_answer]);
  if ((question.options?.length ?? 0) >= 2 && supplied.length >= 2) {
    return rotateAnswers(supplied, index);
  }

  const groundedPool = dedupeAnswers(questions.map((item) => item.correct_answer));
  if (groundedPool.length < 2) {
    return [];
  }
  return rotateAnswers(groundedPool.slice(0, 4), index);
}

export function scoreTutorQuiz(
  questions: readonly QuizQuestion[],
  answers: TutorQuizAnswers,
): TutorQuizScore {
  let answered = 0;
  let correct = 0;
  questions.forEach((question, index) => {
    const answer = normalizeAnswer(answers[index] ?? "");
    if (!answer) {
      return;
    }
    answered += 1;
    if (answer === normalizeAnswer(question.correct_answer)) {
      correct += 1;
    }
  });
  return {
    answered,
    correct,
    total: questions.length,
    complete: questions.length > 0 && answered === questions.length,
  };
}

export function buildTutorActivity(
  sessions: readonly TutorSession[],
  articleTitles: Readonly<Record<string, string>>,
  maxItems = MAX_TUTOR_ACTIVITY_ITEMS,
): TutorActivityItem[] {
  const limit = Number.isFinite(maxItems)
    ? Math.max(0, Math.min(Math.floor(maxItems), MAX_TUTOR_ACTIVITY_ITEMS))
    : MAX_TUTOR_ACTIVITY_ITEMS;

  return [...sessions]
    .sort((left, right) => timestampValue(right.updated_at) - timestampValue(left.updated_at))
    .slice(0, limit)
    .map((session) => {
      const resolvedTitle = session.article_id
        ? normalizeDisplayText(articleTitles[session.article_id])
        : "";
      return {
        key: session.session_id,
        modeLabel: MODE_LABELS[session.mode] ?? "Tutor",
        articleTitle: resolvedTitle || (session.article_id ? "Article context" : "General study"),
        prompt: latestSessionPrompt(session) || MODE_ACTIVITY_LABELS[session.mode] || "Tutor activity",
        updatedAt: formatTutorTimestamp(session.updated_at),
      };
    });
}

export function getSafeTutorMarkdownHref(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const href = value.trim();
  if (!href || /[\u0000-\u001f\u007f\\]/.test(href)) {
    return null;
  }
  const decoded = decodeForSafety(href);
  if (/[\u0000-\u001f\u007f\\]/.test(decoded) || decoded.includes("..")) {
    return null;
  }
  if (href.startsWith("#") && !href.startsWith("##")) {
    return href;
  }
  if (href.startsWith("/articles/") && !href.startsWith("//") && !href.includes("..")) {
    return href;
  }
  return getSafeExternalUrl(href);
}

function latestSessionPrompt(session: TutorSession): string {
  for (let index = session.turns.length - 1; index >= 0; index -= 1) {
    const question = normalizeDisplayText(session.turns[index]?.question);
    if (question) {
      return question;
    }
  }
  return "";
}

function formatTutorTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Recently";
  }
  return parsed.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function timestampValue(value: string): number {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeDisplayText(value: unknown): string {
  if (typeof value !== "string") {
    return "";
  }
  return value.replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, 240);
}

function normalizeAnswer(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLocaleLowerCase("zh-CN");
}

function dedupeAnswers(values: readonly string[]): string[] {
  const seen = new Set<string>();
  const answers: string[] = [];
  values.forEach((value) => {
    const normalized = normalizeAnswer(value);
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    answers.push(value.trim());
  });
  return answers;
}

function rotateAnswers(values: readonly string[], offset: number): string[] {
  if (!values.length) {
    return [];
  }
  const start = Math.abs(offset) % values.length;
  return [...values.slice(start), ...values.slice(0, start)];
}

function decodeForSafety(value: string): string {
  let decoded = value;
  for (let index = 0; index < 2; index += 1) {
    try {
      const next = decodeURIComponent(decoded);
      if (next === decoded) {
        break;
      }
      decoded = next;
    } catch {
      return decoded;
    }
  }
  return decoded;
}
