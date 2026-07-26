from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_root_inventory_ui_explains_uncovered_folders() -> None:
    script = (WEB_UI / "root_inventory.js").read_text(encoding="utf-8")

    assert "Inventaire des dossiers à la racine" in script
    assert "Les projets et anciennes données sont facultatifs et décochés par défaut" in script
    assert "Dossiers et projets à examiner" in script
    assert "Éléments système non inclus" in script
    assert "Profils récupérables dans Windows.old" in script
    assert "réellement ajoutés à l’archive" in script
    assert "/api/v1/sources/root-inventory" in script


def test_drives_ui_loads_root_inventory_module() -> None:
    script = (WEB_UI / "drives.js").read_text(encoding="utf-8")

    assert "/app/root_inventory.js" in script
    assert "data-fsbackup-root-inventory" in script
