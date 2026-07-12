# v1.2 Scoped Threat Model

Status: Approved planning threat model

## Scope and Method

This model covers Structured Reference Extraction, read-only Zotero candidate matching, opt-in Real Provider Evaluation, and CI Security/Release Provenance. Article text, Zotero fields, provider responses, pull-request code, dependencies, caches, and release metadata are untrusted inputs. Every threat has an owner and a testable control.

## Assets

- Frozen Article content, identity, metadata, and corpus fingerprint.
- Reference records, evidence, manifests, indexes, and build integrity.
- Tier 1 user-reviewed decisions and existing M5 local links.
- Private Zotero library metadata and local API availability.
- Provider credentials, budgets, sent prompts/snippets, and evaluation output.
- M3-M7 grounding, refusal, provenance, and compatibility contracts.
- Repository source, dependency locks, CI credentials, workflow identity, SBOM, tags, and release attestations.
- Local absolute paths, user data, runtime corpus, databases, backups, RAG/Graph assets, and other forbidden artifacts.

## Actors

- Local operator/reader: trusted to initiate bounded local actions but can make mistakes.
- Repository maintainer/reviewer: trusted to approve changes and suppressions; account compromise remains possible.
- Malicious or malformed Article/Zotero content: untrusted data, not code or instructions.
- External provider: legitimate service with independent logging, retention, model, cost, and failure behavior.
- Pull-request contributor and dependency/Action publisher: untrusted until reviewed and verified.
- Attacker with repository, CI, dependency, provider, or local-process access.

## Entry Points

- Article Markdown passed to the planned extractor.
- DOI/arXiv/URL/citation candidates and `/v1.2` query parameters.
- Zotero local HTTP API responses and item fields.
- Real-provider CLI flags, environment configuration, requests, responses, and output directories.
- GitHub workflow YAML, Actions, lockfiles, pull requests, caches, scanner output, tags, SBOMs, and attestations.

## Trust Boundaries

| ID | Boundary |
| --- | --- |
| TB1 | Tracked repository to ignored local runtime/private data |
| TB2 | Frozen Article store to rebuildable Reference Store |
| TB3 | Validated local Reference Store to API/browser display |
| TB4 | Application to separate local Zotero Desktop API |
| TB5 | Local evaluation runner to external provider network |
| TB6 | Untrusted change/dependency to GitHub CI runner |
| TB7 | CI runner to privileged release attestation service |

## Reference Extraction Threats

| Asset | Boundary | Threat | Impact | Mitigation | Verification | Residual risk | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Local user/network | TB2/TB3 | Malicious URL uses `file:`, `javascript:`, `data:`, loopback, or executable scheme | Local file disclosure, script execution, unsafe navigation | Allow only HTTP(S) for external references; classify local/internal separately; sanitize UI links | Scheme fixtures, API schema tests, browser safe-link tests | A valid HTTP(S) destination can still be malicious | Reference/API owner |
| Credentials | TB2/TB3 | URL contains `user:password@host` | Secret persisted or displayed | Reject candidate identity, redact userinfo in evidence, retain only one-way raw hash | Credential URL fixtures; secret/artifact scan | Credentials embedded in surrounding free text may require broader redaction | Security owner |
| Extractor availability | TB2 | Catastrophic regex backtracking (ReDoS) | CPU exhaustion and blocked build | Linear/bounded patterns, input/candidate limits, per-Article work budget; avoid nested ambiguous regex | Pathological fixture timing and timeout tests | Novel pathological Unicode/token patterns | Reference owner |
| Store/API bounds | TB2/TB3 | Pathologically long citation or huge candidate count | Memory/disk/API denial of service | Per-candidate, evidence, Article, total-count, and page/provenance bounds; classify overflow | Long/math-heavy fixtures and bounds tests | Legitimate very long citations may be classified for review | Reference owner |
| Reference identity | TB2/TB3 | Unicode spoofing or confusable identifier | False identity, misleading UI | Preserve raw evidence, conservative normalization, IDNA host handling, display canonical + raw classification, never infer exact text identity | Homoglyph/IDN fixtures and human review | Human readers may still misread confusables | Reference/UI owner |
| DOI/arXiv identity | TB2 | Over-aggressive punctuation/version normalization | Distinct works/versions merged | Version-aware canonical keys; strip only proven wrapper punctuation; possible groups instead of merge | Exact normalization and negative fixtures | Unseen legacy syntax may remain unsupported | Reference owner |
| URL identity | TB2 | Tracking cleanup removes identity-bearing query/fragment | Distinct resources merged | Remove only explicit tracking allowlist; preserve unknown query order/duplicates and non-empty fragments | Query/fragment fixtures; dedup negative tests | Some provider-specific tracking keys remain | Reference owner |
| Article provenance | TB2 | Evidence or Article identity is altered/tampered | Unverifiable or false source linkage | Corpus fingerprint, stable evidence hashes, complete foreign-key audit, read-only source store | Mutation injection, fingerprint mismatch, orphan checks | Compromised local filesystem can replace source and derived data together | Operations owner |
| Reference freshness | TB2/TB3 | Stale store served after Article/rule change | Incorrect or missing references | Compare corpus/schema/rule/config fingerprints on load; return 503 and explicit stale state; no request-time rebuild | Stale fingerprint tests and API smoke | Availability is reduced until operator rebuilds | Reference/API owner |
| Store integrity | TB2 | Corrupt/truncated manifest, JSONL, or index | Wrong results, crash, silent loss | Hash/size/count/schema/index reconciliation, atomic staged install, rollback recovery | Corruption and failure-injection tests | Filesystem failure during both install and rollback may need manual recovery | Operations owner |
| Candidate accounting | TB2 | Unsupported/malformed candidates silently disappear | Inflated quality metrics and lost evidence | Candidate input/output/classification equation and zero silent-drop gate | Fixture and pilot reconciliation audit | Candidate detector cannot classify text it never recognizes; reviewed sampling measures this | Evaluation owner |
| API privacy | TB3 | Full Article body, absolute path, or unbounded provenance leaks | Corpus/private path disclosure, oversized response | Dedicated DTOs, bounded evidence, allowlisted fields, no full-dump endpoint | Contract snapshots, local-path scan, response-size tests | Public Article snippets remain copyrighted source content | API owner |

## Zotero Threats

| Asset | Boundary | Threat | Impact | Mitigation | Verification | Residual risk | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Private library | TB4/TB1 | Complete Zotero metadata/export enters reports or Git | Privacy breach | Minimal item fields only; ignored candidate output; no full export; artifact/privacy scan | Fake-provider contract tests and payload field allowlist | Titles/item keys can still reveal research interests locally | Zotero owner |
| Link correctness | TB4 | Ambiguous/title-only match treated as exact | False scientific relationship | Exact requires DOI/arXiv and no conflict; URL at most probable; title-only ambiguous; explicit review only | Conflict/ambiguous fixtures; zero false-exact gate | Source metadata can itself be wrong | Zotero/evaluation owner |
| UI/API integrity | TB4/TB3 | Malicious title, URL, note, or creator field | XSS, unsafe link, layout/resource abuse | Treat as text, React escaping, URL allowlist, length/nesting bounds, no raw HTML | Malicious-field API/UI tests | Browser/library vulnerabilities outside app control | UI owner |
| Local API | TB4 | Compromised or unexpected service on `127.0.0.1:23119` | False metadata or request capture | Treat responses as untrusted; localhost-only default; timeout/size/schema validation; no credentials | Invalid response, oversized response, unavailable-provider tests | A compromised local host can influence all local apps | Zotero owner |
| Zotero library | TB4 | Matcher or UI performs unexpected write | User library corruption | Provider protocol remains read-only; matcher has no write method; no write endpoint/capability | Static interface audit and network-method test | Existing user-initiated M5 local link writes remain separate project state | Zotero owner |
| Item identity | TB4 | Item changes/deletes after candidate build | Stale decision or misleading candidate | Minimal item snapshot fingerprint, stale state, explicit re-review; never auto-rebind | Changed/deleted item fixtures | Zotero does not guarantee immutable item metadata | Zotero owner |
| Tier 1 decisions | TB2/TB1 | Derived cleanup deletes manual reviews | Irrecoverable user work | Separate Tier 1 store, backup manifest classification, cleanup protection | Operations inventory/cleanup/restore tests | Backup may be stale if operator ignores guidance | Operations owner |

## Real Provider Threats

| Asset | Boundary | Threat | Impact | Mitigation | Verification | Residual risk | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API secret | TB5/TB1 | Key/header/environment value logged or serialized | Credential compromise and cost abuse | Header/value redaction, config fingerprint allowlist, no raw metadata, bounded secret scan, never print matched value | Canary-secret tests and output scan | Provider/OS process inspection is outside application control | Provider/security owner |
| Private data | TB5 | Notes, Learning state, Tutor history, Zotero metadata, or full corpus sent | Privacy/copyright breach | Fixed data-category allowlist, public-case data only, consent preflight, bounded snippets, no arbitrary file input | Dry-run request envelope snapshots and denial tests | Public Article excerpts still leave the machine | Provider owner |
| Prompt integrity | TB5 | Article content injects instructions into model | Evaluation manipulation, unsafe output | Delimit evidence as untrusted data, fixed system protocol, source-bound answer validator, never execute output | Prompt-injection fixtures and grounding checks | Model may still follow injected text | Evaluation owner |
| Provider retention | TB5 | Provider logs/retains submitted data | Loss of local-only control | Preflight disclosure, dated provider policy reference, minimal snippets, no private data, operator approval | Consent record and report metadata review | Provider policy/enforcement cannot be technically verified locally | Operator |
| Budget | TB5 | Excessive requests/tokens/cost | Financial loss | Positive hard request/cost caps, pre-request estimate, usage reconciliation, stop-before-next-call, bounded retry | Fake usage/cost overrun tests | Provider pricing/usage can lag or differ | Provider owner |
| Availability | TB5 | Rate limits, timeout, transient/provider errors | Incomplete evidence, repeated costs | Bounded retry/backoff, per-case taxonomy, no automatic unbounded resume | Fake 429/timeout/error tests | External outage can prevent evaluation | Provider owner |
| Model identity | TB5 | Model alias/drift changes behavior | Incomparable or misleading reports | Record provider/model/version/date/config/pricing source; never claim cross-version equivalence | Manifest completeness and comparison guards | Provider may not expose an immutable model version | Evaluation owner |
| Response integrity | TB5 | Malformed, oversized, malicious response | Parser crash, storage abuse, unsafe display | Size/schema/time bounds, sanitize text, no tool execution, classify validation error | Invalid/oversized response fixtures | Valid but low-quality output needs human review | Provider/UI owner |
| Grounding | TB5 | Fluent unsupported answer passes heuristics | False scientific confidence | Existing M3/M7 citation/refusal gates, source support review, human rubric, no heuristic-as-correctness claim | No-source/conflict/fabrication cases | Human review can disagree or miss subtle errors | Evaluation owner |
| Local output | TB5/TB1 | Raw prompts/responses retained indefinitely or committed | Privacy/copyright leakage | Raw off, redacted reports, 30-day redacted/7-day raw defaults, deletion command, ignored path, artifact scan | Retention/deletion tests and Git artifact audit | Operator can manually copy local files | Operator |

## CI and Supply-Chain Threats

| Asset | Boundary | Threat | Impact | Mitigation | Verification | Residual risk | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Workflow execution | TB6 | Mutable Action tag is retargeted | Arbitrary CI code execution | Pin full reviewed SHA with upstream-version comment; controlled update PRs | Workflow linter rejects non-SHA third-party refs | Upstream commit itself may be compromised | CI owner |
| Dependencies | TB6 | Compromised direct/transitive package | Build/runtime compromise | Locked installs, Python/npm plus independent OSV scans, severity gates, expiry-bound suppression | Known-vulnerable fixture/policy tests; scanner jobs | New/unknown vulnerabilities are not detectable immediately | Dependency owners |
| Pull request | TB6/TB7 | Malicious PR accesses write token/secrets | Repository/release compromise | `contents: read` default, no secrets/elevated jobs for forks, separate trusted tag release job | Permission/static workflow audit and fork-event review | Maintainer approval of malicious code remains possible | CI/reviewer owner |
| Workflow token | TB6/TB7 | Excessive permissions grant broader writes | Source, package, or attestation compromise | Explicit per-job permissions; no `packages: write`; OIDC/attestation only release job | Permission matrix test/lint | GitHub platform vulnerabilities | CI owner |
| Logs | TB6 | Secret or scanner match value printed | Credential exposure | Mask values, report fingerprints/rule IDs only, no environment dump, bounded artifact retention | Canary test and log review | Third-party tools may log unexpected context | Security owner |
| Cache | TB6 | Poisoned dependency/build cache crosses trust levels | Compromised build/evidence | Lockfile/runner/tool keyed caches; no privileged release output from untrusted PR cache; validate installed graph/SBOM | Cache-key review and clean-run CI | Registry compromise can still serve malicious locked content | CI owner |
| Release identity | TB7 | Forged/mismatched tag, subject, SBOM, or provenance | Users verify wrong code/artifact | Exact tag/peeled SHA checks, subject digests, GitHub attestation, independent verification commands | Negative digest/ref/tag tests; tag CI gate | Compromised GitHub maintainer/platform can issue valid-looking evidence | Release owner |
| SBOM trust | TB6/TB7 | Incomplete/untrusted SBOM omits dependency or embeds private data | False assurance/privacy leak | Generate from both lockfiles with pinned tools, reconcile component counts, scan output, cap size, attest digest | Schema/component/artifact/secret audit | SBOM records declared resolution, not runtime compromise absence | Release/security owner |
| Scanner suppression | TB6 | Broad/permanent suppression hides finding | Vulnerability accepted without review | Structured exact scope, owner, rationale, URL, mandatory expiry; expired/unmatched fails | Suppression validator tests | Risk acceptance remains a human judgment | Security owner |
| Branch/tag history | TB6/TB7 | Force push or tag movement invalidates evidence | Release immutability loss | Branch protection guidance, protected release tags, no force push, exact-tag verification | Repository-settings review and remote tag audit | Guidance is ineffective until a human enables settings | Repository admin |

## Mitigation Verification Gates

- P3-003 owns reference parsing, bounds, normalization, provenance, stale/corrupt store, no-network, and no-mutation tests.
- P3-004 owns provider consent, budgets, request envelopes, prompt injection, redaction, retention, and fake error tests. No real call is needed to verify these controls.
- P3-005 owns immutable-pin linting, permissions, scanner policy, suppressions, SBOM integrity, forbidden-artifact scans, and provenance verification.
- P3-006 owns full-corpus accounting/idempotency and optional read-only matching evidence.
- P3-007 reruns frozen compatibility, backend/frontend/Docker, artifact, secret, migration, and release-provenance gates.

## Residual Risks

- Deterministic reference rules cannot prove scientific identity for citation text or bad source metadata.
- Provider retention, internal model versioning, and final answer quality cannot be fully verified locally.
- Read-only Zotero data can still expose a user's research interests on the local machine.
- Supply-chain scans detect known/configured classes, not every malicious dependency or compromised platform.
- Branch protection is guidance until a repository administrator applies and verifies it.
- Single-user local JSON/JSONL storage does not provide multi-process transactional guarantees.

## Out-of-Scope Threats

- Public multi-user authentication, authorization, tenant isolation, abuse prevention, quotas, and hosted database security.
- Graph database migration and distributed query/storage threats.
- Remote image crawling, copyright enforcement, and image archive integrity.
- Endpoint/device compromise, full-disk encryption, off-site backup, and operating-system account security.
- Provider-side security beyond documented policy and observable request/response behavior.
