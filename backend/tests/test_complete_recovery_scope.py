from pathlib import Path

import pytest

from app.modules.backup_orchestrator.schemas import BackupRunRequest
from app.modules.execution_planner.windows_service import WindowsExecutionPlannerService


def test_request_accepts_selected_recovery_paths() -> None:
    request = BackupRunRequest(
        source_root="D:\\",
        destination_directory="F:\\Sauvegardes",
        archive_name="poste",
        selected_recovery_paths=["D:\\Windows.old\\Users\\fred"],
    )

    assert request.selected_recovery_paths == ["D:\\Windows.old\\Users\\fred"]


def test_recovery_path_must_belong_to_a_user_profile(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    invalid = root / "ProgramData"
    invalid.mkdir()

    with pytest.raises(ValueError, match="profil utilisateur"):
        WindowsExecutionPlannerService._validate_recovery_path(root, invalid)


def test_old_windows_profile_is_allowed_for_recovery(tmp_path: Path) -> None:
    root = tmp_path / "source"
    profile = root / "Windows.old" / "Users" / "fred"
    profile.mkdir(parents=True)

    WindowsExecutionPlannerService._validate_recovery_path(root, profile)


def test_ui_transmits_selected_recovery_paths() -> None:
    web_ui = Path(__file__).parents[1] / "app" / "web_ui"
    payload = (web_ui / "exclusion_payload.js").read_text(encoding="utf-8")
    inventory = (web_ui / "root_inventory.js").read_text(encoding="utf-8")
    capacity = (web_ui / "capacity.js").read_text(encoding="utf-8")

    assert "selected_recovery_paths" in payload
    assert "getSelectedRecoveryPaths" in inventory
    assert "data-recovery-path" in inventory
    assert "getSelectedRecoverySize" in capacity
