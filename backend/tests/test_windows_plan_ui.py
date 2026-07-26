from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_root_inventory_projects_are_disabled_by_default() -> None:
    script = (WEB_UI / "root_inventory.js").read_text(encoding="utf-8")

    assert 'type="checkbox"' in script
    assert "inventoryState.selected=new Set()" in script
    assert "décochés par défaut" in script
    assert "getSelectedAdditionalPaths" in script


def test_backup_payload_contains_selected_additional_paths() -> None:
    script = (WEB_UI / "exclusion_payload.js").read_text(encoding="utf-8")

    assert "selected_additional_paths" in script
    assert "getSelectedAdditionalPaths" in script


def test_capacity_includes_personal_data_and_selected_projects() -> None:
    script = (WEB_UI / "capacity.js").read_text(encoding="utf-8")

    assert "Données personnelles incluses" in script
    assert "getSelectedAdditionalSize" in script
    assert "fsbackup:plan-selection-changed" in script
    assert "Espace insuffisant" in script
