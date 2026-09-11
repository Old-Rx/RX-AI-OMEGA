# Production deployment

`compose.yaml` is a practical single-host reference topology, not a substitute for an organization-specific high-availability design.

## Required preparation

1. Install Docker Engine with Compose v2.
2. Copy `.env.example` to `.env` and set `RX_ENVIRONMENT=production`.
3. Generate a random `RX_AUTH_SECRET` of at least 32 characters.
4. Set strong, distinct `POSTGRES_PASSWORD` and `RX_BOOTSTRAP_ADMIN_PASSWORD` values.
5. Set `RX_CORS_ORIGINS` to the exact public HTTPS console origin.
6. Choose `RX_PROVIDER` and add only the credentials it needs. Never commit `.env`.

Start the stack:

```bash
docker compose up --build -d
docker compose ps
curl -fsS http://localhost:8000/health/ready
curl -fsS http://localhost:3000/health/ready
```

The API entrypoint applies `alembic upgrade head` before starting. The worker waits for the API health check and uses the same application image. PostgreSQL, Redis, and Qdrant are private Compose services; only the console and API ports are published for operator access.

## Edge security

Terminate TLS at a managed reverse proxy or ingress. Restrict `/metrics` to the monitoring network at that layer, set request/body limits, enable access throttling on `/api/auth/token`, and forward a trusted request ID. Do not expose PostgreSQL, Redis, or Qdrant publicly. The application emits no-store, anti-sniffing, frame-denial, and referrer headers and hides interactive API documentation in production.

## Bootstrap administrator

The initial administrator is created only when the users table is empty. After the first login, create a named administrator and remove `RX_BOOTSTRAP_ADMIN_USERNAME` and `RX_BOOTSTRAP_ADMIN_PASSWORD` from the runtime environment. A production deployment refuses the sample password.

## Data durability and recovery

Back up PostgreSQL and the Qdrant storage volume on a coordinated schedule. Redis holds queued mission IDs but is not the system of record; all mission and step state is in PostgreSQL. Test restore procedures and Alembic upgrades against a restored copy before each release. The Compose health checks detect availability, not backup correctness.

## Scaling notes

Run one worker by default. Before adding concurrent workers, add a database-backed mission claim/advisory lock to prevent two workers from executing the same non-terminal mission concurrently. For multi-node API deployments, aggregate Prometheus metrics externally and centralize JSON logs.

## Provider checks

- `mock`: no network and deterministic; safe for smoke tests.
- `openai`: requires `RX_OPENAI_API_KEY`; live billing and data policies apply.
- `ollama`: requires a reachable Ollama server and a pulled `RX_OLLAMA_MODEL`.
- `qdrant`: the collection is created idempotently on first memory operation.

Docker was not available in the repository authoring environment, so container startup could not be live-tested there. CI validates the Compose model and both images are built from checked-in Dockerfiles.
