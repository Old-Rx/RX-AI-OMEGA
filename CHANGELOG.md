# Changelog

All notable changes to RX-AI OMEGA are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2025-10-25

### Added

- Persistent orchestration schema and Alembic migration.
- Validated DAG planning, ordered execution, and persisted handoffs.
- Human approval gates with approve/resume and reject behavior.
- Argon2/JWT authentication and viewer/operator/admin authorization.
- Mock, OpenAI Responses, and Ollama provider adapters.
- Local and Qdrant retrieval modes.
- Local and Redis execution modes.
- React operations dashboard for agents, missions, approvals, and documents.
- Health checks, Prometheus metrics, structured JSON logging, request IDs.
- Docker Compose topology (frontend, API, worker, PostgreSQL, Redis, Qdrant).
- CI pipeline with ruff, mypy, pytest, frontend lint, and frontend build.
- Repository governance files: SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md.
- Restricted-network Windows offline bundle workflow and release.

### Corrected

- Resets semantic versioning around tested implementation instead of continuing
  cosmetic v32 numbering from the historical scaffold.

[0.1.0]: https://github.com/Old-Rx/RX-AI-OMEGA/releases/tag/v0.1.0
