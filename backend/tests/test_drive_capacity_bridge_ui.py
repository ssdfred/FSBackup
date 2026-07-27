from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_drive_capacity_bridge_normalizes_drive_letters() -> None:
    script = (WEB_UI / "drive_capacity_bridge.js").read_text(encoding="utf-8")

    assert "function fsbackupDriveKey" in script
    assert "selectedDrive" in script
    assert "destination-directory" in script
    assert "fsbackupDriveKey(drive.root)===key" in script


def test_drive_capacity_bridge_displays_free_space() -> None:
    script = (WEB_UI / "drive_capacity_bridge.js").read_text(encoding="utf-8")

    assert "free_bytes" in script
    assert "libres" in script
    assert "refreshDriveCapacityLabels" in script
    assert "fsbackup:drives-loaded" in script
    assert "fsbackup:destination-changed" in script
