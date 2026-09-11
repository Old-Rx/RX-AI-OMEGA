import os
from pathlib import Path

os.environ["RX_ENVIRONMENT"] = "test"
os.environ["RX_DATABASE_URL"] = f"sqlite:///{Path('work/test.sqlite3').resolve().as_posix()}"
os.environ["RX_AUTH_SECRET"] = "test-secret-that-is-long-enough-for-tests-only"
os.environ["RX_BOOTSTRAP_ADMIN_USERNAME"] = "admin"
os.environ["RX_BOOTSTRAP_ADMIN_PASSWORD"] = "test-password-123"
os.environ["RX_PROVIDER"] = "mock"
os.environ["RX_EXECUTION_BACKEND"] = "local"

import pytest
from fastapi.testclient import TestClient

from rx_ai_omega.database import Base, engine
from rx_ai_omega.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/token",
        data={"username": "admin", "password": "test-password-123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
