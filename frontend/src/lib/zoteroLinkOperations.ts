import type {
  ZoteroArticleLinkItem,
  ZoteroRelationType,
} from "./zotero";

export type ZoteroPanelOperationKind =
  | "links-load"
  | "provider-status"
  | "search"
  | "link"
  | "unlink"
  | "reconcile"
  | "export";

export type ZoteroPanelOperation = Readonly<{
  articleId: string;
  generation: number;
  operationId: number;
  kind: ZoteroPanelOperationKind;
  subject: string;
}>;

export type ZoteroUnlinkIntent = Readonly<{
  articleId: string;
  generation: number;
  itemKey: string;
}>;

export type ZoteroMutationExpectation =
  | Readonly<{
      kind: "link";
      itemKey: string;
      relationType: ZoteroRelationType;
      note: string | null;
    }>
  | Readonly<{
      kind: "unlink";
      itemKey: string;
    }>;

export type MutationReadbackOutcome = "applied" | "not-applied" | "inconclusive";

export function normalizeZoteroQuery(query: string): string {
  return query.trim();
}

export function createZoteroPanelOperation(
  articleId: string,
  generation: number,
  operationId: number,
  kind: ZoteroPanelOperationKind,
  subject: string,
): ZoteroPanelOperation {
  return { articleId, generation, operationId, kind, subject };
}

export function ownsZoteroPanelOperation(
  current: ZoteroPanelOperation | null,
  operation: ZoteroPanelOperation,
  articleId: string,
  generation: number,
): boolean {
  return current !== null
    && current.articleId === operation.articleId
    && current.generation === operation.generation
    && current.operationId === operation.operationId
    && current.kind === operation.kind
    && current.subject === operation.subject
    && articleId === operation.articleId
    && generation === operation.generation;
}

export function createZoteroUnlinkIntent(
  articleId: string,
  generation: number,
  itemKey: string,
): ZoteroUnlinkIntent {
  return { articleId, generation, itemKey };
}

export function ownsZoteroUnlinkIntent(
  current: ZoteroUnlinkIntent | null,
  intent: ZoteroUnlinkIntent,
  articleId: string,
  generation: number,
): boolean {
  return current !== null
    && current.articleId === intent.articleId
    && current.generation === intent.generation
    && current.itemKey === intent.itemKey
    && articleId === intent.articleId
    && generation === intent.generation;
}

export function getZoteroLinkFingerprint(links: ZoteroArticleLinkItem[]): string {
  return links
    .map(({ link }) => [
      link.zotero_item_key,
      link.relation_type,
      link.note ?? "",
    ].map(encodeFingerprintPart).join(":"))
    .sort()
    .join("|");
}

export function mergeZoteroLinkItem(
  links: ZoteroArticleLinkItem[],
  incoming: ZoteroArticleLinkItem,
): ZoteroArticleLinkItem[] {
  return [
    incoming,
    ...links.filter(
      (entry) => entry.link.zotero_item_key !== incoming.link.zotero_item_key,
    ),
  ];
}

export function removeZoteroLinkItem(
  links: ZoteroArticleLinkItem[],
  itemKey: string,
): ZoteroArticleLinkItem[] {
  if (!links.some((entry) => entry.link.zotero_item_key === itemKey)) {
    return links;
  }
  return links.filter((entry) => entry.link.zotero_item_key !== itemKey);
}

export function getMutationReadbackOutcome(
  links: ZoteroArticleLinkItem[],
  expectation: ZoteroMutationExpectation,
): MutationReadbackOutcome {
  const current = links.find(
    (entry) => entry.link.zotero_item_key === expectation.itemKey,
  );
  if (expectation.kind === "unlink") {
    return current ? "not-applied" : "applied";
  }
  if (!current) {
    return "not-applied";
  }
  if (
    current.link.relation_type === expectation.relationType
    && current.link.note === expectation.note
  ) {
    return "applied";
  }
  return "inconclusive";
}

function encodeFingerprintPart(value: string): string {
  return `${value.length}:${value}`;
}
