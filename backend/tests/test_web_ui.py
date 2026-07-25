from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_redirects_to_web_interface() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/app/"


def test_dashboard_page_is_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert "FSBackup" in response.text
    assert "Tableau de bord" in response.text
    assert "/app/app.js" in response.text


def test_new_backup_form_is_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert 'id="backup-form"' in response.text
    assert 'id="source-root"' in response.text
    assert 'id="destination-directory"' in response.text
    assert 'id="enable-encryption"' in response.text
    assert 'id="verify-integrity"' in response.text


def test_dashboard_assets_are_served() -> None:
    stylesheet = client.get("/app/styles.css")
    script = client.get("/app/app.js")

    assert stylesheet.status_code == 200
    assert "capability-grid" in stylesheet.text
    assert "form-panel" in stylesheet.text
    assert script.status_code == 200
    assert "/api/v1/dashboard/summary" in script.text
    assert "/api/v1/backup/run" in script.text
    assert "verify_integrity" in script.text
