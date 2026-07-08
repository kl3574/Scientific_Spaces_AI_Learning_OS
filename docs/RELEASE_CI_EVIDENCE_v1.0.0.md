# v1.0.0 Release CI Evidence

## Release Target

- tag: `v1.0.0`
- tag target commit: `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6`
- release URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/releases/tag/v1.0.0`

## Workflow

- workflow name: `CI`
- workflow file: `.github/workflows/ci.yml`
- trigger: `workflow_dispatch`
- ref: `v1.0.0`

## Run Result

- run id: `28931334219`
- run URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28931334219`
- status: `completed`
- conclusion: `success`
- started at: `2026-07-08T09:12:19Z`
- completed at: `2026-07-08T09:13:52Z`
- event: `workflow_dispatch`
- head branch/ref: `v1.0.0`
- head SHA: `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6`

## Checks Covered

- backend pytest: PASS
  - job: `Backend pytest`
  - job id: `85830921768`
  - started at: `2026-07-08T09:12:37Z`
  - completed at: `2026-07-08T09:12:53Z`
- frontend build: PASS
  - job: `Frontend build`
  - job id: `85830921749`
  - started at: `2026-07-08T09:12:37Z`
  - completed at: `2026-07-08T09:13:15Z`
- Docker compose smoke: PASS
  - job: `Docker compose smoke`
  - job id: `85830921664`
  - started at: `2026-07-08T09:12:42Z`
  - completed at: `2026-07-08T09:13:51Z`

## Evidence Summary

Release CI Evidence:

PASS

The manual workflow ran against the `v1.0.0` tag and completed successfully. The workflow covers the required backend pytest and frontend build checks. It also covers Docker compose smoke and that job passed.

## Limitations

- CI is manually triggered with `workflow_dispatch`, not push-triggered.
- Local Docker was unavailable in prior local audits, but Docker compose smoke passed in GitHub Actions for this release evidence run.
- GitHub Actions emitted a Node.js 20 deprecation warning for upstream actions runtime behavior. The warning did not fail the workflow.
- The installed local `gh` version does not support `gh run view --jobs`; job evidence was collected with `gh run view --json jobs`.

## Recommendation

A: Release evidence complete
