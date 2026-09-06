"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ComponentPropsWithoutRef,
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type {
  KeyboardEvent as ReactKeyboardEvent,
  MouseEvent as ReactMouseEvent,
} from "react";
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
  fetchLearningSessions,
  fetchLearningStates,
  fetchNotes,
  updateLearningState,
  updateNote,
} from "@/lib/learning";
import { ReadingHistoryItem, loadReadingHistory, recordReading } from "@/lib/readingHistory";
import {
  getGraphSessionStorage,
  isSameTabNavigation,
  rememberGraphArticleReturnFocus,
} from "@/lib/graphWorkspace";
import { createLearningToolHref } from "@/lib/learningWorkflow";
import {
  SHELL_FOCUS_OPERATION_EVENT,
  SHELL_HISTORY_NAVIGATION_EVENT,
  SHELL_ROUTE_COMMIT_EVENT,
  consumeShellHistoryNavigation,
  createShellRouteIdentity,
  getShellFocusOperationVersion,
  getShellRouteCommitAction,
  getShellRouteCommitFocusOperationVersion,
  hasPendingShellHistoryNavigation,
  isShellDestinationFocusAction,
  recordShellDestinationFocusIntent,
  shouldTransferDeferredReaderFragmentFocus,
} from "@/lib/navigation";
import {
  ReaderMutationKind,
  ReaderMutationOperation,
  ReaderNoteDeleteIntent,
  createReaderNoteDeleteIntent,
  createReaderMutationOperation,
  mergeCreatedLearningNote,
  mergeUpdatedLearningNote,
  ownsReaderNoteDeleteIntent,
  ownsReaderMutation,
  removeLearningNote,
} from "@/lib/readerLearningMutations";
import {
  activateStudySessionItem,
  createStudySessionCompletionSummary,
  createStudySessionReaderHref,
  getStudySessionPosition,
  loadStudySession,
  saveStudySession,
  type StudySessionPosition,
} from "@/lib/studySession";
import { StructuredReferencesPanel } from "@/components/StructuredReferencesPanel";
import { WorkspaceState } from "@/components/WorkspaceState";
import { ZoteroLinksPanel } from "@/components/ZoteroLinksPanel";

type ArticleOperation = {
  articleId: string;
  generation: number;
};

type MutationFeedback = {
  tone: "pending" | "success" | "error";
  message: string;
};

type ReaderFocusRequest = Readonly<{
  articleId: string;
  generation: number;
  interactionVersion: number | null;
  noteId?: string;
  origin?: HTMLElement | null;
  target:
    | "bookmark"
    | "completion"
    | "delete-trigger"
    | "edit-trigger"
    | "learning-state"
    | "note-editor"
    | "note-feedback"
    | "session";
}>;

const ARTICLE_LOAD_TIMEOUT_MS = 10_000;
const DEFERRED_FRAGMENT_FOCUS_TIMEOUT_MS = 20_000;
const READER_MANAGED_HEADING_STATE_KEY = "__scientificSpacesReaderManagedHeadingV1";
type ReaderFragmentTargetId = "article-start" | "article-outline" | "reading-tools";
type ReaderFragmentHistoryIntent = Readonly<{
  articleId: string;
  expectedHash: string;
  routeQuery: string;
  targetId: string;
  targetKind: "fixed" | "hashless" | "heading" | "structured-reference";
}>;
type ReaderRouteFocusIntent =
  | "none"
  | "guided"
  | "history"
  | "history-guided"
  | "retry"
  | "route";

function getReaderFragmentTargetId(hash: string): ReaderFragmentTargetId | null {
  const targetId = decodeHash(hash);
  return targetId === "article-start"
    || targetId === "article-outline"
    || targetId === "reading-tools"
    ? targetId
    : null;
}

function normalizeReaderRouteQuery(search: string): string {
  const parameters = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  parameters.sort();
  return parameters.toString();
}

function parseReaderReferencePage(search: string): number {
  const page = Number.parseInt(new URLSearchParams(search).get("reference_page") ?? "", 10);
  return Number.isSafeInteger(page) && page > 0 ? Math.min(page, 100_000) : 1;
}

function getCurrentReaderArticleId(): string | null {
  const match = /^\/articles\/([^/]+)\/?$/.exec(window.location.pathname);
  if (!match) {
    return null;
  }
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

function getReaderFragmentHistoryIntent(
  includeHashless = false,
  includeUnmanagedHeading = includeHashless,
): ReaderFragmentHistoryIntent | null {
  const articleId = getCurrentReaderArticleId();
  const expectedHash = window.location.hash;
  const decodedTargetId = decodeHash(expectedHash);
  const fixedTargetId = getReaderFragmentTargetId(expectedHash);
  const structuredReferenceTargetId = decodedTargetId?.startsWith("structured-reference-")
    ? decodedTargetId
    : null;
  const managedHeadingState = window.history.state?.[READER_MANAGED_HEADING_STATE_KEY];
  const managedHeadingTargetId = managedHeadingState
    && typeof managedHeadingState === "object"
    && managedHeadingState.articleId === articleId
    && managedHeadingState.targetId === decodedTargetId
    ? decodedTargetId
    : null;
  const headingTargetId = decodedTargetId
    && decodedTargetId.length <= 256
    && (includeUnmanagedHeading || managedHeadingTargetId === decodedTargetId)
    ? decodedTargetId
    : null;
  const hashlessTargetId = includeHashless && expectedHash === "" ? "article-start" : null;
  const targetId = fixedTargetId
    ?? structuredReferenceTargetId
    ?? hashlessTargetId
    ?? headingTargetId;
  if (!articleId || !targetId) {
    return null;
  }
  return {
    articleId,
    expectedHash,
    routeQuery: normalizeReaderRouteQuery(window.location.search),
    targetId,
    targetKind: fixedTargetId
      ? "fixed"
      : structuredReferenceTargetId
        ? "structured-reference"
        : hashlessTargetId
          ? "hashless"
          : "heading",
  };
}

function hasOpenReaderModal(): boolean {
  return document.querySelector('[role="dialog"][aria-modal="true"]') !== null;
}

function shouldUseGuidedReaderRouteFocus(hash: string): boolean {
  const decodedTargetId = decodeHash(hash);
  return hash === ""
    || (
      getReaderFragmentTargetId(hash) === null
      && !decodedTargetId?.startsWith("structured-reference-")
    );
}

function hasGraphDetailFocusTarget(returnTo: string): boolean {
  if (!returnTo.startsWith("/graph?")) {
    return false;
  }
  return Boolean(new URLSearchParams(returnTo.slice(returnTo.indexOf("?") + 1)).get("node_id")?.trim());
}

function focusVisibleElement(target: HTMLElement | null) {
  if (!target?.isConnected) {
    return;
  }
  target.scrollIntoView({ behavior: "auto", block: "nearest", inline: "nearest" });
  target.focus({ preventScroll: true });
}

export function ArticleDetailView({
  articleId,
  listReturnTo,
}: Readonly<{
  articleId: string;
  listReturnTo: string;
}>) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const routeQuery = searchParams.toString();
  const [readerRouteFocusIntent, setReaderRouteFocusIntent] =
    useState<ReaderRouteFocusIntent>("none");
  const [shellRouteCommitVersion, setShellRouteCommitVersion] = useState(0);
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [learningState, setLearningState] = useState<LearningState | null>(null);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [notes, setNotes] = useState<LearningNote[]>([]);
  const [noteDraft, setNoteDraft] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState("");
  const [activeSession, setActiveSession] = useState<LearningSession | null>(null);
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [articleRevision, setArticleRevision] = useState(0);
  const [learningError, setLearningError] = useState<string | null>(null);
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [readingProgress, setReadingProgress] = useState(0);
  const [readerPreferences, setReaderPreferences] = useState<ReaderPreferences>(DEFAULT_READER_PREFERENCES);
  const [studySessionPosition, setStudySessionPosition] = useState<StudySessionPosition | null>(null);
  const [studySessionWarning, setStudySessionWarning] = useState<string | null>(null);
  const [studySessionEligible, setStudySessionEligible] = useState(false);
  const [completionRegionMounted, setCompletionRegionMounted] = useState(false);
  const [completionPrepared, setCompletionPrepared] = useState(false);
  const [completionPending, setCompletionPending] = useState<"complete" | "advance" | "timer" | null>(null);
  const [completionMessage, setCompletionMessage] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [completionTerminal, setCompletionTerminal] = useState(false);
  const [timerWarning, setTimerWarning] = useState<"confirmed-open" | "unknown" | "unavailable" | null>(null);
  const [sessionLoadState, setSessionLoadState] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [learningMutationPending, setLearningMutationPending] = useState(false);
  const [sessionEndPending, setSessionEndPending] = useState(false);
  const [bookmarkMutationPending, setBookmarkMutationPending] = useState(false);
  const [bookmarkFeedback, setBookmarkFeedback] = useState<MutationFeedback | null>(null);
  const [noteMutationPending, setNoteMutationPending] = useState<ReaderMutationOperation | null>(null);
  const [noteFeedback, setNoteFeedback] = useState<MutationFeedback | null>(null);
  const [noteDeleteIntent, setNoteDeleteIntent] = useState<ReaderNoteDeleteIntent | null>(null);
  const [noteDeleteReconciliationRequired, setNoteDeleteReconciliationRequired] =
    useState<ReaderNoteDeleteIntent | null>(null);
  const [readerFocusRequest, setReaderFocusRequest] = useState<ReaderFocusRequest | null>(null);
  const [bookmarkLoadState, setBookmarkLoadState] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [noteLoadState, setNoteLoadState] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const learningLoadArticleRef = useRef<string | null>(null);
  const articleIdRef = useRef(articleId);
  const articleGenerationRef = useRef(0);
  const completionOperationRef = useRef<ArticleOperation | null>(null);
  const learningMutationRef = useRef<ArticleOperation | null>(null);
  const sessionEndOperationRef = useRef<ArticleOperation | null>(null);
  const bookmarkMutationRef = useRef<ReaderMutationOperation | null>(null);
  const noteMutationRef = useRef<ReaderMutationOperation | null>(null);
  const mutationSequenceRef = useRef(0);
  const articleRootRef = useRef<HTMLElement | null>(null);
  const articleHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const articleRetryRef = useRef<HTMLButtonElement | null>(null);
  const completionRegionRef = useRef<HTMLElement | null>(null);
  const fragmentFocusFrameRef = useRef(0);
  const fragmentHistoryIntentRef = useRef<ReaderFragmentHistoryIntent | null>(null);
  const deferredFragmentFocusCleanupRef = useRef<(() => void) | null>(null);
  const fragmentVisibilityCleanupRef = useRef<(() => void) | null>(null);
  const readerInteractionVersionRef = useRef(0);
  const readerFocusClaimInteractionVersionRef = useRef<number | null>(null);
  const explicitSectionRef = useRef<ArticleOutlineItem | null>(null);
  const noteDeleteCancelRef = useRef<HTMLButtonElement | null>(null);
  const noteDeleteConfirmationRef = useRef<HTMLDivElement | null>(null);
  const noteDeleteButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const noteStatusRef = useRef<HTMLParagraphElement | null>(null);
  const noteErrorRef = useRef<HTMLParagraphElement | null>(null);
  const noteEditorRefs = useRef(new Map<string, HTMLTextAreaElement>());
  const noteEditButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const learningStateRegionRef = useRef<HTMLElement | null>(null);
  const bookmarkRegionRef = useRef<HTMLElement | null>(null);
  const sessionRegionRef = useRef<HTMLElement | null>(null);
  const noteDeleteRouteQueryRef = useRef(routeQuery);
  const returnLabel = listReturnTo === "/session"
    ? "Back to study session"
    : listReturnTo.startsWith("/library")
      ? "Back to saved library"
      : listReturnTo.startsWith("/graph?node_id=concept%3A")
        ? "Back to concept"
        : listReturnTo.startsWith("/graph")
          ? "Return to graph"
      : "Back to articles";
  const isGuidedReaderRoute = listReturnTo === "/session" || listReturnTo.startsWith("/graph");
  const ownsRouteFocus = readerRouteFocusIntent !== "none";
  const bookmarkControlsReady = bookmarkLoadState === "loaded";
  const noteControlsReady = noteLoadState === "loaded";
  const activeNoteDeleteIntent = noteDeleteIntent?.articleId === articleId
    && noteDeleteIntent.generation === articleGenerationRef.current
    ? noteDeleteIntent
    : null;
  const activeNoteDeleteReconciliation = noteDeleteReconciliationRequired?.articleId === articleId
    && noteDeleteReconciliationRequired.generation === articleGenerationRef.current
    ? noteDeleteReconciliationRequired
    : null;
  const noteInteractionLocked = noteMutationPending !== null
    || activeNoteDeleteIntent !== null
    || activeNoteDeleteReconciliation !== null;

  const claimReaderRouteFocus = useCallback((intent: ReaderRouteFocusIntent) => {
    readerFocusClaimInteractionVersionRef.current = intent === "none"
      ? null
      : readerInteractionVersionRef.current;
    setReaderRouteFocusIntent(intent);
  }, []);

  useEffect(() => {
    const recordReaderInteraction = () => {
      readerInteractionVersionRef.current += 1;
    };
    window.addEventListener("keydown", recordReaderInteraction, true);
    window.addEventListener("pointerdown", recordReaderInteraction, true);
    window.addEventListener("touchstart", recordReaderInteraction, { capture: true, passive: true });
    window.addEventListener("wheel", recordReaderInteraction, { capture: true, passive: true });
    return () => {
      window.removeEventListener("keydown", recordReaderInteraction, true);
      window.removeEventListener("pointerdown", recordReaderInteraction, true);
      window.removeEventListener("touchstart", recordReaderInteraction, true);
      window.removeEventListener("wheel", recordReaderInteraction, true);
    };
  }, []);

  useLayoutEffect(() => {
    const recordShellRouteCommit = () => {
      setShellRouteCommitVersion((current) => current + 1);
    };
    window.addEventListener(SHELL_ROUTE_COMMIT_EVENT, recordShellRouteCommit);
    return () => window.removeEventListener(SHELL_ROUTE_COMMIT_EVENT, recordShellRouteCommit);
  }, []);

  useEffect(() => {
    const restoreGuidedHeadingFocus = () => {
      const pendingHistoryIntent = fragmentHistoryIntentRef.current;
      if (
        !isGuidedReaderRoute
        || !articleIdRef.current
        || (
          pendingHistoryIntent?.articleId === articleIdRef.current
          && pendingHistoryIntent.expectedHash === window.location.hash
        )
        || getReaderFragmentHistoryIntent(false) !== null
        || !shouldUseGuidedReaderRouteFocus(window.location.hash)
      ) {
        return;
      }
      fragmentHistoryIntentRef.current = null;
      claimReaderRouteFocus("history-guided");
    };
    window.addEventListener("hashchange", restoreGuidedHeadingFocus);
    return () => window.removeEventListener("hashchange", restoreGuidedHeadingFocus);
  }, [claimReaderRouteFocus, isGuidedReaderRoute]);

  useEffect(() => {
    const normalizedRouteQuery = normalizeReaderRouteQuery(routeQuery);
    const hasPendingHistoryNavigation = hasPendingShellHistoryNavigation(
      window.location.pathname,
      window.location.search,
      window.location.hash,
    );
    let historyIntent = fragmentHistoryIntentRef.current;
    if (
      (!historyIntent
        || historyIntent.articleId !== articleId
        || historyIntent.routeQuery !== normalizedRouteQuery
        || historyIntent.expectedHash !== window.location.hash)
      && hasPendingHistoryNavigation
    ) {
      historyIntent = getReaderFragmentHistoryIntent(!isGuidedReaderRoute);
      fragmentHistoryIntentRef.current = historyIntent;
    }
    if (
      historyIntent?.articleId === articleId
      && historyIntent.routeQuery === normalizedRouteQuery
      && historyIntent.expectedHash === window.location.hash
    ) {
      claimReaderRouteFocus("history");
      return;
    }
    fragmentHistoryIntentRef.current = null;
    if (
      isGuidedReaderRoute
      && hasPendingHistoryNavigation
      && shouldUseGuidedReaderRouteFocus(window.location.hash)
    ) {
      claimReaderRouteFocus("history-guided");
      return;
    }

    const routeIdentity = createShellRouteIdentity(
      window.location.pathname,
      window.location.search,
    );
    const routeCommitAction = getShellRouteCommitAction(routeIdentity);
    const routeFocusOperationIsCurrent = getShellRouteCommitFocusOperationVersion(routeIdentity)
      === getShellFocusOperationVersion();
    const readerOwnsCommittedDestination = routeCommitAction === "route"
      || routeCommitAction === "invalidate";
    if (
      routeFocusOperationIsCurrent
      && routeCommitAction === "route"
      && !isGuidedReaderRoute
      && window.location.hash === ""
      && !hasOpenReaderModal()
    ) {
      document.getElementById("main-content")?.focus({ preventScroll: true });
    }
    claimReaderRouteFocus(
      !routeFocusOperationIsCurrent
        ? "none"
        : isGuidedReaderRoute
          && (
            isShellDestinationFocusAction(routeCommitAction)
            || routeCommitAction === "invalidate"
          )
        ? "guided"
        : readerOwnsCommittedDestination
          ? "route"
          : "none",
    );
  }, [
    articleId,
    claimReaderRouteFocus,
    isGuidedReaderRoute,
    routeQuery,
    shellRouteCommitVersion,
  ]);

  useEffect(() => {
    function cancelReaderOwnedFocus() {
      fragmentHistoryIntentRef.current = null;
      if (fragmentFocusFrameRef.current) {
        window.cancelAnimationFrame(fragmentFocusFrameRef.current);
        fragmentFocusFrameRef.current = 0;
      }
      deferredFragmentFocusCleanupRef.current?.();
      fragmentVisibilityCleanupRef.current?.();
      claimReaderRouteFocus("none");
    }

    window.addEventListener(SHELL_FOCUS_OPERATION_EVENT, cancelReaderOwnedFocus);
    return () => {
      window.removeEventListener(SHELL_FOCUS_OPERATION_EVENT, cancelReaderOwnedFocus);
      fragmentHistoryIntentRef.current = null;
      if (fragmentFocusFrameRef.current) {
        window.cancelAnimationFrame(fragmentFocusFrameRef.current);
        fragmentFocusFrameRef.current = 0;
      }
      deferredFragmentFocusCleanupRef.current?.();
      fragmentVisibilityCleanupRef.current?.();
    };
  }, [claimReaderRouteFocus]);

  useLayoutEffect(() => {
    articleIdRef.current = articleId;
  }, [articleId]);

  useLayoutEffect(() => {
    if (
      !article
      || article.id === articleId
      || isGuidedReaderRoute
      || hasOpenReaderModal()
    ) {
      return;
    }
    document.getElementById("main-content")?.focus({ preventScroll: true });
  }, [article, articleId, isGuidedReaderRoute]);

  useLayoutEffect(() => {
    const intent = activeNoteDeleteIntent;
    if (
      !intent
      || noteMutationPending?.kind === "note-delete"
      || !ownsReaderNoteDeleteIntent(
        noteDeleteIntent,
        intent,
        articleIdRef.current,
        articleGenerationRef.current,
      )
    ) {
      return;
    }
    focusVisibleElement(noteDeleteCancelRef.current);
  }, [activeNoteDeleteIntent, noteDeleteIntent, noteMutationPending]);

  useLayoutEffect(() => {
    const previousRouteQuery = noteDeleteRouteQueryRef.current;
    noteDeleteRouteQueryRef.current = routeQuery;
    const intent = activeNoteDeleteIntent;
    if (
      previousRouteQuery === routeQuery
      || !intent
      || !ownsReaderNoteDeleteIntent(
        noteDeleteIntent,
        intent,
        articleIdRef.current,
        articleGenerationRef.current,
      )
    ) {
      return;
    }
    const operation = noteMutationRef.current;
    if (
      operation?.kind === "note-delete"
      && operation.articleId === intent.articleId
      && operation.generation === intent.generation
      && operation.noteId === intent.noteId
    ) {
      noteMutationRef.current = null;
      setNoteMutationPending(null);
      setNoteDeleteReconciliationRequired(intent);
      setNoteFeedback({
        tone: "error",
        message: "The note deletion could not be confirmed after navigation. The current Reader rendering was kept, but the saved result may differ. Reload this Article before retrying.",
      });
    }
    focusVisibleElement(articleHeadingRef.current);
    setNoteDeleteIntent(null);
    setReaderFocusRequest(null);
  }, [activeNoteDeleteIntent, noteDeleteIntent, routeQuery]);

  useLayoutEffect(() => {
    const request = readerFocusRequest;
    if (!request) {
      return;
    }
    if (
      articleIdRef.current !== request.articleId
      || articleGenerationRef.current !== request.generation
    ) {
      setReaderFocusRequest((current) => (current === request ? null : current));
      return;
    }
    const activeElement = document.activeElement;
    const stillOwnsFocus = request.interactionVersion === null
      || (
        readerInteractionVersionRef.current === request.interactionVersion
        && (
          !activeElement
          || activeElement === document.body
          || !activeElement.isConnected
          || activeElement === request.origin
        )
      );
    const target = resolveReaderFocusTarget(request);
    if (stillOwnsFocus) {
      focusVisibleElement(target);
    }
    setReaderFocusRequest((current) => (current === request ? null : current));
  }, [readerFocusRequest, noteFeedback]);

  function resolveReaderFocusTarget(request: ReaderFocusRequest): HTMLElement | null {
    if (request.target === "learning-state") {
      return learningStateRegionRef.current;
    }
    if (request.target === "bookmark") {
      return bookmarkRegionRef.current;
    }
    if (request.target === "completion") {
      return completionRegionRef.current;
    }
    if (request.target === "session") {
      return sessionRegionRef.current;
    }
    if (request.target === "note-feedback") {
      return noteFeedback?.tone === "error" ? noteErrorRef.current : noteStatusRef.current;
    }
    if (request.target === "note-editor") {
      return request.noteId ? noteEditorRefs.current.get(request.noteId) ?? null : null;
    }
    if (request.target === "edit-trigger") {
      return request.noteId ? noteEditButtonRefs.current.get(request.noteId) ?? null : null;
    }
    return request.noteId ? noteDeleteButtonRefs.current.get(request.noteId) ?? null : null;
  }

  function prepareGraphReturnFocus(event: ReactMouseEvent<HTMLAnchorElement>) {
    if (isSameTabNavigation(event) && listReturnTo.startsWith("/graph")) {
      if (hasGraphDetailFocusTarget(listReturnTo)) {
        recordShellDestinationFocusIntent(listReturnTo, window.location.href);
      }
      rememberGraphArticleReturnFocus(
        getGraphSessionStorage(window),
        listReturnTo,
        article?.id ?? articleId,
      );
    }
  }

  const scheduleReaderFragmentFocus = useCallback((
    targetId: string,
    options: Readonly<{
      expectedHash?: string;
      frameCount?: number;
      interactionVersion?: number;
      onSettled?: () => void;
      preserveNewerFocus?: boolean;
      requireArticleHeading?: boolean;
    }> = {},
  ) => {
    const expectedArticleId = articleIdRef.current;
    const expectedGeneration = articleGenerationRef.current;
    const expectedRouteQuery = normalizeReaderRouteQuery(window.location.search);
    const expectedHash = options.expectedHash ?? `#${targetId}`;
    const expectedInteractionVersion = options.interactionVersion
      ?? readerFocusClaimInteractionVersionRef.current;
    const initialActiveElement = document.activeElement;
    let remainingFrames = Math.max(options.frameCount ?? 1, 1);
    deferredFragmentFocusCleanupRef.current?.();
    fragmentVisibilityCleanupRef.current?.();
    if (fragmentFocusFrameRef.current) {
      window.cancelAnimationFrame(fragmentFocusFrameRef.current);
      fragmentFocusFrameRef.current = 0;
    }
    const scheduleFrame = () => {
      fragmentFocusFrameRef.current = window.requestAnimationFrame(() => {
        fragmentFocusFrameRef.current = 0;
        remainingFrames -= 1;
        if (remainingFrames > 0) {
          scheduleFrame();
          return;
        }
        const target = document.getElementById(targetId);
        try {
          const currentArticleId = getCurrentReaderArticleId();
          if (
            articleIdRef.current !== expectedArticleId
            || articleGenerationRef.current !== expectedGeneration
            || currentArticleId !== expectedArticleId
            || normalizeReaderRouteQuery(window.location.search) !== expectedRouteQuery
            || window.location.hash !== expectedHash
            || (
              expectedInteractionVersion !== null
              && readerInteractionVersionRef.current !== expectedInteractionVersion
            )
            || !target?.isConnected
            || (
              options.requireArticleHeading
              && (
                !(target instanceof HTMLHeadingElement)
                || !articleRootRef.current?.contains(target)
              )
            )
            || hasOpenReaderModal()
          ) {
            return;
          }
          if (options.preserveNewerFocus) {
            const activeElement = document.activeElement;
            const main = document.getElementById("main-content");
            const focusCanTransfer = shouldTransferDeferredReaderFragmentFocus(
              !activeElement || activeElement === document.body,
              Boolean(activeElement?.isConnected),
              activeElement === main,
              activeElement === target,
              activeElement === initialActiveElement,
            )
              || activeElement === articleHeadingRef.current
              || (
                expectedHash === ""
                && activeElement instanceof HTMLElement
                && getReaderFragmentTargetId(`#${activeElement.id}`) !== null
              );
            if (!focusCanTransfer) {
              return;
            }
          }
          target.scrollIntoView({ behavior: "auto", block: "start" });
          target.focus({ preventScroll: true });
          const visibilityDeadline = window.performance.now() + 5_000;
          let visibilityActive = true;
          const stopVisibility = () => {
            if (!visibilityActive) {
              return;
            }
            visibilityActive = false;
            if (fragmentFocusFrameRef.current) {
              window.cancelAnimationFrame(fragmentFocusFrameRef.current);
              fragmentFocusFrameRef.current = 0;
            }
            window.removeEventListener("keydown", stopVisibility, true);
            window.removeEventListener("pointerdown", stopVisibility, true);
            window.removeEventListener("touchstart", stopVisibility, true);
            window.removeEventListener("wheel", stopVisibility, true);
            if (fragmentVisibilityCleanupRef.current === stopVisibility) {
              fragmentVisibilityCleanupRef.current = null;
            }
          };
          fragmentVisibilityCleanupRef.current = stopVisibility;
          window.addEventListener("keydown", stopVisibility, true);
          window.addEventListener("pointerdown", stopVisibility, true);
          window.addEventListener("touchstart", stopVisibility, { capture: true, passive: true });
          window.addEventListener("wheel", stopVisibility, { capture: true, passive: true });
          const keepFocusedTargetVisible = () => {
            fragmentFocusFrameRef.current = window.requestAnimationFrame(() => {
              fragmentFocusFrameRef.current = 0;
              if (
                !visibilityActive
                || document.activeElement !== target
                || articleIdRef.current !== expectedArticleId
                || articleGenerationRef.current !== expectedGeneration
                || window.location.hash !== expectedHash
                || hasOpenReaderModal()
              ) {
                stopVisibility();
                return;
              }
              const bounds = target.getBoundingClientRect();
              const intersectsViewport = bounds.bottom > 0
                && bounds.right > 0
                && bounds.top < window.innerHeight
                && bounds.left < window.innerWidth;
              if (!intersectsViewport) {
                target.scrollIntoView({ behavior: "auto", block: "start" });
              }
              if (window.performance.now() >= visibilityDeadline) {
                stopVisibility();
                return;
              }
              keepFocusedTargetVisible();
            });
          };
          keepFocusedTargetVisible();
        } finally {
          options.onSettled?.();
        }
      });
    };
    scheduleFrame();
  }, []);

  const scheduleDeferredReaderFragmentFocus = useCallback((
    targetId: string,
    options: Readonly<{
      expectedHash?: string;
      fallbackToMain?: boolean;
      onSettled?: () => void;
      preserveNewerFocus?: boolean;
    }> = {},
  ) => {
    const expectedArticleId = articleIdRef.current;
    const expectedGeneration = articleGenerationRef.current;
    const expectedRouteQuery = normalizeReaderRouteQuery(window.location.search);
    const expectedHash = options.expectedHash ?? `#${targetId}`;
    const expectedReferencePage = parseReaderReferencePage(expectedRouteQuery);
    const expectedInteractionVersion = readerFocusClaimInteractionVersionRef.current;
    const main = document.getElementById("main-content");
    const initialActiveElement = document.activeElement;
    let active = true;
    let frame = 0;
    let timeout = 0;
    const observer = new MutationObserver(() => tryFocusTarget());

    deferredFragmentFocusCleanupRef.current?.();
    fragmentVisibilityCleanupRef.current?.();
    if (fragmentFocusFrameRef.current) {
      window.cancelAnimationFrame(fragmentFocusFrameRef.current);
      fragmentFocusFrameRef.current = 0;
    }

    const cleanup = () => {
      if (!active) {
        return;
      }
      active = false;
      observer.disconnect();
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timeout);
      window.removeEventListener("keydown", cancel, true);
      window.removeEventListener("pointerdown", cancel, true);
      window.removeEventListener("touchstart", cancel, true);
      window.removeEventListener("wheel", cancel, true);
      if (deferredFragmentFocusCleanupRef.current === cleanup) {
        deferredFragmentFocusCleanupRef.current = null;
      }
    };
    const settle = (useMainFallback = false) => {
      if (
        useMainFallback
        && options.fallbackToMain
        && main?.isConnected
        && articleIdRef.current === expectedArticleId
        && articleGenerationRef.current === expectedGeneration
        && getCurrentReaderArticleId() === expectedArticleId
        && normalizeReaderRouteQuery(window.location.search) === expectedRouteQuery
        && window.location.hash === expectedHash
        && (
          expectedInteractionVersion === null
          || readerInteractionVersionRef.current === expectedInteractionVersion
        )
        && !hasOpenReaderModal()
      ) {
        const activeElement = document.activeElement;
        const focusCanTransfer = shouldTransferDeferredReaderFragmentFocus(
          !activeElement || activeElement === document.body,
          Boolean(activeElement?.isConnected),
          activeElement === main,
          false,
          activeElement === initialActiveElement,
        );
        if (focusCanTransfer) {
          main.focus({ preventScroll: true });
        }
      }
      cleanup();
      options.onSettled?.();
    };
    const cancel = () => settle(false);
    function tryFocusTarget() {
      if (!active) {
        return;
      }
      if (
        articleIdRef.current !== expectedArticleId
        || articleGenerationRef.current !== expectedGeneration
        || getCurrentReaderArticleId() !== expectedArticleId
        || normalizeReaderRouteQuery(window.location.search) !== expectedRouteQuery
        || window.location.hash !== expectedHash
        || (
          expectedInteractionVersion !== null
          && readerInteractionVersionRef.current !== expectedInteractionVersion
        )
        || hasOpenReaderModal()
      ) {
        cancel();
        return;
      }
      const referencePanel = targetId.startsWith("structured-reference-")
        ? main?.querySelector<HTMLElement>("[data-structured-references-state]") ?? null
        : null;
      if (
        referencePanel
        && (
          referencePanel.dataset.structuredReferencesArticleId !== expectedArticleId
          || referencePanel.dataset.structuredReferencesPage !== String(expectedReferencePage)
        )
      ) {
        return;
      }
      const target = document.getElementById(targetId);
      if (!(target instanceof HTMLElement)) {
        if (referencePanel) {
          const referenceState = referencePanel.dataset.structuredReferencesState;
          if (referenceState === "ready" || referenceState === "empty" || referenceState === "error") {
            settle(true);
          }
        }
        return;
      }
      if (options.preserveNewerFocus) {
        const activeElement = document.activeElement;
        const focusCanTransfer = shouldTransferDeferredReaderFragmentFocus(
          !activeElement || activeElement === document.body,
          Boolean(activeElement?.isConnected),
          activeElement === main,
          activeElement === target,
          activeElement === initialActiveElement,
        );
        if (!focusCanTransfer) {
          cancel();
          return;
        }
      }
      target.scrollIntoView({ behavior: "auto", block: "nearest", inline: "nearest" });
      target.focus({ preventScroll: true });
      cancel();
    }

    deferredFragmentFocusCleanupRef.current = cleanup;
    window.addEventListener("keydown", cancel, true);
    window.addEventListener("pointerdown", cancel, true);
    window.addEventListener("touchstart", cancel, { capture: true, passive: true });
    window.addEventListener("wheel", cancel, { capture: true, passive: true });
    if (main) {
      observer.observe(main, { childList: true, subtree: true });
    }
    frame = window.requestAnimationFrame(tryFocusTarget);
    timeout = window.setTimeout(() => settle(true), DEFERRED_FRAGMENT_FOCUS_TIMEOUT_MS);
  }, []);

  function handleReaderFragmentNavigate(
    event: ReactMouseEvent<HTMLAnchorElement>,
    targetId: ReaderFragmentTargetId,
  ) {
    if (!isSameTabNavigation(event)) {
      return;
    }
    fragmentHistoryIntentRef.current = null;
    deferredFragmentFocusCleanupRef.current?.();
    fragmentVisibilityCleanupRef.current?.();
    claimReaderRouteFocus("none");
    scheduleReaderFragmentFocus(targetId, {
      interactionVersion: readerInteractionVersionRef.current,
    });
  }

  useEffect(() => {
    function restoreReaderFragmentFocus(afterRouteCommit: boolean) {
      const intent = fragmentHistoryIntentRef.current;
      if (
        !intent
        || article?.id !== articleId
        || intent.articleId !== articleId
        || intent.routeQuery !== normalizeReaderRouteQuery(routeQuery)
        || intent.expectedHash !== window.location.hash
      ) {
        return;
      }
      if (hasOpenReaderModal()) {
        if (fragmentHistoryIntentRef.current === intent) {
          fragmentHistoryIntentRef.current = null;
        }
        setReaderRouteFocusIntent((current) => {
          if (current !== "history") {
            return current;
          }
          readerFocusClaimInteractionVersionRef.current = null;
          return "none";
        });
        return;
      }
      const focusOptions = {
        expectedHash: intent.expectedHash,
        onSettled: () => {
          if (fragmentHistoryIntentRef.current === intent) {
            fragmentHistoryIntentRef.current = null;
          }
          setReaderRouteFocusIntent((current) => {
            if (current !== "history") {
              return current;
            }
            readerFocusClaimInteractionVersionRef.current = null;
            return "none";
          });
        },
        preserveNewerFocus: afterRouteCommit,
      };
      if (intent.targetId.startsWith("structured-reference-")) {
        scheduleDeferredReaderFragmentFocus(intent.targetId, {
          ...focusOptions,
          fallbackToMain: true,
        });
      } else {
        scheduleReaderFragmentFocus(intent.targetId, {
          ...focusOptions,
          frameCount: afterRouteCommit ? 4 : 1,
          requireArticleHeading: intent.targetKind === "heading",
        });
      }
    }

    function captureReaderFragmentFocus(afterRouteCommit: boolean) {
      if (
        getCurrentReaderArticleId() !== articleId
        || normalizeReaderRouteQuery(window.location.search)
          !== normalizeReaderRouteQuery(routeQuery)
      ) {
        return;
      }
      const historyNavigation = consumeShellHistoryNavigation(
        window.location.pathname,
        window.location.search,
        window.location.hash,
      );
      if (!historyNavigation) {
        return;
      }
      const destination = getReaderFragmentHistoryIntent(
        !isGuidedReaderRoute,
        !isGuidedReaderRoute || !afterRouteCommit,
      );
      fragmentHistoryIntentRef.current = destination;
      if (destination) {
        claimReaderRouteFocus("history");
      } else {
        claimReaderRouteFocus(
          isGuidedReaderRoute && shouldUseGuidedReaderRouteFocus(window.location.hash)
            ? "history-guided"
            : "none",
        );
      }
      restoreReaderFragmentFocus(afterRouteCommit);
    }

    const handleShellHistoryNavigation = () => captureReaderFragmentFocus(false);
    window.addEventListener(SHELL_HISTORY_NAVIGATION_EVENT, handleShellHistoryNavigation);
    captureReaderFragmentFocus(true);
    restoreReaderFragmentFocus(true);

    return () => {
      window.removeEventListener(SHELL_HISTORY_NAVIGATION_EVENT, handleShellHistoryNavigation);
      if (fragmentFocusFrameRef.current) {
        window.cancelAnimationFrame(fragmentFocusFrameRef.current);
      }
      fragmentVisibilityCleanupRef.current?.();
    };
  }, [
    article?.id,
    articleId,
    claimReaderRouteFocus,
    isGuidedReaderRoute,
    routeQuery,
    scheduleDeferredReaderFragmentFocus,
    scheduleReaderFragmentFocus,
  ]);

  useEffect(() => {
    const generation = articleGenerationRef.current + 1;
    articleGenerationRef.current = generation;
    setArticle(null);
    setError(null);
    setHistoryError(null);
    setActiveSectionId(null);
    setReadingProgress(0);
    setLearningState(null);
    setIsBookmarked(false);
    setNotes([]);
    setNoteDraft("");
    setEditingNoteId(null);
    setEditingContent("");
    setActiveSession(null);
    setLearningError(null);
    setStudySessionPosition(null);
    setStudySessionWarning(null);
    setStudySessionEligible(false);
    setCompletionRegionMounted(false);
    setCompletionPrepared(false);
    setCompletionPending(null);
    setCompletionMessage(null);
    setCompletionError(null);
    setCompletionTerminal(false);
    setTimerWarning(null);
    setSessionLoadState("idle");
    setLearningMutationPending(false);
    setSessionEndPending(false);
    setBookmarkMutationPending(false);
    setBookmarkFeedback(null);
    setNoteMutationPending(null);
    setNoteFeedback(null);
    setNoteDeleteIntent(null);
    setNoteDeleteReconciliationRequired(null);
    setReaderFocusRequest(null);
    setBookmarkLoadState("idle");
    setNoteLoadState("idle");
    completionOperationRef.current = null;
    learningMutationRef.current = null;
    sessionEndOperationRef.current = null;
    bookmarkMutationRef.current = null;
    noteMutationRef.current = null;
    learningLoadArticleRef.current = null;
    explicitSectionRef.current = null;
    setHistory(loadReadingHistory());
    const requestedArticleId = articleId;
    const controller = new AbortController();
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      if (
        articleIdRef.current === requestedArticleId
        && articleGenerationRef.current === generation
      ) {
        articleGenerationRef.current = generation + 1;
        setError("Article loading timed out. Try again.");
      }
      controller.abort();
    }, ARTICLE_LOAD_TIMEOUT_MS);
    fetchArticle(requestedArticleId, { signal: controller.signal })
      .then((loadedArticle) => {
        window.clearTimeout(timeout);
        if (
          articleIdRef.current !== requestedArticleId
          || articleGenerationRef.current !== generation
        ) {
          return;
        }
        setArticle(loadedArticle);
        try {
          setHistory(recordReading(loadedArticle));
        } catch {
          setHistory(loadReadingHistory());
          setHistoryError("Reading history is unavailable in this browser session.");
        }
        void loadLearningContext(loadedArticle.id, generation);
      })
      .catch((err) => {
        window.clearTimeout(timeout);
        if (
          articleIdRef.current === requestedArticleId
          && articleGenerationRef.current === generation
        ) {
          setError(
            timedOut
              ? "Article loading timed out. Try again."
              : err instanceof Error
                ? err.message
                : "Failed to load article",
          );
        }
      });
    return () => {
      window.clearTimeout(timeout);
      if (articleGenerationRef.current === generation) {
        articleGenerationRef.current = generation + 1;
      }
      completionOperationRef.current = null;
      learningMutationRef.current = null;
      sessionEndOperationRef.current = null;
      bookmarkMutationRef.current = null;
      noteMutationRef.current = null;
      noteDeleteCancelRef.current = null;
      noteDeleteConfirmationRef.current = null;
      if (learningLoadArticleRef.current === requestedArticleId) {
        learningLoadArticleRef.current = null;
      }
      controller.abort();
    };
  }, [articleId, articleRevision]);

  useEffect(() => {
    setReaderPreferences(loadReaderPreferences());
  }, []);

  useEffect(() => {
    if (!error || !ownsRouteFocus) {
      return;
    }
    const ownedFocusIntent = readerRouteFocusIntent;
    const expectedArticleId = articleIdRef.current;
    const expectedGeneration = articleGenerationRef.current;
    const expectedRouteIdentity = createShellRouteIdentity(
      window.location.pathname,
      window.location.search,
    );
    const expectedInteractionVersion = readerFocusClaimInteractionVersionRef.current;
    const clearOwnedFocusIntent = () => {
      setReaderRouteFocusIntent((current) => {
        if (current !== ownedFocusIntent) {
          return current;
        }
        readerFocusClaimInteractionVersionRef.current = null;
        return "none";
      });
    };
    const frame = window.requestAnimationFrame(() => {
      if (
        articleIdRef.current !== expectedArticleId
        || articleGenerationRef.current !== expectedGeneration
        || createShellRouteIdentity(window.location.pathname, window.location.search)
          !== expectedRouteIdentity
        || expectedInteractionVersion === null
        || readerInteractionVersionRef.current !== expectedInteractionVersion
        || hasOpenReaderModal()
      ) {
        clearOwnedFocusIntent();
        return;
      }
      const activeElement = document.activeElement;
      const main = document.getElementById("main-content");
      const retry = articleRetryRef.current;
      const focusCanTransfer = !activeElement
        || activeElement === document.body
        || !activeElement.isConnected
        || activeElement === main
        || activeElement === retry;
      if (focusCanTransfer) {
        retry?.scrollIntoView({ behavior: "auto", block: "nearest" });
        retry?.focus({ preventScroll: true });
      }
      clearOwnedFocusIntent();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [error, ownsRouteFocus, readerRouteFocusIntent]);

  useEffect(() => {
    if (listReturnTo !== "/session") {
      setStudySessionPosition(null);
      setStudySessionWarning(null);
      setStudySessionEligible(false);
      setCompletionRegionMounted(false);
      return;
    }

    const snapshot = loadStudySession();
    if (!snapshot.storageAvailable) {
      setStudySessionPosition(null);
      setStudySessionWarning("The focused session could not be recovered from browser-local storage.");
      setStudySessionEligible(false);
      return;
    }
    const currentPosition = getStudySessionPosition(snapshot.state, articleId);
    if (!currentPosition) {
      setStudySessionPosition(null);
      setStudySessionWarning("This Article is no longer present in the focused session queue.");
      setStudySessionEligible(false);
      return;
    }

    const isActive = snapshot.state.activeArticleId === articleId;
    setStudySessionPosition(currentPosition);
    setStudySessionEligible(isActive);
    setCompletionRegionMounted(isActive);
    setStudySessionWarning(
      isActive
        ? null
        : "Review-only view. Set this Article as current in Focused Session to use completion actions.",
    );
  }, [articleId, listReturnTo]);

  useEffect(() => {
    if (!article?.id) {
      return;
    }
    if (listReturnTo.startsWith("/graph")) {
      if (hasGraphDetailFocusTarget(listReturnTo)) {
        recordShellDestinationFocusIntent(listReturnTo, window.location.href);
      }
      rememberGraphArticleReturnFocus(
        getGraphSessionStorage(window),
        listReturnTo,
        article.id,
      );
    }
    if (
      readerRouteFocusIntent === "none"
      || readerRouteFocusIntent === "history"
      || (readerRouteFocusIntent === "guided" && !isGuidedReaderRoute)
    ) {
      return;
    }
    const ownedFocusIntent = readerRouteFocusIntent;
    const expectedInteractionVersion = readerFocusClaimInteractionVersionRef.current;
    const clearOwnedFocusIntent = () => {
      setReaderRouteFocusIntent((current) => {
        if (current !== ownedFocusIntent) {
          return current;
        }
        readerFocusClaimInteractionVersionRef.current = null;
        return "none";
      });
    };
    if (hasOpenReaderModal()) {
      clearOwnedFocusIntent();
      return;
    }
    const fragmentTargetId = getReaderFragmentTargetId(window.location.hash);
    if (fragmentTargetId) {
      scheduleReaderFragmentFocus(fragmentTargetId, {
        frameCount: 3,
        onSettled: clearOwnedFocusIntent,
        preserveNewerFocus: true,
      });
      return;
    }
    const delegatedHashTargetId = decodeHash(window.location.hash);
    if (delegatedHashTargetId?.startsWith("structured-reference-")) {
      scheduleDeferredReaderFragmentFocus(delegatedHashTargetId, {
        fallbackToMain: true,
        onSettled: clearOwnedFocusIntent,
        preserveNewerFocus: true,
      });
      return deferredFragmentFocusCleanupRef.current ?? undefined;
    }
    if (delegatedHashTargetId && readerRouteFocusIntent === "route") {
      scheduleReaderFragmentFocus(delegatedHashTargetId, {
        expectedHash: window.location.hash,
        frameCount: 3,
        onSettled: clearOwnedFocusIntent,
        preserveNewerFocus: true,
        requireArticleHeading: true,
      });
      return;
    }
    const expectedHash = window.location.hash;
    const expectedHashTargetId = decodeHash(expectedHash);
    const waitsForNativeHashFocus = readerRouteFocusIntent === "history-guided"
      && expectedHashTargetId !== null;
    let focusFrame = 0;
    let remainingFrames = waitsForNativeHashFocus ? 16 : 2;
    let settled = false;
    const cleanup = () => {
      window.cancelAnimationFrame(focusFrame);
      document.removeEventListener("focusin", handleNativeHashFocus, true);
    };
    const settleRouteFocus = () => {
      if (settled) {
        return;
      }
      settled = true;
      try {
        const activeElement = document.activeElement;
        const main = document.getElementById("main-content");
        const savedRoutePosition = readerRouteFocusIntent === "route"
          && expectedHash === ""
          ? loadReaderProgress(article.id)
          : null;
        const savedRouteTarget = savedRoutePosition?.section_id
          ? document.getElementById(savedRoutePosition.section_id)
          : null;
        const routeFocusTarget = savedRouteTarget instanceof HTMLElement
          && /^H[1-6]$/.test(savedRouteTarget.tagName)
          && articleRootRef.current?.contains(savedRouteTarget)
          ? savedRouteTarget
          : articleHeadingRef.current;
        if (
          articleIdRef.current === article.id
          && window.location.hash === expectedHash
          && expectedInteractionVersion !== null
          && readerInteractionVersionRef.current === expectedInteractionVersion
          && !hasOpenReaderModal()
          && (
            !activeElement
            || activeElement === document.body
            || !activeElement.isConnected
            || activeElement === main
            || activeElement === routeFocusTarget
            || (
              readerRouteFocusIntent === "history-guided"
              && activeElement instanceof HTMLElement
              && (
                getReaderFragmentTargetId(`#${activeElement.id}`) !== null
                || expectedHashTargetId === activeElement.id
              )
            )
          )
        ) {
          routeFocusTarget?.scrollIntoView({ behavior: "auto", block: "start" });
          routeFocusTarget?.focus({ preventScroll: true });
        }
      } finally {
        cleanup();
        clearOwnedFocusIntent();
      }
    };
    const scheduleRouteFocus = () => {
      focusFrame = window.requestAnimationFrame(() => {
        remainingFrames -= 1;
        if (remainingFrames > 0) {
          scheduleRouteFocus();
          return;
        }
        settleRouteFocus();
      });
    };
    function handleNativeHashFocus(event: FocusEvent) {
      if (
        !waitsForNativeHashFocus
        || !(event.target instanceof HTMLElement)
        || event.target.id !== expectedHashTargetId
        || !articleRootRef.current?.contains(event.target)
      ) {
        return;
      }
      window.cancelAnimationFrame(focusFrame);
      remainingFrames = 1;
      scheduleRouteFocus();
    }
    if (waitsForNativeHashFocus) {
      document.addEventListener("focusin", handleNativeHashFocus, true);
    }
    scheduleRouteFocus();
    return () => {
      settled = true;
      cleanup();
    };
  }, [
    article?.id,
    isGuidedReaderRoute,
    listReturnTo,
    readerRouteFocusIntent,
    scheduleDeferredReaderFragmentFocus,
    scheduleReaderFragmentFocus,
  ]);

  async function loadLearningContext(nextArticleId: string, generation: number) {
    if (
      learningLoadArticleRef.current === nextArticleId
      && articleGenerationRef.current === generation
    ) {
      return;
    }
    learningLoadArticleRef.current = nextArticleId;
    setLearningError(null);
    setSessionLoadState("loading");
    setBookmarkLoadState("loading");
    setNoteLoadState("loading");
    const [stateResult, bookmarkResult, noteResult] = await Promise.allSettled([
      fetchLearningState(nextArticleId),
      fetchBookmarks(),
      fetchNotes(nextArticleId),
    ]);
    if (
      learningLoadArticleRef.current !== nextArticleId
      || articleGenerationRef.current !== generation
    ) {
      return;
    }
    const errors: string[] = [];
    if (stateResult.status === "fulfilled") {
      setLearningState(stateResult.value);
    } else {
      errors.push(errorText(stateResult.reason, "Failed to load learning state"));
    }
    if (bookmarkResult.status === "fulfilled") {
      setIsBookmarked(bookmarkResult.value.items.some((bookmark) => bookmark.article_id === nextArticleId));
      setBookmarkLoadState("loaded");
    } else {
      setBookmarkLoadState("error");
      setBookmarkFeedback({
        tone: "error",
        message: "Bookmark status is unavailable. Reload this Article before changing it.",
      });
      errors.push(errorText(bookmarkResult.reason, "Failed to load bookmarks"));
    }
    if (noteResult.status === "fulfilled") {
      setNotes(noteResult.value.items);
      setNoteLoadState("loaded");
    } else {
      setNoteLoadState("error");
      setNoteFeedback({
        tone: "error",
        message: "Notes are unavailable. Reload this Article before changing them.",
      });
      errors.push(errorText(noteResult.reason, "Failed to load notes"));
    }
    try {
      const session = await createSession(nextArticleId, "reader");
      if (
        learningLoadArticleRef.current !== nextArticleId
        || articleGenerationRef.current !== generation
      ) {
        try {
          await endSession(session.session_id);
        } catch {
          // The stale Reader no longer owns a surface where cleanup failure can be reported.
        }
        return;
      }
      setActiveSession(session);
      setSessionLoadState("loaded");
    } catch (sessionError) {
      if (
        learningLoadArticleRef.current !== nextArticleId
        || articleGenerationRef.current !== generation
      ) {
        return;
      }
      setActiveSession(null);
      setSessionLoadState("error");
      errors.push(errorText(sessionError, "Reader timer could not be started"));
    }
    if (
      learningLoadArticleRef.current === nextArticleId
      && articleGenerationRef.current === generation
    ) {
      setLearningError(errors.length ? errors.join(" · ") : null);
    }
  }

  async function handleStatusChange(nextStatus: LearningStatus, origin: HTMLButtonElement) {
    if (
      !article
      || completionOperationRef.current
      || learningMutationRef.current
      || learningState?.status === nextStatus
    ) {
      return;
    }
    const operation: ArticleOperation = {
      articleId: article.id,
      generation: articleGenerationRef.current,
    };
    const interactionVersion = readerInteractionVersionRef.current;
    learningMutationRef.current = operation;
    setLearningMutationPending(true);
    setLearningError(null);
    try {
      let updatedState: LearningState;
      try {
        updatedState = await updateLearningState(operation.articleId, nextStatus);
      } catch (writeError) {
        if (!isCurrentOperation(learningMutationRef, operation)) {
          return;
        }
        const readback = await fetchLearningState(operation.articleId);
        if (readback.status !== nextStatus) {
          throw writeError;
        }
        updatedState = readback;
      }
      if (isCurrentOperation(learningMutationRef, operation)) {
        setLearningState(updatedState);
        if (updatedState.status !== "completed") {
          setCompletionPrepared(false);
          setCompletionTerminal(false);
          setCompletionMessage(null);
          setCompletionError(null);
        }
      }
    } catch (err) {
      if (isCurrentOperation(learningMutationRef, operation)) {
        setLearningError(err instanceof Error ? err.message : "Failed to update learning state");
      }
    } finally {
      if (isCurrentOperation(learningMutationRef, operation)) {
        queueOwnedReaderFocus(operation, "learning-state", origin, interactionVersion);
        learningMutationRef.current = null;
        setLearningMutationPending(false);
      }
    }
  }

  async function handleBookmarkToggle(origin: HTMLButtonElement) {
    if (
      !article
      || article.id !== articleIdRef.current
      || !bookmarkControlsReady
      || bookmarkMutationRef.current
    ) {
      return;
    }
    const operation = nextReaderMutation(
      article.id,
      isBookmarked ? "bookmark-remove" : "bookmark-add",
    );
    const interactionVersion = readerInteractionVersionRef.current;
    bookmarkMutationRef.current = operation;
    setBookmarkMutationPending(true);
    setBookmarkFeedback({
      tone: "pending",
      message: isBookmarked ? "Removing bookmark..." : "Saving bookmark...",
    });
    try {
      if (operation.kind === "bookmark-remove") {
        await deleteBookmark(operation.articleId);
      } else {
        await addBookmark(operation.articleId);
      }
      if (!isCurrentReaderMutation(bookmarkMutationRef, operation)) {
        return;
      }
      const bookmarked = operation.kind === "bookmark-add";
      setIsBookmarked(bookmarked);
      setBookmarkFeedback({
        tone: "success",
        message: bookmarked ? "Bookmark saved." : "Bookmark removed.",
      });
    } catch (err) {
      if (isCurrentReaderMutation(bookmarkMutationRef, operation)) {
        setBookmarkFeedback({
          tone: "error",
          message: `The bookmark update could not be confirmed. ${errorText(err, "The request failed.")} The displayed bookmark state was kept; reload this Article before retrying if the result is uncertain.`,
        });
      }
    } finally {
      if (bookmarkMutationRef.current === operation) {
        bookmarkMutationRef.current = null;
        if (
          articleIdRef.current === operation.articleId
          && articleGenerationRef.current === operation.generation
        ) {
          queueOwnedReaderFocus(operation, "bookmark", origin, interactionVersion);
          setBookmarkMutationPending(false);
        }
      }
    }
  }

  async function handleCreateNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const origin = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const interactionVersion = readerInteractionVersionRef.current;
    const submittedDraft = noteDraft.trim();
    if (
      !article
      || article.id !== articleIdRef.current
      || !noteControlsReady
      || !submittedDraft
      || noteMutationRef.current
      || noteInteractionLocked
    ) {
      return;
    }
    const operation = nextReaderMutation(article.id, "note-create");
    noteMutationRef.current = operation;
    setNoteMutationPending(operation);
    setNoteFeedback({ tone: "pending", message: "Saving note..." });
    try {
      const note = await createNote(operation.articleId, submittedDraft);
      if (!isCurrentReaderMutation(noteMutationRef, operation)) {
        return;
      }
      if (note.article_id !== operation.articleId) {
        throw new Error("The note response did not belong to this Article.");
      }
      setNotes((current) => mergeCreatedLearningNote(current, note, operation.articleId));
      setNoteDraft((current) => (current.trim() === submittedDraft ? "" : current));
      setNoteFeedback({ tone: "success", message: "Note saved." });
    } catch (err) {
      if (isCurrentReaderMutation(noteMutationRef, operation)) {
        setNoteFeedback({
          tone: "error",
          message: `The note could not be confirmed. ${errorText(err, "The request failed.")} Your draft was kept; reload this Article before retrying if the result is uncertain.`,
        });
      }
    } finally {
      if (noteMutationRef.current === operation) {
        noteMutationRef.current = null;
        if (
          articleIdRef.current === operation.articleId
          && articleGenerationRef.current === operation.generation
        ) {
          queueOwnedReaderFocus(operation, "note-feedback", origin, interactionVersion);
          setNoteMutationPending(null);
        }
      }
    }
  }

  async function handleUpdateNote(noteId: string, origin: HTMLButtonElement) {
    const submittedContent = editingContent.trim();
    const interactionVersion = readerInteractionVersionRef.current;
    if (
      !article
      || article.id !== articleIdRef.current
      || !noteControlsReady
      || !submittedContent
      || noteMutationRef.current
      || noteInteractionLocked
    ) {
      return;
    }
    const operation = nextReaderMutation(article.id, "note-update", noteId);
    noteMutationRef.current = operation;
    setNoteMutationPending(operation);
    setNoteFeedback({ tone: "pending", message: "Updating note..." });
    try {
      const updated = await updateNote(noteId, submittedContent);
      if (!isCurrentReaderMutation(noteMutationRef, operation)) {
        return;
      }
      if (updated.note_id !== noteId || updated.article_id !== operation.articleId) {
        throw new Error("The note response did not match this Article and note.");
      }
      setNotes((current) => mergeUpdatedLearningNote(current, updated, operation.articleId));
      setEditingNoteId(null);
      setEditingContent("");
      setNoteFeedback({ tone: "success", message: "Note updated." });
    } catch (err) {
      if (isCurrentReaderMutation(noteMutationRef, operation)) {
        setNoteFeedback({
          tone: "error",
          message: `The note update could not be confirmed. ${errorText(err, "The request failed.")} The current note was kept.`,
        });
      }
    } finally {
      if (noteMutationRef.current === operation) {
        noteMutationRef.current = null;
        if (
          articleIdRef.current === operation.articleId
          && articleGenerationRef.current === operation.generation
        ) {
          queueOwnedReaderFocus(
            operation,
            "note-feedback",
            origin,
            interactionVersion,
            noteId,
          );
          setNoteMutationPending(null);
        }
      }
    }
  }

  function queueNoteFocus(
    intent: ReaderNoteDeleteIntent,
    target: "delete-trigger" | "note-feedback",
  ) {
    setReaderFocusRequest({
      articleId: intent.articleId,
      generation: intent.generation,
      interactionVersion: null,
      noteId: intent.noteId,
      target,
    });
  }

  function queueOwnedReaderFocus(
    operation: ArticleOperation,
    target: ReaderFocusRequest["target"],
    origin: HTMLElement | null,
    interactionVersion: number,
    noteId?: string,
  ) {
    setReaderFocusRequest({
      articleId: operation.articleId,
      generation: operation.generation,
      interactionVersion,
      noteId,
      origin,
      target,
    });
  }

  function beginEditingNote(note: LearningNote, origin: HTMLButtonElement) {
    if (!article || article.id !== articleIdRef.current) {
      return;
    }
    const operation = {
      articleId: article.id,
      generation: articleGenerationRef.current,
    };
    const interactionVersion = readerInteractionVersionRef.current;
    setEditingNoteId(note.note_id);
    setEditingContent(note.content);
    queueOwnedReaderFocus(operation, "note-editor", origin, interactionVersion, note.note_id);
  }

  function cancelEditingNote(noteId: string, origin: HTMLButtonElement) {
    if (!article || article.id !== articleIdRef.current) {
      return;
    }
    const operation = {
      articleId: article.id,
      generation: articleGenerationRef.current,
    };
    const interactionVersion = readerInteractionVersionRef.current;
    setEditingNoteId(null);
    setEditingContent("");
    queueOwnedReaderFocus(operation, "edit-trigger", origin, interactionVersion, noteId);
  }

  function handleRequestNoteDelete(noteId: string) {
    if (
      !article
      || article.id !== articleIdRef.current
      || !noteControlsReady
      || noteMutationRef.current
      || noteInteractionLocked
      || !notes.some((note) => note.note_id === noteId)
    ) {
      return;
    }
    focusVisibleElement(noteStatusRef.current);
    setNoteFeedback(null);
    setNoteDeleteIntent(
      createReaderNoteDeleteIntent(
        article.id,
        articleGenerationRef.current,
        noteId,
      ),
    );
  }

  function handleCancelNoteDelete(intent: ReaderNoteDeleteIntent) {
    if (
      noteMutationRef.current
      || !ownsReaderNoteDeleteIntent(
        noteDeleteIntent,
        intent,
        articleIdRef.current,
        articleGenerationRef.current,
      )
    ) {
      return;
    }
    focusVisibleElement(noteStatusRef.current);
    setNoteDeleteIntent(null);
    queueNoteFocus(intent, "delete-trigger");
  }

  function handleNoteDeleteConfirmationKeyDown(
    event: ReactKeyboardEvent<HTMLDivElement>,
    intent: ReaderNoteDeleteIntent,
  ) {
    if (event.key !== "Escape") {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    handleCancelNoteDelete(intent);
  }

  async function handleDeleteNote(intent: ReaderNoteDeleteIntent, origin: HTMLButtonElement) {
    if (
      !article
      || article.id !== articleIdRef.current
      || !noteControlsReady
      || noteMutationRef.current
      || !ownsReaderNoteDeleteIntent(
        noteDeleteIntent,
        intent,
        articleIdRef.current,
        articleGenerationRef.current,
      )
      || !notes.some((note) => note.note_id === intent.noteId)
    ) {
      return;
    }
    const focusOrigin = noteDeleteConfirmationRef.current ?? origin;
    const interactionVersion = readerInteractionVersionRef.current;
    focusVisibleElement(focusOrigin);
    const operation = nextReaderMutation(article.id, "note-delete", intent.noteId);
    noteMutationRef.current = operation;
    setNoteMutationPending(operation);
    setNoteFeedback({ tone: "pending", message: "Deleting note..." });
    try {
      await deleteNote(intent.noteId);
      if (!isCurrentReaderMutation(noteMutationRef, operation)) {
        return;
      }
      setNotes((current) => removeLearningNote(current, intent.noteId));
      if (editingNoteId === intent.noteId) {
        setEditingNoteId(null);
        setEditingContent("");
      }
      setNoteDeleteIntent(null);
      setNoteFeedback({ tone: "success", message: "Note deleted." });
      queueOwnedReaderFocus(
        operation,
        "note-feedback",
        focusOrigin,
        interactionVersion,
        intent.noteId,
      );
    } catch (err) {
      if (isCurrentReaderMutation(noteMutationRef, operation)) {
        setNoteDeleteIntent(null);
        setNoteFeedback({
          tone: "error",
          message: `The note deletion could not be confirmed. ${errorText(err, "The request failed.")} The current Reader rendering was kept, but the saved result may differ. Reload this Article before retrying.`,
        });
        queueOwnedReaderFocus(
          operation,
          "delete-trigger",
          focusOrigin,
          interactionVersion,
          intent.noteId,
        );
      }
    } finally {
      if (noteMutationRef.current === operation) {
        noteMutationRef.current = null;
        if (
          articleIdRef.current === operation.articleId
          && articleGenerationRef.current === operation.generation
        ) {
          setNoteMutationPending(null);
        }
      }
    }
  }

  async function handleEndSession(origin: HTMLButtonElement) {
    if (
      !article
      || !activeSession
      || activeSession.ended_at
      || completionOperationRef.current
      || sessionEndOperationRef.current
    ) {
      return;
    }
    const operation: ArticleOperation = {
      articleId: article.id,
      generation: articleGenerationRef.current,
    };
    const interactionVersion = readerInteractionVersionRef.current;
    const sessionId = activeSession.session_id;
    sessionEndOperationRef.current = operation;
    setSessionEndPending(true);
    setLearningError(null);
    let warningRecorded = false;
    try {
      const sessions = await fetchLearningSessions();
      if (!isCurrentOperation(sessionEndOperationRef, operation)) {
        return;
      }
      const exactSession = sessions.items.find((item) => item.session_id === sessionId);
      if (!exactSession) {
        warningRecorded = true;
        setTimerWarning("unavailable");
        throw new Error("The exact Reader timer could not be found, so no end request was sent.");
      }
      if (exactSession.ended_at) {
        setActiveSession(exactSession);
        setTimerWarning(null);
        return;
      }
      try {
        const ended = await endSession(sessionId);
        if (isCurrentOperation(sessionEndOperationRef, operation)) {
          setActiveSession(ended);
          setTimerWarning(null);
        }
      } catch (endError) {
        let readback;
        try {
          readback = await fetchLearningSessions();
        } catch {
          if (isCurrentOperation(sessionEndOperationRef, operation)) {
            warningRecorded = true;
            setTimerWarning("unknown");
          }
          throw endError;
        }
        if (!isCurrentOperation(sessionEndOperationRef, operation)) {
          return;
        }
        const reconciled = readback.items.find((item) => item.session_id === sessionId);
        if (reconciled?.ended_at) {
          setActiveSession(reconciled);
          setTimerWarning(null);
          return;
        }
        if (reconciled) {
          setActiveSession(reconciled);
          warningRecorded = true;
          setTimerWarning("confirmed-open");
          throw new Error("The Reader timer is still open. Retry End session to try once more.");
        }
        warningRecorded = true;
        setTimerWarning("unavailable");
        throw endError;
      }
    } catch (err) {
      if (isCurrentOperation(sessionEndOperationRef, operation)) {
        if (!warningRecorded) {
          setTimerWarning("unknown");
        }
        setLearningError(err instanceof Error ? err.message : "Failed to end session");
      }
    } finally {
      if (isCurrentOperation(sessionEndOperationRef, operation)) {
        queueOwnedReaderFocus(operation, "session", origin, interactionVersion);
        sessionEndOperationRef.current = null;
        setSessionEndPending(false);
      }
    }
  }

  function focusCompletionRegion() {
    window.requestAnimationFrame(() => completionRegionRef.current?.focus({ preventScroll: true }));
  }

  function isCurrentOperation(
    operationRef: { current: ArticleOperation | null },
    operation: ArticleOperation,
  ) {
    return operationRef.current === operation
      && articleIdRef.current === operation.articleId
      && articleGenerationRef.current === operation.generation;
  }

  function nextReaderMutation(
    targetArticleId: string,
    kind: ReaderMutationKind,
    noteId: string | null = null,
  ): ReaderMutationOperation {
    mutationSequenceRef.current += 1;
    return createReaderMutationOperation(
      targetArticleId,
      articleGenerationRef.current,
      mutationSequenceRef.current,
      kind,
      noteId,
    );
  }

  function isCurrentReaderMutation(
    operationRef: { current: ReaderMutationOperation | null },
    operation: ReaderMutationOperation,
  ): boolean {
    return ownsReaderMutation(
      operationRef.current,
      operation,
      articleIdRef.current,
      articleGenerationRef.current,
    );
  }

  function loadEligibleSessionState(targetArticleId: string, focusOnFailure = true) {
    if (articleIdRef.current !== targetArticleId) {
      return null;
    }
    const snapshot = loadStudySession();
    const position = getStudySessionPosition(snapshot.state, targetArticleId);
    if (!snapshot.storageAvailable) {
      setStudySessionEligible(false);
      setCompletionError("Browser-local session storage is unavailable.");
      if (focusOnFailure) {
        focusCompletionRegion();
      }
      return null;
    }
    if (!position || snapshot.state.activeArticleId !== targetArticleId) {
      setStudySessionEligible(false);
      setCompletionError("This Article is no longer the active item in the focused session.");
      if (focusOnFailure) {
        focusCompletionRegion();
      }
      return null;
    }
    setStudySessionPosition(position);
    setStudySessionEligible(true);
    return snapshot.state;
  }

  async function endReaderTimerAfterCompletion(
    operation: ArticleOperation,
  ): Promise<"closed" | "warning" | "stale"> {
    if (!isCurrentOperation(completionOperationRef, operation)) {
      return "stale";
    }
    const session = activeSession;
    if (session?.ended_at) {
      setTimerWarning(null);
      return "closed";
    }
    if (!session || session.article_id !== operation.articleId || sessionLoadState !== "loaded") {
      setTimerWarning("unavailable");
      return "warning";
    }
    if (timerWarning) {
      try {
        const sessions = await fetchLearningSessions();
        if (!isCurrentOperation(completionOperationRef, operation)) {
          return "stale";
        }
        const readback = sessions.items.find((item) => item.session_id === session.session_id);
        if (readback?.ended_at) {
          setActiveSession(readback);
          setTimerWarning(null);
          return "closed";
        }
        if (readback) {
          setActiveSession(readback);
          setTimerWarning("confirmed-open");
        } else {
          setTimerWarning("unavailable");
        }
      } catch {
        if (isCurrentOperation(completionOperationRef, operation)) {
          setTimerWarning("unknown");
        }
      }
      return "warning";
    }
    try {
      const ended = await endSession(session.session_id);
      if (!isCurrentOperation(completionOperationRef, operation)) {
        return "stale";
      }
      setActiveSession(ended);
      setTimerWarning(null);
      return "closed";
    } catch {
      try {
        const sessions = await fetchLearningSessions();
        if (!isCurrentOperation(completionOperationRef, operation)) {
          return "stale";
        }
        const readback = sessions.items.find((item) => item.session_id === session.session_id);
        if (readback?.ended_at) {
          setActiveSession(readback);
          setTimerWarning(null);
        } else if (readback) {
          setActiveSession(readback);
          setTimerWarning("confirmed-open");
        } else {
          setTimerWarning("unavailable");
        }
      } catch {
        if (isCurrentOperation(completionOperationRef, operation)) {
          setTimerWarning("unknown");
        }
      }
      return "warning";
    }
  }

  async function handlePrepareCompletion(origin: HTMLButtonElement) {
    if (
      !article
      || completionOperationRef.current
      || learningMutationRef.current
      || sessionEndOperationRef.current
      || (sessionLoadState !== "loaded" && sessionLoadState !== "error")
    ) {
      return;
    }
    const operation: ArticleOperation = {
      articleId: article.id,
      generation: articleGenerationRef.current,
    };
    const interactionVersion = readerInteractionVersionRef.current;
    completionOperationRef.current = operation;
    if (!loadEligibleSessionState(operation.articleId)) {
      completionOperationRef.current = null;
      return;
    }
    setCompletionPending("complete");
    setCompletionError(null);
    setCompletionMessage("Checking canonical completion status...");
    setCompletionTerminal(false);

    try {
      let canonicalState = await fetchLearningState(operation.articleId);
      if (!isCurrentOperation(completionOperationRef, operation)) {
        return;
      }
      if (canonicalState.status !== "completed") {
        try {
          canonicalState = await updateLearningState(operation.articleId, "completed");
        } catch (writeError) {
          if (!isCurrentOperation(completionOperationRef, operation)) {
            return;
          }
          const readback = await fetchLearningState(operation.articleId);
          if (readback.status !== "completed") {
            throw writeError;
          }
          canonicalState = readback;
        }
      }
      if (!isCurrentOperation(completionOperationRef, operation)) {
        return;
      }
      setLearningState(canonicalState);
      setCompletionPrepared(true);
      setCompletionMessage("Article completion confirmed. Finishing this Reader timer...");
      const timerResult = await endReaderTimerAfterCompletion(operation);
      if (!isCurrentOperation(completionOperationRef, operation)) {
        return;
      }
      setCompletionMessage(
        timerResult === "closed"
          ? "Article completion is confirmed. You can now open the next unfinished Article."
          : "Article completion is confirmed. Resolve the Reader timer or use the warned continuation.",
      );
    } catch (completionFailure) {
      if (isCurrentOperation(completionOperationRef, operation)) {
        setCompletionPrepared(false);
        setCompletionMessage(null);
        setCompletionError(errorText(completionFailure, "Article completion could not be confirmed"));
      }
    } finally {
      if (isCurrentOperation(completionOperationRef, operation)) {
        completionOperationRef.current = null;
        setCompletionPending(null);
        queueOwnedReaderFocus(operation, "completion", origin, interactionVersion);
      }
    }
  }

  async function handleRetryTimer(origin: HTMLButtonElement) {
    if (
      !article
      || !activeSession
      || activeSession.ended_at
      || completionOperationRef.current
      || learningMutationRef.current
      || sessionEndOperationRef.current
    ) {
      setTimerWarning(activeSession?.ended_at ? null : "unavailable");
      focusCompletionRegion();
      return;
    }
    const operation: ArticleOperation = {
      articleId: article.id,
      generation: articleGenerationRef.current,
    };
    const interactionVersion = readerInteractionVersionRef.current;
    const sessionId = activeSession.session_id;
    completionOperationRef.current = operation;
    const previousWarning = timerWarning;
    setCompletionPending("timer");
    setCompletionError(null);
    setCompletionMessage("Checking the exact Reader timer...");
    try {
      const sessions = await fetchLearningSessions();
      if (!isCurrentOperation(completionOperationRef, operation)) {
        return;
      }
      const readback = sessions.items.find((item) => item.session_id === sessionId);
      if (!readback) {
        setTimerWarning("unavailable");
        setCompletionMessage("The exact Reader timer could not be found. Article completion remains confirmed.");
        return;
      }
      setActiveSession(readback);
      if (readback.ended_at) {
        setTimerWarning(null);
        setCompletionMessage("Reader timer end confirmed. You can open the next unfinished Article.");
        return;
      }
      if (previousWarning !== "confirmed-open") {
        setTimerWarning("confirmed-open");
        setCompletionMessage("The Reader timer is still open. Retry once to end this confirmed timer.");
        return;
      }

      try {
        const ended = await endSession(readback.session_id);
        if (!isCurrentOperation(completionOperationRef, operation)) {
          return;
        }
        setActiveSession(ended);
        setTimerWarning(null);
        setCompletionMessage("Reader timer end confirmed. You can open the next unfinished Article.");
      } catch {
        const finalReadback = await fetchLearningSessions();
        if (!isCurrentOperation(completionOperationRef, operation)) {
          return;
        }
        const finalSession = finalReadback.items.find((item) => item.session_id === readback.session_id);
        if (finalSession?.ended_at) {
          setActiveSession(finalSession);
          setTimerWarning(null);
          setCompletionMessage("Reader timer end confirmed. You can open the next unfinished Article.");
        } else {
          setTimerWarning(finalSession ? "confirmed-open" : "unavailable");
          setCompletionMessage("Article completion remains confirmed, but the Reader timer did not close.");
        }
      }
    } catch (timerFailure) {
      if (isCurrentOperation(completionOperationRef, operation)) {
        setTimerWarning("unknown");
        setCompletionMessage(null);
        setCompletionError(errorText(timerFailure, "Reader timer status could not be confirmed"));
      }
    } finally {
      if (isCurrentOperation(completionOperationRef, operation)) {
        completionOperationRef.current = null;
        setCompletionPending(null);
        queueOwnedReaderFocus(operation, "completion", origin, interactionVersion);
      }
    }
  }

  async function handleOpenNextUnfinished(
    origin: HTMLButtonElement,
    allowUnconfirmedTimer = false,
  ) {
    if (
      !article
      || completionOperationRef.current
      || learningMutationRef.current
      || sessionEndOperationRef.current
      || !completionPrepared
    ) {
      return;
    }
    if (timerWarning && !allowUnconfirmedTimer) {
      setCompletionError("Resolve the Reader timer or explicitly continue without timer confirmation.");
      focusCompletionRegion();
      return;
    }
    const operation: ArticleOperation = {
      articleId: article.id,
      generation: articleGenerationRef.current,
    };
    const interactionVersion = readerInteractionVersionRef.current;
    completionOperationRef.current = operation;
    if (!loadEligibleSessionState(operation.articleId)) {
      completionOperationRef.current = null;
      return;
    }

    setCompletionPending("advance");
    setCompletionError(null);
    setCompletionMessage("Refreshing completion status and finding the next unfinished Article...");
    let navigationStarted = false;
    try {
      const [currentState, stateResponse] = await Promise.all([
        fetchLearningState(operation.articleId),
        fetchLearningStates(),
      ]);
      if (!isCurrentOperation(completionOperationRef, operation)) {
        return;
      }
      setLearningState(currentState);
      const latestQueueState = loadEligibleSessionState(operation.articleId, false);
      if (!latestQueueState) {
        return;
      }
      const completion = createStudySessionCompletionSummary(
        latestQueueState,
        stateResponse.items,
        operation.articleId,
      );
      if (currentState.status !== "completed" || completion.current?.status !== "completed") {
        setCompletionPrepared(false);
        throw new Error("The current Article is not confirmed complete. Complete it before advancing.");
      }
      if (completion.isComplete || !completion.nextIncomplete) {
        setCompletionTerminal(true);
        setCompletionMessage("Focused Session complete. Every queued Article is confirmed complete.");
        return;
      }

      const nextState = activateStudySessionItem(
        latestQueueState,
        completion.nextIncomplete.articleId,
        new Date().toISOString(),
      );
      if (nextState === latestQueueState || !saveStudySession(nextState)) {
        throw new Error("The next Article could not be saved as current. Navigation was cancelled.");
      }
      setCompletionMessage(`Opening ${completion.nextIncomplete.title}...`);
      router.replace(createStudySessionReaderHref({ ...completion.nextIncomplete, sectionId: null }));
      navigationStarted = true;
    } catch (advanceFailure) {
      if (isCurrentOperation(completionOperationRef, operation)) {
        setCompletionMessage(null);
        setCompletionError(errorText(advanceFailure, "The next unfinished Article could not be opened"));
      }
    } finally {
      if (isCurrentOperation(completionOperationRef, operation) && !navigationStarted) {
        completionOperationRef.current = null;
        setCompletionPending(null);
        queueOwnedReaderFocus(operation, "completion", origin, interactionVersion);
      }
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
    let positionTrackingArmed = false;
    let positionDirty = false;
    let pendingPositionPersistence = false;
    let frame = 0;
    let restoreFrame = 0;
    let trackingArmFrame = 0;
    let trackingArmFollowupFrame = 0;
    let persistenceTimer: ReturnType<typeof setTimeout> | null = null;
    let pendingState = {
      article_id: currentArticleId,
      section_id: null as string | null,
      section_title: null as string | null,
      progress: 0,
      updated_at: new Date().toISOString(),
    };

    const persist = () => {
      if (!restored || !positionDirty) {
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
      positionDirty = false;
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
      const shouldPersistPosition = pendingPositionPersistence;
      pendingPositionPersistence = false;

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
      positionDirty = positionDirty || shouldPersistPosition;
      if (explicitSectionRef.current?.id === nextSection?.id) {
        explicitSectionRef.current = null;
      }
      if (shouldPersistPosition) {
        schedulePersist();
      }
    };

    const schedulePositionUpdate = (event: Event) => {
      if (!positionTrackingArmed) {
        return;
      }
      pendingPositionPersistence = pendingPositionPersistence || event.type === "scroll";
      if (!frame) {
        frame = window.requestAnimationFrame(updateReadingPosition);
      }
    };

    const restorePosition = () => {
      const saved = loadReaderProgress(currentArticleId);
      const hashSection = decodeHash(window.location.hash);
      const fragmentTargetId = getReaderFragmentTargetId(window.location.hash);
      const graphOrigin = listReturnTo.startsWith("/graph");
      const delegatedHashTarget = hashSection?.startsWith("structured-reference-") ?? false;
      const readerHeadingOwnsViewport = document.activeElement === articleHeadingRef.current
        && (
          window.location.hash === ""
          || (
            isGuidedReaderRoute
            && shouldUseGuidedReaderRouteFocus(window.location.hash)
          )
        );
      const targetSection = graphOrigin
        || fragmentTargetId
        || delegatedHashTarget
        || readerHeadingOwnsViewport
        ? null
        : hashSection && outline.some((item) => item.id === hashSection)
          ? hashSection
          : saved?.section_id;
      const target = fragmentTargetId
        ? document.getElementById(fragmentTargetId)
        : targetSection
          ? document.getElementById(targetSection)
          : null;
      if (target) {
        target.scrollIntoView({ behavior: "auto", block: "start" });
        if (targetSection) {
          setActiveSectionId(targetSection);
        }
      }
      if (saved) {
        pendingState = saved;
        if (!graphOrigin) {
          setReadingProgress(saved.progress);
        }
      }
      restored = true;
      if (!graphOrigin && readerHeadingOwnsViewport && saved) {
        positionTrackingArmed = true;
        return;
      }
      if (graphOrigin) {
        trackingArmFrame = window.requestAnimationFrame(() => {
          trackingArmFollowupFrame = window.requestAnimationFrame(() => {
            positionTrackingArmed = true;
          });
        });
        return;
      }
      positionTrackingArmed = true;
      pendingPositionPersistence = true;
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
      if (trackingArmFrame) {
        window.cancelAnimationFrame(trackingArmFrame);
      }
      if (trackingArmFollowupFrame) {
        window.cancelAnimationFrame(trackingArmFollowupFrame);
      }
      persist();
    };
  }, [article?.id, isGuidedReaderRoute, listReturnTo, outline]);

  function handleOutlineNavigate(sectionId: string) {
    const target = document.getElementById(sectionId);
    const section = outline.find((item) => item.id === sectionId);
    if (!target || !article || !section) {
      return;
    }
    const currentHistoryState = window.history.state;
    const nextHistoryState = currentHistoryState
      && typeof currentHistoryState === "object"
      && !Array.isArray(currentHistoryState)
      ? {
          ...currentHistoryState,
          [READER_MANAGED_HEADING_STATE_KEY]: {
            articleId: article.id,
            targetId: sectionId,
          },
        }
      : {
          [READER_MANAGED_HEADING_STATE_KEY]: {
            articleId: article.id,
            targetId: sectionId,
          },
        };
    window.history.replaceState(nextHistoryState, "", `#${encodeURIComponent(sectionId)}`);
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

  const completionContextReady = Boolean(article)
    && (sessionLoadState === "loaded" || sessionLoadState === "error");
  const focusedCompletionPanel = listReturnTo === "/session" && completionRegionMounted ? (
    <section
      ref={completionRegionRef}
      aria-labelledby="focused-completion-heading"
      className="mt-4 scroll-mt-24 border-l-4 border-sky-700 bg-sky-50 px-4 py-4 outline-none focus:ring-2 focus:ring-sky-700"
      data-state={
        error
          ? "unavailable"
          : !completionContextReady
            ? "preparing"
            : completionTerminal
              ? "complete"
              : completionPrepared
                ? "ready-to-advance"
                : "ready-to-complete"
      }
      data-testid="focused-session-completion"
      tabIndex={-1}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-sky-800">Focused Session</p>
          <h2 className="mt-1 text-base font-semibold text-sky-950" id="focused-completion-heading">
            Complete, then continue
          </h2>
        </div>
        <span className="text-xs font-semibold text-sky-900">
          {error
            ? "Article unavailable"
            : !completionContextReady
              ? "Preparing Reader state"
              : learningState?.status === "completed"
                ? "Canonical status: completed"
                : "Completion not yet confirmed"}
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <button
          className="min-h-11 rounded bg-sky-800 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-900 disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={
            !article
            || !studySessionEligible
            || !completionContextReady
            || completionPrepared
            || completionPending !== null
            || learningMutationPending
            || sessionEndPending
          }
          type="button"
          onClick={(event) => void handlePrepareCompletion(event.currentTarget)}
        >
          {completionPending === "complete"
            ? "Confirming completion..."
            : completionPrepared
              ? "Article completion confirmed"
              : "Mark Article complete"}
        </button>
        <button
          className="min-h-11 rounded border border-sky-700 bg-white px-4 py-2 text-sm font-semibold text-sky-950 hover:bg-sky-100 disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400"
          disabled={
            !article
            || !studySessionEligible
            || !completionContextReady
            || !completionPrepared
            || completionTerminal
            || timerWarning !== null
            || completionPending !== null
            || learningMutationPending
            || sessionEndPending
          }
          type="button"
          onClick={(event) => void handleOpenNextUnfinished(event.currentTarget)}
        >
          {completionPending === "advance" ? "Finding next Article..." : "Open next unfinished Article"}
        </button>
      </div>

      {completionPrepared && timerWarning ? (
        <div
          className="mt-3 border border-amber-300 bg-amber-50 p-3"
          data-testid="focused-session-timer-warning"
        >
          <p className="text-sm font-semibold text-amber-950">Article completion is safe, but the Reader timer is not confirmed closed.</p>
          <p className="mt-1 text-xs leading-5 text-amber-900">{timerWarningText(timerWarning)}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {activeSession ? (
              <button
                className="rounded border border-amber-700 bg-white px-3 py-2 text-sm font-semibold text-amber-950 hover:bg-amber-100 disabled:text-slate-400"
                disabled={completionPending !== null || learningMutationPending || sessionEndPending}
                type="button"
                onClick={(event) => void handleRetryTimer(event.currentTarget)}
              >
                {completionPending === "timer" ? "Checking timer..." : "Retry timer check"}
              </button>
            ) : null}
            <button
              className="rounded bg-amber-800 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-900 disabled:bg-slate-300"
              disabled={completionPending !== null || learningMutationPending || sessionEndPending}
              type="button"
              onClick={(event) => void handleOpenNextUnfinished(event.currentTarget, true)}
            >
              Continue without timer confirmation
            </button>
          </div>
        </div>
      ) : null}

      {completionTerminal ? (
        <Link className="mt-3 inline-block text-sm font-semibold text-emerald-800 underline underline-offset-2" href="/session">
          Review completed session
        </Link>
      ) : null}

      <p aria-atomic="true" aria-live="polite" className="mt-3 text-sm text-sky-950" data-testid="focused-session-completion-status">
        {completionMessage ?? "Completion and timer state are checked independently before guided navigation."}
      </p>
      {completionError ? (
        <p className="mt-2 text-sm font-semibold text-red-800" role="alert">{completionError}</p>
      ) : null}
    </section>
  ) : null;

  if (error) {
    return (
      <section
        className="grid gap-4"
        data-shell-focus-owner={ownsRouteFocus ? "pending" : undefined}
        data-shell-route-ready="article-detail"
      >
        {focusedCompletionPanel}
        <WorkspaceState
          action={
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-md border border-red-400 bg-red-900 px-3 py-2 text-sm font-semibold text-white hover:bg-red-950 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-red-900"
                ref={articleRetryRef}
                type="button"
                onClick={() => {
                  setError(null);
                  claimReaderRouteFocus("retry");
                  setArticleRevision((current) => current + 1);
                }}
              >
                Retry article
              </button>
              <Link
                className="rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-900 hover:border-red-500"
                href={listReturnTo}
                onClick={prepareGraphReturnFocus}
              >
                {returnLabel}
              </Link>
            </div>
          }
          detail={error}
          title="Article unavailable"
          tone="error"
        />
      </section>
    );
  }

  if (!article) {
    return (
      <section
        aria-busy="true"
        className="grid gap-4"
        data-shell-focus-owner={ownsRouteFocus ? "pending" : undefined}
        data-shell-route-ready="article-detail"
      >
        {focusedCompletionPanel}
        <WorkspaceState
          action={
            <Link
              className="text-sm font-semibold text-slate-700 underline underline-offset-2"
              href={listReturnTo}
              onClick={prepareGraphReturnFocus}
            >
              {returnLabel}
            </Link>
          }
          title="Loading article"
          tone="loading"
        />
      </section>
    );
  }

  const workflowContext = {
    articleId: article.id,
    articleTitle: article.title,
    listReturnTo,
    sectionId: activeSectionId,
  };

  return (
    <section
      className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start"
      data-shell-route-ready="article-detail"
    >
      <div className="min-w-0 space-y-4">
        <article
          ref={articleRootRef}
          id="article-start"
          className="reader-workspace min-w-0 scroll-mt-24 rounded border border-slate-200 bg-white p-5 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700"
          data-reader-size={readerPreferences.textSize}
          data-reader-width={readerPreferences.width}
          data-shell-focus-owner={ownsRouteFocus ? "pending" : undefined}
          tabIndex={-1}
        >
        <Link
          className="text-sm text-slate-600 hover:text-slate-950"
          href={listReturnTo}
          onClick={prepareGraphReturnFocus}
        >
          {returnLabel}
        </Link>
        {listReturnTo === "/session" ? (
          <StudySessionReaderNavigation
            locked={completionPending !== null || learningMutationPending || sessionEndPending}
            position={studySessionPosition}
            warning={studySessionWarning}
          />
        ) : null}
        <h1 ref={articleHeadingRef} className="mt-4 scroll-mt-24 break-words text-2xl font-semibold leading-tight focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700" tabIndex={-1}>{article.title}</h1>
        {focusedCompletionPanel}
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
            onClick={(event) => handleReaderFragmentNavigate(event, "article-outline")}
          >
            Outline
          </a>
          <a
            className="rounded border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 lg:hidden"
            href="#reading-tools"
            onClick={(event) => handleReaderFragmentNavigate(event, "reading-tools")}
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
      </div>

      <aside
        id="reading-tools"
        aria-label="Reading tools"
        className="min-w-0 scroll-mt-24 space-y-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto lg:pr-1"
        tabIndex={-1}
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-300 pb-2">
          <h2 className="text-base font-semibold">Reading tools</h2>
          <a
            className="text-xs font-medium text-emerald-800 hover:text-emerald-950 lg:hidden"
            href="#article-start"
            onClick={(event) => handleReaderFragmentNavigate(event, "article-start")}
          >
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
        <section
          id="article-outline"
          className="scroll-mt-24 rounded border border-slate-200 bg-white p-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700"
          tabIndex={-1}
        >
          <ArticleOutline activeSectionId={activeSectionId} items={outline} onNavigate={handleOutlineNavigate} />
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <ReaderDisplayControls preferences={readerPreferences} onChange={handleReaderPreferences} />
        </section>

        <section
          ref={learningStateRegionRef}
          className="scroll-mt-24 rounded border border-slate-200 bg-white p-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
          data-testid="learning-state-controls"
          tabIndex={-1}
        >
          <h2 className="text-base font-semibold">Learning State</h2>
          {learningError ? <p className="mt-3 text-sm text-red-700">{learningError}</p> : null}
          <div className="mt-3 grid grid-cols-3 gap-2">
            {(["unread", "reading", "completed"] as LearningStatus[]).map((status) => (
              <button
                key={status}
                aria-pressed={learningState?.status === status}
                className={
                  learningState?.status === status
                    ? "rounded border border-slate-950 bg-slate-950 px-2 py-2 text-xs font-medium text-white"
                    : "rounded border border-slate-300 bg-white px-2 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                }
                disabled={completionPending !== null || learningMutationPending || learningState?.status === status}
                type="button"
                onClick={(event) => void handleStatusChange(status, event.currentTarget)}
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

        <section
          ref={bookmarkRegionRef}
          aria-busy={bookmarkLoadState === "loading" || bookmarkMutationPending}
          className="scroll-mt-24 rounded border border-slate-200 bg-white p-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
          data-testid="bookmark-controls"
          tabIndex={-1}
        >
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold">Bookmark</h2>
            <button
              className="rounded border border-slate-300 px-3 py-1 text-sm font-medium hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500"
              disabled={!bookmarkControlsReady || bookmarkMutationPending}
              type="button"
              onClick={(event) => void handleBookmarkToggle(event.currentTarget)}
            >
              {bookmarkMutationPending
                ? isBookmarked ? "Removing..." : "Saving..."
                : isBookmarked ? "Remove" : "Save"}
            </button>
          </div>
          <p className="mt-3 text-sm text-slate-600">
            {bookmarkLoadState === "loading" || bookmarkLoadState === "idle"
              ? "Loading bookmark status."
              : bookmarkLoadState === "error"
                ? "Bookmark status is unavailable."
                : isBookmarked
                  ? "This article is in your bookmarks."
                  : "This article is not bookmarked."}
          </p>
          <p
            aria-atomic="true"
            aria-live="polite"
            className={bookmarkFeedback && bookmarkFeedback.tone !== "error" ? "mt-2 text-sm text-slate-600" : "sr-only"}
            data-testid="bookmark-mutation-status"
            role="status"
          >
            {bookmarkFeedback && bookmarkFeedback.tone !== "error" ? bookmarkFeedback.message : ""}
          </p>
          <p
            aria-atomic="true"
            className={bookmarkFeedback?.tone === "error" ? "mt-2 text-sm text-red-700" : "sr-only"}
            data-testid="bookmark-mutation-error"
            role="alert"
          >
            {bookmarkFeedback?.tone === "error" ? bookmarkFeedback.message : ""}
          </p>
        </section>

        <section
          ref={sessionRegionRef}
          className="scroll-mt-24 rounded border border-slate-200 bg-white p-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
          data-testid="reader-session-controls"
          tabIndex={-1}
        >
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
            disabled={
              !activeSession
              || Boolean(activeSession.ended_at)
              || sessionEndPending
              || completionPending !== null
            }
            type="button"
            onClick={(event) => void handleEndSession(event.currentTarget)}
          >
            {sessionEndPending ? "Ending session..." : "End session"}
          </button>
        </section>

        <section
          aria-busy={noteLoadState === "loading" || noteMutationPending !== null}
          className="rounded border border-slate-200 bg-white p-4"
          data-testid="notes-controls"
        >
          <h2 className="text-base font-semibold">Notes</h2>
          <form className="mt-3 space-y-2" onSubmit={handleCreateNote}>
            <textarea
              aria-label="New learning note"
              className="min-h-24 w-full resize-y rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950 focus:ring-2 focus:ring-sky-700 focus:ring-offset-2"
              disabled={noteInteractionLocked}
              placeholder="Write a learning note"
              value={noteDraft}
              onChange={(event) => setNoteDraft(event.target.value)}
            />
            <button
              className="rounded bg-slate-950 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={!noteControlsReady || noteInteractionLocked || !noteDraft.trim()}
              type="submit"
            >
              {noteMutationPending?.kind === "note-create" ? "Saving note..." : "Add note"}
            </button>
          </form>
          <p
            aria-atomic="true"
            aria-live="polite"
            className={`${noteFeedback && noteFeedback.tone !== "error" ? "mt-2 text-sm text-slate-600" : "sr-only"} outline-none focus:ring-2 focus:ring-sky-700 focus:ring-offset-2`}
            data-testid="note-mutation-status"
            ref={noteStatusRef}
            role="status"
            tabIndex={-1}
          >
            {noteFeedback && noteFeedback.tone !== "error" ? noteFeedback.message : ""}
          </p>
          <p
            aria-atomic="true"
            className={`${noteFeedback?.tone === "error" ? "mt-2 text-sm text-red-700" : "sr-only"} outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2`}
            data-testid="note-mutation-error"
            ref={noteErrorRef}
            role="alert"
            tabIndex={-1}
          >
            {noteFeedback?.tone === "error" ? noteFeedback.message : ""}
          </p>
          <div className="mt-4 grid gap-3">
            {noteLoadState === "loading" || noteLoadState === "idle" ? (
              <p className="text-sm text-slate-600">Loading notes...</p>
            ) : noteLoadState === "error" ? (
              <p className="text-sm text-slate-600">Notes could not be loaded.</p>
            ) : notes.length ? (
              notes.map((note) => {
                const deleteIntent = activeNoteDeleteIntent?.noteId === note.note_id
                  ? activeNoteDeleteIntent
                  : null;
                const deletePending = noteMutationPending?.kind === "note-delete"
                  && noteMutationPending.noteId === note.note_id;
                const confirmationTitleId = `note-delete-title-${note.note_id}`;
                const confirmationDescriptionId = `note-delete-description-${note.note_id}`;
                return (
                  <article
                    key={note.note_id}
                    className="rounded border border-slate-100 p-3 text-sm"
                    data-testid="learning-note"
                  >
                    {editingNoteId === note.note_id ? (
                      <div className="space-y-2">
                        <textarea
                          aria-label="Edit learning note"
                          className="min-h-20 w-full resize-y rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950 focus:ring-2 focus:ring-sky-700 focus:ring-offset-2"
                          disabled={noteInteractionLocked}
                          ref={(node) => {
                            if (node) {
                              noteEditorRefs.current.set(note.note_id, node);
                            } else {
                              noteEditorRefs.current.delete(note.note_id);
                            }
                          }}
                          value={editingContent}
                          onChange={(event) => setEditingContent(event.target.value)}
                        />
                        <div className="flex gap-2">
                          <button
                            className="rounded bg-slate-950 px-3 py-1 text-xs font-medium text-white"
                            disabled={!noteControlsReady || noteInteractionLocked || !editingContent.trim()}
                            type="button"
                            onClick={(event) => void handleUpdateNote(note.note_id, event.currentTarget)}
                          >
                            {noteMutationPending?.kind === "note-update"
                              && noteMutationPending.noteId === note.note_id
                              ? "Saving..."
                              : "Save"}
                          </button>
                          <button
                            className="rounded border border-slate-300 px-3 py-1 text-xs font-medium"
                            disabled={!noteControlsReady || noteInteractionLocked}
                            type="button"
                            onClick={(event) => cancelEditingNote(note.note_id, event.currentTarget)}
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
                            disabled={!noteControlsReady || noteInteractionLocked}
                            ref={(node) => {
                              if (node) {
                                noteEditButtonRefs.current.set(note.note_id, node);
                              } else {
                                noteEditButtonRefs.current.delete(note.note_id);
                              }
                            }}
                            type="button"
                            onClick={(event) => beginEditingNote(note, event.currentTarget)}
                          >
                            Edit
                          </button>
                          <button
                            className="rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-700"
                            disabled={!noteControlsReady || noteInteractionLocked}
                            ref={(node) => {
                              if (node) {
                                noteDeleteButtonRefs.current.set(note.note_id, node);
                              } else {
                                noteDeleteButtonRefs.current.delete(note.note_id);
                              }
                            }}
                            type="button"
                            onClick={() => handleRequestNoteDelete(note.note_id)}
                          >
                            Delete
                          </button>
                        </div>
                        {deleteIntent ? (
                          <div
                            aria-busy={deletePending}
                            aria-describedby={confirmationDescriptionId}
                            aria-labelledby={confirmationTitleId}
                            className="mt-3 border border-red-200 bg-red-50 p-3 outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
                            data-testid="note-delete-confirmation"
                            onKeyDown={(event) => handleNoteDeleteConfirmationKeyDown(event, deleteIntent)}
                            ref={noteDeleteConfirmationRef}
                            role="group"
                            tabIndex={-1}
                          >
                            <p className="font-semibold text-red-900" id={confirmationTitleId}>
                              Delete this note permanently?
                            </p>
                            <p className="mt-1 leading-5 text-red-800" id={confirmationDescriptionId}>
                              This action cannot be undone.
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2">
                              <button
                                className="rounded border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-900"
                                disabled={deletePending}
                                onClick={() => handleCancelNoteDelete(deleteIntent)}
                                ref={noteDeleteCancelRef}
                                type="button"
                              >
                                Cancel
                              </button>
                              <button
                                className="rounded bg-red-700 px-3 py-1 text-xs font-medium text-white disabled:cursor-not-allowed disabled:bg-red-300"
                                disabled={deletePending}
                                onClick={(event) => void handleDeleteNote(deleteIntent, event.currentTarget)}
                                type="button"
                              >
                                {deletePending ? "Deleting..." : "Delete permanently"}
                              </button>
                            </div>
                          </div>
                        ) : null}
                      </>
                    )}
                  </article>
                );
              })
            ) : (
              <p className="text-sm text-slate-600">No notes yet.</p>
            )}
          </div>
        </section>

        <ZoteroLinksPanel key={article.id} articleId={article.id} initialQuery={article.title} />

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
          {historyError ? (
            <p className="mt-2 text-sm text-amber-900" role="status">{historyError}</p>
          ) : null}
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

function StudySessionReaderNavigation({
  locked,
  position,
  warning,
}: Readonly<{
  locked: boolean;
  position: StudySessionPosition | null;
  warning: string | null;
}>) {
  return (
    <nav
      aria-label="Focused study session position"
      className="mt-4 border-y border-slate-200 py-3"
      data-testid="study-session-reader-navigation"
    >
      {warning ? <p className="text-sm text-amber-800" role="status">{warning}</p> : null}
      {position ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-semibold text-slate-700">
            Article {position.index + 1} of {position.total}
          </p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm font-semibold">
            {position.previous ? (
              <Link
                aria-label={`Previous in session: ${position.previous.title}`}
                aria-disabled={locked}
                className={locked ? "cursor-not-allowed text-slate-400" : "text-emerald-800 hover:text-emerald-950"}
                href={createStudySessionReaderHref(position.previous)}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (event) => event.preventDefault() : undefined}
              >
                Previous
              </Link>
            ) : null}
            {position.next ? (
              <Link
                aria-label={`Next in session: ${position.next.title}`}
                aria-disabled={locked}
                className={locked ? "cursor-not-allowed text-slate-400" : "text-emerald-800 hover:text-emerald-950"}
                href={createStudySessionReaderHref(position.next)}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (event) => event.preventDefault() : undefined}
              >
                Next
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}
    </nav>
  );
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Not recorded";
  }
  return new Date(value).toLocaleString();
}

function errorText(value: unknown, fallback: string): string {
  return value instanceof Error ? value.message : fallback;
}

function timerWarningText(status: "confirmed-open" | "unknown" | "unavailable"): string {
  if (status === "confirmed-open") {
    return "The exact timer is still open. Retry performs a fresh read before at most one end request.";
  }
  if (status === "unknown") {
    return "The exact timer could not be read back. Retry checks status only and never replays the end request blindly.";
  }
  return "No exact timer can be confirmed for this Reader. Continuing will not claim that a timer ended.";
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
      <h2 {...props} id={headingIdForNode(node, headingIdsByLine)} className="scroll-mt-24 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700" tabIndex={-1} />
    ),
    h3: ({ node, ...props }) => (
      <h3 {...props} id={headingIdForNode(node, headingIdsByLine)} className="scroll-mt-24 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700" tabIndex={-1} />
    ),
    h4: ({ node, ...props }) => (
      <h4 {...props} id={headingIdForNode(node, headingIdsByLine)} className="scroll-mt-24 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700" tabIndex={-1} />
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
