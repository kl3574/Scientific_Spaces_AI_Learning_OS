"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import { ArticleDetail, fetchArticle, formatMetadata } from "@/lib/articles";
import {
  LearningNote,
  LearningSession,
  LearningState,
  LearningStatus,
  addBookmark,
  createNote,
  createSession,
  deleteBookmark,
  deleteNote,
  endSession,
  fetchBookmarks,
  fetchLearningState,
  fetchNotes,
  updateLearningState,
  updateNote,
} from "@/lib/learning";
import { ReadingHistoryItem, loadReadingHistory, recordReading } from "@/lib/readingHistory";
import { ZoteroLinksPanel } from "@/components/ZoteroLinksPanel";

export function ArticleDetailView({ articleId }: Readonly<{ articleId: string }>) {
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [learningState, setLearningState] = useState<LearningState | null>(null);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [notes, setNotes] = useState<LearningNote[]>([]);
  const [noteDraft, setNoteDraft] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState("");
  const [activeSession, setActiveSession] = useState<LearningSession | null>(null);
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [learningError, setLearningError] = useState<string | null>(null);

  useEffect(() => {
    setHistory(loadReadingHistory());
    fetchArticle(articleId)
      .then((loadedArticle) => {
        setArticle(loadedArticle);
        setHistory(recordReading(loadedArticle));
        void loadLearningContext(loadedArticle.id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load article"));
  }, [articleId]);

  async function loadLearningContext(nextArticleId: string) {
    setLearningError(null);
    try {
      const [state, bookmarkResponse, noteResponse, session] = await Promise.all([
        fetchLearningState(nextArticleId),
        fetchBookmarks(),
        fetchNotes(nextArticleId),
        createSession(nextArticleId, "reader"),
      ]);
      setLearningState(state);
      setIsBookmarked(bookmarkResponse.items.some((bookmark) => bookmark.article_id === nextArticleId));
      setNotes(noteResponse.items);
      setActiveSession(session);
    } catch (err) {
      setLearningError(err instanceof Error ? err.message : "Failed to load learning state");
    }
  }

  async function handleStatusChange(nextStatus: LearningStatus) {
    if (!article) {
      return;
    }
    setLearningError(null);
    try {
      setLearningState(await updateLearningState(article.id, nextStatus));
    } catch (err) {
      setLearningError(err instanceof Error ? err.message : "Failed to update learning state");
    }
  }

  async function handleBookmarkToggle() {
    if (!article) {
      return;
    }
    setLearningError(null);
    try {
      if (isBookmarked) {
        await deleteBookmark(article.id);
        setIsBookmarked(false);
      } else {
        await addBookmark(article.id);
        setIsBookmarked(true);
      }
    } catch (err) {
      setLearningError(err instanceof Error ? err.message : "Failed to update bookmark");
    }
  }

  async function handleCreateNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!article || !noteDraft.trim()) {
      return;
    }
    setLearningError(null);
    try {
      const note = await createNote(article.id, noteDraft.trim());
      setNotes([note, ...notes]);
      setNoteDraft("");
    } catch (err) {
      setLearningError(err instanceof Error ? err.message : "Failed to save note");
    }
  }

  async function handleUpdateNote(noteId: string) {
    if (!editingContent.trim()) {
      return;
    }
    setLearningError(null);
    try {
      const updated = await updateNote(noteId, editingContent.trim());
      setNotes(notes.map((note) => (note.note_id === noteId ? updated : note)));
      setEditingNoteId(null);
      setEditingContent("");
    } catch (err) {
      setLearningError(err instanceof Error ? err.message : "Failed to update note");
    }
  }

  async function handleDeleteNote(noteId: string) {
    setLearningError(null);
    try {
      await deleteNote(noteId);
      setNotes(notes.filter((note) => note.note_id !== noteId));
    } catch (err) {
      setLearningError(err instanceof Error ? err.message : "Failed to delete note");
    }
  }

  async function handleEndSession() {
    if (!activeSession || activeSession.ended_at) {
      return;
    }
    setLearningError(null);
    try {
      setActiveSession(await endSession(activeSession.session_id));
    } catch (err) {
      setLearningError(err instanceof Error ? err.message : "Failed to end session");
    }
  }

  if (error) {
    return (
      <section className="space-y-4">
        <Link className="text-sm text-slate-600 hover:text-slate-950" href="/articles">
          Back to articles
        </Link>
        <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>
      </section>
    );
  }

  if (!article) {
    return <p className="text-sm text-slate-600">Loading article...</p>;
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <article className="min-w-0 rounded border border-slate-200 bg-white p-5">
        <Link className="text-sm text-slate-600 hover:text-slate-950" href="/articles">
          Back to articles
        </Link>
        <h1 className="mt-4 text-2xl font-semibold leading-tight">{article.title}</h1>
        <p className="mt-2 text-sm text-slate-500">{formatMetadata(article.metadata)}</p>
        <a
          className="mt-2 inline-block text-sm text-slate-600 hover:text-slate-950"
          href={article.url}
          rel="noreferrer"
          target="_blank"
        >
          Source article
        </a>
        <div className="reader-markdown mt-6">
          <ReactMarkdown>{article.content}</ReactMarkdown>
        </div>
      </article>

      <aside className="space-y-4">
        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Learning State</h2>
          {learningError ? <p className="mt-3 text-sm text-red-700">{learningError}</p> : null}
          <div className="mt-3 grid grid-cols-3 gap-2">
            {(["unread", "reading", "completed"] as LearningStatus[]).map((status) => (
              <button
                key={status}
                className={
                  learningState?.status === status
                    ? "rounded border border-slate-950 bg-slate-950 px-2 py-2 text-xs font-medium text-white"
                    : "rounded border border-slate-300 bg-white px-2 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                }
                type="button"
                onClick={() => void handleStatusChange(status)}
              >
                {status}
              </button>
            ))}
          </div>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="text-slate-500">Read count</dt>
              <dd>{learningState?.read_count ?? 0}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Last read</dt>
              <dd>{formatDate(learningState?.last_read_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Completed</dt>
              <dd>{formatDate(learningState?.completed_at)}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold">Bookmark</h2>
            <button
              className="rounded border border-slate-300 px-3 py-1 text-sm font-medium hover:bg-slate-50"
              type="button"
              onClick={() => void handleBookmarkToggle()}
            >
              {isBookmarked ? "Remove" : "Save"}
            </button>
          </div>
          <p className="mt-3 text-sm text-slate-600">
            {isBookmarked ? "This article is in your bookmarks." : "This article is not bookmarked."}
          </p>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Session</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="text-slate-500">Started</dt>
              <dd>{formatDate(activeSession?.started_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Ended</dt>
              <dd>{formatDate(activeSession?.ended_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Duration</dt>
              <dd>{activeSession?.duration_seconds !== null && activeSession?.duration_seconds !== undefined ? `${activeSession.duration_seconds}s` : "Open"}</dd>
            </div>
          </dl>
          <button
            className="mt-3 rounded bg-slate-950 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={!activeSession || Boolean(activeSession.ended_at)}
            type="button"
            onClick={() => void handleEndSession()}
          >
            End session
          </button>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Notes</h2>
          <form className="mt-3 space-y-2" onSubmit={handleCreateNote}>
            <textarea
              className="min-h-24 w-full resize-y rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
              placeholder="Write a learning note"
              value={noteDraft}
              onChange={(event) => setNoteDraft(event.target.value)}
            />
            <button className="rounded bg-slate-950 px-3 py-2 text-sm font-medium text-white" type="submit">
              Add note
            </button>
          </form>
          <div className="mt-4 grid gap-3">
            {notes.length ? (
              notes.map((note) => (
                <article key={note.note_id} className="rounded border border-slate-100 p-3 text-sm">
                  {editingNoteId === note.note_id ? (
                    <div className="space-y-2">
                      <textarea
                        className="min-h-20 w-full resize-y rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
                        value={editingContent}
                        onChange={(event) => setEditingContent(event.target.value)}
                      />
                      <div className="flex gap-2">
                        <button
                          className="rounded bg-slate-950 px-3 py-1 text-xs font-medium text-white"
                          type="button"
                          onClick={() => void handleUpdateNote(note.note_id)}
                        >
                          Save
                        </button>
                        <button
                          className="rounded border border-slate-300 px-3 py-1 text-xs font-medium"
                          type="button"
                          onClick={() => {
                            setEditingNoteId(null);
                            setEditingContent("");
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="whitespace-pre-wrap leading-6 text-slate-700">{note.content}</p>
                      <p className="mt-2 text-xs text-slate-500">{formatDate(note.updated_at)}</p>
                      <div className="mt-3 flex gap-2">
                        <button
                          className="rounded border border-slate-300 px-3 py-1 text-xs font-medium"
                          type="button"
                          onClick={() => {
                            setEditingNoteId(note.note_id);
                            setEditingContent(note.content);
                          }}
                        >
                          Edit
                        </button>
                        <button
                          className="rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-700"
                          type="button"
                          onClick={() => void handleDeleteNote(note.note_id)}
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </article>
              ))
            ) : (
              <p className="text-sm text-slate-600">No notes yet.</p>
            )}
          </div>
        </section>

        <ZoteroLinksPanel articleId={article.id} initialQuery={article.title} />

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Metadata</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="text-slate-500">Date</dt>
              <dd>{article.metadata.date ?? "Unknown"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Category</dt>
              <dd>{article.metadata.category ?? "Unknown"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Images</dt>
              <dd>{article.metadata.images?.length ?? 0}</dd>
            </div>
            <div>
              <dt className="text-slate-500">References</dt>
              <dd>{article.metadata.references?.length ?? 0}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Recent Reading</h2>
          <div className="mt-3 grid gap-2">
            {history.length ? (
              history.slice(0, 5).map((item) => (
                <Link
                  key={`${item.id}-${item.last_read_at}`}
                  className="rounded border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50"
                  href={`/articles/${item.id}`}
                >
                  <span className="block font-medium">{item.title}</span>
                  <span className="mt-1 block text-xs text-slate-500">
                    {new Date(item.last_read_at).toLocaleString()}
                  </span>
                </Link>
              ))
            ) : (
              <p className="text-sm text-slate-600">No reading history yet.</p>
            )}
          </div>
        </section>
      </aside>
    </section>
  );
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Not recorded";
  }
  return new Date(value).toLocaleString();
}
