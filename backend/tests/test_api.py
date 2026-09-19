from time import perf_counter

from sqlmodel import Session

from app.db import engine
from app.models import User
from app.security import create_access_token, hash_password


def test_health_and_openapi(client):
    assert client.get("/health").json()["status"] == "ok"
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/projects/{project_id}/matching" in schema.json()["paths"]


def test_catalog_was_imported(client):
    response = client.get("/api/v1/catalog?limit=1")
    assert response.status_code == 200
    assert response.json()["count"] == 187
    assert response.json()["items"][0]["source_status"] == "source_present"


def test_demo_full_analytics_path(client, auth):
    project = client.post("/api/v1/projects/demo", headers=auth, json={})
    assert project.status_code == 200
    body = project.json()
    assert body["object_type_code"] == "warehouse"
    assert len(body["parameters"]) >= 40

    started = perf_counter()
    matching = client.post(f"/api/v1/projects/{body['id']}/matching", headers=auth, json={})
    assert matching.status_code == 200
    assert len(matching.json()["candidates"]) >= 3
    assert matching.json()["candidates"][0]["contributions"]

    economics = client.post(f"/api/v1/projects/{body['id']}/economics", headers=auth, json={})
    assert economics.status_code == 200
    assert set(economics.json()["scenarios"]) == {"baseline", "purchase", "raas"}
    assert perf_counter() - started < 10


def test_project_isolation_returns_not_found(client, auth):
    project = client.post("/api/v1/projects/demo", headers=auth, json={}).json()
    outsider = User(
        email="other@example.test",
        password_hash=hash_password("password"),
        role="user",
    )
    with Session(engine) as session:
        session.add(outsider)
        session.commit()
        session.refresh(outsider)
        outsider_token = create_access_token(outsider)
    response = client.get(
        f"/api/v1/projects/{project['id']}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 404


def test_admin_role_is_checked_server_side(client, auth):
    item = client.get("/api/v1/catalog?limit=1").json()["items"][0]
    response = client.patch(
        f"/api/v1/catalog/{item['id']}",
        headers=auth,
        json={"price_rub": 1},
    )
    assert response.status_code == 403
