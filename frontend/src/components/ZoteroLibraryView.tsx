"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ZoteroItem,
  ZoteroStatus,
  exportZoteroBibtex,
  fetchZoteroStatus,
  searchZoteroItems,
} from "@/lib/zotero";

export function ZoteroLibraryView() {
  const [status, setStatus] = useState<ZoteroStatus | null>(null);
  const [query, setQuery] = useState("attention");
  const [items, setItems] = useState<ZoteroItem[]>([]);
  const [bibtex, setBibtex] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchZoteroStatus()
      .then(setStatus)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load Zotero status"));
  }, []);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBibtex("");
    try {
      const response = await searchZoteroItems(query, 20);
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search Zotero items");
    }
  }

  async function handleExport(itemKey: string) {
    setError(null);
    try {
      const response = await exportZoteroBibtex([itemKey]);
      setBibtex(response.bibtex);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export BibTeX");
    }
  }

  return (
    <section className="space-y-6">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-semibold">Zotero Library</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Search paper metadata and export BibTeX from the configured read-only Zotero provider.
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold">Provider Status</h2>
        <dl className="mt-3 grid gap-2 text-sm md:grid-cols-4">
          <div>
            <dt className="text-slate-500">Provider</dt>
            <dd>{status?.provider ?? "Unknown"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Available</dt>
            <dd>{status ? String(status.available) : "Unknown"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Read only</dt>
            <dd>{status ? String(status.read_only) : "Unknown"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Version</dt>
            <dd>{status?.version ?? "Unknown"}</dd>
          </div>
        </dl>
        {status?.error ? <p className="mt-3 text-sm text-slate-600">{status.error}</p> : null}
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSearch}>
          <input
            className="min-w-0 flex-1 rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
            placeholder="Search title, creator, tag"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white" type="submit">
            Search
          </button>
        </form>
      </section>

      <section className="grid gap-3">
        {items.length ? (
          items.map((item) => (
            <article key={item.item_key} className="rounded border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-base font-semibold">{item.title}</h2>
                  <p className="mt-1 text-sm text-slate-600">{formatItemLine(item)}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.item_type} · {item.item_key} · {item.bibtex_key}
                  </p>
                </div>
                <button
                  className="rounded border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50"
                  type="button"
                  onClick={() => void handleExport(item.item_key)}
                >
                  Export BibTeX
                </button>
              </div>
              {item.abstract_note ? <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">{item.abstract_note}</p> : null}
            </article>
          ))
        ) : (
          <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">No Zotero items loaded.</p>
        )}
      </section>

      {bibtex ? (
        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">BibTeX</h2>
          <pre className="mt-3 overflow-auto rounded bg-slate-950 p-3 text-xs leading-5 text-white">{bibtex}</pre>
        </section>
      ) : null}
    </section>
  );
}

function formatItemLine(item: ZoteroItem): string {
  const creators = item.creators.length ? item.creators.join(", ") : "Unknown creators";
  return [creators, item.year, item.publication_title].filter(Boolean).join(" · ");
}
