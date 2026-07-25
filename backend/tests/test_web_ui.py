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


def test_dashboard_assets_are_served() -> None:
    stylesheet = client.get("/app/styles.css")
    script = client.get("/app/app.js")

    assert stylesheet.status_code == 200
    assert "capability-grid" in stylesheet.text
    assert script.status_code == 200
    assert "/api/v1/dashboard/summary" in script.text
