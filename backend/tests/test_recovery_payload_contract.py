from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_recovery_selection_is_sent_and_counted() -> None:
    payload = (WEB_UI / "exclusion_payload.js").read_text(encoding="utf-8")
    inventory = (WEB_UI / "root_inventory.js").read_text(encoding="utf-8")
    capacity = (WEB_UI / "capacity.js").read_text(encoding="utf-8")

    assert "selected_recovery_paths" in payload
    assert "getSelectedRecoveryPaths" in inventory
    assert "getSelectedRecoverySize" in capacity
