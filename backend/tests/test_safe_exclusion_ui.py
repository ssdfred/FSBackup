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


def test_exclusion_ui_displays_risk_and_before_after_sizes() -> None:
    script = (WEB_UI / "diagnostic.js").read_text(encoding="utf-8")

    assert "Risque ${item.risk}" in script
    assert "Source estimée" in script
    assert "Après exclusions" in script
    assert "Ces données ne seront pas présentes dans l’archive" in script
