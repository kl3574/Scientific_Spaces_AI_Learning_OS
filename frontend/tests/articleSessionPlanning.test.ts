import { strict as assert } from "node:assert";
import test from "node:test";

import {
  createArticleSessionCapturePlan,
  formatArticleSessionCaptureOutcome,
  getArticleLearningStatusLabel,
  ownsArticleResultGeneration,
  reconcileArticleSelection,
  updateArticleSelection,
} from "../src/lib/articleSessionPlanning";
import {
  STUDY_SESSION_ITEM_LIMIT,
  addStudySessionItems,
  createEmptyStudySession,
  type StudySessionState,
} from "../src/lib/studySession";

const ARTICLES = [
  { id: "article-a", title: "Alpha" },
  { id: "article-b", title: "Beta" },
  { id: "article-c", title: "Gamma" },
];

test("request ownership is exact across A-B-A generations", () => {
  assert.equal(ownsArticleResultGeneration(1, 3), false);
  assert.equal(ownsArticleResultGeneration(2, 3), false);
  assert.equal(ownsArticleResultGeneration(3, 3), true);
});

test("selection reconciles to the latest visible page in displayed order", () => {
  assert.deepEqual(
    reconcileArticleSelection(ARTICLES, ["article-c", "stale", "article-a"]),
    ["article-a", "article-c"],
  );
  assert.deepEqual(reconcileArticleSelection([{ id: "article-z", title: "Zeta" }], ["article-a"]), []);
});

test("selection toggle rejects non-visible ids and remains duplicate-free", () => {
  assert.deepEqual(updateArticleSelection(ARTICLES, [], "article-b", true), ["article-b"]);
  assert.deepEqual(updateArticleSelection(ARTICLES, ["article-b"], "article-b", true), ["article-b"]);
  assert.deepEqual(updateArticleSelection(ARTICLES, ["article-b"], "unknown", true), ["article-b"]);
  assert.deepEqual(updateArticleSelection(ARTICLES, ["article-a", "article-b"], "article-a", false), ["article-b"]);
});

test("learning-state omission is unread only after a successful load", () => {
  const states = {
    "article-a": { article_id: "article-a", status: "completed" as const },
  };

  assert.equal(getArticleLearningStatusLabel("loaded", states, "article-a"), "completed");
  assert.equal(getArticleLearningStatusLabel("loaded", states, "article-b"), "unread");
  assert.equal(getArticleLearningStatusLabel("loading", states, "article-a"), "Status loading");
  assert.equal(getArticleLearningStatusLabel("error", states, "article-a"), "Status unavailable");
});

test("capture reload plan appends selected Articles in visible order and preserves active identity", () => {
  const existing = addStudySessionItems(
    createEmptyStudySession(),
    [{ articleId: "existing", title: "Existing Article" }],
    "2026-09-01T00:00:00.000Z",
  ).state;
  const plan = createArticleSessionCapturePlan(
    ARTICLES,
    ["article-c", "article-a"],
    existing,
    "2026-09-05T00:00:00.000Z",
  );

  assert.deepEqual(plan.selectedArticles.map((article) => article.id), ["article-a", "article-c"]);
  assert.deepEqual(plan.mutation.state.items.map((item) => item.articleId), ["existing", "article-a", "article-c"]);
  assert.equal(plan.mutation.state.activeArticleId, "existing");
  assert.deepEqual(plan.remainingSelectionIds, []);
  assert.equal(plan.requiresSave, true);
});

test("capture activates the first accepted Article only when the reloaded queue is empty", () => {
  const plan = createArticleSessionCapturePlan(
    ARTICLES,
    ["article-b", "article-a"],
    createEmptyStudySession(),
    "2026-09-05T00:00:00.000Z",
  );

  assert.deepEqual(plan.mutation.state.items.map((item) => item.articleId), ["article-a", "article-b"]);
  assert.equal(plan.mutation.state.activeArticleId, "article-a");
});

test("duplicate and capacity outcomes clear only records resolved in the queue", () => {
  const fullMinusOne = sessionWithItems(STUDY_SESSION_ITEM_LIMIT - 1);
  const visible = [
    { id: "existing-0", title: "Existing duplicate" },
    { id: "new-a", title: "New A" },
    { id: "new-b", title: "New B" },
  ];
  const plan = createArticleSessionCapturePlan(
    visible,
    visible.map((article) => article.id),
    fullMinusOne,
    "2026-09-05T00:00:00.000Z",
  );

  assert.deepEqual(plan.mutation.outcomes, {
    added: 1,
    alreadyPresent: 1,
    invalid: 0,
    capacityOmitted: 1,
  });
  assert.deepEqual(plan.remainingSelectionIds, ["new-b"]);
  assert.equal(plan.mutation.state.activeArticleId, "existing-0");
});

test("duplicate-only capture requires no persistence rewrite", () => {
  const existing = addStudySessionItems(
    createEmptyStudySession(),
    [{ articleId: "article-a", title: "Alpha Article" }],
    "2026-09-01T00:00:00.000Z",
  ).state;
  const plan = createArticleSessionCapturePlan(
    ARTICLES,
    ["article-a"],
    existing,
    "2026-09-05T00:00:00.000Z",
  );

  assert.equal(plan.requiresSave, false);
  assert.equal(plan.mutation.state, existing);
  assert.deepEqual(plan.remainingSelectionIds, []);
  assert.deepEqual(plan.mutation.outcomes, {
    added: 0,
    alreadyPresent: 1,
    invalid: 0,
    capacityOmitted: 0,
  });
});

test("invalid selected records remain selected after an otherwise successful plan", () => {
  const invalid = [{ id: "../private", title: "Invalid" }];
  const plan = createArticleSessionCapturePlan(
    invalid,
    ["../private"],
    createEmptyStudySession(),
    "2026-09-05T00:00:00.000Z",
  );

  assert.deepEqual(plan.mutation.outcomes, {
    added: 0,
    alreadyPresent: 0,
    invalid: 1,
    capacityOmitted: 0,
  });
  assert.deepEqual(plan.remainingSelectionIds, ["../private"]);
  assert.equal(plan.requiresSave, false);
});

test("invalid candidate sharing an existing id is not cleared as a duplicate", () => {
  const existing = addStudySessionItems(
    createEmptyStudySession(),
    [{ articleId: "article-a", title: "Valid existing title" }],
    "2026-09-01T00:00:00.000Z",
  ).state;
  const invalidVisible = [{ id: "article-a", title: "article-a" }];
  const plan = createArticleSessionCapturePlan(
    invalidVisible,
    ["article-a"],
    existing,
    "2026-09-05T00:00:00.000Z",
  );

  assert.deepEqual(plan.mutation.outcomes, {
    added: 0,
    alreadyPresent: 0,
    invalid: 1,
    capacityOmitted: 0,
  });
  assert.deepEqual(plan.remainingSelectionIds, ["article-a"]);
  assert.equal(plan.requiresSave, false);
});

test("capture outcome text reports every aggregate without recommendation claims", () => {
  assert.equal(
    formatArticleSessionCaptureOutcome({
      added: 2,
      alreadyPresent: 1,
      invalid: 1,
      capacityOmitted: 3,
    }),
    "2 added; 1 already present; 1 invalid; 3 omitted by capacity.",
  );
});

function sessionWithItems(count: number): StudySessionState {
  return addStudySessionItems(
    createEmptyStudySession(),
    Array.from({ length: count }, (_, index) => ({
      articleId: `existing-${index}`,
      title: `Existing ${index}`,
    })),
    "2026-09-01T00:00:00.000Z",
  ).state;
}
