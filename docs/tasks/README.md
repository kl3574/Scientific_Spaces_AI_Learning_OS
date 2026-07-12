# Canonical Task Specifications

## Purpose

`docs/tasks/` stores durable, auditable specifications for the current task and historical tasks. These files preserve task meaning independently of temporary chat or attachment transport paths.

## Source-of-Truth Priority

1. `AGENTS.md`
   - Repository governance, safety, alignment, and execution boundaries.
2. `docs/tasks/CURRENT_TASK.md`
   - The single entry point for the current task.
   - Points to the current canonical task specification.
3. `docs/tasks/<TASK_ID>_*.md`
   - Durable task semantics, including scope, prohibitions, deliverables, acceptance, and Git plan.
4. `alignment.md`
   - The user-confirmed execution alignment for the current repository state.
   - Must reference the canonical task specification.
5. `docs/00_PROJECT_STATE.md`
   - Current version, phase, status, completed tasks, and next task.
6. `docs/V*_ROADMAP.md`
   - Milestone ordering, dependencies, and deferred scope.
7. Task reports and audit reports
   - Evidence from completed execution, verification, and blockers.
8. Codex attachments and pasted prompts
   - Transport input for a new task only.
   - They stop being the long-term authority after repository persistence.

## Attachment Policy

- An attachment UUID and filesystem path are transport identity, not durable task identity.
- Re-pasting the same task can produce a different path, inode, timestamp, line count, byte count, or raw SHA-256.
- A path change alone does not mean the task changed.
- Task identity is determined by its goals, scope, prohibited actions, deliverables, acceptance criteria, and Git requirements.
- A new task may initially be recovered from an attachment.
- After the user confirms alignment, its semantics must be persisted in `docs/tasks/<TASK_ID>_<NAME>.md`.
- Once committed, the repository file becomes the long-term canonical source.
- Later attachment UUID changes must not cause recursive realignment unless a substantive task dimension changes.

## Task Lifecycle

```text
DRAFT
-> ALIGNMENT REQUIRED
-> APPROVED
-> IN PROGRESS
-> PASS / CONDITIONAL / BLOCKED
-> CLOSED
```

`APPROVED FOR ALIGNMENT` means architecture and scope are ready to be aligned. It is not implementation authorization.

## Completion Policy

When a task finishes, synchronize all of the following:

- canonical task status;
- execution or verification report;
- `docs/00_PROJECT_STATE.md`;
- `docs/tasks/CURRENT_TASK.md`;
- completion commit SHA;
- CI run URL and result;
- next task and its authorization state.

Do not mark implementation complete from planning evidence, and do not treat a pushed task specification as authorization to execute the task it describes.
