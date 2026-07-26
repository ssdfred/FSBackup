from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_dynamic_ui_modules_are_cache_busted() -> None:
    script = (WEB_UI / "drives.js").read_text(encoding="utf-8")

    assert 'const UI_MODULE_VERSION="10.6.1"' in script
    assert 'v=${encodeURIComponent(UI_MODULE_VERSION)}' in script
    assert 'loadOptionalModule("/app/capacity.js"' in script
    assert 'loadOptionalModule("/app/diagnostic.js"' in script
