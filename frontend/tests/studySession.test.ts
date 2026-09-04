import assert from "node:assert/strict";
import test from "node:test";

import {
  STUDY_SESSION_ITEM_LIMIT,
  activateStudySessionItem,
  addStudySessionItems,
  addStudySessionItem,
  clearStudySession,
  createEmptyStudySession,
  createStudySessionReaderHref,
  getStudySessionPosition,
  moveStudySessionItem,
  parseStudySessionStore,
  removeStudySessionItem,
  serializeStudySession,
} from "../src/lib/studySession";

const FIRST_TIME = "2026-09-01T00:00:00.000Z";
const SECOND_TIME = "2026-09-01T00:01:00.000Z";
const THIRD_TIME = "2026-09-01T00:02:00.000Z";

test("versioned study session round-trips readable bounded records", () => {
  const raw = JSON.stringify({
    version: 1,
    active_article_id: "attention-basics",
    updated_at: SECOND_TIME,
    items: [
      {
        article_id: "attention-basics",
        title: "Attention机制入门",
        section_id: "scaled-attention",
        added_at: FIRST_TIME,
      },
      {
        article_id: "crb-formula",
        title: "CRB公式与估计下界",
        section_id: null,
        added_at: SECOND_TIME,
      },
    ],
  });

  const parsed = parseStudySessionStore(raw);

  assert.equal(parsed.recovered, false);
  assert.equal(parsed.droppedCount, 0);
  assert.equal(parsed.truncatedCount, 0);
  assert.equal(parsed.state.activeArticleId, "attention-basics");
  assert.deepEqual(parsed.state.items.map((item) => item.title), [
    "Attention机制入门",
    "CRB公式与估计下界",
  ]);
  assert.deepEqual(parseStudySessionStore(serializeStudySession(parsed.state)).state, parsed.state);
});

test("malformed, duplicate, unreadable, and over-limit records fail closed", () => {
  const items = Array.from({ length: STUDY_SESSION_ITEM_LIMIT + 2 }, (_, index) => ({
    article_id: `article-${String(index).padStart(2, "0")}`,
    title: `Readable Article ${index}`,
    section_id: null,
    added_at: FIRST_TIME,
  }));
  items.splice(1, 0, { ...items[0] });
  items.splice(2, 0, {
    article_id: "raw-title-id",
    title: "raw-title-id",
    section_id: null,
    added_at: FIRST_TIME,
  });
  items.splice(3, 0, {
    article_id: "unsafe/id",
    title: "Unsafe record",
    section_id: null,
    added_at: FIRST_TIME,
  });

  const parsed = parseStudySessionStore(JSON.stringify({
    version: 1,
    active_article_id: "missing-active",
    updated_at: "invalid date",
    items,
  }));

  assert.equal(parsed.recovered, true);
  assert.equal(parsed.droppedCount, 3);
  assert.equal(parsed.truncatedCount, 2);
  assert.equal(parsed.state.items.length, STUDY_SESSION_ITEM_LIMIT);
  assert.equal(parsed.state.activeArticleId, "article-00");
  assert.equal(parsed.state.items.some((item) => item.title === "raw-title-id"), false);
  assert.deepEqual(parseStudySessionStore("not json"), {
    state: createEmptyStudySession(),
    recovered: true,
    droppedCount: 0,
    truncatedCount: 0,
  });
});

test("safe item normalization is surfaced as a recovered queue", () => {
  const parsed = parseStudySessionStore(JSON.stringify({
    version: 1,
    active_article_id: "attention-basics",
    updated_at: SECOND_TIME,
    items: [
      {
        article_id: " attention-basics ",
        title: "Attention\u0000  机制入门",
        section_id: "unsafe?section",
        added_at: "invalid timestamp",
      },
    ],
  }));

  assert.equal(parsed.recovered, true);
  assert.equal(parsed.droppedCount, 0);
  assert.equal(parsed.state.activeArticleId, "attention-basics");
  assert.deepEqual(parsed.state.items[0], {
    articleId: "attention-basics",
    title: "Attention 机制入门",
    sectionId: null,
    addedAt: new Date(0).toISOString(),
  });
});

test("queue mutation is deterministic across add, deduplicate, reorder, remove, and clear", () => {
  let state = createEmptyStudySession();
  const first = addStudySessionItem(
    state,
    { articleId: "attention-basics", title: "Attention机制入门", sectionId: "attention" },
    FIRST_TIME,
  );
  assert.equal(first.outcome, "added");
  state = first.state;

  const second = addStudySessionItem(
    state,
    { articleId: "crb-formula", title: "CRB公式与估计下界", sectionId: null },
    SECOND_TIME,
  );
  assert.equal(second.outcome, "added");
  state = second.state;

  const duplicate = addStudySessionItem(
    state,
    { articleId: "attention-basics", title: "Attention机制入门", sectionId: null },
    THIRD_TIME,
  );
  assert.equal(duplicate.outcome, "already-present");
  assert.deepEqual(duplicate.state, state);

  state = moveStudySessionItem(state, "crb-formula", -1, THIRD_TIME);
  assert.deepEqual(state.items.map((item) => item.articleId), ["crb-formula", "attention-basics"]);
  state = activateStudySessionItem(state, "attention-basics", THIRD_TIME);
  assert.equal(state.activeArticleId, "attention-basics");

  const position = getStudySessionPosition(state, "attention-basics");
  assert.equal(position?.index, 1);
  assert.equal(position?.total, 2);
  assert.equal(position?.previous?.articleId, "crb-formula");
  assert.equal(position?.next, null);

  state = removeStudySessionItem(state, "attention-basics", THIRD_TIME);
  assert.equal(state.activeArticleId, "crb-formula");
  assert.deepEqual(state.items.map((item) => item.articleId), ["crb-formula"]);
  assert.deepEqual(clearStudySession(state, THIRD_TIME), createEmptyStudySession(THIRD_TIME));
});

test("bulk append preserves queue order and active Article while classifying every input", () => {
  const original = parseStudySessionStore(JSON.stringify({
    version: 1,
    active_article_id: "existing-b",
    updated_at: FIRST_TIME,
    items: [
      { article_id: "existing-a", title: "Existing A", section_id: null, added_at: FIRST_TIME },
      { article_id: "existing-b", title: "Existing B", section_id: null, added_at: FIRST_TIME },
    ],
  })).state;

  const mutation = addStudySessionItems(original, [
    { articleId: "new-a", title: "New A" },
    { articleId: "existing-a", title: "Existing A" },
    { articleId: "unsafe/id", title: "Unsafe" },
    { articleId: "new-a", title: "New A duplicate" },
    { articleId: "new-b", title: "New B" },
  ], SECOND_TIME);

  assert.deepEqual(mutation.state.items.map((item) => item.articleId), [
    "existing-a",
    "existing-b",
    "new-a",
    "new-b",
  ]);
  assert.equal(mutation.state.activeArticleId, "existing-b");
  assert.deepEqual(mutation.outcomes, {
    added: 2,
    alreadyPresent: 2,
    invalid: 1,
    capacityOmitted: 0,
  });
  assert.equal(mutation.changed, true);
});

test("bulk append reports 19/20 and 20/20 capacity without replacing existing Articles", () => {
  const nineteen = Array.from({ length: STUDY_SESSION_ITEM_LIMIT - 1 }, (_, index) => ({
    article_id: `existing-${String(index).padStart(2, "0")}`,
    title: `Existing ${index}`,
    section_id: null,
    added_at: FIRST_TIME,
  }));
  const state = parseStudySessionStore(JSON.stringify({
    version: 1,
    active_article_id: "existing-05",
    updated_at: FIRST_TIME,
    items: nineteen,
  })).state;

  const first = addStudySessionItems(state, [
    { articleId: "new-a", title: "New A" },
    { articleId: "new-b", title: "New B" },
  ], SECOND_TIME);
  assert.equal(first.state.items.length, STUDY_SESSION_ITEM_LIMIT);
  assert.equal(first.state.items.at(-1)?.articleId, "new-a");
  assert.equal(first.state.activeArticleId, "existing-05");
  assert.deepEqual(first.outcomes, {
    added: 1,
    alreadyPresent: 0,
    invalid: 0,
    capacityOmitted: 1,
  });

  const second = addStudySessionItems(first.state, [
    { articleId: "new-a", title: "New A" },
    { articleId: "new-c", title: "New C" },
  ], THIRD_TIME);
  assert.equal(second.state, first.state);
  assert.equal(second.changed, false);
  assert.deepEqual(second.outcomes, {
    added: 0,
    alreadyPresent: 1,
    invalid: 0,
    capacityOmitted: 1,
  });
});

test("queue rejects invalid additions and preserves a strict twenty-item bound", () => {
  let state = createEmptyStudySession();
  assert.equal(
    addStudySessionItem(state, { articleId: "unsafe/id", title: "Unsafe", sectionId: null }, FIRST_TIME).outcome,
    "invalid",
  );
  assert.equal(
    addStudySessionItem(state, { articleId: "raw-id", title: "raw-id", sectionId: null }, FIRST_TIME).outcome,
    "invalid",
  );

  for (let index = 0; index < STUDY_SESSION_ITEM_LIMIT; index += 1) {
    state = addStudySessionItem(
      state,
      { articleId: `bounded-${index}`, title: `Bounded Article ${index}`, sectionId: null },
      FIRST_TIME,
    ).state;
  }
  const full = addStudySessionItem(
    state,
    { articleId: "one-too-many", title: "One Too Many", sectionId: null },
    SECOND_TIME,
  );
  assert.equal(full.outcome, "full");
  assert.equal(full.state.items.length, STUDY_SESSION_ITEM_LIMIT);
});

test("session Reader destinations retain the canonical session return path", () => {
  const item = {
    articleId: "attention-basics",
    title: "Attention机制入门",
    sectionId: "scaled-attention",
    addedAt: FIRST_TIME,
  };

  assert.equal(
    createStudySessionReaderHref(item),
    "/articles/attention-basics?from=%2Fsession#scaled-attention",
  );
});
