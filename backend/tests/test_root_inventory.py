from pathlib import Path

import pytest

from app.modules.source_discovery.root_inventory import inventory_root
from app.modules.source_discovery.root_inventory_schemas import RootEntryCategory
from app.modules.source_discovery.service import SourceDiscoveryService


def _write(path: Path, size: int = 4) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


@pytest.fixture
def allow_temporary_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow a pytest temporary directory to stand in for a Windows drive root."""

    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda _self, source_root: Path(source_root).resolve(strict=True),
    )


def test_root_inventory_classifies_projects_system_and_windows_old(
    tmp_path: Path,
    allow_temporary_root: None,
) -> None:
    (tmp_path / "Windows").mkdir()
    (tmp_path / "ProgramData").mkdir()
    _write(tmp_path / "laragon" / "www" / "site" / "index.php", 7)
    _write(tmp_path / "OSADAPT01" / "project.txt", 5)
    _write(
        tmp_path / "Windows.old" / "Users" / "fred" / "Documents" / "old.txt",
        9,
    )
    _write(
        tmp_path / "Windows.old" / "Users" / "fred" / "AppData" / "Roaming" / "mail.dat",
        13,
    )

    report = inventory_root(tmp_path)
    entries = {entry.name: entry for entry in report.entries}

    assert entries["Windows"].category == RootEntryCategory.SYSTEM
    assert entries["ProgramData"].category == RootEntryCategory.SYSTEM
    assert entries["laragon"].category == RootEntryCategory.REVIEW
    assert entries["laragon"].size_bytes == 7
    assert entries["OSADAPT01"].category == RootEntryCategory.REVIEW
    assert entries["Windows.old"].category == RootEntryCategory.OLD_WINDOWS
    assert entries["Windows.old"].included_by_default is False
    assert entries["Windows.old"].size_bytes == 22
    assert report.review_size_bytes == 12
    assert len(report.old_windows_profiles) == 1
    profile = report.old_windows_profiles[0]
    assert profile.name == "fred"
    assert profile.standard_size_bytes == 9
    assert profile.total_size_bytes == 22
    assert profile.additional_size_bytes == 13


def test_root_inventory_reports_current_profile_content_beyond_standard_folders(
    tmp_path: Path,
    allow_temporary_root: None,
) -> None:
    _write(tmp_path / "Users" / "fred" / "Documents" / "document.txt", 5)
    _write(tmp_path / "Users" / "fred" / "AppData" / "Roaming" / "settings.dat", 17)
    _write(tmp_path / "Users" / "fred" / ".ssh" / "config", 11)

    report = inventory_root(tmp_path)

    assert len(report.current_windows_profiles) == 1
    profile = report.current_windows_profiles[0]
    assert profile.path == str(tmp_path / "Users" / "fred")
    assert profile.standard_size_bytes == 5
    assert profile.total_size_bytes == 33
    assert profile.additional_size_bytes == 28
    assert report.recoverable_profile_size_bytes == 33


def test_root_inventory_does_not_follow_directory_symlinks(
    tmp_path: Path,
    allow_temporary_root: None,
) -> None:
    target = tmp_path / "outside"
    _write(target / "secret.txt", 11)
    link = tmp_path / "project-link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        return

    report = inventory_root(tmp_path)

    assert "project-link" not in {entry.name for entry in report.entries}
