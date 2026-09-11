# Architecture

## Control flow

```text
React console / API client
          │ JWT + RBAC
          ▼
      FastAPI API ─────────────► audit_events
          │
          ▼
        Kernel
          │
          ▼
 MissionExecutor ──► GovernancePolicy ──► Approval (durable pause)
          │ allowed/resumed
          ▼
    RuntimeEngine ──► Provider adapter ──► mock | OpenAI | Ollama
          │
          ├──► workflow_steps + handoffs
          └──► mission terminal state
```

The `Kernel` is a stable orchestration boundary. The executor owns persisted state transitions and dependency scheduling; the runtime owns a single provider invocation; governance decides whether invocation is allowed to begin. Keeping the gate before the runtime is the central safety invariant.

## Domain model

- `users` authenticate and receive one of three roles.
- `agents` bind reusable instructions and an optional provider override.
- `missions` own an ordered set of `workflow_steps`.
- `workflow_steps.depends_on` stores stable step keys. A unique mission/key constraint and application-level cycle validation protect the graph.
- `handoffs` preserve dependency output passed between steps.
- `approvals` are one-to-one with controlled steps and record the administrator decision.
- `audit_events` append control-plane and execution transitions.
- `documents` persist source content even when Qdrant is the retrieval index.

## State machines

```text
mission: draft → queued → running → completed
                            ├─────→ failed
                            └─────→ waiting_approval → queued → running
                                                  └──→ rejected

step: pending → running → completed
       └─────→ waiting_approval → pending
                             └──→ rejected
```

The local queue runs work as a FastAPI background task. It is useful for development but does not survive a process crash. Redis mode durably separates submission from a worker process. The current queue is at-least-once transport; terminal state checks make re-delivery safe, while deployments requiring concurrent workers should add database advisory locking before horizontal worker scaling.

## Retrieval

Local retrieval uses token-set similarity over persisted documents and is suitable for deterministic development and small corpora. The Qdrant adapter uses a deterministic 128-dimensional hashing vector so it needs no separate embedding credential. This is operationally complete but not semantically equivalent to a learned embedding model; a learned embedding implementation can be introduced behind `MemoryStore` without changing API routes.

## Historical v32 comparison

The verified v32 archive expressed `API → Kernel → Runtime → Governance → Enterprise Platform`. This repository retains the first four concepts but corrects the control order: governance is evaluated before runtime/provider side effects. The legacy substring check and `/execute` endpoint were intentionally not carried forward because they lacked authentication, persistence, approval, and an auditable execution model.
