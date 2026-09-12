# RX-AI OMEGA

RX-AI OMEGA is an auditable, approval-aware mission orchestrator for teams that want agent automation without surrendering operational control. It turns a mission into a validated dependency graph, runs each step through a configured model provider, persists every transition, and pauses consequential actions for an administrator to approve or reject.

This repository is a ground-up, working successor to the verified **v32 baseline scaffold**. It does **not** claim that the historical scaffold implemented enterprise capabilities; see [Provenance](#provenance) and [Release notes](RELEASE_NOTES.md).

## What works

- FastAPI control plane with an explicit API → kernel → executor/runtime → governance flow.
- Persistent users, agents, missions, workflow steps, handoffs, approvals, documents, and audit events.
- SQLite local profile and PostgreSQL production configuration, with Alembic migrations.
- DAG validation and deterministic topological execution.
- Human approval gates for medium/high risk and production, release, deploy, delete, or publish actions.
- JWT bearer authentication, Argon2 password hashing, and viewer/operator/admin RBAC.
- OpenAI Responses API, Ollama, and deterministic mock provider adapters.
- Local lexical retrieval plus deterministic vector generation and a Qdrant production adapter.
- In-process background execution for development and a Redis queue/worker path.
- React operations console for agents, missions, approvals, and document memory.
- JSON logs, request IDs, readiness/liveness checks, Prometheus metrics, strict production configuration validation, and security headers.
- Docker Compose topology for frontend, API, worker, PostgreSQL, Redis, and Qdrant.

The mock provider and local retrieval are intentionally development implementations. OpenAI, Ollama, Redis, PostgreSQL, and Qdrant paths require their corresponding services or credentials.

## Local quick start

Requirements: Python 3.11+ and Node 20+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
alembic upgrade head
rx-api
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The development bootstrap login from `.env.example` is `admin` / `change-me-now`; change it immediately in any shared environment. API documentation is at `http://localhost:8000/docs` outside production.

For a quick API-only run, schema creation is enabled by default in development. Running `alembic upgrade head` is still recommended because production disables automatic schema creation.

### Restricted-network Windows setup

If the Windows machine cannot reach PyPI, run the **Build Windows offline bundle** workflow from the repository's Actions page. Download and extract the private release asset `rx-ai-omega-windows-py314-wheelhouse.zip`, then install entirely offline:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links .\wheelhouse "rx-ai-omega[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\rx-api.exe
```

The workflow also publishes a SHA-256 checksum beside the archive. Verify it before installation.

## Model and execution profiles

| Concern | Local default | Production path |
|---|---|---|
| Database | SQLite | PostgreSQL (`RX_DATABASE_URL`) |
| Provider | Deterministic mock | OpenAI Responses or Ollama (`RX_PROVIDER`) |
| Retrieval | In-database lexical search | Qdrant (`RX_MEMORY_BACKEND=qdrant`) |
| Background work | FastAPI background task | Redis queue + `rx-worker` |

No credential is compiled into the repository. The application refuses weak/default authentication secrets, SQLite, and the default bootstrap password when `RX_ENVIRONMENT=production`.

## Roles and control model

- **Viewer:** inspect agents, missions, approvals, and search memory.
- **Operator:** viewer abilities plus create agents/missions, run missions, and ingest documents.
- **Admin:** operator abilities plus manage users, decide approvals, and read the complete audit history.

An approval decision is immutable through the API. Approval creates a durable pause before provider execution; approval resumes the same persisted step, while rejection terminates the mission.

## Development checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing
cd frontend
npm run lint
npm run build
```

Python dependencies use bounded compatible ranges in `pyproject.toml`; the frontend has a committed `package-lock.json` and CI uses `npm ci`. Container builds are the reproducible production unit. When preparing a regulated deployment, generate and review a platform-specific Python constraints lock from the tested environment and pin the resulting image digest.

## Deployment

See [Deployment guide](docs/DEPLOYMENT.md) for Compose startup, secret requirements, service dependencies, TLS guidance, migrations, backup scope, and smoke checks. Docker is optional for local development.

## Provenance

The source archive supplied as the historical v32 baseline was independently verified before inspection:

```text
SHA-256 B979B7B8A47DD5E6AEDC5D0D4D08BF72873C4E455B37A25C62246E2707BC0C55
```

It contained eight small files (1,225 bytes total): a single unauthenticated execution endpoint, pass-through kernel, runtime with a substring policy, static HTML, one assertion, and brief README/architecture statements. The archive itself is intentionally not tracked as a duplicate; its lineage and the architectural changes are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Project policy

Licensed under the MIT License. Security reports should follow [SECURITY.md](SECURITY.md); contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
