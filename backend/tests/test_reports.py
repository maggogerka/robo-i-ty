from app.api.reports import _csv_bytes, template_environment


def test_csv_export_is_authenticated_structured_and_excel_safe(client, auth):
    project = client.post("/api/v1/projects/demo", headers=auth, json={}).json()

    response = client.get(
        f"/api/v1/projects/{project['id']}/exports/analysis.csv",
        headers=auth,
    )

    assert response.status_code == 200
    assert response.content.startswith("\ufeffsep=;".encode())
    assert "attachment;" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "Входной параметр" in response.content.decode("utf-8-sig")

    snapshot = {
        "project": {"name": "=2+2"},
        "parameters": [],
        "candidates": [],
        "economics": None,
        "simulation": None,
    }
    assert "'=2+2" in _csv_bytes(snapshot).decode("utf-8-sig")


def test_report_template_escapes_project_text():
    html = template_environment.get_template("report.html").render(
        project={
            "name": "<script>alert(1)</script>",
            "object_type_code": "warehouse",
            "calculation_version": "2026.09.1",
        },
        generated_at="21.09.2026",
        candidates=[],
        economics=None,
        simulation=None,
        parameters=[],
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
