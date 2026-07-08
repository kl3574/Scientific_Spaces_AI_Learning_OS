export type TutorMode = "explain" | "derive" | "qa" | "quiz" | "research";

export type TutorSource = {
  source_type: string;
  source_id: string;
  title: string;
  url: string | null;
  section_title: string | null;
  chunk_index: number | null;
  evidence: unknown;
  metadata: Record<string, unknown>;
};

export type TutorResponse = {
  answer: string;
  mode: TutorMode;
  sources: TutorSource[];
  graph_context: {
    nodes?: Array<Record<string, unknown>>;
    edges?: Array<Record<string, unknown>>;
  };
  zotero_context: Array<Record<string, unknown>>;
  follow_up_questions: string[];
  refusal_reason: string | null;
};

export type QuizQuestion = {
  question: string;
  options: string[] | null;
  correct_answer: string;
  explanation: string;
  sources: TutorSource[];
};

export type TutorQuizResponse = {
  questions: QuizQuestion[];
  total: number;
};

export type TutorSession = {
  session_id: string;
  mode: TutorMode;
  article_id: string | null;
  node_id: string | null;
  created_at: string;
  updated_at: string;
  turns: Array<Record<string, unknown>>;
};

export type TutorSessionsResponse = {
  items: TutorSession[];
  total: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function askTutor(input: {
  question: string;
  mode: TutorMode;
  article_id?: string;
  node_id?: string;
  top_k?: number;
  include_graph_context?: boolean;
  include_zotero_context?: boolean;
}): Promise<TutorResponse> {
  return requestJson<TutorResponse>("/tutor/ask", {
    body: JSON.stringify(input),
    method: "POST",
  });
}

export async function requestTutorQuiz(input: {
  article_id?: string;
  node_id?: string;
  num_questions?: number;
}): Promise<TutorQuizResponse> {
  return requestJson<TutorQuizResponse>("/tutor/quiz", {
    body: JSON.stringify(input),
    method: "POST",
  });
}

export async function fetchTutorSessions(): Promise<TutorSessionsResponse> {
  return requestJson<TutorSessionsResponse>("/tutor/sessions");
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(new URL(path, API_BASE_URL).toString(), {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Tutor request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
