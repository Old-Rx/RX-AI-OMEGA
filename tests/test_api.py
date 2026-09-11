from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rx_ai_omega.database import SessionLocal
from rx_ai_omega.models import AuditEvent, Handoff, Mission


def create_agent(client: TestClient, headers: dict[str, str], name: str = "Analyst") -> str:
    response = client.post(
        "/api/agents",
        headers=headers,
        json={"name": name, "instructions": "Return a concise result.", "provider": "mock"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_mission(
    client: TestClient,
    headers: dict[str, str],
    agent_id: str,
    risk: str = "low",
    action: str = "analysis",
) -> str:
    response = client.post(
        "/api/missions",
        headers=headers,
        json={
            "title": "Release intelligence",
            "objective": "Produce a controlled result",
            "steps": [
                {"key": "research", "agent_id": agent_id, "prompt": "Find facts", "depends_on": []},
                {
                    "key": "deliver",
                    "agent_id": agent_id,
                    "prompt": "Deliver result",
                    "depends_on": ["research"],
                    "risk": risk,
                    "action": action,
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_authentication_and_rbac(client: TestClient, admin_headers: dict[str, str]) -> None:
    assert client.get("/api/agents").status_code == 401
    created = client.post(
        "/api/users",
        headers=admin_headers,
        json={"username": "reader", "password": "long-reader-password", "role": "viewer"},
    )
    assert created.status_code == 201
    login = client.post("/api/auth/token", data={"username": "reader", "password": "long-reader-password"})
    viewer = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/agents", headers=viewer).status_code == 200
    assert client.post(
        "/api/agents",
        headers=viewer,
        json={"name": "Forbidden", "instructions": "No"},
    ).status_code == 403
    assert client.get("/api/users", headers=viewer).status_code == 403


def test_dag_execution_handoff_persistence_and_audit(client: TestClient, admin_headers: dict[str, str]) -> None:
    agent_id = create_agent(client, admin_headers)
    mission_id = create_mission(client, admin_headers, agent_id)
    response = client.post(f"/api/missions/{mission_id}/run", headers=admin_headers)
    assert response.status_code == 202
    persisted = client.get(f"/api/missions/{mission_id}", headers=admin_headers).json()
    assert persisted["status"] == "completed"
    assert [step["status"] for step in persisted["steps"]] == ["completed", "completed"]
    assert "research" in persisted["steps"][1]["output"]
    with SessionLocal() as fresh_session:
        assert fresh_session.get(Mission, mission_id).status.value == "completed"  # type: ignore[union-attr]
        assert fresh_session.scalar(select(func.count()).select_from(Handoff)) == 1
        actions = set(fresh_session.scalars(select(AuditEvent.action)).all())
        assert {"mission.created", "mission.completed", "step.completed"} <= actions


def test_approval_and_resume(client: TestClient, admin_headers: dict[str, str]) -> None:
    mission_id = create_mission(client, admin_headers, create_agent(client, admin_headers), "high", "release")
    client.post(f"/api/missions/{mission_id}/run", headers=admin_headers)
    mission = client.get(f"/api/missions/{mission_id}", headers=admin_headers).json()
    assert mission["status"] == "waiting_approval"
    assert mission["steps"][0]["status"] == "completed"
    approval = client.get("/api/approvals?status=pending", headers=admin_headers).json()[0]
    decided = client.post(
        f"/api/approvals/{approval['id']}/approve",
        headers=admin_headers,
        json={"note": "Reviewed release evidence"},
    )
    assert decided.status_code == 200
    mission = client.get(f"/api/missions/{mission_id}", headers=admin_headers).json()
    assert mission["status"] == "completed"
    assert mission["steps"][1]["status"] == "completed"


def test_approval_rejection_is_terminal(client: TestClient, admin_headers: dict[str, str]) -> None:
    mission_id = create_mission(client, admin_headers, create_agent(client, admin_headers), "medium")
    client.post(f"/api/missions/{mission_id}/run", headers=admin_headers)
    approval = client.get("/api/approvals?status=pending", headers=admin_headers).json()[0]
    response = client.post(
        f"/api/approvals/{approval['id']}/reject",
        headers=admin_headers,
        json={"note": "Insufficient evidence"},
    )
    assert response.status_code == 200
    mission = client.get(f"/api/missions/{mission_id}", headers=admin_headers).json()
    assert mission["status"] == "rejected"
    assert mission["steps"][1]["status"] == "rejected"


def test_document_ingestion_and_local_retrieval(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/documents",
        headers=admin_headers,
        json={"title": "Runbook", "content": "Rotate credentials before a production release.", "metadata": {"team": "ops"}},
    )
    assert response.status_code == 201
    hits = client.get("/api/documents/search?q=rotate+credentials", headers=admin_headers).json()
    assert hits and hits[0]["title"] == "Runbook"


def test_invalid_dag_is_rejected(client: TestClient, admin_headers: dict[str, str]) -> None:
    agent_id = create_agent(client, admin_headers)
    response = client.post(
        "/api/missions",
        headers=admin_headers,
        json={
            "title": "Cycle",
            "objective": "Must not persist",
            "steps": [
                {"key": "a", "agent_id": agent_id, "prompt": "a", "depends_on": ["b"]},
                {"key": "b", "agent_id": agent_id, "prompt": "b", "depends_on": ["a"]},
            ],
        },
    )
    assert response.status_code == 422
    assert "cycle" in response.json()["detail"]


def test_health_and_metrics(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "rx_http_requests_total" in metrics.text
