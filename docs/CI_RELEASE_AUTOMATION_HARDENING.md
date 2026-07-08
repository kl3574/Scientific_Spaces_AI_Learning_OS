# CI and Release Automation Hardening

## Current Baseline

The repository has already released Scientific Spaces AI Learning OS v1.0.0 MVP.

- Release URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/releases/tag/v1.0.0`
- Release CI evidence: `docs/RELEASE_CI_EVIDENCE_v1.0.0.md`
- Previous release evidence run: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28928542749`
- Previous limitation: CI supported `pull_request` and manual `workflow_dispatch`, but not `push` to `main`.
- Previous release evidence process: manual workflow dispatch against the exact release tag.

This task is part of the post-MVP v1.1 Sprint 0 CI and release automation hardening work. It does not implement product features.

## Workflow Changes

Modified workflow file:

- `.github/workflows/ci.yml`

Configured triggers:

- `pull_request`
- `push` to `main`
- `push` to `v*` tags
- `workflow_dispatch`

Jobs:

- `Backend pytest`
  - Python: `3.11`
  - Command: `uv run --project backend --extra dev pytest -q`
  - Uses fake/test providers by default.
  - Does not require a real API key or real Zotero library.
- `Frontend build`
  - Node: `22`
  - Install command: `npm ci`
  - Build command: `npm run build`
  - Does not require a running backend.
- `Docker compose smoke`
  - Command: `docker compose up --build -d`
  - Backend smoke: `http://localhost:8000/health`
  - Frontend smoke: `http://localhost:3000`
  - Runs only for manual `workflow_dispatch` or `v*` tag pushes.

Docker smoke behavior was intentionally narrowed so PR and `main` push feedback is not blocked by Docker-only environment failures. Docker remains available for manual release evidence and tag-level release validation.

## Coverage

Backend pytest:

- Covered on PR.
- Covered on `main` push.
- Covered on `v*` tag push.
- Covered on manual workflow dispatch.

Frontend build:

- Covered on PR.
- Covered on `main` push.
- Covered on `v*` tag push.
- Covered on manual workflow dispatch.

Docker compose smoke:

- Covered on `v*` tag push.
- Covered on manual workflow dispatch.
- Not run on PR or normal `main` push.

Manual workflow dispatch:

- Retained for release evidence on an exact ref or tag.

## Release Automation Boundary

This task does not move the `v1.0.0` tag.

This task does not create a new GitHub Release.

This task does not rewrite the existing v1.0.0 release notes.

This task does not automate release publishing. Release creation remains manual. The workflow only hardens test/build automation and release-evidence readiness.

## Validation Evidence

Local backend test:

```text
uv run --project backend --extra dev pytest -q
63 passed, 2 skipped in 3.58s
```

Local frontend build:

```text
npm run build
Next.js 15.5.20 build completed successfully.
Generated routes: /, /articles, /articles/[id], /graph, /tutor, /zotero.
```

Workflow syntax sanity:

```text
git diff --check
PASS

ruby -e "require 'yaml'; YAML.load_file('.github/workflows/ci.yml'); puts 'workflow yaml parse ok'"
workflow yaml parse ok
```

GitHub CLI:

```text
gh auth status
Logged in to github.com account kl3574

gh workflow list
CI active
```

GitHub Actions result:

- The updated workflow is expected to run automatically after this commit is pushed to `main`.
- The post-push run should be checked as part of the final execution report for this task.

## Known Risks

- Push-triggered CI increases GitHub Actions usage.
- Docker compose smoke remains dependent on GitHub-hosted runner Docker behavior.
- Docker smoke is not a blocker for PR/main push backend/frontend validation.
- Release creation remains manual.
- Tag-level release evidence still requires checking the exact tag/ref run before publishing a release.

## Recommendation

A: CI hardening complete

