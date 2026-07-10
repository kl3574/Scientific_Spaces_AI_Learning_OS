import { useState } from "react";
import Link from "next/link";

import type { GraphNode, GraphSubgraphResponse } from "@/lib/graph";
import {
  ConceptSource,
  getConceptProvenance,
  getProvenanceSourceView,
  getSafeArticleId,
  getSafeDisplayText,
  getSafeExternalUrl,
} from "@/lib/graphPresentation";

export type GraphLoadState = "idle" | "loading" | "loaded" | "error";

type GraphBounds = {
  depth: number;
  nodeLimit: number;
  edgeLimit: number;
};

type GraphNodeDetailProps = {
  node: GraphNode | null;
  detailStatus: GraphLoadState;
  detailError: string | null;
  subgraph: GraphSubgraphResponse | null;
  subgraphStatus: GraphLoadState;
  subgraphError: string | null;
  bounds: GraphBounds;
  onSelectNode: (nodeId: string) => void;
  onRetry: () => void;
};

export function GraphNodeDetail({
  node,
  detailStatus,
  detailError,
  subgraph,
  subgraphStatus,
  subgraphError,
  bounds,
  onSelectNode,
  onRetry,
}: Readonly<GraphNodeDetailProps>) {
  return (
    <aside className="min-w-0 space-y-4">
      <section className="min-w-0 rounded border border-slate-200 bg-white p-4" aria-busy={detailStatus === "loading"}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold">Selected Node</h2>
          {detailStatus === "error" ? (
            <button className="text-xs font-medium text-slate-600 hover:text-slate-950" type="button" onClick={onRetry}>
              Retry
            </button>
          ) : null}
        </div>

        {detailStatus === "idle" ? (
          <p className="mt-3 text-sm leading-6 text-slate-600">Select a node to inspect its details and local context.</p>
        ) : null}
        {detailStatus === "loading" ? (
          <p className="mt-3 text-sm text-slate-600" role="status">
            Loading node details...
          </p>
        ) : null}
        {detailStatus === "error" ? (
          <p className="mt-3 break-words text-sm text-red-700" role="alert">
            {detailError}
          </p>
        ) : null}
        {detailStatus === "loaded" && node ? <NodeContent key={node.node_id} node={node} /> : null}
      </section>

      <section className="min-w-0 rounded border border-slate-200 bg-white p-4" aria-busy={subgraphStatus === "loading"}>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
          <h2 className="text-base font-semibold">Bounded Context</h2>
          <p className="text-xs text-slate-500">
            Depth {bounds.depth} | {bounds.nodeLimit} nodes | {bounds.edgeLimit} relationships
          </p>
        </div>

        {subgraphStatus === "idle" ? (
          <p className="mt-3 text-sm leading-6 text-slate-600">No node selected.</p>
        ) : null}
        {subgraphStatus === "loading" ? (
          <p className="mt-3 text-sm text-slate-600" role="status">
            Loading bounded context...
          </p>
        ) : null}
        {subgraphStatus === "error" ? (
          <div className="mt-3 flex items-start justify-between gap-3" role="alert">
            <p className="min-w-0 break-words text-sm text-red-700">{subgraphError}</p>
            <button className="shrink-0 text-xs font-medium text-slate-600 hover:text-slate-950" type="button" onClick={onRetry}>
              Retry
            </button>
          </div>
        ) : null}
        {subgraphStatus === "loaded" && subgraph ? (
          <SubgraphContent node={node} subgraph={subgraph} onSelectNode={onSelectNode} />
        ) : null}
      </section>
    </aside>
  );
}

function NodeContent({ node }: Readonly<{ node: GraphNode }>) {
  const [sourcesExpanded, setSourcesExpanded] = useState(false);
  const label = getSafeDisplayText(node.label) ?? "Untitled node";
  const provenance = getConceptProvenance(node);
  const sourceView = getProvenanceSourceView(provenance?.sources ?? [], sourcesExpanded);

  return (
    <div className="mt-3 min-w-0 space-y-4">
      <div className="min-w-0">
        <span className="inline-block rounded border border-slate-200 px-2 py-1 text-xs text-slate-600">
          {formatNodeType(node.node_type)}
        </span>
        <h3 className="mt-2 min-w-0 break-words text-lg font-semibold leading-7 [overflow-wrap:anywhere]">{label}</h3>
        <NodeLinks node={node} />
      </div>

      {provenance ? (
        <section className="border-t border-slate-200 pt-4">
          <h3 className="text-sm font-semibold">Concept Provenance</h3>
          <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <ProvenanceFact label="Sources" value={provenance.sourceCount} />
            <ProvenanceFact label="Response" value={provenance.truncated ? "Truncated" : "Complete"} />
            <ProvenanceFact label="Omitted" value={provenance.omittedCount} />
          </dl>

          {sourceView.sources.length ? (
            <ol className="mt-4 divide-y divide-slate-100 border-y border-slate-100">
              {sourceView.sources.map((source, index) => (
                <li key={`${source.articleId ?? "source"}-${source.sourceType ?? "unknown"}-${index}`} className="py-3">
                  <ProvenanceSourceItem source={source} />
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-3 text-sm text-slate-600">No provenance sources were returned.</p>
          )}

          {provenance.sources.length > 3 ? (
            <button
              className="mt-3 text-xs font-medium text-slate-600 hover:text-slate-950 hover:underline"
              type="button"
              onClick={() => setSourcesExpanded((current) => !current)}
            >
              {sourcesExpanded
                ? "Show fewer returned sources"
                : `Show ${sourceView.hiddenReturnedCount} more returned sources`}
            </button>
          ) : null}

          {provenance.omittedCount > 0 ? (
            <p className="mt-3 text-xs leading-5 text-slate-500">
              {provenance.omittedCount} additional {provenance.omittedCount === 1 ? "source was" : "sources were"} omitted.
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function NodeLinks({ node }: Readonly<{ node: GraphNode }>) {
  const articleId = node.node_type === "article" ? getSafeArticleId(node.source_id) : null;
  const sourceUrl = getSafeExternalUrl(node.source_url);
  const showZotero = node.node_type === "zotero_item";

  if (!articleId && !sourceUrl && !showZotero) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm">
      {articleId ? (
        <Link className="font-medium text-slate-600 hover:text-slate-950 hover:underline" href={`/articles/${encodeURIComponent(articleId)}`}>
          Open article
        </Link>
      ) : null}
      {showZotero ? (
        <Link className="font-medium text-slate-600 hover:text-slate-950 hover:underline" href="/zotero">
          Open Zotero
        </Link>
      ) : null}
      {sourceUrl ? (
        <a className="font-medium text-slate-600 hover:text-slate-950 hover:underline" href={sourceUrl} rel="noreferrer" target="_blank">
          Original source
        </a>
      ) : null}
    </div>
  );
}

function ProvenanceFact({ label, value }: Readonly<{ label: string; value: number | string }>) {
  return (
    <div className="min-w-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="mt-1 break-words font-semibold text-slate-950">{value}</dd>
    </div>
  );
}

function ProvenanceSourceItem({ source }: Readonly<{ source: ConceptSource }>) {
  const title = source.articleTitle ?? source.sectionTitle ?? "Article source";

  return (
    <div className="min-w-0 text-sm">
      <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <p className="min-w-0 break-words font-medium leading-5 [overflow-wrap:anywhere]">{title}</p>
        {source.sourceType ? (
          <span className="shrink-0 text-xs text-slate-500">{formatSourceType(source.sourceType)}</span>
        ) : null}
      </div>
      {source.sectionTitle && source.sectionTitle !== title ? (
        <p className="mt-1 break-words text-xs text-slate-600 [overflow-wrap:anywhere]">Section: {source.sectionTitle}</p>
      ) : null}
      {source.chunkIndex !== null ? <p className="mt-1 text-xs text-slate-500">Chunk {source.chunkIndex}</p> : null}
      {source.sourceContext ? (
        <p className="mt-2 break-words text-xs leading-5 text-slate-600 [overflow-wrap:anywhere]">{source.sourceContext}</p>
      ) : null}
      {source.evidence ? (
        <p className="mt-1 break-words text-xs leading-5 text-slate-500 [overflow-wrap:anywhere]">Evidence: {source.evidence}</p>
      ) : null}
      {source.articleId || source.articleUrl ? (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {source.articleId ? (
            <Link className="font-medium text-slate-600 hover:text-slate-950 hover:underline" href={`/articles/${encodeURIComponent(source.articleId)}`}>
              Open article
            </Link>
          ) : null}
          {source.articleUrl ? (
            <a className="font-medium text-slate-600 hover:text-slate-950 hover:underline" href={source.articleUrl} rel="noreferrer" target="_blank">
              Original source
            </a>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function SubgraphContent({
  node,
  subgraph,
  onSelectNode,
}: Readonly<{
  node: GraphNode | null;
  subgraph: GraphSubgraphResponse;
  onSelectNode: (nodeId: string) => void;
}>) {
  const relatedNodes = subgraph.nodes.filter((item) => item.node_id !== node?.node_id);
  const nodeLabels = new Map(subgraph.nodes.map((item) => [item.node_id, getSafeDisplayText(item.label) ?? "Untitled node"]));
  if (node) {
    nodeLabels.set(node.node_id, getSafeDisplayText(node.label) ?? "Untitled node");
  }

  if (!relatedNodes.length && !subgraph.edges.length) {
    return <p className="mt-3 text-sm text-slate-600">No related nodes or relationships were returned.</p>;
  }

  return (
    <div className="mt-4 space-y-5">
      <section>
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">Related Nodes</h3>
          <span className="text-xs text-slate-500">{relatedNodes.length}</span>
        </div>
        {relatedNodes.length ? (
          <div className="mt-2 divide-y divide-slate-100 border-y border-slate-100">
            {relatedNodes.map((relatedNode) => (
              <button
                key={relatedNode.node_id}
                className="block w-full min-w-0 px-1 py-3 text-left hover:bg-slate-50"
                type="button"
                onClick={() => onSelectNode(relatedNode.node_id)}
              >
                <span className="block min-w-0 break-words text-sm font-medium [overflow-wrap:anywhere]">
                  {getSafeDisplayText(relatedNode.label) ?? "Untitled node"}
                </span>
                <span className="mt-1 block text-xs text-slate-500">{formatNodeType(relatedNode.node_type)}</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-600">No related nodes returned.</p>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">Relationships</h3>
          <span className="text-xs text-slate-500">{subgraph.edges.length}</span>
        </div>
        {subgraph.edges.length ? (
          <ul className="mt-2 divide-y divide-slate-100 border-y border-slate-100">
            {subgraph.edges.map((edge) => (
              <li key={edge.edge_id} className="min-w-0 py-3 text-xs leading-5 text-slate-600">
                <p className="break-words [overflow-wrap:anywhere]">
                  <span className="font-medium text-slate-950">{nodeLabels.get(edge.source_node_id) ?? "Unknown node"}</span>
                  <span className="px-1.5 text-slate-400">{getSafeDisplayText(edge.edge_type) ?? "related"}</span>
                  <span className="font-medium text-slate-950">{nodeLabels.get(edge.target_node_id) ?? "Unknown node"}</span>
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-slate-600">No relationships returned.</p>
        )}
      </section>
    </div>
  );
}

function formatNodeType(nodeType: GraphNode["node_type"]): string {
  const labels: Record<GraphNode["node_type"], string> = {
    article: "Article",
    section: "Section",
    concept: "Concept",
    formula: "Formula",
    zotero_item: "Zotero item",
  };
  return labels[nodeType];
}

function formatSourceType(sourceType: string): string {
  return sourceType.replaceAll("_", " ");
}
