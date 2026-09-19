import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-that-is-long-enough"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def user_token(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@robo.local", "password": "Demo-2026!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def auth(user_token):
    return {"Authorization": f"Bearer {user_token}"}
