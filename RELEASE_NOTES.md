# Release notes

## 0.1.0 — Ground-up verified baseline

This is the first release whose capabilities are tied to executable implementation and automated tests.

### Added

- Persistent orchestration schema and Alembic migration.
- Validated DAG planning, ordered execution, and persisted handoffs.
- Human gates with approve/resume and reject behavior.
- Argon2/JWT authentication and viewer/operator/admin authorization.
- Mock, OpenAI Responses, and Ollama providers.
- Local and Qdrant retrieval modes.
- Local and Redis execution modes.
- Operations dashboard, health checks, metrics, JSON logging, Compose topology, CI, and repository governance files.

### Corrected historical record

The supplied “v32 Final Enterprise Release” was a minimal eight-file scaffold. Its README claims are treated as intent, not shipped functionality. Version 0.1.0 deliberately resets semantic versioning around the tested implementation instead of continuing cosmetic v32 numbering.

### Known limits

- Local background work is process-bound; Redis mode is the production path.
- Horizontal worker concurrency needs a database claim lock before scaling above one worker.
- The deterministic hashing vector is operational but not a learned semantic embedding.
- External providers and the full Compose stack need live infrastructure and credentials to exercise.
