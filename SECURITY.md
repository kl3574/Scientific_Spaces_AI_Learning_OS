# Security Policy

## Supported Versions

| Version | Support status |
| --- | --- |
| `v1.0.x` | MVP security and privacy documentation baseline. |
| `main` | Active post-MVP hardening branch. |

## Reporting Vulnerabilities

Report security issues through GitHub private vulnerability reporting or by contacting the repository owner directly. Do not open public issues for exploitable vulnerabilities until the issue has been triaged.

Useful reports include:

- affected commit, tag, or branch
- affected endpoint, route, command, or workflow
- reproduction steps
- expected impact
- whether local runtime data, provider keys, or Zotero metadata may be exposed

## Security Model

Scientific Spaces AI Learning OS is currently a local-first MVP. It is intended for trusted local development and single-user study workflows.

The MVP does not implement authentication, authorization, account separation, or production multi-user isolation. Production or public deployment must remain blocked until those controls are explicitly designed, implemented, and verified.

## Secrets Policy

- Do not commit `.env`, `.env.*`, API keys, GitHub tokens, provider tokens, Zotero exports, or local runtime data.
- `.env.example` contains placeholders and local defaults only.
- Real OpenAI-compatible provider keys are optional and must be supplied through an untracked local environment file or external runtime environment.
- Tests and CI use fake providers by default and must not require real provider credentials.
- Provider keys must not be logged, returned from API responses, or exposed through frontend code.

## Local Data Policy

Runtime stores are local artifacts and must not be committed:

- Article JSON stores
- Learning JSON stores
- SQLite database files
- Zotero link stores
- Knowledge Graph JSON output
- Tutor session stores
- FAISS/vector indexes and embedding caches
- generated PDFs, HTML dumps, traces, profiles, and browser artifacts

The default runtime root is `.local_data/scientific_spaces`. SQLite is an opt-in local structured persistence backend for learning data and is not a production multi-user database.

## AI Grounding Policy

- Fake embedding and LLM providers are the default local/test providers.
- Real OpenAI-compatible providers are optional and enabled only through environment configuration.
- RAG and tutor answers must be grounded in local article sources.
- No-source cases must refuse instead of fabricating answers.
- Tutor graph and Zotero context may supplement an answer, but cannot replace article-source citations for substantive answers.
- Research mode is local-only and does not perform autonomous web research or paper downloads.

## Zotero Privacy Boundary

- The default Zotero provider is fake and read-only.
- The optional local Zotero API provider is selected only with `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=local`.
- Zotero integration reads metadata and BibTeX through local API GET requests.
- The project does not implement Zotero library imports, connector saves, attachment fetches, or write operations.
- Do not commit real Zotero exports, attachment paths, personal library data, or profile paths.

## Known Limitations

- No authentication or authorization is implemented in the MVP.
- Local JSON and SQLite stores are not production multi-user storage.
- CORS is limited to local frontend origins, but production host configuration is not yet implemented.
- Dependency and secret audits must be rerun periodically.
- LocalStorage reading history is browser-local user activity data.
- Real-provider key management is the responsibility of the deployment environment.

## Responsible Use

Use the system only with data you are authorized to process. Keep local runtime data out of source control, verify citations before relying on AI-generated answers, and do not deploy the MVP as a public multi-user service without additional security, privacy, persistence, and authentication work.
