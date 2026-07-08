export type LearningStatus = "unread" | "reading" | "completed";
export type SessionSource = "reader" | "rag";

export type LearningState = {
  article_id: string;
  status: LearningStatus;
  last_read_at: string | null;
  completed_at: string | null;
  read_count: number;
  updated_at: string | null;
};

export type Bookmark = {
  article_id: string;
  title: string;
  url: string;
  created_at: string;
};

export type LearningNote = {
  note_id: string;
  article_id: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type LearningSession = {
  session_id: string;
  article_id: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  source: SessionSource;
};

export type RecentLearningArticle = {
  article_id: string;
  title: string;
  url: string;
  status: LearningStatus;
  last_read_at: string | null;
  updated_at: string | null;
};

export type LearningStats = {
  total_articles: number;
  unread_count: number;
  reading_count: number;
  completed_count: number;
  bookmark_count: number;
  note_count: number;
  recent_articles: RecentLearningArticle[];
  recent_sessions: LearningSession[];
};

export type ListResponse<T> = {
  items: T[];
  total: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchLearningStats(): Promise<LearningStats> {
  return requestJson<LearningStats>("/learning/stats");
}

export async function fetchLearningStates(): Promise<ListResponse<LearningState>> {
  return requestJson<ListResponse<LearningState>>("/learning/state");
}

export async function fetchLearningState(articleId: string): Promise<LearningState> {
  return requestJson<LearningState>(`/learning/state/${articleId}`);
}

export async function updateLearningState(articleId: string, status: LearningStatus): Promise<LearningState> {
  return requestJson<LearningState>(`/learning/state/${articleId}`, {
    body: JSON.stringify({ status }),
    method: "PUT",
  });
}

export async function fetchBookmarks(): Promise<ListResponse<Bookmark>> {
  return requestJson<ListResponse<Bookmark>>("/learning/bookmarks");
}

export async function addBookmark(articleId: string): Promise<Bookmark> {
  return requestJson<Bookmark>(`/learning/bookmarks/${articleId}`, { method: "POST" });
}

export async function deleteBookmark(articleId: string): Promise<void> {
  await requestNoContent(`/learning/bookmarks/${articleId}`, { method: "DELETE" });
}

export async function fetchNotes(articleId: string): Promise<ListResponse<LearningNote>> {
  return requestJson<ListResponse<LearningNote>>(`/learning/notes/${articleId}`);
}

export async function createNote(articleId: string, content: string): Promise<LearningNote> {
  return requestJson<LearningNote>(`/learning/notes/${articleId}`, {
    body: JSON.stringify({ content }),
    method: "POST",
  });
}

export async function updateNote(noteId: string, content: string): Promise<LearningNote> {
  return requestJson<LearningNote>(`/learning/notes/${noteId}`, {
    body: JSON.stringify({ content }),
    method: "PUT",
  });
}

export async function deleteNote(noteId: string): Promise<void> {
  await requestNoContent(`/learning/notes/${noteId}`, { method: "DELETE" });
}

export async function createSession(articleId: string, source: SessionSource = "reader"): Promise<LearningSession> {
  return requestJson<LearningSession>("/learning/sessions", {
    body: JSON.stringify({ article_id: articleId, source }),
    method: "POST",
  });
}

export async function endSession(sessionId: string): Promise<LearningSession> {
  return requestJson<LearningSession>(`/learning/sessions/${sessionId}/end`, { method: "PUT" });
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
    throw new Error(`Learning request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestNoContent(path: string, init: RequestInit = {}): Promise<void> {
  const response = await fetch(new URL(path, API_BASE_URL).toString(), {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Learning request failed: ${response.status}`);
  }
}
