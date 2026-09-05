import { strict as assert } from "node:assert";
import test from "node:test";

import type { LearningNote } from "../src/lib/learning";
import {
  createReaderNoteDeleteIntent,
  createReaderMutationOperation,
  mergeCreatedLearningNote,
  mergeUpdatedLearningNote,
  ownsReaderNoteDeleteIntent,
  ownsReaderMutation,
  removeLearningNote,
} from "../src/lib/readerLearningMutations";

const ALPHA_NOTE: LearningNote = {
  note_id: "note-alpha",
  article_id: "article-a",
  content: "Alpha",
  created_at: "2026-09-05T00:00:00Z",
  updated_at: "2026-09-05T00:00:00Z",
};

const BETA_NOTE: LearningNote = {
  note_id: "note-beta",
  article_id: "article-a",
  content: "Beta",
  created_at: "2026-09-05T00:01:00Z",
  updated_at: "2026-09-05T00:01:00Z",
};

test("Reader mutation ownership requires exact Article generation, operation, and kind", () => {
  const operation = createReaderMutationOperation("article-a", 7, 11, "note-create");

  assert.equal(ownsReaderMutation(operation, operation, "article-a", 7), true);
  assert.equal(
    ownsReaderMutation(
      createReaderMutationOperation("article-a", 7, 10, "note-create"),
      operation,
      "article-a",
      7,
    ),
    false,
  );
  assert.equal(
    ownsReaderMutation(
      createReaderMutationOperation("article-a", 7, 11, "bookmark-add"),
      operation,
      "article-a",
      7,
    ),
    false,
  );
  assert.equal(ownsReaderMutation(operation, operation, "article-b", 7), false);
  assert.equal(ownsReaderMutation(operation, operation, "article-a", 8), false);
  assert.equal(ownsReaderMutation(null, operation, "article-a", 7), false);

  for (const kind of [
    "bookmark-add",
    "bookmark-remove",
    "note-create",
    "note-update",
    "note-delete",
  ] as const) {
    const exact = createReaderMutationOperation("article-a", 9, 14, kind, "note-alpha");
    assert.equal(ownsReaderMutation(exact, exact, "article-a", 9), true, kind);
  }
});

test("Reader note deletion intent requires exact Article generation and note identity", () => {
  const intent = createReaderNoteDeleteIntent("article-a", 7, "note-alpha");

  assert.deepEqual(intent, {
    articleId: "article-a",
    generation: 7,
    noteId: "note-alpha",
  });
  assert.equal(ownsReaderNoteDeleteIntent(intent, intent, "article-a", 7), true);
  assert.equal(
    ownsReaderNoteDeleteIntent(
      createReaderNoteDeleteIntent("article-a", 7, "note-beta"),
      intent,
      "article-a",
      7,
    ),
    false,
  );
  assert.equal(
    ownsReaderNoteDeleteIntent(
      createReaderNoteDeleteIntent("article-b", 7, "note-alpha"),
      intent,
      "article-a",
      7,
    ),
    false,
  );
  assert.equal(ownsReaderNoteDeleteIntent(intent, intent, "article-b", 7), false);
  assert.equal(ownsReaderNoteDeleteIntent(intent, intent, "article-a", 8), false);
  assert.equal(ownsReaderNoteDeleteIntent(null, intent, "article-a", 7), false);
});

test("created notes are prepended once and merged by note identity", () => {
  assert.deepEqual(mergeCreatedLearningNote([ALPHA_NOTE], BETA_NOTE, "article-a"), [
    BETA_NOTE,
    ALPHA_NOTE,
  ]);

  const revisedBeta = { ...BETA_NOTE, content: "Beta revised" };
  assert.deepEqual(
    mergeCreatedLearningNote([BETA_NOTE, ALPHA_NOTE], revisedBeta, "article-a"),
    [revisedBeta, ALPHA_NOTE],
  );
  assert.deepEqual(
    mergeCreatedLearningNote([BETA_NOTE, ALPHA_NOTE, BETA_NOTE], revisedBeta, "article-a"),
    [revisedBeta, ALPHA_NOTE],
  );
});

test("note merges reject cross-Article responses", () => {
  const crossArticle = { ...BETA_NOTE, article_id: "article-b" };
  const current = [ALPHA_NOTE];

  assert.equal(mergeCreatedLearningNote(current, crossArticle, "article-a"), current);
  assert.equal(mergeUpdatedLearningNote(current, crossArticle, "article-a"), current);
});

test("updated notes keep their position and unknown notes do not appear", () => {
  const updatedAlpha = {
    ...ALPHA_NOTE,
    content: "Alpha updated",
    updated_at: "2026-09-05T01:00:00Z",
  };

  assert.deepEqual(
    mergeUpdatedLearningNote([BETA_NOTE, ALPHA_NOTE], updatedAlpha, "article-a"),
    [BETA_NOTE, updatedAlpha],
  );
  assert.deepEqual(
    mergeUpdatedLearningNote([ALPHA_NOTE, BETA_NOTE, ALPHA_NOTE], updatedAlpha, "article-a"),
    [updatedAlpha, BETA_NOTE],
  );
  assert.deepEqual(mergeUpdatedLearningNote([BETA_NOTE], updatedAlpha, "article-a"), [BETA_NOTE]);
});

test("note removal uses the supplied current state and leaves unknown ids unchanged", () => {
  assert.deepEqual(removeLearningNote([BETA_NOTE, ALPHA_NOTE], "note-beta"), [ALPHA_NOTE]);
  const current = [ALPHA_NOTE];
  assert.equal(removeLearningNote(current, "missing"), current);
});
