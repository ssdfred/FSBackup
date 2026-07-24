"""Focused tests for Browser Inspector helper functions."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.modules.browser_inspector import models
from app.modules.browser_inspector.models import (
    BrowserBase,
    ChromeBrowser,
    FirefoxBrowser,
    _chromium_profile_active_time,
    _chromium_webkit_timestamp_to_datetime,
    _count_chromium_extensions,
    _count_firefox_extensions,
    _path_mtime,
    _sqlite_count_rows,
    _timestamp_to_datetime,
)


class MinimalBrowser(BrowserBase):
    """Concrete browser used to exercise default BrowserBase behavior."""

    key = "minimal"
    display_name = "Minimal"

    def executable_candidates(self) -> tuple[Path, ...]:
        return ()

    def profile_roots(self) -> tuple[Path, ...]:
        return ()


class FakeCursor:
    def __init__(self, row: object) -> None:
        self.row = row

    def fetchone(self) -> object:
        return self.row


class FakeConnection:
    def __init__(self, *, row: object = (1,), error: Exception | None = None) -> None:
        self.row = row
        self.error = error
        self.closed = False

    def execute(self, query: str) -> FakeCursor:
        if self.error is not None:
            raise self.error
        return FakeCursor(self.row)

    def close(self) -> None:
        self.closed = True


def test_browser_base_default_helpers_return_neutral_values(tmp_path: Path) -> None:
    browser = MinimalBrowser()
    profile = tmp_path / "Profile"

    assert browser.should_keep_profile("anything") is True
    assert browser.profile_name(profile) == "Profile"
    assert browser.profile_path(tmp_path, profile) == profile
    assert tuple(browser.last_used_candidates(tmp_path, profile, profile)) == ()
    assert browser.bookmarks_count(tmp_path, profile, profile) == 0
    assert browser.extensions_count(tmp_path, profile, profile) == 0
    assert browser.history_entries(tmp_path, profile, profile) == 0
    assert browser.cookies_count(tmp_path, profile, profile) == 0


@pytest.mark.parametrize(
    ("size_bytes", "expected"),
    [
        (0, "0 B"),
        (1023, "1023 B"),
        (1024, "1.00 KB"),
        (1024**2, "1.00 MB"),
        (1024**3, "1.00 GB"),
        (1024**4, "1.00 TB"),
    ],
)
def test_profile_size_human_formats_units(size_bytes: int, expected: str) -> None:
    assert MinimalBrowser().profile_size_human(size_bytes) == expected


def test_chromium_profile_filter_rejects_guest_and_unrelated_profiles() -> None:
    browser = ChromeBrowser()

    assert browser.should_keep_profile("Default") is True
    assert browser.should_keep_profile("Profile 12") is True
    assert browser.should_keep_profile("Guest Profile") is False
    assert browser.should_keep_profile("System Profile") is False
    assert browser.should_keep_profile("Crashpad") is False


def test_timestamp_helpers_handle_seconds_milliseconds_and_missing_paths(
    tmp_path: Path,
) -> None:
    expected = datetime.fromtimestamp(1_700_000_000, tz=UTC)

    assert _timestamp_to_datetime(1_700_000_000) == expected
    assert _timestamp_to_datetime(1_700_000_000_000) == expected
    assert _timestamp_to_datetime(None) is None

    missing = tmp_path / "missing"
    assert _path_mtime(missing) is None


def test_webkit_timestamp_conversion_handles_valid_and_invalid_values() -> None:
    assert _chromium_webkit_timestamp_to_datetime(None) is None
    assert _chromium_webkit_timestamp_to_datetime("invalid") is None
    assert _chromium_webkit_timestamp_to_datetime(-1) is None

    converted = _chromium_webkit_timestamp_to_datetime("11644473600000000")
    assert converted == datetime(1970, 1, 1, tzinfo=UTC)


def test_extension_counters_count_supported_entries(tmp_path: Path) -> None:
    chromium_root = tmp_path / "chromium"
    (chromium_root / "extension-a" / "1.0").mkdir(parents=True)
    (chromium_root / "extension-b").mkdir()
    (chromium_root / "README.txt").write_text("x", encoding="utf-8")

    firefox_root = tmp_path / "firefox"
    (firefox_root / "directory-extension").mkdir(parents=True)
    (firefox_root / "packed-extension.XPI").write_bytes(b"x")
    (firefox_root / "notes.txt").write_text("x", encoding="utf-8")

    assert _count_chromium_extensions(chromium_root) == 1
    assert _count_firefox_extensions(firefox_root) == 2


def test_extension_counters_tolerate_iteration_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chromium_root = tmp_path / "chromium"
    firefox_root = tmp_path / "firefox"
    chromium_root.mkdir()
    firefox_root.mkdir()
    original_iterdir = Path.iterdir

    def fail_for_roots(path: Path):
        if path in {chromium_root, firefox_root}:
            raise OSError("access denied")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_for_roots)

    assert _count_chromium_extensions(chromium_root) == 0
    assert _count_firefox_extensions(firefox_root) == 0


@pytest.mark.parametrize(
    "error",
    [
        PermissionError("denied"),
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("unable to open database file"),
        sqlite3.OperationalError("database disk image is malformed"),
        sqlite3.OperationalError("other operational error"),
        sqlite3.DatabaseError("file is not a database"),
        sqlite3.DatabaseError("other database error"),
        sqlite3.InterfaceError("interface error"),
    ],
)
def test_sqlite_count_rows_handles_database_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    database = tmp_path / "database.sqlite"
    database.write_bytes(b"placeholder")
    connection = FakeConnection(error=error)
    monkeypatch.setattr(models, "open_sqlite_readonly", lambda _: connection)

    assert _sqlite_count_rows(database, "SELECT COUNT(*) FROM rows") == 0
    assert connection.closed is True


def test_sqlite_count_rows_handles_empty_and_null_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "database.sqlite"
    database.write_bytes(b"placeholder")

    empty_connection = FakeConnection(row=None)
    monkeypatch.setattr(models, "open_sqlite_readonly", lambda _: empty_connection)
    assert _sqlite_count_rows(database, "SELECT 1") == 0
    assert empty_connection.closed is True

    null_connection = FakeConnection(row=(None,))
    monkeypatch.setattr(models, "open_sqlite_readonly", lambda _: null_connection)
    assert _sqlite_count_rows(database, "SELECT 1") == 0
    assert null_connection.closed is True


def test_chromium_active_time_reads_valid_value_and_missing_file(tmp_path: Path) -> None:
    assert _chromium_profile_active_time(tmp_path, "Default") is None

    payload = {
        "profile": {
            "info_cache": {
                "Default": {"active_time": 1_700_000_000},
            }
        }
    }
    (tmp_path / "Local State").write_text(json.dumps(payload), encoding="utf-8")

    assert _chromium_profile_active_time(tmp_path, "Default") == datetime.fromtimestamp(
        1_700_000_000,
        tz=UTC,
    )


def test_firefox_last_used_candidates_include_existing_file_mtimes(tmp_path: Path) -> None:
    profile = tmp_path / "default-release"
    profile.mkdir()
    prefs = profile / "prefs.js"
    prefs.write_text("", encoding="utf-8")

    candidates = tuple(FirefoxBrowser().last_used_candidates(tmp_path, profile, profile))

    assert len(candidates) == 4
    assert candidates[0] is not None
    assert candidates[1:] == (None, None, None)
