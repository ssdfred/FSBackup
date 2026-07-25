from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_summary_exposes_ui_capabilities() -> None:
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["application"] == "FSBackup"
    assert payload["api_version"] == "v1"
    assert payload["status"] == "ready"
    assert {item["key"] for item in payload["capabilities"]} == {
        "backup",
        "catalog",
        "restore",
        "retention_simulation",
        "retention_execution",
    }
    retention = next(
        item for item in payload["capabilities"] if item["key"] == "retention_execution"
    )
    assert retention["destructive"] is True


def test_openapi_contains_primary_ui_routes() -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/dashboard/summary" in paths
    assert "/api/v1/backup/run" in paths
    assert "/api/v1/backups/catalog" in paths
    assert "/api/v1/restore/run" in paths
    assert "/api/v1/backups/retention/simulate" in paths
    assert "/api/v1/backups/retention/execute" in paths


def test_http_errors_use_stable_envelope() -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_404",
            "message": "Not Found",
            "details": [],
        }
    }


def test_validation_errors_use_stable_envelope() -> None:
    response = client.post("/api/v1/backups/catalog", json={})

    assert response.status_code == 422
    payload = response.json()["error"]
    assert payload["code"] == "validation_error"
    assert payload["message"] == "The request payload is invalid."
    assert payload["details"]
    assert payload["details"][0]["location"] == ["body", "directory"]
