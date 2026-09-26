from __future__ import annotations

import base64

from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine
from app.models import User
from app.plan_assets import AssetValidationError, detect_media_type, validate_svg
from app.security import hash_password

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nWQAAAAASUVORK5CYII="
)


def _second_user_token(client) -> str:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "isolation@robo.local")).first()
        if user is None:
            session.add(
                User(
                    email="isolation@robo.local",
                    password_hash=hash_password("Isolation-2026!"),
                    role="user",
                )
            )
            session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "isolation@robo.local", "password": "Isolation-2026!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_asset_signatures_and_active_svg_are_rejected():
    assert detect_media_type(PNG_1X1[:64]) == "image/png"
    assert detect_media_type(b"%PDF-1.7\n") == "application/pdf"

    try:
        validate_svg(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    except AssetValidationError:
        pass
    else:
        raise AssertionError("Активный SVG должен быть отклонён")


def test_upload_recognition_history_and_project_isolation(client, auth, tmp_path):
    settings = get_settings()
    original_storage = settings.plan_storage_dir
    settings.plan_storage_dir = tmp_path
    try:
        project = client.post("/api/v1/projects/demo", headers=auth, json={}).json()
        project_id = project["id"]
        upload = client.post(
            f"/api/v1/projects/{project_id}/plan-assets",
            headers=auth,
            files={"file": ("warehouse.png", PNG_1X1, "image/png")},
        )
        assert upload.status_code == 201
        asset = upload.json()
        assert asset["byte_size"] == len(PNG_1X1)
        assert len(asset["sha256"]) == 64
        assert "storage_path" not in asset

        spoofed = client.post(
            f"/api/v1/projects/{project_id}/plan-assets",
            headers=auth,
            files={"file": ("spoofed.pdf", PNG_1X1, "application/pdf")},
        )
        assert spoofed.status_code == 422

        providers = client.get(
            f"/api/v1/projects/{project_id}/plan-recognition/providers", headers=auth
        )
        assert providers.status_code == 200
        demo = next(item for item in providers.json() if item["key"] == "demo")
        assert demo["available"] is True
        assert demo["uses_model"] is False

        recognized = client.post(
            f"/api/v1/projects/{project_id}/plan-assets/{asset['id']}/recognize",
            headers=auth,
            params={"provider": "demo"},
        )
        assert recognized.status_code == 200
        body = recognized.json()
        assert body["provider"]["uses_model"] is False
        assert body["plan"]["scale_status"] == "unknown"
        assert all(item["source"] == "demo" for item in body["plan"]["elements"])

        revisions = client.get(f"/api/v1/projects/{project_id}/plan-revisions", headers=auth)
        assert revisions.status_code == 200
        assert revisions.json()[0]["provider_key"] == "demo"

        other_auth = {"Authorization": f"Bearer {_second_user_token(client)}"}
        assert (
            client.get(
                f"/api/v1/projects/{project_id}/plan-assets/{asset['id']}/content",
                headers=other_auth,
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/v1/projects/{project_id}/plan-assets/{asset['id']}/recognize",
                headers=other_auth,
            ).status_code
            == 404
        )
    finally:
        settings.plan_storage_dir = original_storage
