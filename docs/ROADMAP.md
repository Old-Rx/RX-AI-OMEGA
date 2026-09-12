# Public roadmap

RX-AI OMEGA is developed in small, verifiable increments. This roadmap communicates direction; it is not a promise of dates or production certification.

## Current baseline — 0.1.x

- Authenticated API and role-based access control.
- Persistent missions, workflow steps, handoffs, approvals, documents, and audit events.
- Validated dependency graphs and deterministic execution order.
- Human approval before medium/high-risk and controlled actions.
- Mock, OpenAI Responses, and Ollama provider adapters.
- Local and production-oriented database, queue, and memory profiles.
- React operations console, automated tests, CI, containers, and deployment guidance.

## Next — workflow depth

- Multi-step workflow authoring in the operations console.
- Better mission inspection, retry controls, and failure explanations.
- Database-backed step claiming for safe concurrent workers.
- Integration tests for Redis, PostgreSQL, Qdrant, OpenAI, and Ollama profiles.
- Learned embedding support behind the existing memory interface.

## Later — operational maturity

- Versioned workflow templates and reusable mission definitions.
- Provider budgets, quotas, timeouts, and per-step model routing policies.
- Evaluation datasets and regression checks for model output quality.
- OpenTelemetry traces and deployment-specific dashboards.
- Backup/restore exercises, upgrade tests, and documented recovery objectives.
- External security review before any production-certification claim.

## Contribution priorities

Security invariants, tests, migration safety, provider reliability, and clear operator experience take precedence over adding a large number of loosely integrated features. Proposals are welcome through GitHub issues.
