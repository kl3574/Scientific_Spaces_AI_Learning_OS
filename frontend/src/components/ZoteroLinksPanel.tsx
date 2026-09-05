"use client";

import {
  FormEvent,
  KeyboardEvent as ReactKeyboardEvent,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  ZoteroArticleLinkItem,
  ZoteroItem,
  ZoteroRelationType,
  createArticleZoteroLink,
  deleteArticleZoteroLink,
  exportZoteroBibtex,
  fetchArticleZoteroLinks,
  fetchZoteroStatus,
  searchZoteroItems,
} from "@/lib/zotero";
import {
  ZoteroMutationExpectation,
  ZoteroPanelOperation,
  ZoteroUnlinkIntent,
  createZoteroPanelOperation,
  createZoteroUnlinkIntent,
  getMutationReadbackOutcome,
  getZoteroLinkFingerprint,
  mergeZoteroLinkItem,
  normalizeZoteroQuery,
  ownsZoteroPanelOperation,
  ownsZoteroUnlinkIntent,
  removeZoteroLinkItem,
} from "@/lib/zoteroLinkOperations";

const relationTypes: ZoteroRelationType[] = ["related", "cites", "background"];

type LinksStatus = "loading" | "ready" | "error" | "reconciling";
type ProviderStatus = "loading" | "available" | "unavailable" | "error";
type SearchStatus = "idle" | "loading" | "ready" | "error";
type BibtexStatus = "idle" | "loading" | "ready" | "error";
type MutationKind = "link" | "unlink";

type PendingMutation = Readonly<{
  operation: ZoteroPanelOperation;
  kind: MutationKind;
  itemKey: string;
  itemTitle: string;
}>;

type PanelFeedback = Readonly<{
  tone: "status" | "error";
  message: string;
}>;

type LoadMode = "initial" | "manual";

type FocusTarget =
  | "feedback"
  | "bibtex"
  | "unlink-cancel"
  | "reload"
  | "retry-links"
  | "provider"
  | "link-button"
  | "unlink-button";

type FocusRequest = Readonly<{
  articleId: string;
  generation: number;
  requestId: number;
  target: FocusTarget;
  itemKey?: string;
}>;

export function ZoteroLinksPanel({ articleId, initialQuery }: Readonly<{ articleId: string; initialQuery: string }>) {
  const [links, setLinks] = useState<ZoteroArticleLinkItem[]>([]);
  const [linksStatus, setLinksStatus] = useState<LinksStatus>("loading");
  const [linksError, setLinksError] = useState<string | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>("loading");
  const [providerMessage, setProviderMessage] = useState<string | null>(null);
  const [results, setResults] = useState<ZoteroItem[]>([]);
  const [query, setQuery] = useState(initialQuery);
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const [searchStatus, setSearchStatus] = useState<SearchStatus>("idle");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [relationType, setRelationType] = useState<ZoteroRelationType>("related");
  const [note, setNote] = useState("");
  const [bibtex, setBibtex] = useState("");
  const [bibtexItemCount, setBibtexItemCount] = useState(0);
  const [bibtexOpen, setBibtexOpen] = useState(false);
  const [bibtexStatus, setBibtexStatus] = useState<BibtexStatus>("idle");
  const [bibtexError, setBibtexError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<PanelFeedback | null>(null);
  const [pendingMutation, setPendingMutation] = useState<PendingMutation | null>(null);
  const [unlinkIntent, setUnlinkIntent] = useState<ZoteroUnlinkIntent | null>(null);
  const [reconciliationRequired, setReconciliationRequired] = useState(false);
  const [focusRequest, setFocusRequest] = useState<FocusRequest | null>(null);

  const mountedRef = useRef(false);
  const panelRef = useRef<HTMLElement>(null);
  const contextRef = useRef({ articleId, generation: 0 });
  const operationSequenceRef = useRef(0);
  const focusSequenceRef = useRef(0);
  const linksRef = useRef<ZoteroArticleLinkItem[]>([]);
  const activeLinksOperationRef = useRef<ZoteroPanelOperation | null>(null);
  const activeProviderOperationRef = useRef<ZoteroPanelOperation | null>(null);
  const activeSearchOperationRef = useRef<ZoteroPanelOperation | null>(null);
  const activeMutationOperationRef = useRef<ZoteroPanelOperation | null>(null);
  const activeExportOperationRef = useRef<ZoteroPanelOperation | null>(null);
  const unlinkIntentRef = useRef<ZoteroUnlinkIntent | null>(null);
  const reconciliationRequiredRef = useRef(false);
  const hasSuccessfulLinksLoadRef = useRef(false);
  const linksControllerRef = useRef<AbortController | null>(null);
  const providerControllerRef = useRef<AbortController | null>(null);
  const searchControllerRef = useRef<AbortController | null>(null);
  const exportControllerRef = useRef<AbortController | null>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const bibtexRegionRef = useRef<HTMLDivElement>(null);
  const linksRegionRef = useRef<HTMLDivElement>(null);
  const providerRegionRef = useRef<HTMLDivElement>(null);
  const unlinkCancelRef = useRef<HTMLButtonElement>(null);
  const reloadLinksRef = useRef<HTMLButtonElement>(null);
  const retryLinksRef = useRef<HTMLButtonElement>(null);
  const unlinkButtonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const linkButtonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const linkedKeys = useMemo(
    () => new Set(links.map((entry) => entry.link.zotero_item_key)),
    [links],
  );
  const providerAvailable = providerStatus === "available";
  const linksReady = linksStatus === "ready" && linksError === null;
  const mutationLocked = pendingMutation !== null
    || unlinkIntent !== null
    || reconciliationRequired
    || bibtexStatus === "loading";
  const linksBusy = linksStatus === "loading"
    || linksStatus === "reconciling"
    || pendingMutation !== null;
  const mutationAnnouncement = pendingMutation
    ? pendingMutation.kind === "link"
      ? `Linking ${pendingMutation.itemTitle} to this Article.`
      : `Unlinking ${pendingMutation.itemTitle} from this Article.`
    : "";
  const linksAnnouncement = getLinksAnnouncement(
    linksStatus,
    links.length,
    linksError,
    reconciliationRequired,
  );

  useLayoutEffect(() => {
    mountedRef.current = true;
    cancelReadOperations();
    operationSequenceRef.current += 1;
    const generation = contextRef.current.generation + 1;
    contextRef.current = { articleId, generation };
    activeLinksOperationRef.current = null;
    activeProviderOperationRef.current = null;
    activeSearchOperationRef.current = null;
    activeMutationOperationRef.current = null;
    activeExportOperationRef.current = null;
    unlinkIntentRef.current = null;
    reconciliationRequiredRef.current = false;
    hasSuccessfulLinksLoadRef.current = false;
    linksRef.current = [];

    setLinks([]);
    setLinksStatus("loading");
    setLinksError(null);
    setProviderStatus("loading");
    setProviderMessage(null);
    setResults([]);
    setQuery(initialQuery);
    setSubmittedQuery(null);
    setSearchStatus("idle");
    setSearchError(null);
    setRelationType("related");
    setNote("");
    setFeedback(null);
    setPendingMutation(null);
    setUnlinkIntent(null);
    setReconciliationRequired(false);
    setFocusRequest(null);
    resetBibtexState();

    void loadProvider(articleId, generation);
    void loadLinks(articleId, generation, "initial");

    return () => {
      mountedRef.current = false;
      cancelReadOperations();
      activeLinksOperationRef.current = null;
      activeProviderOperationRef.current = null;
      activeSearchOperationRef.current = null;
      activeMutationOperationRef.current = null;
      activeExportOperationRef.current = null;
      unlinkIntentRef.current = null;
    };
  }, [articleId, initialQuery]);

  useLayoutEffect(() => {
    if (!focusRequest) {
      return;
    }
    const context = contextRef.current;
    if (
      !mountedRef.current
      || focusRequest.articleId !== context.articleId
      || focusRequest.generation !== context.generation
    ) {
      return;
    }
    const target = resolveFocusTarget(focusRequest);
    if (!target?.isConnected) {
      return;
    }
    target.focus({ preventScroll: true });
    target.scrollIntoView({ behavior: "auto", block: "nearest" });
  }, [focusRequest]);

  function nextOperation(kind: ZoteroPanelOperation["kind"], subject: string): ZoteroPanelOperation {
    const context = contextRef.current;
    operationSequenceRef.current += 1;
    return createZoteroPanelOperation(
      context.articleId,
      context.generation,
      operationSequenceRef.current,
      kind,
      subject,
    );
  }

  function operationIsCurrent(
    current: ZoteroPanelOperation | null,
    operation: ZoteroPanelOperation,
  ): boolean {
    const context = contextRef.current;
    return mountedRef.current
      && ownsZoteroPanelOperation(
        current,
        operation,
        context.articleId,
        context.generation,
      );
  }

  function cancelReadOperations() {
    linksControllerRef.current?.abort();
    providerControllerRef.current?.abort();
    searchControllerRef.current?.abort();
    exportControllerRef.current?.abort();
    linksControllerRef.current = null;
    providerControllerRef.current = null;
    searchControllerRef.current = null;
    exportControllerRef.current = null;
  }

  function requestOwnedFocus(
    target: FocusTarget,
    expectedArticleId: string,
    expectedGeneration: number,
    itemKey?: string,
  ) {
    focusSequenceRef.current += 1;
    setFocusRequest({
      articleId: expectedArticleId,
      generation: expectedGeneration,
      requestId: focusSequenceRef.current,
      target,
      itemKey,
    });
  }

  function resolveFocusTarget(request: FocusRequest): HTMLElement | null {
    if (request.target === "feedback") return feedbackRef.current;
    if (request.target === "bibtex") return bibtexRegionRef.current;
    if (request.target === "unlink-cancel") return unlinkCancelRef.current;
    if (request.target === "reload") return reloadLinksRef.current;
    if (request.target === "retry-links") return retryLinksRef.current;
    if (request.target === "provider") return providerRegionRef.current;
    if (request.target === "link-button" && request.itemKey) {
      return linkButtonRefs.current.get(request.itemKey) ?? null;
    }
    if (request.target === "unlink-button" && request.itemKey) {
      return unlinkButtonRefs.current.get(request.itemKey) ?? null;
    }
    return null;
  }

  function parkPanelFocus() {
    const bridge = linksRegionRef.current;
    if (bridge?.isConnected && document.activeElement !== bridge) {
      bridge.focus({ preventScroll: true });
    }
  }

  function resetBibtexState() {
    exportControllerRef.current?.abort();
    exportControllerRef.current = null;
    activeExportOperationRef.current = null;
    setBibtex("");
    setBibtexItemCount(0);
    setBibtexOpen(false);
    setBibtexStatus("idle");
    setBibtexError(null);
  }

  function commitLinks(nextLinks: ZoteroArticleLinkItem[]) {
    linksRef.current = nextLinks;
    setLinks(nextLinks);
    resetBibtexState();
  }

  function clearMutationState() {
    activeMutationOperationRef.current = null;
    setPendingMutation(null);
  }

  function clearUnlinkIntent() {
    unlinkIntentRef.current = null;
    setUnlinkIntent(null);
  }

  function setUncertainState(required: boolean) {
    reconciliationRequiredRef.current = required;
    setReconciliationRequired(required);
  }

  function mutationIsLocked(): boolean {
    return activeMutationOperationRef.current !== null
      || activeExportOperationRef.current !== null
      || unlinkIntentRef.current !== null
      || reconciliationRequiredRef.current;
  }

  function announce(
    tone: PanelFeedback["tone"],
    message: string,
    operation: ZoteroPanelOperation,
    focus = true,
  ) {
    if (!operationIsCurrent(
      tone === "error" && operation.kind === "search"
        ? activeSearchOperationRef.current
        : operation.kind === "export"
          ? activeExportOperationRef.current
          : operation.kind === "provider-status"
            ? activeProviderOperationRef.current
            : operation.kind === "links-load" || operation.kind === "reconcile"
              ? activeLinksOperationRef.current
              : activeMutationOperationRef.current,
      operation,
    )) {
      return;
    }
    setFeedback({ tone, message });
    if (focus) {
      requestOwnedFocus("feedback", operation.articleId, operation.generation);
    }
  }

  async function loadProvider(
    expectedArticleId: string,
    expectedGeneration: number,
    focusResult = false,
  ) {
    const operation = nextOperation("provider-status", expectedArticleId);
    if (operation.articleId !== expectedArticleId || operation.generation !== expectedGeneration) {
      return;
    }
    providerControllerRef.current?.abort();
    const controller = new AbortController();
    providerControllerRef.current = controller;
    activeProviderOperationRef.current = operation;
    setProviderStatus("loading");
    setProviderMessage(null);
    try {
      const status = await fetchZoteroStatus(controller.signal);
      if (!operationIsCurrent(activeProviderOperationRef.current, operation)) {
        return;
      }
      if (status.available) {
        setProviderStatus("available");
        setProviderMessage(null);
      } else {
        setProviderStatus("unavailable");
        setProviderMessage("Zotero is unavailable. Existing project links remain visible.");
      }
      if (focusResult) {
        requestOwnedFocus("provider", operation.articleId, operation.generation);
      }
    } catch (error) {
      if (isAbortError(error) || !operationIsCurrent(activeProviderOperationRef.current, operation)) {
        return;
      }
      setProviderStatus("error");
      setProviderMessage("Zotero availability could not be checked.");
      if (focusResult) {
        requestOwnedFocus("provider", operation.articleId, operation.generation);
      }
    } finally {
      if (operationIsCurrent(activeProviderOperationRef.current, operation)) {
        activeProviderOperationRef.current = null;
        providerControllerRef.current = null;
      }
    }
  }

  async function loadLinks(
    expectedArticleId: string,
    expectedGeneration: number,
    mode: LoadMode,
  ) {
    const operation = nextOperation("links-load", `${mode}:${expectedArticleId}`);
    if (operation.articleId !== expectedArticleId || operation.generation !== expectedGeneration) {
      return;
    }
    linksControllerRef.current?.abort();
    const controller = new AbortController();
    linksControllerRef.current = controller;
    activeLinksOperationRef.current = operation;
    setLinksStatus(mode === "initial" ? "loading" : "reconciling");
    setLinksError(null);
    try {
      const response = await fetchArticleZoteroLinks(expectedArticleId, controller.signal);
      if (!operationIsCurrent(activeLinksOperationRef.current, operation)) {
        return;
      }
      commitLinks(response.items);
      hasSuccessfulLinksLoadRef.current = true;
      setLinksStatus("ready");
      setLinksError(null);
      setUncertainState(false);
      if (mode === "manual") {
        announce("status", "Related papers reloaded from project storage.", operation);
      }
    } catch (error) {
      if (isAbortError(error) || !operationIsCurrent(activeLinksOperationRef.current, operation)) {
        return;
      }
      if (mode === "initial" || !hasSuccessfulLinksLoadRef.current) {
        const message = mode === "initial"
          ? "Related papers could not be loaded."
          : "Related papers still could not be loaded.";
        setLinksStatus("error");
        setLinksError(message);
        setUncertainState(false);
        setFeedback(null);
        if (mode === "manual") {
          requestOwnedFocus("retry-links", operation.articleId, operation.generation);
        }
      } else {
        const message = "Related papers could not be reloaded. Persistence remains unconfirmed.";
        setLinksStatus("ready");
        setLinksError(null);
        setUncertainState(true);
        announce("error", message, operation);
      }
    } finally {
      if (operationIsCurrent(activeLinksOperationRef.current, operation)) {
        activeLinksOperationRef.current = null;
        linksControllerRef.current = null;
      }
    }
  }

  function handleQueryChange(nextQuery: string) {
    const normalizedNext = normalizeZoteroQuery(nextQuery);
    const activeSearch = activeSearchOperationRef.current;
    setQuery(nextQuery);
    if (
      activeSearch?.kind === "search"
      && activeSearch.subject === normalizedNext
    ) {
      return;
    }
    if (
      submittedQuery !== null
      && normalizeZoteroQuery(submittedQuery) === normalizedNext
      && searchStatus !== "error"
    ) {
      return;
    }
    searchControllerRef.current?.abort();
    searchControllerRef.current = null;
    activeSearchOperationRef.current = null;
    setResults([]);
    setSubmittedQuery(null);
    setSearchStatus("idle");
    setSearchError(null);
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitted = normalizeZoteroQuery(query);
    if (!submitted) {
      setSearchStatus("error");
      setSearchError("Enter a title or keyword to search Zotero.");
      return;
    }
    if (!providerAvailable) {
      setSearchStatus("error");
      setSearchError("Zotero must be available before searching.");
      return;
    }
    if (
      activeSearchOperationRef.current?.kind === "search"
      && activeSearchOperationRef.current.subject === submitted
    ) {
      return;
    }

    searchControllerRef.current?.abort();
    const controller = new AbortController();
    searchControllerRef.current = controller;
    const operation = nextOperation("search", submitted);
    activeSearchOperationRef.current = operation;
    if (document.activeElement === event.currentTarget.querySelector('button[type="submit"]')) {
      parkPanelFocus();
    }
    setSubmittedQuery(submitted);
    setSearchStatus("loading");
    setSearchError(null);
    setResults([]);
    try {
      const response = await searchZoteroItems(submitted, 10, controller.signal);
      if (!operationIsCurrent(activeSearchOperationRef.current, operation)) {
        return;
      }
      setResults(response.items);
      setSearchStatus("ready");
    } catch (error) {
      if (isAbortError(error) || !operationIsCurrent(activeSearchOperationRef.current, operation)) {
        return;
      }
      setSearchStatus("error");
      setSearchError("Zotero search failed. Try again when the provider is available.");
    } finally {
      if (operationIsCurrent(activeSearchOperationRef.current, operation)) {
        activeSearchOperationRef.current = null;
        searchControllerRef.current = null;
      }
    }
  }

  async function handleLink(item: ZoteroItem) {
    if (
      !providerAvailable
      || !linksReady
      || mutationIsLocked()
      || linkedKeys.has(item.item_key)
    ) {
      return;
    }
    const operation = nextOperation("link", item.item_key);
    activeMutationOperationRef.current = operation;
    parkPanelFocus();
    setPendingMutation({
      operation,
      kind: "link",
      itemKey: item.item_key,
      itemTitle: item.title,
    });
    setFeedback(null);
    const submittedNote = note.trim() || null;
    const expectation: ZoteroMutationExpectation = {
      kind: "link",
      itemKey: item.item_key,
      relationType,
      note: submittedNote,
    };
    try {
      const created = await createArticleZoteroLink(
        operation.articleId,
        item.item_key,
        relationType,
        submittedNote,
      );
      if (!operationIsCurrent(activeMutationOperationRef.current, operation)) {
        return;
      }
      if (
        created.article_id !== operation.articleId
        || created.zotero_item_key !== item.item_key
      ) {
        throw new Error("Unexpected Zotero link identity");
      }
      parkPanelFocus();
      commitLinks(mergeZoteroLinkItem(linksRef.current, { link: created, item }));
      setNote("");
      clearMutationState();
      setFeedback({ tone: "status", message: `${item.title} linked to this article.` });
      requestOwnedFocus("feedback", operation.articleId, operation.generation);
    } catch {
      if (!operationIsCurrent(activeMutationOperationRef.current, operation)) {
        return;
      }
      await reconcileMutation(operation, expectation, item.title);
    }
  }

  function openUnlink(itemKey: string) {
    if (mutationIsLocked()) {
      return;
    }
    const context = contextRef.current;
    const intent = createZoteroUnlinkIntent(context.articleId, context.generation, itemKey);
    parkPanelFocus();
    unlinkIntentRef.current = intent;
    setUnlinkIntent(intent);
    setFeedback(null);
    requestOwnedFocus("unlink-cancel", intent.articleId, intent.generation);
  }

  function cancelUnlink(intent: ZoteroUnlinkIntent) {
    const context = contextRef.current;
    if (!ownsZoteroUnlinkIntent(
      unlinkIntentRef.current,
      intent,
      context.articleId,
      context.generation,
    ) || activeMutationOperationRef.current) {
      return;
    }
    parkPanelFocus();
    clearUnlinkIntent();
    requestOwnedFocus(
      "unlink-button",
      intent.articleId,
      intent.generation,
      intent.itemKey,
    );
  }

  function handleConfirmationKeyDown(
    event: ReactKeyboardEvent<HTMLDivElement>,
    intent: ZoteroUnlinkIntent,
  ) {
    if (event.key !== "Escape" || activeMutationOperationRef.current) {
      return;
    }
    event.preventDefault();
    cancelUnlink(intent);
  }

  async function confirmUnlink(intent: ZoteroUnlinkIntent, itemTitle: string) {
    const context = contextRef.current;
    if (
      activeMutationOperationRef.current
      || !ownsZoteroUnlinkIntent(
        unlinkIntentRef.current,
        intent,
        context.articleId,
        context.generation,
      )
    ) {
      return;
    }
    const operation = nextOperation("unlink", intent.itemKey);
    activeMutationOperationRef.current = operation;
    parkPanelFocus();
    setPendingMutation({
      operation,
      kind: "unlink",
      itemKey: intent.itemKey,
      itemTitle,
    });
    setFeedback(null);
    const expectation: ZoteroMutationExpectation = {
      kind: "unlink",
      itemKey: intent.itemKey,
    };
    try {
      await deleteArticleZoteroLink(operation.articleId, intent.itemKey);
      if (!operationIsCurrent(activeMutationOperationRef.current, operation)) {
        return;
      }
      parkPanelFocus();
      commitLinks(removeZoteroLinkItem(linksRef.current, intent.itemKey));
      clearMutationState();
      clearUnlinkIntent();
      setFeedback({
        tone: "status",
        message: `${itemTitle} unlinked. The Zotero library item was not deleted.`,
      });
      requestOwnedFocus("feedback", operation.articleId, operation.generation);
    } catch {
      if (!operationIsCurrent(activeMutationOperationRef.current, operation)) {
        return;
      }
      await reconcileMutation(operation, expectation, itemTitle);
    }
  }

  async function reconcileMutation(
    mutationOperation: ZoteroPanelOperation,
    expectation: ZoteroMutationExpectation,
    itemTitle: string,
  ) {
    const reconcileOperation = nextOperation(
      "reconcile",
      `${mutationOperation.operationId}:${expectation.kind}:${expectation.itemKey}`,
    );
    activeLinksOperationRef.current = reconcileOperation;
    linksControllerRef.current?.abort();
    const controller = new AbortController();
    linksControllerRef.current = controller;
    setLinksStatus("reconciling");
    setLinksError(null);
    try {
      const response = await fetchArticleZoteroLinks(
        mutationOperation.articleId,
        controller.signal,
      );
      if (
        !operationIsCurrent(activeMutationOperationRef.current, mutationOperation)
        || !operationIsCurrent(activeLinksOperationRef.current, reconcileOperation)
      ) {
        return;
      }
      const outcome = getMutationReadbackOutcome(response.items, expectation);
      parkPanelFocus();
      commitLinks(response.items);
      setLinksStatus("ready");
      clearMutationState();
      clearUnlinkIntent();
      if (outcome === "applied") {
        if (expectation.kind === "link") {
          setNote("");
        }
        setFeedback({
          tone: "status",
          message: expectation.kind === "link"
            ? `${itemTitle} link confirmed after reloading project storage.`
            : `${itemTitle} unlink confirmed after reloading project storage. The Zotero item was not deleted.`,
        });
        requestOwnedFocus("feedback", mutationOperation.articleId, mutationOperation.generation);
        return;
      }
      if (outcome === "not-applied") {
        const message = expectation.kind === "link"
          ? `${itemTitle} was not linked. You can retry.`
          : `${itemTitle} was not unlinked. You can retry.`;
        setFeedback({ tone: "error", message });
        requestOwnedFocus(
          expectation.kind === "link" ? "link-button" : "unlink-button",
          mutationOperation.articleId,
          mutationOperation.generation,
          expectation.itemKey,
        );
        return;
      }
      requireManualReconciliation(
        mutationOperation,
        `${itemTitle} changed, but the requested relationship could not be confirmed. Persistence remains unconfirmed; reload related papers before another change.`,
      );
    } catch (error) {
      if (
        isAbortError(error)
        || !operationIsCurrent(activeMutationOperationRef.current, mutationOperation)
      ) {
        return;
      }
      parkPanelFocus();
      clearMutationState();
      clearUnlinkIntent();
      setLinksStatus("ready");
      requireManualReconciliation(
        mutationOperation,
        `${itemTitle} may have changed, but project storage could not be reloaded. Persistence remains unconfirmed; reload related papers before another change.`,
      );
    } finally {
      if (operationIsCurrent(activeLinksOperationRef.current, reconcileOperation)) {
        activeLinksOperationRef.current = null;
        linksControllerRef.current = null;
      }
    }
  }

  function requireManualReconciliation(operation: ZoteroPanelOperation, message: string) {
    setUncertainState(true);
    setFeedback({ tone: "error", message });
    requestOwnedFocus("reload", operation.articleId, operation.generation);
  }

  function handleReloadLinks() {
    if (activeLinksOperationRef.current || activeMutationOperationRef.current) {
      return;
    }
    const context = contextRef.current;
    parkPanelFocus();
    setFeedback(null);
    void loadLinks(context.articleId, context.generation, "manual");
  }

  function handleProviderRetry() {
    if (activeProviderOperationRef.current) {
      return;
    }
    const context = contextRef.current;
    parkPanelFocus();
    void loadProvider(context.articleId, context.generation, true);
  }

  async function handleExportLinked() {
    if (bibtexOpen && bibtexStatus !== "loading") {
      setBibtexOpen(false);
      return;
    }
    if (
      !linksRef.current.length
      || !providerAvailable
      || mutationIsLocked()
      || activeExportOperationRef.current
    ) {
      return;
    }
    const fingerprint = getZoteroLinkFingerprint(linksRef.current);
    const operation = nextOperation("export", fingerprint);
    const controller = new AbortController();
    exportControllerRef.current = controller;
    activeExportOperationRef.current = operation;
    parkPanelFocus();
    setBibtexOpen(true);
    setBibtexStatus("loading");
    setBibtexError(null);
    setBibtex("");
    setBibtexItemCount(0);
    requestOwnedFocus("bibtex", operation.articleId, operation.generation);
    try {
      const itemKeys = linksRef.current.map((entry) => entry.link.zotero_item_key);
      const response = await exportZoteroBibtex(itemKeys, controller.signal);
      if (
        !operationIsCurrent(activeExportOperationRef.current, operation)
        || getZoteroLinkFingerprint(linksRef.current) !== fingerprint
      ) {
        return;
      }
      setBibtex(response.bibtex);
      setBibtexItemCount(response.item_count);
      setBibtexStatus("ready");
      requestOwnedFocus("bibtex", operation.articleId, operation.generation);
    } catch (error) {
      if (isAbortError(error) || !operationIsCurrent(activeExportOperationRef.current, operation)) {
        return;
      }
      setBibtexStatus("error");
      setBibtexError("BibTeX could not be requested for the current links.");
      requestOwnedFocus("bibtex", operation.articleId, operation.generation);
    } finally {
      if (operationIsCurrent(activeExportOperationRef.current, operation)) {
        activeExportOperationRef.current = null;
        exportControllerRef.current = null;
      }
    }
  }

  return (
    <section
      ref={panelRef}
      aria-labelledby="related-papers-title"
      className="min-w-0 rounded border border-slate-200 bg-white p-4"
      data-testid="zotero-links-panel"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="related-papers-title" className="text-base font-semibold">Related Papers</h2>
        <button
          aria-controls="linked-bibtex-region"
          aria-expanded={bibtexOpen}
          className="rounded border border-slate-300 px-3 py-1 text-xs font-medium hover:bg-slate-50 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
          disabled={!links.length || !providerAvailable || mutationLocked}
          type="button"
          onClick={() => void handleExportLinked()}
        >
          {bibtexStatus === "loading" ? "Exporting..." : bibtexOpen ? "Hide BibTeX" : "Export BibTeX"}
        </button>
      </div>

      <div
        ref={providerRegionRef}
        aria-busy={providerStatus === "loading"}
        className="mt-3 text-xs text-slate-600 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700"
        data-testid="zotero-provider-state"
        tabIndex={-1}
      >
        {providerStatus === "loading" ? <p role="status">Checking Zotero availability...</p> : null}
        {providerStatus === "available" ? <p>Zotero is available.</p> : null}
        {providerStatus === "unavailable" || providerStatus === "error" ? (
          <div className="rounded border border-amber-200 bg-amber-50 p-3 text-amber-900">
            <p role={providerStatus === "error" ? "alert" : "status"}>{providerMessage}</p>
            <button
              className="mt-2 rounded border border-amber-300 px-2 py-1 font-medium hover:bg-amber-100 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed"
              disabled={activeProviderOperationRef.current !== null}
              type="button"
              onClick={handleProviderRetry}
            >
              Retry availability
            </button>
          </div>
        ) : null}
      </div>

      {feedback ? (
        <div
          ref={feedbackRef}
          aria-atomic="true"
          aria-live={feedback.tone === "error" ? "assertive" : "polite"}
          className={`mt-3 break-words rounded border p-3 text-sm [overflow-wrap:anywhere] focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 ${
            feedback.tone === "error"
              ? "border-red-200 bg-red-50 text-red-800"
              : "border-emerald-200 bg-emerald-50 text-emerald-900"
          }`}
          data-testid="zotero-panel-feedback"
          role={feedback.tone === "error" ? "alert" : "status"}
          tabIndex={-1}
        >
          {feedback.message}
        </div>
      ) : null}

      {reconciliationRequired ? (
        <button
          ref={reloadLinksRef}
          className="mt-3 rounded border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed"
          disabled={linksStatus === "reconciling"}
          type="button"
          onClick={handleReloadLinks}
        >
          {linksStatus === "reconciling" ? "Reloading..." : "Reload related papers"}
        </button>
      ) : null}

      <p
        aria-atomic="true"
        aria-live="polite"
        className="sr-only"
        data-testid="zotero-links-announcement"
        role="status"
      >
        {linksAnnouncement}
      </p>
      <p
        aria-atomic="true"
        aria-live="polite"
        className="sr-only"
        data-testid="zotero-mutation-announcement"
        role="status"
      >
        {mutationAnnouncement}
      </p>

      <div
        ref={linksRegionRef}
        aria-busy={linksBusy}
        aria-label="Linked project papers"
        className="mt-3 grid min-w-0 gap-2 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700"
        data-testid="zotero-linked-papers"
        tabIndex={-1}
      >
        {linksStatus === "loading" ? (
          <p className="text-sm text-slate-600">Loading related papers...</p>
        ) : null}
        {linksError ? (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <p role="alert">{linksError}</p>
            {!reconciliationRequired ? (
              <button
                ref={retryLinksRef}
                className="mt-2 rounded border border-red-300 px-2 py-1 font-medium hover:bg-red-100 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed"
                disabled={linksStatus === "reconciling"}
                type="button"
                onClick={handleReloadLinks}
              >
                Retry related papers
              </button>
            ) : null}
          </div>
        ) : null}
        {linksStatus !== "loading" && linksStatus !== "error" && links.length ? (
          links.map((entry) => {
            const itemKey = entry.link.zotero_item_key;
            const itemTitle = entry.item?.title ?? itemKey;
            const intent = unlinkIntent?.itemKey === itemKey ? unlinkIntent : null;
            const unlinking = pendingMutation?.kind === "unlink" && pendingMutation.itemKey === itemKey;
            return (
              <article key={itemKey} className="min-w-0 rounded border border-slate-100 p-3 text-sm">
                <h3 className="break-words font-medium">{itemTitle}</h3>
                <p className="mt-1 break-words text-xs text-slate-500">
                  {entry.item ? formatItemLine(entry.item) : "Metadata unavailable"} · {entry.link.relation_type}
                </p>
                {entry.link.note ? <p className="mt-2 break-words text-xs leading-5 text-slate-600">{entry.link.note}</p> : null}
                {intent ? (
                  <div
                    aria-busy={unlinking}
                    aria-describedby="zotero-unlink-consequence"
                    aria-label={`Confirm unlink ${itemTitle}`}
                    className="mt-3 rounded border border-red-200 bg-red-50 p-3"
                    data-testid="zotero-unlink-confirmation"
                    role="group"
                    onKeyDown={(event) => handleConfirmationKeyDown(event, intent)}
                  >
                    <p id="zotero-unlink-consequence" className="break-words text-xs leading-5 text-red-800 [overflow-wrap:anywhere]">
                      Remove this project link and its relationship note permanently? The Zotero library item will not be deleted.
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        ref={unlinkCancelRef}
                        aria-describedby="zotero-unlink-consequence"
                        aria-label={`Cancel unlink ${itemTitle}`}
                        className="rounded border border-slate-300 bg-white px-3 py-1 text-xs font-medium hover:bg-slate-50 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed"
                        disabled={unlinking}
                        type="button"
                        onClick={() => cancelUnlink(intent)}
                      >
                        Cancel
                      </button>
                      <button
                        aria-describedby="zotero-unlink-consequence"
                        aria-label={`Unlink ${itemTitle} permanently`}
                        className="rounded border border-red-300 bg-white px-3 py-1 text-xs font-medium text-red-800 hover:bg-red-100 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed"
                        disabled={unlinking}
                        type="button"
                        onClick={() => void confirmUnlink(intent, itemTitle)}
                      >
                        {unlinking ? "Unlinking..." : "Unlink permanently"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    ref={(node) => {
                      if (node) unlinkButtonRefs.current.set(itemKey, node);
                      else unlinkButtonRefs.current.delete(itemKey);
                    }}
                    aria-label={`Unlink ${itemTitle}`}
                    className="mt-3 rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-50 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed disabled:text-red-300"
                    disabled={mutationLocked}
                    type="button"
                    onClick={() => openUnlink(itemKey)}
                  >
                    Unlink
                  </button>
                )}
              </article>
            );
          })
        ) : null}
        {linksStatus === "ready" && !linksError && !reconciliationRequired && !links.length ? (
          <p className="text-sm text-slate-600">No related papers linked.</p>
        ) : null}
        {linksStatus === "reconciling" ? (
          <p className="text-xs text-slate-600">Reloading related papers...</p>
        ) : null}
      </div>

      <form aria-label="Search Zotero papers" className="mt-4 space-y-3" onSubmit={handleSearch}>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700" htmlFor="zotero-search-query">
            Paper title or keyword
          </label>
          <input
            id="zotero-search-query"
            className="w-full min-w-0 rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950 focus:ring-2 focus:ring-sky-700"
            placeholder="Search Zotero papers"
            value={query}
            onChange={(event) => handleQueryChange(event.target.value)}
          />
        </div>
        <div className="grid min-w-0 grid-cols-1 gap-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700" htmlFor="zotero-relation-type">
              Relationship
            </label>
            <select
              id="zotero-relation-type"
              className="w-full min-w-0 rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950 focus:ring-2 focus:ring-sky-700"
              value={relationType}
              disabled={pendingMutation?.kind === "link"}
              onChange={(event) => setRelationType(event.target.value as ZoteroRelationType)}
            >
              {relationTypes.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          <button
            className="rounded bg-slate-950 px-3 py-2 text-sm font-medium text-white focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={
              !normalizeZoteroQuery(query)
              || !providerAvailable
              || searchStatus === "loading"
                && submittedQuery === normalizeZoteroQuery(query)
            }
            type="submit"
          >
            {searchStatus === "loading" ? "Searching..." : "Search"}
          </button>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700" htmlFor="zotero-relationship-note">
            Relationship note <span className="font-normal text-slate-500">(optional)</span>
          </label>
          <textarea
            id="zotero-relationship-note"
            className="min-h-20 w-full min-w-0 resize-y rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950 focus:ring-2 focus:ring-sky-700"
            placeholder="Why this paper matters for the article"
            value={note}
            disabled={pendingMutation?.kind === "link"}
            onChange={(event) => setNote(event.target.value)}
          />
        </div>
      </form>

      <div className="mt-3 min-w-0" data-testid="zotero-search-results">
        {searchStatus === "loading" ? <p aria-live="polite" className="text-sm text-slate-600" role="status">Searching Zotero...</p> : null}
        {searchStatus === "error" && searchError ? <p className="text-sm text-red-700" role="alert">{searchError}</p> : null}
        {searchStatus === "ready" ? (
          <p aria-atomic="true" aria-live="polite" className="break-words text-xs text-slate-600 [overflow-wrap:anywhere]" role="status">
            {results.length
              ? `${results.length} paper${results.length === 1 ? "" : "s"} found for “${submittedQuery}”.`
              : `No Zotero papers matched “${submittedQuery}”.`}
          </p>
        ) : null}
        {searchStatus === "ready" && results.length ? (
          <div className="mt-2 grid min-w-0 gap-2">
            {results.map((item) => {
              const linked = linkedKeys.has(item.item_key);
              const linking = pendingMutation?.kind === "link" && pendingMutation.itemKey === item.item_key;
              return (
                <article key={item.item_key} className="min-w-0 rounded border border-slate-100 p-3 text-sm">
                  <h3 className="break-words font-medium">{item.title}</h3>
                  <p className="mt-1 break-words text-xs text-slate-500">{formatItemLine(item)}</p>
                  <button
                    ref={(node) => {
                      if (node) linkButtonRefs.current.set(item.item_key, node);
                      else linkButtonRefs.current.delete(item.item_key);
                    }}
                    aria-label={`${linked ? "Linked" : linking ? "Linking" : "Link"} ${item.title}`}
                    className="mt-3 rounded border border-slate-300 px-3 py-1 text-xs font-medium hover:bg-slate-50 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700 disabled:cursor-not-allowed disabled:text-slate-400"
                    disabled={linked || mutationLocked || !providerAvailable || !linksReady}
                    type="button"
                    onClick={() => void handleLink(item)}
                  >
                    {linked ? "Linked" : linking ? "Linking..." : "Link"}
                  </button>
                </article>
              );
            })}
          </div>
        ) : null}
      </div>

      {bibtexOpen ? (
        <div
          ref={bibtexRegionRef}
          id="linked-bibtex-region"
          aria-labelledby="linked-bibtex-title"
          className="mt-3 w-full min-w-0 max-w-full overflow-hidden rounded border border-slate-200 p-3 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-700"
          data-testid="zotero-bibtex-region"
          tabIndex={-1}
        >
          <h3 id="linked-bibtex-title" className="text-sm font-semibold">Linked-paper BibTeX</h3>
          {bibtexStatus === "loading" ? <p aria-live="polite" className="mt-2 text-xs text-slate-600" role="status">Requesting BibTeX...</p> : null}
          {bibtexStatus === "error" && bibtexError ? <p className="mt-2 text-xs text-red-700" role="alert">{bibtexError}</p> : null}
          {bibtexStatus === "ready" && bibtex ? (
            <>
              <p className="mt-2 text-xs text-slate-600">
                Provider response for {bibtexItemCount} requested link{bibtexItemCount === 1 ? "" : "s"}.
              </p>
              <pre
                aria-label="BibTeX export"
                className="mt-2 block w-full min-w-0 max-w-full overflow-x-auto rounded bg-slate-950 p-3 text-xs leading-5 text-white"
                tabIndex={0}
              >
                {bibtex}
              </pre>
            </>
          ) : null}
          {bibtexStatus === "ready" && !bibtex ? (
            <p className="mt-2 text-xs text-slate-600">No BibTeX text was returned for the requested links.</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function formatItemLine(item: ZoteroItem): string {
  const creators = item.creators.length ? item.creators.join(", ") : "Unknown creators";
  return [creators, item.year, item.publication_title].filter(Boolean).join(" · ");
}

function getLinksAnnouncement(
  status: LinksStatus,
  count: number,
  error: string | null,
  reconciliationRequired: boolean,
): string {
  if (status === "loading") return "Loading related papers.";
  if (status === "reconciling") return "Reloading related papers from project storage.";
  if (status === "error" || error || reconciliationRequired) return "";
  return count
    ? `${count} related paper${count === 1 ? "" : "s"} loaded.`
    : "No related papers are linked.";
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
