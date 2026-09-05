"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FormEvent,
  forwardRef,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { toPlainTextPreview } from "@/lib/articlePresentation";
import { createArticleDetailHref } from "@/lib/learningWorkflow";
import {
  ReferenceClassification,
  ReferenceDetail,
  ReferencePage,
  ReferenceRecord,
  ReferenceType,
  ZoteroCandidatePage,
  ZoteroMatchCandidate,
  candidateHref,
  fetchArticleReferences,
  fetchReference,
  fetchReferences,
  fetchZoteroCandidates,
  referenceErrorMessage,
  referenceHref,
} from "@/lib/references";
import {
  CandidateFilter,
  ReferenceReviewState,
  consumeCandidateFilterFocus,
  consumeReferenceDetailFocus,
  consumeReferenceResultsFocus,
  createReferenceRequestOwner,
  createReferenceReviewHref,
  ownsReferenceCandidatePage,
  ownsReferenceRequest,
  rememberCandidateFilterFocus,
  rememberReferenceDetailFocus,
  rememberReferenceResultsFocus,
  parseArticleReferenceReturnTarget,
  resolveAvailableReferencePage,
} from "@/lib/referenceReview";

type LoadState = "idle" | "loading" | "loaded" | "error";

type RequestSnapshot<T> = {
  status: LoadState;
  requestKey: string;
  data: T | null;
  error: string | null;
};

const PAGE_SIZE = 20;
const MAX_PROVENANCE_LIMIT = 20;
const candidateFilters: CandidateFilter[] = ["all", "matched", "ambiguous", "unmatched"];
const referenceTypes: Array<{ value: "" | ReferenceType; label: string }> = [
  { value: "", label: "All types" },
  { value: "doi", label: "DOI" },
  { value: "arxiv", label: "arXiv" },
  { value: "http_url", label: "Web URL" },
  { value: "relative_or_internal_url", label: "Internal URL" },
  { value: "citation_text", label: "Citation text" },
  { value: "unsupported", label: "Unsupported" },
  { value: "malformed", label: "Malformed" },
];
const classifications: Array<{ value: "" | ReferenceClassification; label: string }> = [
  { value: "", label: "All classifications" },
  { value: "extracted", label: "Extracted" },
  { value: "normalized", label: "Normalized" },
  { value: "duplicate", label: "Duplicate" },
  { value: "ambiguous", label: "Ambiguous" },
  { value: "unsupported", label: "Unsupported" },
  { value: "malformed", label: "Malformed" },
  { value: "rejected", label: "Rejected" },
];

export function ZoteroReferenceReview({
  initialState,
}: Readonly<{
  initialState: ReferenceReviewState;
}>) {
  const router = useRouter();
  const [queryDraft, setQueryDraft] = useState(initialState.q);
  const [typeDraft, setTypeDraft] = useState<"" | ReferenceType>(initialState.referenceType ?? "");
  const [classificationDraft, setClassificationDraft] = useState<"" | ReferenceClassification>(
    initialState.classification ?? "",
  );
  const [listRevision, setListRevision] = useState(0);
  const [detailRevision, setDetailRevision] = useState(0);
  const [candidateRevision, setCandidateRevision] = useState(0);
  const [returnRevision, setReturnRevision] = useState(0);
  const [navigating, setNavigating] = useState(false);
  const [referenceSnapshot, setReferenceSnapshot] = useState<RequestSnapshot<ReferencePage>>(
    emptySnapshot(""),
  );
  const [detailSnapshot, setDetailSnapshot] = useState<RequestSnapshot<ReferenceDetail>>(
    emptySnapshot(""),
  );
  const [candidateSnapshot, setCandidateSnapshot] = useState<RequestSnapshot<ZoteroCandidatePage>>(
    emptySnapshot(""),
  );
  const [returnSnapshot, setReturnSnapshot] = useState<RequestSnapshot<string>>(
    emptySnapshot(""),
  );
  const listGeneration = useRef(0);
  const detailGeneration = useRef(0);
  const candidateGeneration = useRef(0);
  const returnGeneration = useRef(0);
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);
  const selectedReferenceRegionRef = useRef<HTMLElement>(null);
  const detailRegionRef = useRef<HTMLElement>(null);
  const detailErrorRef = useRef<HTMLDivElement>(null);

  const listRequestKey = JSON.stringify([
    initialState.q,
    initialState.referenceType,
    initialState.classification,
    initialState.page,
    listRevision,
  ]);
  const detailRequestKey = `${initialState.referenceId ?? ""}:${detailRevision}`;
  const candidateRequestKey = `${initialState.referenceId ?? ""}:${candidateRevision}`;
  const canonicalHref = createReferenceReviewHref(initialState);
  const returnTarget = useMemo(
    () => initialState.referenceId
      ? parseArticleReferenceReturnTarget(initialState.returnTo, initialState.referenceId)
      : null,
    [initialState.referenceId, initialState.returnTo],
  );
  const returnRequestKey = returnTarget && initialState.referenceId
    ? JSON.stringify([
        initialState.referenceId,
        returnTarget.articleId,
        returnTarget.referencePage,
        returnTarget.path,
        returnRevision,
      ])
    : "";

  useEffect(() => {
    setQueryDraft(initialState.q);
    setTypeDraft(initialState.referenceType ?? "");
    setClassificationDraft(initialState.classification ?? "");
  }, [initialState.classification, initialState.q, initialState.referenceType]);

  useEffect(() => {
    setNavigating(false);
  }, [canonicalHref]);

  useEffect(() => {
    const generation = listGeneration.current + 1;
    listGeneration.current = generation;
    const owner = createReferenceRequestOwner(generation, listRequestKey);
    let active = true;
    setReferenceSnapshot({
      status: "loading",
      requestKey: listRequestKey,
      data: null,
      error: null,
    });

    fetchReferences({
      page: initialState.page,
      pageSize: PAGE_SIZE,
      referenceType: initialState.referenceType ?? undefined,
      classification: initialState.classification ?? undefined,
      query: initialState.q,
    })
      .then((response) => {
        if (active && ownsReferenceRequest(owner, listGeneration.current, listRequestKey)) {
          setReferenceSnapshot({
            status: "loaded",
            requestKey: listRequestKey,
            data: response,
            error: null,
          });
        }
      })
      .catch((reason) => {
        if (active && ownsReferenceRequest(owner, listGeneration.current, listRequestKey)) {
          setReferenceSnapshot({
            status: "error",
            requestKey: listRequestKey,
            data: null,
            error: referenceErrorMessage(reason),
          });
        }
      });

    return () => {
      active = false;
      if (listGeneration.current === generation) {
        listGeneration.current += 1;
      }
    };
  }, [initialState.classification, initialState.page, initialState.q, initialState.referenceType, listRequestKey]);

  useEffect(() => {
    if (!initialState.referenceId) {
      setDetailSnapshot(emptySnapshot(""));
      setCandidateSnapshot(emptySnapshot(""));
      return;
    }

    const generation = detailGeneration.current + 1;
    detailGeneration.current = generation;
    const owner = createReferenceRequestOwner(generation, detailRequestKey);
    let active = true;
    setDetailSnapshot({
      status: "loading",
      requestKey: detailRequestKey,
      data: null,
      error: null,
    });

    fetchReference(initialState.referenceId, MAX_PROVENANCE_LIMIT)
      .then((response) => {
        if (!active || !ownsReferenceRequest(owner, detailGeneration.current, detailRequestKey)) {
          return;
        }
        if (response.record.reference_id !== initialState.referenceId) {
          setDetailSnapshot({
            status: "error",
            requestKey: detailRequestKey,
            data: null,
            error: "The selected reference response had an unexpected identity.",
          });
          return;
        }
        setDetailSnapshot({
          status: "loaded",
          requestKey: detailRequestKey,
          data: response,
          error: null,
        });
      })
      .catch((reason) => {
        if (active && ownsReferenceRequest(owner, detailGeneration.current, detailRequestKey)) {
          setDetailSnapshot({
            status: "error",
            requestKey: detailRequestKey,
            data: null,
            error: referenceErrorMessage(reason),
          });
        }
      });

    return () => {
      active = false;
      if (detailGeneration.current === generation) {
        detailGeneration.current += 1;
      }
    };
  }, [detailRequestKey, initialState.referenceId]);

  useEffect(() => {
    if (!initialState.referenceId) {
      setCandidateSnapshot(emptySnapshot(""));
      return;
    }

    const generation = candidateGeneration.current + 1;
    candidateGeneration.current = generation;
    const owner = createReferenceRequestOwner(generation, candidateRequestKey);
    let active = true;
    setCandidateSnapshot({
      status: "loading",
      requestKey: candidateRequestKey,
      data: null,
      error: null,
    });

    fetchZoteroCandidates(initialState.referenceId, { limit: 20 })
      .then((response) => {
        if (!active || !ownsReferenceRequest(owner, candidateGeneration.current, candidateRequestKey)) {
          return;
        }
        if (!ownsReferenceCandidatePage(response, initialState.referenceId)) {
          setCandidateSnapshot({
            status: "error",
            requestKey: candidateRequestKey,
            data: null,
            error: "The Zotero candidate response had an unexpected reference identity.",
          });
          return;
        }
        setCandidateSnapshot({
          status: "loaded",
          requestKey: candidateRequestKey,
          data: response,
          error: null,
        });
      })
      .catch((reason) => {
        if (active && ownsReferenceRequest(owner, candidateGeneration.current, candidateRequestKey)) {
          setCandidateSnapshot({
            status: "error",
            requestKey: candidateRequestKey,
            data: null,
            error: referenceErrorMessage(reason),
          });
        }
      });

    return () => {
      active = false;
      if (candidateGeneration.current === generation) {
        candidateGeneration.current += 1;
      }
    };
  }, [candidateRequestKey, initialState.referenceId]);

  useEffect(() => {
    if (!initialState.referenceId || !returnTarget) {
      setReturnSnapshot(emptySnapshot(""));
      return;
    }

    const generation = returnGeneration.current + 1;
    returnGeneration.current = generation;
    const owner = createReferenceRequestOwner(generation, returnRequestKey);
    let active = true;
    setReturnSnapshot({
      status: "loading",
      requestKey: returnRequestKey,
      data: null,
      error: null,
    });

    fetchArticleReferences(returnTarget.articleId, {
      page: returnTarget.referencePage,
      pageSize: PAGE_SIZE,
    })
      .then((response) => {
        if (!active || !ownsReferenceRequest(owner, returnGeneration.current, returnRequestKey)) {
          return;
        }
        const ownsReturn = response.article_id === returnTarget.articleId
          && response.page === returnTarget.referencePage
          && response.items.some(
            (record) => record.reference_id === initialState.referenceId,
          );
        setReturnSnapshot({
          status: "loaded",
          requestKey: returnRequestKey,
          data: ownsReturn ? returnTarget.path : null,
          error: ownsReturn
            ? null
            : "The originating Article no longer contains this reference on the saved page.",
        });
      })
      .catch((reason) => {
        if (active && ownsReferenceRequest(owner, returnGeneration.current, returnRequestKey)) {
          setReturnSnapshot({
            status: "error",
            requestKey: returnRequestKey,
            data: null,
            error: referenceErrorMessage(reason),
          });
        }
      });

    return () => {
      active = false;
      if (returnGeneration.current === generation) {
        returnGeneration.current += 1;
      }
    };
  }, [initialState.referenceId, returnRequestKey, returnTarget]);

  const referencePage = referenceSnapshot.requestKey === listRequestKey
    ? referenceSnapshot.data
    : null;
  const availablePage = referencePage
    ? resolveAvailableReferencePage(initialState.page, referencePage.total_pages)
    : initialState.page;
  const pageNeedsCorrection = Boolean(
    referencePage && availablePage !== initialState.page,
  );

  useEffect(() => {
    if (!pageNeedsCorrection) {
      return;
    }
    rememberReferenceResultsFocus();
    listGeneration.current += 1;
    setReferenceSnapshot(emptySnapshot(""));
    setNavigating(true);
    router.replace(createReferenceReviewHref({ ...initialState, page: availablePage }));
  }, [availablePage, initialState, pageNeedsCorrection, router]);

  useEffect(() => {
    if (
      !["loaded", "error"].includes(referenceSnapshot.status)
      || !consumeReferenceResultsFocus()
    ) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      const target = resultsHeadingRef.current;
      target?.scrollIntoView({ block: "nearest" });
      target?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [referenceSnapshot.status]);

  useEffect(() => {
    if (
      !["loaded", "error"].includes(detailSnapshot.status)
      || !initialState.referenceId
      || !consumeReferenceDetailFocus(initialState.referenceId)
    ) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      const target = detailSnapshot.status === "loaded"
        ? detailRegionRef.current
        : detailErrorRef.current;
      target?.scrollIntoView({ block: "start" });
      target?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [detailSnapshot.status, initialState.referenceId]);

  useEffect(() => {
    if (
      detailSnapshot.status !== "loaded"
      || candidateSnapshot.status === "loading"
      || !consumeCandidateFilterFocus(initialState.candidateFilter)
    ) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      const target = document.getElementById(`candidate-filter-${initialState.candidateFilter}`);
      target?.scrollIntoView({ block: "center" });
      target?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [candidateSnapshot.status, detailSnapshot.status, initialState.candidateFilter]);

  const detail = detailSnapshot.requestKey === detailRequestKey
    ? detailSnapshot.data
    : null;
  const candidatePage = candidateSnapshot.requestKey === candidateRequestKey
    && ownsReferenceCandidatePage(candidateSnapshot.data, initialState.referenceId)
    ? candidateSnapshot.data
    : null;
  const ownedReturnPath = returnSnapshot.requestKey === returnRequestKey
    ? returnSnapshot.data
    : null;
  const ownedReturnStatus = returnSnapshot.requestKey === returnRequestKey
    ? returnSnapshot.status
    : "idle";
  const ownedReturnError = returnSnapshot.requestKey === returnRequestKey
    ? returnSnapshot.error
    : null;
  const visibleCandidates = useMemo(
    () => (candidatePage?.items ?? []).filter((candidate) => matchesFilter(candidate, initialState.candidateFilter)),
    [candidatePage, initialState.candidateFilter],
  );
  const selectedOnPage = Boolean(
    initialState.referenceId
    && referencePage?.items.some((record) => record.reference_id === initialState.referenceId),
  );

  function navigate(nextState: ReferenceReviewState, focus: "results" | "detail" | "candidate"): void {
    const href = createReferenceReviewHref(nextState);
    if (href === canonicalHref) {
      if (focus === "results") {
        rememberReferenceResultsFocus();
        setListRevision((current) => current + 1);
      } else if (focus === "detail") {
        if (nextState.referenceId) {
          rememberReferenceDetailFocus(nextState.referenceId);
        }
        setDetailRevision((current) => current + 1);
        setCandidateRevision((current) => current + 1);
      }
      return;
    }
    if (focus === "results") {
      rememberReferenceResultsFocus();
    } else if (focus === "detail" && nextState.referenceId) {
      rememberReferenceDetailFocus(nextState.referenceId);
    } else if (focus === "candidate") {
      rememberCandidateFilterFocus(nextState.candidateFilter);
    }
    const listStateChanged = nextState.q !== initialState.q
      || nextState.referenceType !== initialState.referenceType
      || nextState.classification !== initialState.classification
      || nextState.page !== initialState.page;
    if (listStateChanged) {
      listGeneration.current += 1;
      setReferenceSnapshot(emptySnapshot(""));
    }
    if (nextState.referenceId !== initialState.referenceId) {
      detailGeneration.current += 1;
      candidateGeneration.current += 1;
      returnGeneration.current += 1;
      setDetailSnapshot(emptySnapshot(""));
      setCandidateSnapshot(emptySnapshot(""));
      setReturnSnapshot(emptySnapshot(""));
    }
    setNavigating(true);
    router.push(href);
  }

  function retryReferenceResults(): void {
    focusReviewTarget(resultsHeadingRef.current, "nearest");
    rememberReferenceResultsFocus();
    setListRevision((current) => current + 1);
  }

  function retrySelectedReference(): void {
    focusReviewTarget(selectedReferenceRegionRef.current, "start");
    if (initialState.referenceId) {
      rememberReferenceDetailFocus(initialState.referenceId);
    }
    setDetailRevision((current) => current + 1);
  }

  function retryZoteroCandidates(): void {
    focusReviewTarget(
      document.getElementById(`candidate-filter-${initialState.candidateFilter}`),
      "center",
    );
    rememberCandidateFilterFocus(initialState.candidateFilter);
    setCandidateRevision((current) => current + 1);
  }

  function retryArticleReturn(): void {
    focusReviewTarget(detailRegionRef.current, "start");
    setReturnRevision((current) => current + 1);
  }

  function handleFilterSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    navigate(
      {
        q: queryDraft,
        referenceType: typeDraft || null,
        classification: classificationDraft || null,
        page: 1,
        referenceId: null,
        candidateFilter: "all",
        returnTo: null,
      },
      "results",
    );
  }

  function clearFilters(): void {
    setQueryDraft("");
    setTypeDraft("");
    setClassificationDraft("");
    navigate(
      {
        q: "",
        referenceType: null,
        classification: null,
        page: 1,
        referenceId: null,
        candidateFilter: "all",
        returnTo: null,
      },
      "results",
    );
  }

  function selectReference(referenceId: string): void {
    navigate(
      {
        ...initialState,
        referenceId,
        candidateFilter: "all",
      },
      "detail",
    );
  }

  function changePage(page: number): void {
    navigate(
      {
        ...initialState,
        page,
        referenceId: null,
        candidateFilter: "all",
        returnTo: null,
      },
      "results",
    );
  }

  function changeCandidateFilter(filter: CandidateFilter): void {
    navigate({ ...initialState, candidateFilter: filter }, "candidate");
  }

  return (
    <section
      className="border-y border-slate-200 bg-white py-6"
      aria-busy={navigating || referenceSnapshot.status === "loading"}
      aria-labelledby="reference-candidates-heading"
      data-testid="reference-review-workspace"
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="reference-candidates-heading" className="text-lg font-semibold">
              Structured Reference Review
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
              Find extracted sources, inspect Article evidence, and review bounded Zotero match candidates.
            </p>
          </div>
          {referencePage ? (
            <span className="text-xs text-slate-500" aria-live="polite">
              {referencePage.total} references
            </span>
          ) : null}
        </div>

        <form className="grid gap-3 border-y border-slate-200 py-4 md:grid-cols-[minmax(0,1fr)_12rem_12rem_auto]" onSubmit={handleFilterSubmit}>
          <label className="grid min-w-0 gap-1 text-sm font-medium" htmlFor="reference-query">
            Search references
            <input
              id="reference-query"
              className="min-w-0 border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-950 focus-visible:ring-2 focus-visible:ring-sky-600"
              placeholder="Identifier, evidence, Article"
              value={queryDraft}
              onChange={(event) => setQueryDraft(event.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm font-medium" htmlFor="reference-type">
            Type
            <select
              id="reference-type"
              className="border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-950 focus-visible:ring-2 focus-visible:ring-sky-600"
              value={typeDraft}
              onChange={(event) => setTypeDraft(event.target.value as "" | ReferenceType)}
            >
              {referenceTypes.map((option) => (
                <option key={option.value || "all"} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-medium" htmlFor="reference-classification">
            Classification
            <select
              id="reference-classification"
              className="border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-950 focus-visible:ring-2 focus-visible:ring-sky-600"
              value={classificationDraft}
              onChange={(event) => setClassificationDraft(event.target.value as "" | ReferenceClassification)}
            >
              {classifications.map((option) => (
                <option key={option.value || "all"} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <div className="flex items-end gap-2">
            <button
              aria-label="Search structured references"
              className="border border-slate-950 bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 disabled:cursor-wait disabled:opacity-60"
              disabled={navigating}
              type="submit"
            >
              Search
            </button>
            <button
              className="border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-slate-950 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 disabled:cursor-wait disabled:opacity-60"
              disabled={navigating || (!queryDraft && !typeDraft && !classificationDraft)}
              type="button"
              onClick={clearFilters}
            >
              Clear
            </button>
          </div>
        </form>

        <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(16rem,0.85fr)_minmax(0,1.35fr)]">
          <section
            className="min-w-0"
            aria-busy={referenceSnapshot.status === "loading"}
            aria-labelledby="reference-results-heading"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3
                ref={resultsHeadingRef}
                id="reference-results-heading"
                className="text-base font-semibold outline-none focus:ring-2 focus:ring-sky-600"
                tabIndex={-1}
              >
                Reference results
              </h3>
              {referencePage && !pageNeedsCorrection ? (
                <span className="text-xs text-slate-500">
                  Page {referencePage.page} of {Math.max(referencePage.total_pages, 1)}
                </span>
              ) : null}
            </div>

            {referenceSnapshot.status === "loading" ? (
              <p className="mt-3 text-sm text-slate-600" role="status" aria-live="polite">
                Loading reference results...
              </p>
            ) : null}
            {referenceSnapshot.status === "error" ? (
              <div className="mt-3 border-l-2 border-amber-500 bg-amber-50 px-3 py-3 text-sm text-amber-900" role="alert">
                <p>{referenceSnapshot.error}</p>
                <button className="mt-2 font-medium underline underline-offset-2" type="button" onClick={retryReferenceResults}>
                  Retry reference results
                </button>
              </div>
            ) : null}
            {pageNeedsCorrection ? (
              <p className="mt-3 text-sm text-slate-600" role="status" aria-live="polite">
                Requested page is unavailable. Loading page {availablePage}...
              </p>
            ) : null}
            {referenceSnapshot.status === "loaded" && !pageNeedsCorrection && referencePage?.items.length === 0 ? (
              <p className="mt-3 text-sm text-slate-600" role="status" aria-live="polite">No references match these filters.</p>
            ) : null}

            {!pageNeedsCorrection && referencePage?.items.length ? (
              <ul className="mt-3 divide-y divide-slate-200 border-y border-slate-200" data-testid="reference-result-list">
                {referencePage.items.map((record) => (
                  <li key={record.reference_id}>
                    <button
                      className={
                        record.reference_id === initialState.referenceId
                          ? "w-full min-w-0 border-l-2 border-sky-700 bg-sky-50 px-3 py-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-600"
                          : "w-full min-w-0 border-l-2 border-transparent px-3 py-3 text-left hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-600"
                      }
                      type="button"
                      disabled={navigating}
                      data-reference-id={record.reference_id}
                      aria-current={record.reference_id === initialState.referenceId ? "true" : undefined}
                      aria-label={`Review ${referenceIdentity(record)}`}
                      onClick={() => selectReference(record.reference_id)}
                    >
                      <span className="block break-words text-sm font-medium text-slate-900 [overflow-wrap:anywhere]">
                        {referenceLabel(referenceIdentity(record))}
                      </span>
                      <span className="mt-1 block text-xs text-slate-500">
                        {formatReferenceType(record.reference_type)} · {record.classification}
                      </span>
                      <span className="mt-1 block truncate text-xs text-slate-500">
                        {record.source_article_title}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}

            {referencePage && !pageNeedsCorrection && referencePage.total_pages > 1 ? (
              <nav className="mt-4 flex items-center justify-between gap-3" aria-label="Reference result pages">
                <button
                  className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
                  disabled={!referencePage.has_previous || navigating}
                  type="button"
                  onClick={() => changePage(Math.max(1, referencePage.page - 1))}
                >
                  Previous
                </button>
                <span className="text-xs text-slate-500">{referencePage.total} total</span>
                <button
                  className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
                  disabled={!referencePage.has_next || navigating}
                  type="button"
                  onClick={() => changePage(referencePage.page + 1)}
                >
                  Next
                </button>
              </nav>
            ) : null}
          </section>

          <section
            ref={selectedReferenceRegionRef}
            className="min-w-0 scroll-mt-24 border-t border-slate-200 pt-5 outline-none focus:ring-2 focus:ring-sky-600 focus:ring-offset-4 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0"
            aria-busy={
              detailSnapshot.status === "loading"
              || candidateSnapshot.status === "loading"
              || ownedReturnStatus === "loading"
            }
            aria-labelledby="selected-reference-heading"
            data-testid="selected-reference-region"
            tabIndex={-1}
          >
            {!initialState.referenceId ? (
              <div className="border-l-2 border-slate-300 pl-4 text-sm text-slate-600">
                <h3 id="selected-reference-heading" className="font-semibold text-slate-900">Select a reference</h3>
                <p className="mt-1">Choose a result to inspect its source evidence and bounded Zotero candidates.</p>
              </div>
            ) : null}
            {initialState.referenceId && !selectedOnPage && referencePage ? (
              <p className="mb-4 border-l-2 border-sky-600 bg-sky-50 px-3 py-2 text-xs text-sky-900">
                The selected deep-linked reference is outside this result page and remains available below.
              </p>
            ) : null}
            {initialState.referenceId && (detailSnapshot.status === "loading" || (navigating && detailSnapshot.status === "idle")) ? (
              <div role="status" aria-live="polite">
                <h3 id="selected-reference-heading" className="sr-only">Selected reference</h3>
                <p className="text-sm text-slate-600">Loading selected reference...</p>
              </div>
            ) : null}
            {initialState.referenceId && detailSnapshot.status === "error" ? (
              <div
                ref={detailErrorRef}
                className="scroll-mt-24 border-l-2 border-amber-500 bg-amber-50 px-3 py-3 text-sm text-amber-900 outline-none focus:ring-2 focus:ring-sky-600 focus:ring-offset-4"
                role="alert"
                tabIndex={-1}
              >
                <h3 id="selected-reference-heading" className="sr-only">Selected reference unavailable</h3>
                <p>{detailSnapshot.error}</p>
                <button className="mt-2 font-medium underline underline-offset-2" type="button" onClick={retrySelectedReference}>
                  Retry selected reference
                </button>
              </div>
            ) : null}
            {detail ? (
              <ReferenceDetailWorkspace
                ref={detailRegionRef}
                candidateFilter={initialState.candidateFilter}
                candidatePage={candidatePage}
                candidateSnapshot={candidateSnapshot}
                detail={detail}
                hasReturnTarget={Boolean(returnTarget)}
                ownedReturnError={ownedReturnError}
                ownedReturnPath={ownedReturnPath}
                ownedReturnStatus={ownedReturnStatus}
                visibleCandidates={visibleCandidates}
                onCandidateFilter={changeCandidateFilter}
                onRetryArticleReturn={retryArticleReturn}
                onRetryCandidates={retryZoteroCandidates}
                navigating={navigating}
              />
            ) : null}
          </section>
        </div>
      </div>
    </section>
  );
}

const ReferenceDetailWorkspace = forwardRef<HTMLElement, {
  detail: ReferenceDetail;
  hasReturnTarget: boolean;
  ownedReturnError: string | null;
  ownedReturnPath: string | null;
  ownedReturnStatus: LoadState;
  candidateFilter: CandidateFilter;
  candidatePage: ZoteroCandidatePage | null;
  candidateSnapshot: RequestSnapshot<ZoteroCandidatePage>;
  visibleCandidates: ZoteroMatchCandidate[];
  onCandidateFilter: (filter: CandidateFilter) => void;
  onRetryArticleReturn: () => void;
  onRetryCandidates: () => void;
  navigating: boolean;
}>(function ReferenceDetailWorkspace({
  detail,
  hasReturnTarget,
  ownedReturnError,
  ownedReturnPath,
  ownedReturnStatus,
  candidateFilter,
  candidatePage,
  candidateSnapshot,
  visibleCandidates,
  onCandidateFilter,
  onRetryArticleReturn,
  onRetryCandidates,
  navigating,
}, ref) {
  const record = detail.record;
  const href = referenceHref(record);
  const identity = referenceIdentity(record);

  return (
    <article
      ref={ref}
      className="min-w-0 scroll-mt-24 outline-none focus:ring-2 focus:ring-sky-600 focus:ring-offset-4"
      aria-labelledby="selected-reference-heading"
      data-reference-id={record.reference_id}
      data-testid="selected-reference-detail"
      tabIndex={-1}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase text-sky-800">Selected reference</p>
          <h3 id="selected-reference-heading" className="mt-1 break-words text-lg font-semibold [overflow-wrap:anywhere]">
            {href ? (
              <a className="underline decoration-slate-300 underline-offset-4 hover:text-sky-700" href={href} rel="noopener noreferrer" target="_blank">
                {identity}
              </a>
            ) : identity}
          </h3>
        </div>
        {ownedReturnPath ? (
          <Link
            className="border border-slate-300 px-3 py-2 text-sm font-medium text-slate-800 hover:border-slate-950 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
            href={ownedReturnPath}
          >
            Back to source reference
          </Link>
        ) : (
          <div className="flex max-w-sm flex-col items-start gap-2">
            {!hasReturnTarget || ownedReturnStatus !== "loading" ? (
              <Link
                className="border border-slate-300 px-3 py-2 text-sm font-medium text-slate-800 hover:border-slate-950 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
                href={createArticleDetailHref(record.source_article_id)}
              >
                Open primary source Article
              </Link>
            ) : null}
            {hasReturnTarget && ownedReturnStatus === "loading" ? (
              <span className="text-xs text-slate-500" role="status" aria-live="polite">
                Verifying originating Article return...
              </span>
            ) : null}
            {hasReturnTarget && ownedReturnStatus === "loaded" && ownedReturnError ? (
              <span className="text-xs text-amber-700" role="status" aria-live="polite">
                {ownedReturnError}
              </span>
            ) : null}
            {hasReturnTarget && ownedReturnStatus === "error" ? (
              <span className="text-xs text-amber-700" role="alert">
                Return verification failed: {ownedReturnError}
                <button
                  className="ml-2 font-medium underline underline-offset-2"
                  type="button"
                  onClick={onRetryArticleReturn}
                >
                  Retry return verification
                </button>
              </span>
            ) : null}
          </div>
        )}
      </div>

      <dl className="mt-4 grid gap-3 border-y border-slate-200 py-4 text-sm sm:grid-cols-2">
        <div className="min-w-0">
          <dt className="text-xs text-slate-500">Source Article</dt>
          <dd className="mt-1 break-words font-medium">{record.source_article_title}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs text-slate-500">Section</dt>
          <dd className="mt-1 break-words">{record.source_section || "Article root"}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Type and classification</dt>
          <dd className="mt-1">{formatReferenceType(record.reference_type)} · {record.classification}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Observed sources</dt>
          <dd className="mt-1">{record.source_count}</dd>
        </div>
      </dl>

      <section className="mt-5" aria-labelledby="reference-evidence-heading">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h4 id="reference-evidence-heading" className="text-sm font-semibold">Article evidence</h4>
          <span className="text-xs text-slate-500">
            {detail.evidence_total} occurrence{detail.evidence_total === 1 ? "" : "s"}
          </span>
        </div>
        <p className="mt-2 break-words border-l-2 border-sky-600 pl-3 text-sm leading-6 text-slate-700 [overflow-wrap:anywhere]">
          {toPlainTextPreview(record.evidence_text, 700) || "No readable evidence preview is available."}
        </p>
        <details className="mt-3 text-sm text-slate-600">
          <summary className="w-fit cursor-pointer font-medium text-slate-700 hover:text-sky-700">Show provenance occurrences</summary>
          <ol className="mt-3 space-y-3">
            {detail.evidence.map((evidence, index) => (
              <li key={evidence.evidence_id} className="min-w-0 border-l-2 border-slate-200 pl-3">
                <p className="text-xs text-slate-500">
                  {index + 1}.{" "}
                  <Link
                    className="break-words underline underline-offset-2 hover:text-sky-700 [overflow-wrap:anywhere]"
                    href={createArticleDetailHref(evidence.source_article_id)}
                  >
                    {evidence.source_article_title || evidence.source_article_id}
                  </Link>
                  {" · "}{evidence.source_section || "Article root"}
                </p>
                <p className="mt-1 break-words leading-6 [overflow-wrap:anywhere]">{evidence.evidence_text}</p>
              </li>
            ))}
          </ol>
          {detail.provenance_truncated ? (
            <p className="mt-3 text-xs text-slate-500">
              Showing the API-bounded {detail.evidence.length} of {detail.evidence_total} occurrences; the complete count remains visible.
            </p>
          ) : null}
        </details>
      </section>

      <section
        className="mt-6 border-t border-slate-200 pt-5"
        aria-busy={candidateSnapshot.status === "loading"}
        aria-labelledby="zotero-candidate-heading"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h4 id="zotero-candidate-heading" className="text-sm font-semibold">Zotero match candidates</h4>
          {candidatePage ? <span className="text-xs text-slate-500">{candidatePage.total} candidates</span> : null}
        </div>
        <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Candidate result filter">
          {candidateFilters.map((filter) => (
            <button
              key={filter}
              id={`candidate-filter-${filter}`}
              className={
                candidateFilter === filter
                  ? "border border-slate-950 bg-slate-950 px-3 py-2 text-xs font-medium text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
                  : "border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
              }
              type="button"
              disabled={navigating}
              aria-pressed={candidateFilter === filter}
              onClick={() => onCandidateFilter(filter)}
            >
              {candidateFilterLabel(filter)}
            </button>
          ))}
        </div>

        {candidateSnapshot.status === "loading" ? (
          <p className="mt-3 text-sm text-slate-600" role="status" aria-live="polite">Loading Zotero candidates...</p>
        ) : null}
        {candidateSnapshot.status === "error" ? (
          <div className="mt-3 border-l-2 border-amber-500 bg-amber-50 px-3 py-3 text-sm text-amber-900" role="alert">
            <p>{candidateSnapshot.error}</p>
            <button className="mt-2 font-medium underline underline-offset-2" type="button" onClick={onRetryCandidates}>
              Retry Zotero candidates
            </button>
          </div>
        ) : null}
        {candidateSnapshot.status === "loaded" && candidatePage && candidatePage.total === 0 ? (
          <p className="mt-3 text-sm text-slate-600" role="status" aria-live="polite">No Zotero match candidates were recorded for this reference.</p>
        ) : null}
        {candidateSnapshot.status === "loaded" && candidatePage && candidatePage.total > 0 && visibleCandidates.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600" role="status" aria-live="polite">
            No candidates in the loaded bounded set match the selected result filter.
          </p>
        ) : null}
        {visibleCandidates.length ? (
          <ul className="mt-3 divide-y divide-slate-200 border-y border-slate-200" data-testid="candidate-result-list">
            {visibleCandidates.map((candidate) => (
              <li key={candidate.candidate_id} className="py-4">
                <CandidateRow candidate={candidate} />
              </li>
            ))}
          </ul>
        ) : null}
        {candidatePage?.truncated ? (
          <p className="mt-3 text-xs text-slate-500">Showing the first {candidatePage.limit} of {candidatePage.total} bounded candidates.</p>
        ) : null}
      </section>
    </article>
  );
});

function CandidateRow({ candidate }: Readonly<{ candidate: ZoteroMatchCandidate }>) {
  const href = candidateHref(candidate);
  const title = candidate.title ?? candidate.doi ?? candidate.arxiv_id ?? "No Zotero match";

  return (
    <article className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className="border border-slate-300 px-2 py-1 text-xs font-medium">{candidate.decision}</span>
        <span className="text-xs text-slate-500">{candidate.match_method.replaceAll("_", " ")}</span>
        <span className="text-xs text-slate-500">score {candidate.match_score.toFixed(2)}</span>
      </div>
      <h5 className="mt-2 break-words text-sm font-medium [overflow-wrap:anywhere]">
        {href ? (
          <a className="underline underline-offset-2 hover:text-sky-700" href={href} rel="noopener noreferrer" target="_blank">{title}</a>
        ) : title}
      </h5>
      <p className="mt-2 break-words text-xs text-slate-500 [overflow-wrap:anywhere]">
        Matched: {candidate.matched_fields.join(", ") || "none"}
      </p>
      {candidate.conflicting_fields.length ? (
        <p className="mt-1 break-words text-xs text-amber-700 [overflow-wrap:anywhere]">
          Conflicts: {candidate.conflicting_fields.join(", ")}
        </p>
      ) : null}
    </article>
  );
}

function matchesFilter(candidate: ZoteroMatchCandidate, filter: CandidateFilter): boolean {
  if (filter === "all") {
    return true;
  }
  if (filter === "matched") {
    return candidate.decision === "exact" || candidate.decision === "probable";
  }
  if (filter === "ambiguous") {
    return candidate.decision === "ambiguous" || candidate.decision === "rejected";
  }
  return candidate.decision === "unmatched";
}

function focusReviewTarget(
  target: HTMLElement | null,
  block: ScrollLogicalPosition,
): void {
  target?.scrollIntoView({ block });
  target?.focus({ preventScroll: true });
}

function emptySnapshot<T>(requestKey: string): RequestSnapshot<T> {
  return { status: "idle", requestKey, data: null, error: null };
}

function referenceIdentity(record: ReferenceRecord): string {
  return record.normalized_identifier
    ?? record.normalized_url
    ?? toPlainTextPreview(record.evidence_text, 180)
    ?? "Unidentified reference";
}

function referenceLabel(value: string): string {
  return value.length <= 120 ? value : `${value.slice(0, 119).trimEnd()}…`;
}

function formatReferenceType(value: ReferenceType): string {
  return value.replaceAll("_", " ");
}

function candidateFilterLabel(value: CandidateFilter): string {
  const labels: Record<CandidateFilter, string> = {
    all: "All",
    matched: "Matched",
    ambiguous: "Needs review",
    unmatched: "Unmatched",
  };
  return labels[value];
}
