import assert from "node:assert/strict";
import test from "node:test";

import type { ZoteroArticleLinkItem, ZoteroItem } from "../src/lib/zotero";
import {
  createZoteroPanelOperation,
  createZoteroUnlinkIntent,
  getMutationReadbackOutcome,
  getZoteroLinkFingerprint,
  mergeZoteroLinkItem,
  normalizeZoteroQuery,
  ownsZoteroPanelOperation,
  ownsZoteroUnlinkIntent,
  removeZoteroLinkItem,
} from "../src/lib/zoteroLinkOperations";

const paper: ZoteroItem = {
  item_key: "ABCD1234",
  bibtex_key: "vaswani2017attention",
  title: "Attention Is All You Need",
  creators: ["Ashish Vaswani", "Noam Shazeer"],
  year: "2017",
  item_type: "journalArticle",
  publication_title: "NeurIPS",
  doi: null,
  url: "https://arxiv.org/abs/1706.03762",
  abstract_note: null,
  tags: [],
  collections: [],
  updated_at: null,
};

function linkedItem(
  itemKey = paper.item_key,
  relationType: "related" | "cites" | "background" = "related",
  note: string | null = "Foundational context",
): ZoteroArticleLinkItem {
  return {
    link: {
      article_id: "attention-basics",
      zotero_item_key: itemKey,
      relation_type: relationType,
      created_at: "2026-09-05T12:00:00Z",
      note,
    },
    item: itemKey === paper.item_key ? paper : { ...paper, item_key: itemKey, title: `Paper ${itemKey}` },
  };
}

test("panel operation ownership requires exact article, generation, id, kind, and subject", () => {
  const operation = createZoteroPanelOperation(
    "attention-basics",
    4,
    12,
    "search",
    "attention",
  );

  assert.equal(
    ownsZoteroPanelOperation(operation, operation, "attention-basics", 4),
    true,
  );
  assert.equal(
    ownsZoteroPanelOperation(operation, operation, "crb-formula", 4),
    false,
  );
  assert.equal(
    ownsZoteroPanelOperation(operation, operation, "attention-basics", 5),
    false,
  );
  assert.equal(
    ownsZoteroPanelOperation(
      createZoteroPanelOperation("attention-basics", 4, 13, "search", "attention"),
      operation,
      "attention-basics",
      4,
    ),
    false,
  );
  assert.equal(
    ownsZoteroPanelOperation(
      createZoteroPanelOperation("attention-basics", 4, 12, "export", "attention"),
      operation,
      "attention-basics",
      4,
    ),
    false,
  );
  assert.equal(
    ownsZoteroPanelOperation(
      createZoteroPanelOperation("attention-basics", 4, 12, "search", "crb"),
      operation,
      "attention-basics",
      4,
    ),
    false,
  );
});

test("search identity ignores only transport-trimmed outer whitespace", () => {
  assert.equal(normalizeZoteroQuery("  Kay "), "Kay");
  assert.equal(normalizeZoteroQuery("Kay"), normalizeZoteroQuery("Kay "));
  assert.notEqual(normalizeZoteroQuery("Kay"), normalizeZoteroQuery("Kay theory"));
});

test("unlink intent cannot cross article, generation, or item identity", () => {
  const intent = createZoteroUnlinkIntent("attention-basics", 2, "ABCD1234");

  assert.equal(ownsZoteroUnlinkIntent(intent, intent, "attention-basics", 2), true);
  assert.equal(ownsZoteroUnlinkIntent(intent, intent, "crb-formula", 2), false);
  assert.equal(ownsZoteroUnlinkIntent(intent, intent, "attention-basics", 3), false);
  assert.equal(
    ownsZoteroUnlinkIntent(
      createZoteroUnlinkIntent("attention-basics", 2, "EFGH5678"),
      intent,
      "attention-basics",
      2,
    ),
    false,
  );
});

test("link fingerprint is order-independent and includes relation metadata", () => {
  const first = linkedItem("ABCD1234", "related", "context");
  const second = linkedItem("EFGH5678", "cites", null);

  assert.equal(
    getZoteroLinkFingerprint([first, second]),
    getZoteroLinkFingerprint([second, first]),
  );
  assert.notEqual(
    getZoteroLinkFingerprint([first]),
    getZoteroLinkFingerprint([linkedItem("ABCD1234", "background", "context")]),
  );
  assert.notEqual(
    getZoteroLinkFingerprint([first]),
    getZoteroLinkFingerprint([linkedItem("ABCD1234", "related", "changed")]),
  );
});

test("functional merge replaces one matching link without duplicates", () => {
  const oldLink = linkedItem("ABCD1234", "related", "old");
  const otherLink = linkedItem("EFGH5678", "cites", null);
  const incoming = linkedItem("ABCD1234", "background", "new");

  const merged = mergeZoteroLinkItem([oldLink, otherLink, oldLink], incoming);

  assert.equal(merged.length, 2);
  assert.deepEqual(merged[0], incoming);
  assert.deepEqual(merged[1], otherLink);
});

test("functional removal deletes only the requested link", () => {
  const first = linkedItem("ABCD1234");
  const second = linkedItem("EFGH5678");

  assert.deepEqual(removeZoteroLinkItem([first, second], "ABCD1234"), [second]);
  const unchanged = [first, second];
  assert.equal(removeZoteroLinkItem(unchanged, "MISSING"), unchanged);
});

test("readback establishes link outcomes without guessing conflicting metadata", () => {
  assert.equal(
    getMutationReadbackOutcome([linkedItem("ABCD1234", "related", "context")], {
      kind: "link",
      itemKey: "ABCD1234",
      relationType: "related",
      note: "context",
    }),
    "applied",
  );
  assert.equal(
    getMutationReadbackOutcome([], {
      kind: "link",
      itemKey: "ABCD1234",
      relationType: "related",
      note: "context",
    }),
    "not-applied",
  );
  assert.equal(
    getMutationReadbackOutcome([linkedItem("ABCD1234", "background", "different")], {
      kind: "link",
      itemKey: "ABCD1234",
      relationType: "related",
      note: "context",
    }),
    "inconclusive",
  );
  assert.equal(
    getMutationReadbackOutcome([], { kind: "unlink", itemKey: "ABCD1234" }),
    "applied",
  );
  assert.equal(
    getMutationReadbackOutcome([linkedItem()], { kind: "unlink", itemKey: "ABCD1234" }),
    "not-applied",
  );
});
