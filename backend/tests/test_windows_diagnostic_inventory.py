from pathlib import Path

from app.modules.source_discovery.diagnostic import diagnose_windows_source


def make_windows_root(tmp_path: Path) -> Path:
    root = tmp_path / "disk"
    root.mkdir()
    for name in ("Windows", "Users", "ProgramData", "Program Files", "Program Files (x86)"):
        (root / name).mkdir(parents=True)
    return root


def test_diagnostic_detects_system_layout_apps_and_messaging(tmp_path: Path, monkeypatch) -> None:
    root = make_windows_root(tmp_path)
    user = root / "Users" / "Frederic"
    (user / "Documents").mkdir(parents=True)
    (user / "Documents" / "important.txt").write_text("important", encoding="utf-8")
    (user / "AppData" / "Roaming" / "Thunderbird" / "Profiles" / "default").mkdir(parents=True)
    (user / "AppData" / "Roaming" / "Thunderbird" / "Profiles" / "default" / "prefs.js").write_text("", encoding="utf-8")
    (user / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default").mkdir(parents=True)
    (root / "Program Files" / "Git").mkdir()
    (root / "Program Files" / "nodejs").mkdir()

    monkeypatch.setattr(
        "app.modules.source_discovery.service.SourceDiscoveryService._validate_source_root",
        lambda self, value: root,
    )

    report = diagnose_windows_source(root)

    assert report.windows_detected is True
    assert report.confidence == "élevée"
    assert report.system.architecture == "64 bits"
    assert report.system.system_size_bytes == 0
    assert [user.name for user in report.users] == ["Frederic"]
    assert report.users[0].total_file_count == 1
    assert "Google Chrome" in report.detected_browsers
    assert [(item.client, item.user_name) for item in report.messaging_profiles] == [
        ("Thunderbird", "Frederic")
    ]
    assert {application.name for application in report.applications} >= {"Git", "Node.js"}


def test_diagnostic_keeps_unknown_optional_system_information(tmp_path: Path, monkeypatch) -> None:
    root = make_windows_root(tmp_path)
    monkeypatch.setattr(
        "app.modules.source_discovery.service.SourceDiscoveryService._validate_source_root",
        lambda self, value: root,
    )

    report = diagnose_windows_source(root)

    assert report.system.version is None
    assert report.system.edition is None
    assert report.system.computer_name is None
    assert report.system.installation_date is None
