from pathlib import Path


def test_old_profiles_are_explicitly_recoverable() -> None:
    script = (
        Path(__file__).parents[1] / "app" / "web_ui" / "root_inventory.js"
    ).read_text(encoding="utf-8")

    assert "Profils récupérables dans Windows.old" in script
    assert "réellement ajoutés à l’archive" in script
