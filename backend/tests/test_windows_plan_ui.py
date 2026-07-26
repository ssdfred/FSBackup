from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_root_inventory_projects_are_disabled_by_default() -> None:
    script = (WEB_UI / "root_inventory.js").read_text(encoding="utf-8")

    assert 'type="checkbox"' in script
    assert "selected:new Set()" in script
    assert "restent facultatifs" in script
    assert "getSelectedAdditionalPaths" in script
    assert "getSelectedRecoveryPaths" in script


def test_backup_payload_contains_selected_recovery_paths() -> None:
    script = (WEB_UI / "exclusion_payload.js").read_text(encoding="utf-8")

    assert "selected_additional_paths" in script
    assert "getSelectedAdditionalPaths" in script
    assert "selected_recovery_paths" in script
    assert "getSelectedRecoveryPaths" in script


def test_capacity_distinguishes_base_selected_and_recoverable_totals() -> None:
    script = (WEB_UI / "capacity.js").read_text(encoding="utf-8")

    assert "Dossiers standards inclus" in script
    assert "Compléments de profils détectés" in script
    assert "Plan actuellement sélectionné" in script
    assert "Total récupérable visible" in script
    assert "getSelectedAdditionalSize" in script
    assert "getSelectedRecoverySize" in script
    assert "getDetectedRecoverableProfileSize" in script
    assert "fsbackup:plan-selection-changed" in script
    assert "Espace insuffisant" in script
