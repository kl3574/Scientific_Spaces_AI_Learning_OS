"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ReferencePage,
  ZoteroCandidatePage,
  ZoteroMatchCandidate,
  candidateHref,
  fetchReferences,
  fetchZoteroCandidates,
  referenceErrorMessage,
} from "@/lib/references";

type CandidateFilter = "all" | "matched" | "ambiguous" | "unmatched";

const filters: CandidateFilter[] = ["all", "matched", "ambiguous", "unmatched"];

export function ZoteroReferenceReview() {
  const [referencePage, setReferencePage] = useState<ReferencePage | null>(null);
  const [page, setPage] = useState(1);
  const [selectedReference, setSelectedReference] = useState("");
  const [candidatePage, setCandidatePage] = useState<ZoteroCandidatePage | null>(null);
  const [filter, setFilter] = useState<CandidateFilter>("all");
  const [loadingReferences, setLoadingReferences] = useState(true);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoadingReferences(true);
    setError(null);
    fetchReferences({ page, pageSize: 20 })
      .then((response) => {
        if (!active) {
          return;
        }
        setReferencePage(response);
        setSelectedReference((current) => {
          if (response.items.some((item) => item.reference_id === current)) {
            return current;
          }
          return response.items[0]?.reference_id ?? "";
        });
      })
      .catch((reason) => {
        if (active) {
          setError(referenceErrorMessage(reason));
          setReferencePage(null);
          setSelectedReference("");
        }
      })
      .finally(() => {
        if (active) {
          setLoadingReferences(false);
        }
      });
    return () => {
      active = false;
    };
  }, [page]);

  useEffect(() => {
    if (!selectedReference) {
      setCandidatePage(null);
      return;
    }
    let active = true;
    setLoadingCandidates(true);
    setError(null);
    fetchZoteroCandidates(selectedReference, { limit: 20 })
      .then((response) => {
        if (active) {
          setCandidatePage(response);
        }
      })
      .catch((reason) => {
        if (active) {
          setError(referenceErrorMessage(reason));
          setCandidatePage(null);
        }
      })
      .finally(() => {
        if (active) {
          setLoadingCandidates(false);
        }
      });
    return () => {
      active = false;
    };
  }, [selectedReference]);

  const visibleCandidates = useMemo(
    () => (candidatePage?.items ?? []).filter((candidate) => matchesFilter(candidate, filter)),
    [candidatePage, filter],
  );

  return (
    <section className="border-y border-slate-200 bg-white py-5">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-lg font-semibold">Reference Candidates</h2>
          {referencePage ? <span className="text-xs text-slate-500">{referencePage.total} references</span> : null}
        </div>

        {loadingReferences ? <p className="text-sm text-slate-600">Loading references...</p> : null}
        {error ? <p className="border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-sm text-amber-800">{error}</p> : null}
        {!loadingReferences && !error && referencePage?.items.length === 0 ? (
          <p className="text-sm text-slate-600">No references are available for review.</p>
        ) : null}

        {referencePage?.items.length ? (
          <>
            <label className="grid gap-2 text-sm font-medium">
              Reference
              <select
                className="w-full border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-950"
                value={selectedReference}
                onChange={(event) => setSelectedReference(event.target.value)}
              >
                {referencePage.items.map((record) => (
                  <option key={record.reference_id} value={record.reference_id}>
                    {referenceLabel(record.normalized_identifier ?? record.normalized_url ?? record.evidence_text)}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Candidate filter">
              {filters.map((value) => (
                <button
                  key={value}
                  className={
                    filter === value
                      ? "border border-slate-950 bg-slate-950 px-3 py-2 text-xs font-medium text-white"
                      : "border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  }
                  type="button"
                  onClick={() => setFilter(value)}
                >
                  {value}
                </button>
              ))}
            </div>
          </>
        ) : null}

        {loadingCandidates ? <p className="text-sm text-slate-600">Loading candidates...</p> : null}
        {!loadingCandidates && selectedReference && !error && visibleCandidates.length === 0 ? (
          <p className="text-sm text-slate-600">No candidates match this filter.</p>
        ) : null}

        {visibleCandidates.length ? (
          <ul className="divide-y divide-slate-200 border-y border-slate-200">
            {visibleCandidates.map((candidate) => (
              <li key={candidate.candidate_id} className="py-4">
                <CandidateRow candidate={candidate} />
              </li>
            ))}
          </ul>
        ) : null}

        {referencePage && referencePage.total_pages > 1 ? (
          <nav className="flex items-center justify-between gap-3" aria-label="Candidate reference pages">
            <button
              className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
              disabled={!referencePage.has_previous}
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Previous
            </button>
            <span className="text-xs text-slate-500">
              Page {referencePage.page} of {referencePage.total_pages}
            </span>
            <button
              className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
              disabled={!referencePage.has_next}
              type="button"
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </nav>
        ) : null}
      </div>
    </section>
  );
}

function CandidateRow({ candidate }: Readonly<{ candidate: ZoteroMatchCandidate }>) {
  const href = candidateHref(candidate);
  const title = candidate.title ?? candidate.doi ?? candidate.arxiv_id ?? "No Zotero match";

  return (
    <article>
      <div className="flex flex-wrap items-center gap-2">
        <span className="border border-slate-300 px-2 py-1 text-xs font-medium">{candidate.decision}</span>
        <span className="text-xs text-slate-500">{candidate.match_method.replaceAll("_", " ")}</span>
        <span className="text-xs text-slate-500">score {candidate.match_score.toFixed(2)}</span>
      </div>
      <h3 className="mt-2 break-words text-sm font-medium">
        {href ? (
          <a className="underline underline-offset-2 hover:text-sky-700" href={href} rel="noopener noreferrer" target="_blank">
            {title}
          </a>
        ) : (
          title
        )}
      </h3>
      <p className="mt-2 text-xs text-slate-500">
        Matched: {candidate.matched_fields.join(", ") || "none"}
      </p>
      {candidate.conflicting_fields.length ? (
        <p className="mt-1 text-xs text-amber-700">
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

function referenceLabel(value: string): string {
  return value.length <= 120 ? value : `${value.slice(0, 117)}...`;
}
