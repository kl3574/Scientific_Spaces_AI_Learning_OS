"use client";

import Link from "next/link";
import { ComponentPropsWithoutRef, FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import {
  ArticleOutline,
  ReaderDisplayControls,
  ReadingProgress,
} from "@/components/ReaderWorkspaceControls";
import { ArticleDetail, fetchArticle, formatMetadata } from "@/lib/articles";
import {
  ArticleOutlineItem,
  DEFAULT_READER_PREFERENCES,
  ReaderPreferences,
  clampReadingProgress,
  extractArticleOutline,
  loadReaderPreferences,
  loadReaderProgress,
  prepareArticleMarkdown,
  saveReaderPreferences,
  saveReaderProgress,
  updateLastMeaningfulPosition,
} from "@/lib/articleWorkspace";
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
import { createLearningToolHref } from "@/lib/learningWorkflow";
import { StructuredReferencesPanel } from "@/components/StructuredReferencesPanel";
import { WorkspaceState } from "@/components/WorkspaceState";
import { ZoteroLinksPanel } from "@/components/ZoteroLinksPanel";

export function ArticleDetailView({
  articleId,
  listReturnTo,
}: Readonly<{
  articleId: string;
  listReturnTo: string;
}>) {
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
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [readingProgress, setReadingProgress] = useState(0);
  const [readerPreferences, setReaderPreferences] = useState<ReaderPreferences>(DEFAULT_READER_PREFERENCES);
  const learningLoadArticleRef = useRef<string | null>(null);
  const articleRootRef = useRef<HTMLElement | null>(null);
  const explicitSectionRef = useRef<ArticleOutlineItem | null>(null);
  const returnLabel = listReturnTo.startsWith("/library") ? "Back to saved library" : "Back to articles";

  useEffect(() => {
    setArticle(null);
    setError(null);
    setActiveSectionId(null);
    setReadingProgress(0);
    setLearningState(null);
    setIsBookmarked(false);
    setNotes([]);
    setActiveSession(null);
    setLearningError(null);
    learningLoadArticleRef.current = null;
    explicitSectionRef.current = null;
    setHistory(loadReadingHistory());
    fetchArticle(articleId)
      .then((loadedArticle) => {
        setArticle(loadedArticle);
        setHistory(recordReading(loadedArticle));
        void loadLearningContext(loadedArticle.id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load article"));
  }, [articleId]);

  useEffect(() => {
    setReaderPreferences(loadReaderPreferences());
  }, []);

  async function loadLearningContext(nextArticleId: string) {
    if (learningLoadArticleRef.current === nextArticleId) {
      return;
    }
    learningLoadArticleRef.current = nextArticleId;
    setLearningError(null);
    try {
      const [state, bookmarkResponse, noteResponse] = await Promise.all([
        fetchLearningState(nextArticleId),
        fetchBookmarks(),
        fetchNotes(nextArticleId),
      ]);
      const session = await createSession(nextArticleId, "reader");
      setLearningState(state);
      setIsBookmarked(bookmarkResponse.items.some((bookmark) => bookmark.article_id === nextArticleId));
      setNotes(noteResponse.items);
      setActiveSession(session);
    } catch (err) {
      if (learningLoadArticleRef.current === nextArticleId) {
        learningLoadArticleRef.current = null;
      }
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

  const metadataImages = useMemo(() => parseMetadataItems(article?.metadata.images), [article?.metadata.images]);
  const metadataReferences = useMemo(() => parseMetadataItems(article?.metadata.references), [article?.metadata.references]);
  const renderedContent = useMemo(() => prepareArticleMarkdown(article?.content ?? ""), [article?.content]);
  const outline = useMemo(() => extractArticleOutline(renderedContent), [renderedContent]);
  const markdownComponents = useMemo(() => createMarkdownComponents(outline), [outline]);
  const activeSection = useMemo(
    () => outline.find((item) => item.id === activeSectionId) ?? null,
    [activeSectionId, outline],
  );

  useEffect(() => {
    const currentArticleId = article?.id;
    const articleRoot = articleRootRef.current;
    if (!currentArticleId || !articleRoot) {
      return;
    }

    let restored = false;
    let frame = 0;
    let restoreFrame = 0;
    let persistenceTimer: ReturnType<typeof setTimeout> | null = null;
    let pendingState = {
      article_id: currentArticleId,
      section_id: null as string | null,
      section_title: null as string | null,
      progress: 0,
      updated_at: new Date().toISOString(),
    };

    const persist = () => {
      if (!restored) {
        return;
      }
      if (persistenceTimer) {
        clearTimeout(persistenceTimer);
        persistenceTimer = null;
      }
      const explicitSection = explicitSectionRef.current;
      saveReaderProgress({
        ...pendingState,
        section_id: explicitSection?.id ?? pendingState.section_id,
        section_title: explicitSection?.label ?? pendingState.section_title,
        updated_at: new Date().toISOString(),
      });
    };

    const schedulePersist = () => {
      if (persistenceTimer) {
        clearTimeout(persistenceTimer);
      }
      persistenceTimer = setTimeout(persist, 300);
    };

    const updateReadingPosition = () => {
      frame = 0;
      if (!restored) {
        return;
      }

      const readingLine = Math.min(180, Math.max(96, window.innerHeight * 0.2));
      let nextSection: ArticleOutlineItem | null = null;
      for (const item of outline) {
        const heading = document.getElementById(item.id);
        if (heading && heading.getBoundingClientRect().top <= readingLine) {
          nextSection = item;
        } else if (heading) {
          break;
        }
      }

      const articleRect = articleRoot.getBoundingClientRect();
      const articleTop = window.scrollY + articleRect.top;
      const readableDistance = Math.max(1, articleRoot.scrollHeight - window.innerHeight);
      const nextProgress = clampReadingProgress(((window.scrollY - articleTop) / readableDistance) * 100);
      setActiveSectionId(nextSection?.id ?? null);
      setReadingProgress(nextProgress);
      pendingState = updateLastMeaningfulPosition(
        pendingState,
        nextSection,
        nextProgress,
        new Date().toISOString(),
      );
      if (explicitSectionRef.current?.id === nextSection?.id) {
        explicitSectionRef.current = null;
      }
      schedulePersist();
    };

    const schedulePositionUpdate = () => {
      if (!frame) {
        frame = window.requestAnimationFrame(updateReadingPosition);
      }
    };

    const restorePosition = () => {
      const saved = loadReaderProgress(currentArticleId);
      const hashSection = decodeHash(window.location.hash);
      const targetSection = hashSection && outline.some((item) => item.id === hashSection)
        ? hashSection
        : saved?.section_id;
      const target = targetSection ? document.getElementById(targetSection) : null;
      if (target) {
        target.scrollIntoView({ behavior: "auto", block: "start" });
        setActiveSectionId(targetSection ?? null);
      }
      if (saved) {
        setReadingProgress(saved.progress);
      }
      restored = true;
      updateReadingPosition();
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        persist();
      }
    };

    window.addEventListener("scroll", schedulePositionUpdate, { passive: true });
    window.addEventListener("resize", schedulePositionUpdate);
    window.addEventListener("pagehide", persist);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    restoreFrame = window.requestAnimationFrame(() => {
      restoreFrame = window.requestAnimationFrame(restorePosition);
    });

    return () => {
      window.removeEventListener("scroll", schedulePositionUpdate);
      window.removeEventListener("resize", schedulePositionUpdate);
      window.removeEventListener("pagehide", persist);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (frame) {
        window.cancelAnimationFrame(frame);
      }
      if (restoreFrame) {
        window.cancelAnimationFrame(restoreFrame);
      }
      persist();
    };
  }, [article?.id, outline]);

  function handleOutlineNavigate(sectionId: string) {
    const target = document.getElementById(sectionId);
    const section = outline.find((item) => item.id === sectionId);
    if (!target || !article || !section) {
      return;
    }
    window.history.replaceState(null, "", `#${encodeURIComponent(sectionId)}`);
    explicitSectionRef.current = section;
    target.scrollIntoView({ behavior: "auto", block: "start" });
    target.focus({ preventScroll: true });
    setActiveSectionId(sectionId);
    saveReaderProgress({
      article_id: article.id,
      section_id: section.id,
      section_title: section.label,
      progress: readingProgress,
      updated_at: new Date().toISOString(),
    });
  }

  function handleReaderPreferences(nextPreferences: ReaderPreferences) {
    const saved = saveReaderPreferences(nextPreferences);
    setReaderPreferences(saved);
  }

  if (error) {
    return (
      <WorkspaceState
        action={
          <Link
            className="rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-900 hover:border-red-500"
            href={listReturnTo}
          >
            {returnLabel}
          </Link>
        }
        detail={error}
        title="Article unavailable"
        tone="error"
      />
    );
  }

  if (!article) {
    return <WorkspaceState title="Loading article" tone="loading" />;
  }

  const workflowContext = {
    articleId: article.id,
    articleTitle: article.title,
    listReturnTo,
    sectionId: activeSectionId,
  };

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start">
      <article
        ref={articleRootRef}
        id="article-start"
        className="reader-workspace min-w-0 rounded border border-slate-200 bg-white p-5"
        data-reader-size={readerPreferences.textSize}
        data-reader-width={readerPreferences.width}
      >
        <Link className="text-sm text-slate-600 hover:text-slate-950" href={listReturnTo}>
          {returnLabel}
        </Link>
        <h1 className="mt-4 break-words text-2xl font-semibold leading-tight">{article.title}</h1>
        <p className="mt-2 text-sm text-slate-500">{formatMetadata(article.metadata)}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <a
            className="inline-block text-sm font-medium text-emerald-800 hover:text-emerald-950"
            href={article.url}
            rel="noreferrer"
            target="_blank"
          >
            Source article
          </a>
          <span aria-hidden="true" className="text-slate-300">/</span>
          <a
            className="rounded border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 lg:hidden"
            href="#article-outline"
          >
            Outline
          </a>
          <a
            className="rounded border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 lg:hidden"
            href="#reading-tools"
          >
            Reading tools
          </a>
        </div>
        <ReadingProgress activeSection={activeSection} progress={readingProgress} />
        <div className="reader-content mt-6">
          <div className="reader-markdown">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
              components={markdownComponents}
            >
              {renderedContent}
            </ReactMarkdown>
          </div>
        </div>
        <StructuredReferencesPanel articleId={article.id} />
      </article>

      <aside
        id="reading-tools"
        aria-label="Reading tools"
        className="scroll-mt-24 space-y-4 lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto lg:pr-1"
        tabIndex={-1}
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-300 pb-2">
          <h2 className="text-base font-semibold">Reading tools</h2>
          <a className="text-xs font-medium text-emerald-800 hover:text-emerald-950 lg:hidden" href="#article-start">
            Back to article
          </a>
        </div>
        <section data-testid="article-study-actions" className="rounded border border-emerald-200 bg-emerald-50 p-4">
          <h2 className="text-base font-semibold text-emerald-950">Study this article</h2>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Link
              className="rounded bg-emerald-800 px-3 py-2 text-center text-sm font-semibold text-white hover:bg-emerald-900"
              href={createLearningToolHref("tutor", workflowContext)}
            >
              Ask tutor
            </Link>
            <Link
              className="rounded border border-emerald-300 bg-white px-3 py-2 text-center text-sm font-semibold text-emerald-900 hover:border-emerald-600"
              href={createLearningToolHref("graph", workflowContext)}
            >
              Explore graph
            </Link>
          </div>
        </section>
        <section id="article-outline" className="scroll-mt-24 rounded border border-slate-200 bg-white p-4">
          <ArticleOutline activeSectionId={activeSectionId} items={outline} onNavigate={handleOutlineNavigate} />
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <ReaderDisplayControls preferences={readerPreferences} onChange={handleReaderPreferences} />
        </section>

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
          <dl className="mt-3 space-y-3 text-sm">
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
              <dd>{renderMetadataList(metadataImages, "Image")}</dd>
            </div>
            <div>
              <dt className="text-slate-500">References</dt>
              <dd>{renderMetadataList(metadataReferences, "Reference")}</dd>
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

type MarkdownItem = {
  label: string;
  href?: string;
};

const metadataLabelKeys = ["title", "name", "label", "filename", "path", "source", "reference", "id"];
const metadataLinkKeys = ["url", "link", "href", "source_url", "pdf_url", "download_url", "html_url", "image"];

function parseMetadataItems(values?: Array<string | Record<string, unknown>>): MarkdownItem[] {
  if (!values?.length) {
    return [];
  }
  const parsed = values
    .map((value) => {
      if (typeof value === "string") {
        return toMarkdownItem({ text: value, link: value });
      }
      if (value && typeof value === "object") {
        const text = pickString(value as Record<string, unknown>, metadataLabelKeys);
        const link = pickString(value as Record<string, unknown>, metadataLinkKeys);
        return toMarkdownItem({ text, link });
      }
      return null;
    })
    .filter((item): item is MarkdownItem => item !== null);

  return parsed;
}

function pickString(input: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = input[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function toMarkdownItem({ text, link }: { text: string | null; link?: string | null }): MarkdownItem | null {
  if (!text) {
    return null;
  }
  const label = sanitizeDisplay(text);
  const href = (link ?? "").trim();
  if (href && isExternalUrl(href)) {
    return { label, href };
  }
  return { label };
}

function sanitizeDisplay(value: string): string {
  const raw = value.trim();
  if (!raw) {
    return "Unknown";
  }
  return looksLikeLocalPath(raw) ? raw.split(/[\\/]/).pop() ?? raw : raw;
}

function looksLikeLocalPath(value: string): boolean {
  return (
    value.startsWith("/") ||
    value.startsWith("./") ||
    value.startsWith("../") ||
    /^[a-zA-Z]:\\/.test(value) ||
    value.includes("/tmp/") ||
    value.includes("\\tmp\\")
  );
}

function isExternalUrl(value: string): boolean {
  return /^https?:\/\//i.test(value) || /^mailto:/i.test(value) || /^tel:/i.test(value);
}

function renderMetadataList(values: MarkdownItem[], emptyLabel: string): ReactNode {
  if (!values.length) {
    return <p className="text-xs text-slate-500">No {emptyLabel.toLowerCase()} metadata.</p>;
  }
  return (
    <ul className="mt-1 list-disc space-y-1 break-all pl-5 text-sm">
      {values.map((item) => (
        <li key={`${item.label}-${item.href ?? "no-url"}`}>
          {item.href ? (
            <a className="text-slate-700 underline underline-offset-2 hover:text-slate-950" href={item.href} rel="noreferrer" target="_blank">
              {item.label}
            </a>
          ) : (
            item.label
          )}
        </li>
      ))}
    </ul>
  );
}

const baseMarkdownComponents: Components = {
  a: ({ node: _node, href, ...props }) => {
    const normalizedHref = normalizeContentUrl(href);
    const isExternal = typeof normalizedHref === "string" && isExternalUrl(normalizedHref);
    if (!isExternal) {
      return (
        <a
          {...props}
          href={normalizedHref ?? "#"}
          rel={props.rel ?? undefined}
          target={props.target ?? undefined}
          className="text-sky-700 underline underline-offset-2 hover:text-slate-950"
        />
      );
    }
    return (
      <a
        {...props}
        href={normalizedHref}
        rel="noopener noreferrer"
        target="_blank"
        className="text-sky-700 underline underline-offset-2 hover:text-slate-950"
      />
    );
  },
  img: (props) => <MarkdownImage {...props} />,
};

function createMarkdownComponents(outline: ArticleOutlineItem[]): Components {
  const headingIdsByLine = new Map(outline.map((item) => [item.line, item.id]));
  return {
    ...baseMarkdownComponents,
    h2: ({ node, ...props }) => (
      <h2 {...props} id={headingIdForNode(node, headingIdsByLine)} className="scroll-mt-24" tabIndex={-1} />
    ),
    h3: ({ node, ...props }) => (
      <h3 {...props} id={headingIdForNode(node, headingIdsByLine)} className="scroll-mt-24" tabIndex={-1} />
    ),
    h4: ({ node, ...props }) => (
      <h4 {...props} id={headingIdForNode(node, headingIdsByLine)} className="scroll-mt-24" tabIndex={-1} />
    ),
  };
}

function headingIdForNode(node: unknown, headingIdsByLine: Map<number, string>): string | undefined {
  const candidate = node as { position?: { start?: { line?: number } } } | undefined;
  const line = candidate?.position?.start?.line;
  return typeof line === "number" ? headingIdsByLine.get(line) : undefined;
}

function MarkdownImage({ node: _node, src: rawSrc, alt: rawAlt, ...props }: ComponentPropsWithoutRef<"img"> & { node?: unknown }) {
  const src = normalizeContentUrl(typeof rawSrc === "string" ? rawSrc : "") ?? "";
  const alt = typeof rawAlt === "string" && rawAlt.trim() ? rawAlt : "Article image";

  if (!src) {
    return (
      <span className="mt-1 inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-700">
        <span>{`${alt} unavailable`}</span>
      </span>
    );
  }

  if (!isInlineImageUrl(src)) {
    return (
      <span className="my-2 block border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        <span className="font-medium">{alt}</span>
        <span className="block text-xs leading-5 text-amber-800">External image not loaded automatically.</span>
        <a className="mt-1 inline-block text-xs font-semibold underline underline-offset-2" href={src} rel="noopener noreferrer" target="_blank">
          Open image at source
        </a>
      </span>
    );
  }

  return (
    <img
      {...props}
      src={src}
      alt={alt}
      className="max-w-full rounded border border-slate-200"
      loading="lazy"
    />
  );
}

function isInlineImageUrl(value: string): boolean {
  return value.startsWith("data:") || value.startsWith("blob:");
}

function normalizeContentUrl(value: string | undefined): string | undefined {
  if (!value) {
    return value;
  }
  if (isExternalUrl(value) || value.startsWith("#")) {
    return value;
  }
  if (value.startsWith("//")) {
    return `https:${value}`;
  }
  try {
    return new URL(value, "https://spaces.ac.cn").toString();
  } catch {
    return value;
  }
}

function decodeHash(hash: string): string | null {
  if (!hash.startsWith("#") || hash.length <= 1) {
    return null;
  }
  try {
    return decodeURIComponent(hash.slice(1));
  } catch {
    return null;
  }
}
