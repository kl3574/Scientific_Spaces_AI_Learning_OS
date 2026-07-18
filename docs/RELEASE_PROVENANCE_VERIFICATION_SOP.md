# Release Provenance Verification SOP

## Trust Boundary

Release evidence is eligible only on an exact `refs/tags/v*` ref reached by a tag push or explicit `workflow_dispatch` against that tag. Ordinary pull requests and branch pushes cannot authorize or publish release evidence.

P3-005 implements a local `--dry-run --no-publish` boundary only. It grants no release, tag, OIDC, attestation, package, or contents write permission.

## Preconditions

- Backend pytest: PASS
- Frontend build: PASS
- Docker compose smoke: PASS for the tag/manual run
- Workflow policy: PASS
- Dependency audit: PASS
- Secret audit: PASS
- SBOM validation: PASS
- Tag object and peeled target are locally verifiable

## Local No-Publish Check

```bash
SBOM_DIR="$(mktemp -d)"
python scripts/security/build_sbom.py --output-dir "$SBOM_DIR"
python scripts/security/validate_sbom.py "$SBOM_DIR"
python scripts/release/build_release_evidence.py \
  --tag v1.1.0 \
  --sbom-dir "$SBOM_DIR" \
  --dry-run \
  --no-publish
python scripts/release/verify_release_evidence.py \
  --evidence "$SBOM_DIR/release-evidence.json" \
  --no-network
```

On a branch, `would_authorize_publish` and `publish_authorized` must both be false. The evidence binds the current commit, tag object type and target, workflow identity/ref/event, each SBOM digest, and the exact eligible artifact list.

## Eligible Artifacts

Only these generated dependency documents are eligible in the current design:

- `backend.cdx.json`
- `frontend.cdx.json`
- `combined.cdx.json`

Corpus, Article exports, PDFs, HTML, images, databases, backups, Graph/RAG/FAISS data, local runtime stores, private Zotero/user data, credentials, and scanner caches are never eligible.

## Failure Handling

Stop release processing if the ref is not an exact tag, the event is untrusted, the tag target differs from the SBOM commit, any prerequisite gate fails, an unknown artifact appears, a digest differs, or evidence contains a local path or secret-like value. Do not move a tag, create a Release, or bypass a failed check.

Future formal attestation publication requires a separately reviewed workflow revision, narrowly scoped permissions, and explicit release authorization.
