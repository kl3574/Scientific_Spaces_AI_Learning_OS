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

- run id: `28928542749`
- run URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28928542749`
- status: `completed`
- conclusion: `success`
- started at: `2026-07-08T08:24:56Z`
- completed at: `2026-07-08T08:26:10Z`
- event: `workflow_dispatch`
- head branch/ref: `v1.0.0`
- head SHA: `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6`

## Checks Covered

- backend pytest: PASS
  - job: `Backend pytest`
  - job id: `85821785344`
  - started at: `2026-07-08T08:25:00Z`
  - completed at: `2026-07-08T08:25:16Z`
- frontend build: PASS
  - job: `Frontend build`
  - job id: `85821785336`
  - started at: `2026-07-08T08:25:01Z`
  - completed at: `2026-07-08T08:25:41Z`
- Docker compose smoke: PASS
  - job: `Docker compose smoke`
  - job id: `85821785349`
  - started at: `2026-07-08T08:25:02Z`
  - completed at: `2026-07-08T08:26:09Z`

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
