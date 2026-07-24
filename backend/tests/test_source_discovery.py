"""Tests for read-only Windows source discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.source_discovery.schemas import SourceType
from app.modules.source_discovery.service import (
    SourceDiscoveryError,
    SourceDiscoveryService,
)


def _create_windows_disk(root: Path) -> None:
    """Create the minimum structure of a Windows disk."""

    (root / "Windows").mkdir()
    (root / "Users").mkdir()


def _create_chromium_profile(
    user_path: Path,
    browser_parts: tuple[str, ...],
    profile_name: str = "Default",
) -> Path:
    """Create a minimal Chromium profile."""

    profile_path = user_path.joinpath(*browser_parts, profile_name)
    profile_path.mkdir(parents=True)

    (profile_path / "Bookmarks").write_text("{}", encoding="utf-8")
    (profile_path / "History").write_bytes(b"history")
    (profile_path / "Login Data").write_bytes(b"logins")
    (profile_path / "Web Data").write_bytes(b"autofill")
    (profile_path / "Preferences").write_text("{}", encoding="utf-8")

    (profile_path / "Network").mkdir()
    (profile_path / "Network" / "Cookies").write_bytes(b"cookies")

    (profile_path / "Extensions").mkdir()
    (profile_path / "Sessions").mkdir()

    return profile_path


def _create_firefox_profile(
    user_path: Path,
    profile_name: str = "abc123.default-release",
) -> Path:
    """Create a minimal Firefox profile."""

    profile_path = user_path.joinpath(
        "AppData",
        "Roaming",
        "Mozilla",
        "Firefox",
        "Profiles",
        profile_name,
    )
    profile_path.mkdir(parents=True)

    (profile_path / "prefs.js").write_text("", encoding="utf-8")
    (profile_path / "places.sqlite").write_bytes(b"places")
    (profile_path / "cookies.sqlite").write_bytes(b"cookies")
    (profile_path / "logins.json").write_text("{}", encoding="utf-8")
    (profile_path / "key4.db").write_bytes(b"key")
    (profile_path / "formhistory.sqlite").write_bytes(b"autofill")
    (profile_path / "sessionstore.jsonlz4").write_bytes(b"session")
    (profile_path / "extensions").mkdir()

    return profile_path


def test_missing_source_raises_error(tmp_path: Path) -> None:
    """A nonexistent source must be rejected."""

    service = SourceDiscoveryService()

    with pytest.raises(SourceDiscoveryError, match="n'existe pas"):
        service.discover(tmp_path / "missing")


def test_source_must_be_a_directory(tmp_path: Path) -> None:
    """A regular file cannot be used as source_root."""

    source_file = tmp_path / "disk.txt"
    source_file.write_text("not a disk", encoding="utf-8")

    service = SourceDiscoveryService()

    with pytest.raises(SourceDiscoveryError, match="n'est pas un dossier"):
        service.discover(source_file)


def test_source_must_be_a_root_directory(tmp_path: Path) -> None:
    """A nested directory must not be accepted as a disk root."""

    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()

    service = SourceDiscoveryService()

    with pytest.raises(
        SourceDiscoveryError,
        match="racine d'un disque",
    ):
        service.discover(nested_directory)


def test_windows_disk_without_users_directory_returns_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source without Users must return an empty report."""

    root = tmp_path / "disk"
    root.mkdir()
    (root / "Windows").mkdir()

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    assert report.windows_detected is False
    assert report.users == []
    assert report.users_directory is None
    assert len(report.warnings) == 1
    assert "utilisateurs est introuvable" in report.warnings[0]


def test_system_users_are_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Technical Windows profiles must not appear in the report."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    ignored_users = (
        "Default",
        "Default User",
        "Public",
        "All Users",
        "CodexSandboxOffline",
        "DefaultAppPool",
        "systemprofile",
        "LocalService",
        "NetworkService",
        "IIS APPPOOL",
        "CodexSandbox123",
    )

    for user_name in ignored_users:
        (root / "Users" / user_name).mkdir()

    real_user = root / "Users" / "Fred"
    real_user.mkdir()

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    assert [user.name for user in report.users] == ["Fred"]


def test_multiple_real_users_are_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple normal Windows users must be returned."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    (root / "Users" / "Alice").mkdir()
    (root / "Users" / "Fred").mkdir()

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    assert [user.name for user in report.users] == [
        "Alice",
        "Fred",
    ]


def test_chrome_profile_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chrome and its useful data must be discovered."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    user_path = root / "Users" / "Fred"
    user_path.mkdir()

    _create_chromium_profile(
        user_path,
        (
            "AppData",
            "Local",
            "Google",
            "Chrome",
            "User Data",
        ),
    )

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    browser = report.users[0].browsers[0]
    profile = browser.profiles[0]

    assert browser.key == "chrome"
    assert browser.name == "Google Chrome"
    assert profile.name == "Default"

    assert profile.data.bookmarks is True
    assert profile.data.history is True
    assert profile.data.cookies is True
    assert profile.data.passwords is True
    assert profile.data.autofill is True
    assert profile.data.extensions is True
    assert profile.data.sessions is True
    assert profile.data.preferences is True

    assert profile.data.potentially_encrypted == [
        "passwords",
        "cookies",
    ]


@pytest.mark.parametrize(
    ("browser_key", "browser_name", "browser_parts"),
    [
        (
            "edge",
            "Microsoft Edge",
            (
                "AppData",
                "Local",
                "Microsoft",
                "Edge",
                "User Data",
            ),
        ),
        (
            "brave",
            "Brave",
            (
                "AppData",
                "Local",
                "BraveSoftware",
                "Brave-Browser",
                "User Data",
            ),
        ),
    ],
)
def test_other_chromium_browsers_are_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    browser_key: str,
    browser_name: str,
    browser_parts: tuple[str, ...],
) -> None:
    """Edge and Brave must use the same Chromium discovery logic."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    user_path = root / "Users" / "Fred"
    user_path.mkdir()

    _create_chromium_profile(
        user_path,
        browser_parts,
    )

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    browser = report.users[0].browsers[0]

    assert browser.key == browser_key
    assert browser.name == browser_name
    assert browser.profiles[0].name == "Default"


def test_firefox_profile_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Firefox profiles and encrypted data markers must be detected."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    user_path = root / "Users" / "Fred"
    user_path.mkdir()

    _create_firefox_profile(user_path)

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    browser = report.users[0].browsers[0]
    profile = browser.profiles[0]

    assert browser.key == "firefox"
    assert browser.name == "Mozilla Firefox"
    assert profile.name == "abc123.default-release"

    assert profile.data.bookmarks is True
    assert profile.data.history is True
    assert profile.data.cookies is True
    assert profile.data.passwords is True
    assert profile.data.autofill is True
    assert profile.data.extensions is True
    assert profile.data.sessions is True
    assert profile.data.preferences is True

    assert profile.data.potentially_encrypted == [
        "passwords",
        "cookies",
    ]


def test_user_without_browser_is_still_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real Windows user may exist without supported browser data."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    (root / "Users" / "Fred").mkdir()

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    assert len(report.users) == 1
    assert report.users[0].name == "Fred"
    assert report.users[0].browsers == []


def test_empty_browser_profile_root_is_returned_without_profiles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A browser directory may exist without a valid profile."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    profile_root = root.joinpath(
        "Users",
        "Fred",
        "AppData",
        "Local",
        "Google",
        "Chrome",
        "User Data",
    )
    profile_root.mkdir(parents=True)

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    report = SourceDiscoveryService().discover(root)

    browser = report.users[0].browsers[0]

    assert browser.key == "chrome"
    assert browser.profiles == []


def test_windows_disk_source_type_is_returned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-system source must be classified as an old Windows disk."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )
    monkeypatch.setattr(
        SourceDiscoveryService,
        "_detect_source_type",
        lambda self, source_root: SourceType.WINDOWS_DISK,
    )

    report = SourceDiscoveryService().discover(root)

    assert report.source_type == SourceType.WINDOWS_DISK
    assert report.windows_detected is True


def test_discovery_does_not_modify_source_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discovery must remain strictly read-only."""

    root = tmp_path / "disk"
    root.mkdir()
    _create_windows_disk(root)

    user_path = root / "Users" / "Fred"
    user_path.mkdir()

    profile_path = _create_chromium_profile(
        user_path,
        (
            "AppData",
            "Local",
            "Google",
            "Chrome",
            "User Data",
        ),
    )

    files_before = {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )

    SourceDiscoveryService().discover(root)

    files_after = {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }

    assert profile_path.exists()
    assert files_after == files_before


def test_path_outside_source_is_rejected(
    tmp_path: Path,
) -> None:
    """A path outside the authorized source must not be accepted."""

    root = tmp_path / "disk"
    root.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    service = SourceDiscoveryService()

    assert service._is_inside_root(root, root / "Users" / "Fred") is True
    assert service._is_inside_root(root, outside) is False