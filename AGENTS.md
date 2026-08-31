# AGENTS.md

This file defines repository-level execution rules for coding agents.

## Authoritative Task Context

1. Read `docs/tasks/CURRENT_TASK.md` before starting work.
2. Follow the canonical task specification referenced by that file.
3. Read `alignment.md` for the user-approved scope, deliverables, acceptance
   criteria, and authorization boundaries.
4. Read `docs/00_PROJECT_STATE.md` and the relevant roadmap section when task
   status or milestone context matters.
5. Treat attachment paths as transport locations only. Once a task is
   persisted under `docs/tasks/`, semantic task requirements take precedence
   over attachment identity changes.

If no active task exists, or the requested work materially changes the goal,
scope, allowed paths, prohibitions, deliverables, acceptance criteria, or Git
actions, obtain explicit user alignment before modifying files or external
state.

## Startup Checks

Before implementation:

1. Check `REWORK.md` and `.audit/`. Unresolved failures take priority.
2. Inspect the current branch, HEAD, upstream relationship, worktree, index,
   and untracked files.
3. Preserve pre-existing user changes. Never reset, restore, clean, stash,
   rebase, amend, or overwrite them without explicit authorization.
4. Confirm that the planned work fits the active canonical task.

## Scope And Engineering Rules

- Prefer existing project patterns, interfaces, dependencies, and ownership
  boundaries.
- Keep changes limited to the active task. Record out-of-scope defects instead
  of silently widening the implementation.
- Do not change frozen modules, published contracts, source records, or release
  metadata unless the active task explicitly authorizes it.
- Use structured parsers and APIs instead of ad hoc text manipulation when
  practical.
- Use `apply_patch` for manual file edits.
- Add focused tests proportional to behavior and risk.
- Run every validation command required by the active task and report exact
  results, including skipped or unavailable gates.

## Data, Artifact, And Secret Safety

- Never commit credentials, tokens, cookies, private keys, `.env`, private
  databases, runtime stores, caches, browser profiles, traces, screenshots,
  generated corpora, PDFs, downloaded HTML, or other private artifacts unless
  the active task explicitly requires and permits a specific artifact.
- Keep temporary evidence outside the repository and remove it after extracting
  the required bounded result.
- Do not access source sites, private libraries, real providers, or paid APIs
  without explicit task authorization.
- Treat local readback, cloud synchronization, remote publication, and release
  status as separate claims requiring separate evidence.

## Git And External Actions

- Commit, push, CI inspection, tag creation, release creation, and external
  writes require explicit authorization in the active alignment.
- Before committing, inspect `git status`, `git diff --stat`, staged changes,
  untracked files, and forbidden artifacts.
- Never force-push, move published tags, rewrite shared history, or create a
  release unless explicitly authorized.
- When exact-SHA CI is required, verify that the run head SHA matches the
  intended commit and record job-level results.

## Completion

- Update the canonical task, project state, evidence report, and roadmap as
  required by the active task.
- Do not claim PASS or closure until every acceptance criterion has current,
  direct evidence.
- Finish with a clean, synchronized worktree when the active task requires it.
