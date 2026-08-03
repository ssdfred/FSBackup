from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_guard_only_rejects_a_response_from_another_selected_source() -> None:
    script = (WEB_UI / "diagnostic_source_guard.js").read_text(encoding="utf-8")

    assert "requestVersions" not in script
    assert "source === selectedSource()" in script
    assert "Les appels simultanés du diagnostic et de la capacité" in script
    assert "return new Promise(() => {})" in script
