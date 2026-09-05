"use client";

import Link from "next/link";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  MIN_GLOBAL_SEARCH_LENGTH,
  getWorkspaceQuickResults,
  normalizeGlobalSearchQuery,
  searchGlobalContent,
  type GlobalSearchGroup,
  type GlobalSearchResponse,
  type GlobalSearchResult,
} from "@/lib/globalSearch";
import type { ShellNavigationEvent } from "@/lib/navigation";

type SearchStatus = "idle" | "loading" | "loaded" | "error";

export function GlobalSearchDialog({
  open,
  onDismiss,
  onNavigate,
}: Readonly<{
  open: boolean;
  onDismiss: () => void;
  onNavigate: (href: string, event: ShellNavigationEvent) => void;
}>) {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<GlobalSearchResponse | null>(null);
  const [status, setStatus] = useState<SearchStatus>("idle");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const requestSequenceRef = useRef(0);
  const normalizedQuery = normalizeGlobalSearchQuery(query);
  const workspaceResults = useMemo(() => getWorkspaceQuickResults(query), [query]);
  const groups = useMemo(
    () => buildVisibleGroups(workspaceResults, response),
    [response, workspaceResults],
  );
  const results = useMemo(() => groups.flatMap((group) => group.items), [groups]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    const focusFrame = window.requestAnimationFrame(() => inputRef.current?.focus());
    document.body.style.overflow = "hidden";
    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    const requestSequence = ++requestSequenceRef.current;
    setSelectedIndex(0);
    if (!open || normalizedQuery.length < MIN_GLOBAL_SEARCH_LENGTH) {
      setResponse(null);
      setStatus("idle");
      return;
    }

    setResponse(null);
    setStatus("loading");
    const timer = window.setTimeout(() => {
      searchGlobalContent(normalizedQuery)
        .then((nextResponse) => {
          if (requestSequence !== requestSequenceRef.current) {
            return;
          }
          setResponse(nextResponse);
          setStatus("loaded");
        })
        .catch(() => {
          if (requestSequence !== requestSequenceRef.current) {
            return;
          }
          setResponse(null);
          setStatus("error");
        });
    }, 250);

    return () => window.clearTimeout(timer);
  }, [normalizedQuery, open]);

  useEffect(() => {
    if (selectedIndex >= results.length) {
      setSelectedIndex(Math.max(results.length - 1, 0));
    }
  }, [results.length, selectedIndex]);

  if (!open) {
    return null;
  }

  function focusResult(nextIndex: number) {
    const elements = getResultElements(dialogRef.current);
    if (elements.length === 0) {
      inputRef.current?.focus();
      return;
    }
    const boundedIndex = (nextIndex + elements.length) % elements.length;
    setSelectedIndex(boundedIndex);
    elements[boundedIndex]?.focus();
  }

  function handleKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onDismiss();
      return;
    }

    const resultElements = getResultElements(dialogRef.current);
    const activeResultIndex = resultElements.findIndex((element) => element === document.activeElement);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusResult(activeResultIndex >= 0 ? activeResultIndex + 1 : selectedIndex);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      focusResult(activeResultIndex >= 0 ? activeResultIndex - 1 : results.length - 1);
      return;
    }
    if (event.key === "Enter" && document.activeElement === inputRef.current && resultElements.length > 0) {
      event.preventDefault();
      resultElements[selectedIndex]?.click();
      return;
    }
    if (event.key !== "Tab") {
      return;
    }

    const focusable = getFocusableElements(dialogRef.current);
    if (focusable.length === 0) {
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  const contentResultCount = response?.groups.reduce((count, group) => count + group.items.length, 0) ?? 0;

  return (
    <div className="fixed inset-0 z-[70]" data-testid="global-search-dialog">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-slate-950/45" />
      <div
        className="relative flex min-h-full items-start justify-center p-2 sm:p-6"
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) {
            onDismiss();
          }
        }}
      >
        <div
          ref={dialogRef}
          aria-label="Global search"
          aria-modal="true"
          className="mt-2 flex max-h-[calc(100dvh-1rem)] w-full max-w-2xl flex-col overflow-hidden rounded-md border border-slate-300 bg-white shadow-2xl sm:mt-[8vh] sm:max-h-[min(42rem,84vh)]"
          role="dialog"
          onKeyDown={handleKeyDown}
        >
          <header className="flex shrink-0 items-center gap-2 border-b border-slate-200 p-3 sm:p-4">
            <label className="min-w-0 flex-1">
              <span className="sr-only">Search library</span>
              <input
                ref={inputRef}
                aria-controls="global-search-results"
                aria-expanded="true"
                aria-label="Search library"
                autoComplete="off"
                className="block min-h-11 w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none placeholder:text-slate-400 focus:border-slate-950"
                placeholder="Article, reference, or concept"
                role="combobox"
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            {query ? (
              <button
                className="min-h-11 shrink-0 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700 hover:border-slate-500 hover:bg-slate-50"
                type="button"
                onClick={() => {
                  setQuery("");
                  inputRef.current?.focus();
                }}
              >
                Clear
              </button>
            ) : null}
            <button
              className="min-h-11 shrink-0 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700 hover:border-slate-500 hover:bg-slate-50"
              type="button"
              onClick={onDismiss}
            >
              Close
            </button>
          </header>

          <div
            aria-busy={status === "loading"}
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain"
            id="global-search-results"
          >
            {groups.length > 0 ? (
              <div className="divide-y divide-slate-200">
                {groups.map((group) => (
                  <SearchResultGroup
                    key={group.key}
                    group={group}
                    resultOffset={findGroupOffset(groups, group.key)}
                    selectedIndex={selectedIndex}
                    onFocusResult={setSelectedIndex}
                    onNavigate={onNavigate}
                  />
                ))}
              </div>
            ) : null}

            {normalizedQuery.length === 1 ? (
              <SearchMessage title="Keep typing" detail="Enter at least two characters." />
            ) : null}
            {status === "loading" ? (
              <SearchMessage title="Searching" detail="Checking the local learning library." tone="loading" />
            ) : null}
            {status === "error" ? (
              <SearchMessage title="Search unavailable" detail="The local search could not be completed." tone="error" />
            ) : null}
            {status === "loaded" && contentResultCount === 0 && response?.failures.length === 0 ? (
              <SearchMessage title="No matching learning material" detail="Try another title, citation, or concept." />
            ) : null}
            {response?.failures.length ? (
              <div className="border-t border-amber-200 bg-amber-50 px-4 py-3" role="status">
                <p className="text-sm font-semibold text-amber-950">Some sources are unavailable</p>
                <p className="mt-1 text-xs leading-5 text-amber-900">
                  {response.failures.map((failure) => failure.message).join(" ")}
                </p>
              </div>
            ) : null}
          </div>

          <p aria-atomic="true" aria-live="polite" className="sr-only" role="status">
            {getStatusAnnouncement(status, normalizedQuery, contentResultCount, response?.failures.length ?? 0)}
          </p>
        </div>
      </div>
    </div>
  );
}

type VisibleGroup = {
  key: string;
  label: string;
  total: number;
  items: GlobalSearchResult[];
};

function buildVisibleGroups(
  workspaceResults: GlobalSearchResult[],
  response: GlobalSearchResponse | null,
): VisibleGroup[] {
  const groups: VisibleGroup[] = [];
  if (workspaceResults.length > 0) {
    groups.push({
      key: "workspaces",
      label: "Workspaces",
      total: workspaceResults.length,
      items: workspaceResults,
    });
  }
  groups.push(...(response?.groups.map(toVisibleGroup) ?? []));
  return groups;
}

function toVisibleGroup(group: GlobalSearchGroup): VisibleGroup {
  return { key: group.source, label: group.label, total: group.total, items: group.items };
}

function findGroupOffset(groups: VisibleGroup[], key: string): number {
  let offset = 0;
  for (const group of groups) {
    if (group.key === key) {
      return offset;
    }
    offset += group.items.length;
  }
  return offset;
}

function SearchResultGroup({
  group,
  resultOffset,
  selectedIndex,
  onFocusResult,
  onNavigate,
}: Readonly<{
  group: VisibleGroup;
  resultOffset: number;
  selectedIndex: number;
  onFocusResult: (index: number) => void;
  onNavigate: (href: string, event: ShellNavigationEvent) => void;
}>) {
  return (
    <section aria-labelledby={`global-search-group-${group.key}`} className="py-2">
      <header className="flex items-center justify-between gap-3 px-4 py-2">
        <h2
          className="text-xs font-semibold uppercase text-slate-500"
          id={`global-search-group-${group.key}`}
        >
          {group.label}
        </h2>
        <span className="text-xs tabular-nums text-slate-400">{group.total}</span>
      </header>
      <ul className="grid" role="list">
        {group.items.map((result, localIndex) => {
          const index = resultOffset + localIndex;
          return (
            <li key={result.key}>
              <Link
                className={`block min-h-14 border-l-4 px-4 py-2.5 outline-none ${
                  selectedIndex === index
                    ? "border-emerald-600 bg-emerald-50 text-slate-950"
                    : "border-transparent text-slate-700 hover:bg-slate-50"
                }`}
                data-global-search-result
                data-result-index={index}
                data-testid={`global-search-result-${result.kind}`}
                href={result.href}
                prefetch={false}
                onFocus={() => onFocusResult(index)}
                onMouseMove={() => onFocusResult(index)}
                onNavigate={(event) => onNavigate(result.href, event)}
              >
                <span className="block break-words text-sm font-semibold leading-5">{result.title}</span>
                <span className="mt-0.5 block break-words text-xs leading-5 text-slate-500">
                  {result.description}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function SearchMessage({
  title,
  detail,
  tone = "neutral",
}: Readonly<{
  title: string;
  detail: string;
  tone?: "neutral" | "loading" | "error";
}>) {
  return (
    <div
      className={`px-4 py-8 text-center ${tone === "error" ? "text-red-800" : "text-slate-600"}`}
      role={tone === "error" ? "alert" : tone === "loading" ? "status" : undefined}
    >
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-xs leading-5">{detail}</p>
    </div>
  );
}

function getResultElements(root: HTMLDivElement | null): HTMLAnchorElement[] {
  return Array.from(root?.querySelectorAll<HTMLAnchorElement>("[data-global-search-result]") ?? []);
}

function getFocusableElements(root: HTMLDivElement | null): HTMLElement[] {
  return Array.from(
    root?.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) ?? [],
  );
}

function getStatusAnnouncement(
  status: SearchStatus,
  query: string,
  resultCount: number,
  failureCount: number,
): string {
  if (status === "loading") {
    return `Searching for ${query}`;
  }
  if (status === "loaded") {
    return `${resultCount} learning results. ${failureCount ? `${failureCount} sources unavailable.` : ""}`;
  }
  if (status === "error") {
    return "Search unavailable";
  }
  return query.length === 1 ? "Enter at least two characters" : "Quick navigation ready";
}
