"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ZoteroArticleLinkItem,
  ZoteroItem,
  ZoteroRelationType,
  createArticleZoteroLink,
  deleteArticleZoteroLink,
  exportZoteroBibtex,
  fetchArticleZoteroLinks,
  searchZoteroItems,
} from "@/lib/zotero";

const relationTypes: ZoteroRelationType[] = ["related", "cites", "background"];

export function ZoteroLinksPanel({ articleId, initialQuery }: Readonly<{ articleId: string; initialQuery: string }>) {
  const [links, setLinks] = useState<ZoteroArticleLinkItem[]>([]);
  const [results, setResults] = useState<ZoteroItem[]>([]);
  const [query, setQuery] = useState(initialQuery);
  const [relationType, setRelationType] = useState<ZoteroRelationType>("related");
  const [note, setNote] = useState("");
  const [bibtex, setBibtex] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadLinks(articleId);
  }, [articleId]);

  async function loadLinks(nextArticleId: string) {
    setError(null);
    try {
      const response = await fetchArticleZoteroLinks(nextArticleId);
      setLinks(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Zotero links");
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const response = await searchZoteroItems(query, 10);
      setResults(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search Zotero");
    }
  }

  async function handleLink(itemKey: string) {
    setError(null);
    try {
      await createArticleZoteroLink(articleId, itemKey, relationType, note.trim() || null);
      setNote("");
      await loadLinks(articleId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to link Zotero item");
    }
  }

  async function handleDelete(itemKey: string) {
    setError(null);
    try {
      await deleteArticleZoteroLink(articleId, itemKey);
      await loadLinks(articleId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlink Zotero item");
    }
  }

  async function handleExportLinked() {
    setError(null);
    try {
      const itemKeys = links.map((entry) => entry.link.zotero_item_key);
      const response = await exportZoteroBibtex(itemKeys);
      setBibtex(response.bibtex);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export linked BibTeX");
    }
  }

  return (
    <section className="rounded border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Related Papers</h2>
        <button
          className="rounded border border-slate-300 px-3 py-1 text-xs font-medium hover:bg-slate-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
          disabled={!links.length}
          type="button"
          onClick={() => void handleExportLinked()}
        >
          BibTeX
        </button>
      </div>

      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}

      <div className="mt-3 grid gap-2">
        {links.length ? (
          links.map((entry) => (
            <article key={entry.link.zotero_item_key} className="rounded border border-slate-100 p-3 text-sm">
              <h3 className="font-medium">{entry.item?.title ?? entry.link.zotero_item_key}</h3>
              <p className="mt-1 text-xs text-slate-500">
                {entry.item ? formatItemLine(entry.item) : "Metadata unavailable"} · {entry.link.relation_type}
              </p>
              {entry.link.note ? <p className="mt-2 text-xs leading-5 text-slate-600">{entry.link.note}</p> : null}
              <button
                className="mt-3 rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
                type="button"
                onClick={() => void handleDelete(entry.link.zotero_item_key)}
              >
                Unlink
              </button>
            </article>
          ))
        ) : (
          <p className="text-sm text-slate-600">No related papers linked.</p>
        )}
      </div>

      <form className="mt-4 space-y-2" onSubmit={handleSearch}>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
          placeholder="Search Zotero papers"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <select
            className="rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
            value={relationType}
            onChange={(event) => setRelationType(event.target.value as ZoteroRelationType)}
          >
            {relationTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <button className="rounded bg-slate-950 px-3 py-2 text-sm font-medium text-white" type="submit">
            Search
          </button>
        </div>
        <textarea
          className="min-h-20 w-full resize-y rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
          placeholder="Optional relationship note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </form>

      {results.length ? (
        <div className="mt-3 grid gap-2">
          {results.map((item) => (
            <article key={item.item_key} className="rounded border border-slate-100 p-3 text-sm">
              <h3 className="font-medium">{item.title}</h3>
              <p className="mt-1 text-xs text-slate-500">{formatItemLine(item)}</p>
              <button
                className="mt-3 rounded border border-slate-300 px-3 py-1 text-xs font-medium hover:bg-slate-50"
                type="button"
                onClick={() => void handleLink(item.item_key)}
              >
                Link
              </button>
            </article>
          ))}
        </div>
      ) : null}

      {bibtex ? <pre className="mt-3 overflow-auto rounded bg-slate-950 p-3 text-xs leading-5 text-white">{bibtex}</pre> : null}
    </section>
  );
}

function formatItemLine(item: ZoteroItem): string {
  const creators = item.creators.length ? item.creators.join(", ") : "Unknown creators";
  return [creators, item.year, item.publication_title].filter(Boolean).join(" · ");
}
