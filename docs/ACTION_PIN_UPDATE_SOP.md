# GitHub Action Pin Update SOP

## Policy

Every third-party `uses:` entry must reference a verified 40-character commit SHA. A readable release tag comment is required, but the comment is not the trust anchor.

The authoritative local map is `.github/security/action-pins.json`.

## Update Procedure

1. Select a released version from the Action owner's official GitHub repository.
2. Resolve that tag through the official Git ref API or an equivalent authenticated read-only Git operation.
3. If the tag is annotated, peel it to the commit used by GitHub Actions.
4. Confirm the repository owner, release URL, version tag, and final commit SHA.
5. Update every matching `uses:` line and retain `# vX.Y.Z` beside the SHA.
6. Update `.github/security/action-pins.json` with the same SHA, tag, release URL, verification date, and method.
7. Review the Action's release notes and changed permissions before accepting the update.

Never resolve a pin from an untrusted mirror, a fork, a branch name, or a mutable major tag.

## Verification

```bash
python scripts/security/check_workflow_policy.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover \
  -s scripts/security/tests -p 'test_*.py' -v
git diff -- .github/workflows .github/security/action-pins.json
```

Acceptance requires:

- `third_party_action_full_sha_pin_rate = 1.0`
- `workflow_permissions_explicit_rate = 1.0`
- no new write permission or ordinary-branch publication path

Action updates require normal code review and CI. Dependabot may propose dependency updates, but it does not auto-merge, tag, or release.
