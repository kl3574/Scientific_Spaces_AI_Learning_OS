# SBOM Verification SOP

## Scope

P3-005 generates temporary Backend, Frontend, and combined CycloneDX 1.6 JSON SBOMs from `backend/uv.lock` and `frontend/package-lock.json`. Generated SBOMs are evidence artifacts, not repository source files, and must not be committed.

## Build And Validate

```bash
SBOM_DIR="$(mktemp -d)"
python scripts/security/build_sbom.py --output-dir "$SBOM_DIR"
python scripts/security/validate_sbom.py "$SBOM_DIR"
```

The validator downloads the schema through the official CycloneDX GitHub repository at the immutable commit and digest recorded in `.github/security/sbom-policy.json`. The validator executable is version-pinned in `.github/security/tool-versions.json`.

## Required Checks

- `bomFormat` is `CycloneDX` and `specVersion` is `1.6`.
- Backend components exactly cover `backend/uv.lock`.
- Frontend components exactly cover `frontend/package-lock.json`.
- Dependency references resolve to known components.
- Reliable lockfile hashes are retained where available.
- A second build at the same commit is byte-identical.
- Combined output is no larger than 5 MiB.
- Forbidden runtime/private artifact count is zero.
- No local absolute path or secret-like value is present.
- Official schema validation passes.

## Reproducibility

Build into two independent temporary directories and compare all three files byte for byte. A difference is a blocker until its source is explained and removed.

## Cleanup And Publication

Delete the temporary directories after verification. Do not commit SBOM JSON, scanner caches, corpus data, PDF/HTML/image content, databases, Graph/RAG state, backups, or private data.

P3-005 validates only local no-publish release evidence. Any future SBOM attachment or attestation publication requires an exact release tag, successful release gates, and separate authorization.
