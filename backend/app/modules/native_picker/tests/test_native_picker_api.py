from fastapi.testclient import TestClient

from app.main import app
from app.modules.native_picker.schemas import NativePickerReport
from app.modules.native_picker.service import NativePickerService

client = TestClient(app)


def test_pick_directory_returns_selected_path(monkeypatch) -> None:
    monkeypatch.setattr(
        NativePickerService,
        "pick_directory",
        staticmethod(
            lambda initial_path=None: NativePickerReport(
                selected=True,
                path=r"H:\FSBackup\TestsRetention",
            )
        ),
    )

    response = client.post(
        "/api/v1/system/picker/directory",
        json={"initial_path": r"H:\FSBackup"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "selected": True,
        "path": r"H:\FSBackup\TestsRetention",
        "error": None,
    }


def test_pick_archive_can_be_cancelled(monkeypatch) -> None:
    monkeypatch.setattr(
        NativePickerService,
        "pick_archive",
        staticmethod(
            lambda initial_path=None: NativePickerReport(selected=False)
        ),
    )

    response = client.post(
        "/api/v1/system/picker/archive",
        json={"initial_path": None},
    )

    assert response.status_code == 200
    assert response.json()["selected"] is False
    assert response.json()["path"] is None
