from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_exclusion_ui_keeps_suggestions_disabled_by_default() -> None:
    script = (WEB_UI / "diagnostic.js").read_text(encoding="utf-8")

    assert "selected:false" in script
    assert 'type="checkbox"' in script
    assert "Aucune exclusion n’est active par défaut" in script


def test_exclusion_ui_requires_separate_confirmation() -> None:
    script = (WEB_UI / "diagnostic.js").read_text(encoding="utf-8")

    assert "Validation séparée obligatoire" in script
    assert "Confirmer les exclusions" in script
    assert "stopImmediatePropagation" in script
    assert "exclusions_confirmed" in script
    assert "approved_exclusions" in script


def test_exclusion_ui_displays_risk_and_clear_estimates() -> None:
    script = (WEB_UI / "diagnostic.js").read_text(encoding="utf-8")

    assert "Risque ${item.risk}" in script
    assert "Données personnelles estimées" in script
    assert "Économie potentielle" in script
    assert "Ces données ne seront pas présentes dans l’archive" in script


def test_capacity_ui_distinguishes_disk_personal_data_and_plan() -> None:
    script = (WEB_UI / "capacity.js").read_text(encoding="utf-8")

    assert "Capacité du lecteur source" in script
    assert "Données personnelles repérées" in script
    assert "Plan réellement sauvegardé" in script
    assert "ne réalise pas une image complète" in script


def test_capacity_ui_blocks_an_unknown_or_insufficient_destination() -> None:
    script = (WEB_UI / "capacity.js").read_text(encoding="utf-8")

    assert "Espace insuffisant" in script
    assert "fsbackupDestinationCapacityValid" in script
    assert "stopImmediatePropagation" in script
    assert "Données Windows récupérables" in script
