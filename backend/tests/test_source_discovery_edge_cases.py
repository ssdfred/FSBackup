"""Edge-case tests for the read-only source discovery service."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.modules.source_discovery.schemas import SourceType
from app.modules.source_discovery.service import (
    BrowserDefinition,
    SourceDiscoveryError,
    SourceDiscoveryService,
    discover_source,
)


def test_validate_source_root_wraps_resolution_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolution failures must be exposed as domain errors."""

    root = tmp_path / "disk"
    root.mkdir()
    original_resolve = Path.resolve

    def fail_for_root(path: Path, strict: bool = False) -> Path:
        if path == root:
            raise OSError("volume indisponible")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_for_root)

    with pytest.raises(SourceDiscoveryError, match="Impossible de résoudre"):
        SourceDiscoveryService()._validate_source_root(root)


def test_detect_source_type_recognizes_system_drive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The active Windows root must be classified as local Windows."""

    root = tmp_path / "system"
    root.mkdir()
    monkeypatch.setenv("SystemDrive", "C:")
    original_resolve = Path.resolve

    def resolve_system_drive(path: Path, strict: bool = False) -> Path:
        if str(path) == "C:\\":
            return root
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve_system_drive)

    assert SourceDiscoveryService._detect_source_type(root) == SourceType.LOCAL_WINDOWS


def test_detect_source_type_tolerates_resolution_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreadable SystemDrive must fall back to an external disk."""

    root = tmp_path / "disk"
    root.mkdir()
    monkeypatch.setenv("SystemDrive", "Z:")
    original_resolve = Path.resolve

    def fail_for_system_drive(path: Path, strict: bool = False) -> Path:
        if str(path) == "Z:\\":
            raise OSError("lecteur absent")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_for_system_drive)

    assert SourceDiscoveryService._detect_source_type(root) == SourceType.WINDOWS_DISK


@pytest.mark.parametrize("error", [PermissionError(), OSError("lecture impossible")])
def test_discover_users_reports_directory_listing_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
) -> None:
    """User-directory listing failures must become warnings."""

    root = tmp_path / "disk"
    users_directory = root / "Users"
    users_directory.mkdir(parents=True)
    original_iterdir = Path.iterdir

    def fail_for_users(path: Path):
        if path == users_directory:
            raise error
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_for_users)
    warnings: list[str] = []

    users = SourceDiscoveryService()._discover_users(
        root=root,
        users_directory=users_directory,
        warnings=warnings,
    )

    assert users == []
    assert len(warnings) == 1


def test_discover_users_skips_files_and_paths_outside_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only directories that remain inside the source may become users."""

    root = tmp_path / "disk"
    users_directory = root / "Users"
    users_directory.mkdir(parents=True)
    (users_directory / "document.txt").write_text("x", encoding="utf-8")
    outside_user = users_directory / "LinkedUser"
    outside_user.mkdir()

    service = SourceDiscoveryService()
    original_inside = service._is_inside_root
    monkeypatch.setattr(
        service,
        "_is_inside_root",
        lambda source, candidate: False
        if candidate == outside_user
        else original_inside(source, candidate),
    )
    warnings: list[str] = []

    users = service._discover_users(
        root=root,
        users_directory=users_directory,
        warnings=warnings,
    )

    assert users == []
    assert any("hors de la source" in warning for warning in warnings)


def test_discover_users_reports_is_dir_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing user-directory inspection must not abort discovery."""

    root = tmp_path / "disk"
    users_directory = root / "Users"
    user_path = users_directory / "Fred"
    user_path.mkdir(parents=True)
    original_is_dir = Path.is_dir

    def fail_for_user(path: Path) -> bool:
        if path == user_path:
            raise OSError("métadonnées illisibles")
        return original_is_dir(path)

    monkeypatch.setattr(Path, "is_dir", fail_for_user)
    warnings: list[str] = []

    users = SourceDiscoveryService()._discover_users(
        root=root,
        users_directory=users_directory,
        warnings=warnings,
    )

    assert users == []
    assert "Impossible d'inspecter" in warnings[0]


def test_discover_browsers_handles_unsafe_and_unreadable_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsafe and unreadable browser roots must be skipped independently."""

    root = tmp_path / "disk"
    user_path = root / "Users" / "Fred"
    user_path.mkdir(parents=True)
    definitions = (
        BrowserDefinition("unsafe", "Unsafe", ("unsafe",), "chromium"),
        BrowserDefinition("broken", "Broken", ("broken",), "chromium"),
    )
    monkeypatch.setattr(
        "app.modules.source_discovery.service.BROWSER_DEFINITIONS",
        definitions,
    )
    unsafe_root = user_path / "unsafe"
    broken_root = user_path / "broken"
    broken_root.mkdir()
    original_is_dir = Path.is_dir

    def fail_for_broken(path: Path) -> bool:
        if path == broken_root:
            raise OSError("accès impossible")
        return original_is_dir(path)

    monkeypatch.setattr(Path, "is_dir", fail_for_broken)
    service = SourceDiscoveryService()
    monkeypatch.setattr(
        service,
        "_is_inside_root",
        lambda source, candidate: candidate != unsafe_root,
    )
    warnings: list[str] = []

    browsers = service._discover_browsers(
        root=root,
        user_path=user_path,
        warnings=warnings,
    )

    assert browsers == []
    assert len(warnings) == 2
    assert "hors de la source" in warnings[0]
    assert "Impossible d'inspecter" in warnings[1]


@pytest.mark.parametrize("error", [PermissionError(), OSError("profil illisible")])
def test_discover_profiles_reports_listing_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
) -> None:
    """Profile-root listing failures must be converted to warnings."""

    root = tmp_path / "disk"
    profile_root = root / "profiles"
    profile_root.mkdir(parents=True)
    original_iterdir = Path.iterdir

    def fail_for_profiles(path: Path):
        if path == profile_root:
            raise error
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_for_profiles)
    warnings: list[str] = []

    profiles = SourceDiscoveryService()._discover_profiles(
        root=root,
        profile_root=profile_root,
        browser_family="chromium",
        warnings=warnings,
    )

    assert profiles == []
    assert len(warnings) == 1


def test_discover_profiles_skips_invalid_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Files, unsafe paths and directories without markers must be ignored."""

    root = tmp_path / "disk"
    profile_root = root / "profiles"
    profile_root.mkdir(parents=True)
    (profile_root / "plain-file").write_text("x", encoding="utf-8")
    unsafe = profile_root / "Unsafe"
    unsafe.mkdir()
    invalid = profile_root / "Random"
    invalid.mkdir()

    service = SourceDiscoveryService()
    monkeypatch.setattr(
        service,
        "_is_inside_root",
        lambda source, candidate: candidate != unsafe,
    )
    warnings: list[str] = []

    profiles = service._discover_profiles(
        root=root,
        profile_root=profile_root,
        browser_family="chromium",
        warnings=warnings,
    )

    assert profiles == []
    assert any("Profil ignoré" in warning for warning in warnings)


def test_profile_detectors_accept_names_and_marker_files(tmp_path: Path) -> None:
    """Known Chromium names and browser marker files must identify profiles."""

    default = tmp_path / "Default"
    default.mkdir()
    numbered = tmp_path / "Profile 7"
    numbered.mkdir()
    chromium_marker = tmp_path / "CustomChromium"
    chromium_marker.mkdir()
    (chromium_marker / "History").write_bytes(b"")
    firefox_marker = tmp_path / "CustomFirefox"
    firefox_marker.mkdir()
    (firefox_marker / "prefs.js").write_text("", encoding="utf-8")

    assert SourceDiscoveryService._is_chromium_profile(default) is True
    assert SourceDiscoveryService._is_chromium_profile(numbered) is True
    assert SourceDiscoveryService._is_chromium_profile(chromium_marker) is True
    assert SourceDiscoveryService._is_firefox_profile(firefox_marker) is True


def test_minimal_profile_inspection_reports_unavailable_data(tmp_path: Path) -> None:
    """Empty profiles must produce a fully false availability report."""

    chromium = tmp_path / "chromium"
    firefox = tmp_path / "firefox"
    chromium.mkdir()
    firefox.mkdir()

    chromium_data = SourceDiscoveryService._inspect_chromium_profile(chromium)
    firefox_data = SourceDiscoveryService._inspect_firefox_profile(firefox)

    assert chromium_data.potentially_encrypted == []
    assert firefox_data.potentially_encrypted == []
    assert chromium_data.model_dump(exclude={"potentially_encrypted"}) == {
        "bookmarks": False,
        "history": False,
        "cookies": False,
        "passwords": False,
        "autofill": False,
        "extensions": False,
        "sessions": False,
        "preferences": False,
    }
    assert firefox_data.model_dump(exclude={"potentially_encrypted"}) == {
        "bookmarks": False,
        "history": False,
        "cookies": False,
        "passwords": False,
        "autofill": False,
        "extensions": False,
        "sessions": False,
        "preferences": False,
    }


def test_is_inside_root_handles_resolution_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Path-resolution errors must be treated as an unsafe path."""

    root = tmp_path / "disk"
    candidate = root / "Users" / "Fred"
    root.mkdir()
    original_resolve = Path.resolve

    def fail_for_candidate(path: Path, strict: bool = False) -> Path:
        if path == candidate:
            raise RuntimeError("boucle de liens")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_for_candidate)

    assert SourceDiscoveryService._is_inside_root(root, candidate) is False


def test_discover_source_uses_service_entry_point(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The convenience function must delegate to the service."""

    root = tmp_path / "disk"
    root.mkdir()
    expected = object()
    monkeypatch.setattr(
        SourceDiscoveryService,
        "discover",
        lambda self, source_root: expected,
    )

    assert discover_source(root) is expected
    assert os.fspath(root).endswith("disk")
