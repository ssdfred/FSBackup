"""Tests for browser discovery models and orchestration."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.modules.browser_inspector.models import (
    BrowserProfileRecord,
    BrowserSnapshot,
    ChromeBrowser,
    FirefoxBrowser,
    ProfileStorageStats,
    _chromium_profile_active_time,
    _chromium_webkit_timestamp_to_datetime,
    _count_chromium_extensions,
    _count_firefox_extensions,
    _load_chromium_bookmarks,
    _sqlite_count_rows,
    _timestamp_to_datetime,
)
from app.modules.browser_inspector.service import BrowserDiscoveryEngine


class StubChromeBrowser(ChromeBrowser):
    """Chrome implementation with controlled roots and executable paths."""

    def __init__(self, root: Path, executable: Path | None = None) -> None:
        self.root = root
        self.executable = executable

    def profile_roots(self) -> tuple[Path, ...]:
        return (self.root,)

    def executable_candidates(self) -> tuple[Path, ...]:
        return (self.executable,) if self.executable is not None else ()


class StaticBrowser:
    """Return a predefined browser snapshot."""

    def __init__(self, key: str, snapshot: BrowserSnapshot) -> None:
        self.key = key
        self.snapshot = snapshot

    def discover(self) -> BrowserSnapshot:
        return self.snapshot


def create_count_database(path: Path, table: str, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
        connection.executemany(
            f"INSERT INTO {table} DEFAULT VALUES",
            [() for _ in range(rows)],
        )
        connection.commit()
    finally:
        connection.close()


def empty_snapshot(*profiles: BrowserProfileRecord) -> BrowserSnapshot:
    return BrowserSnapshot(installed=bool(profiles), version=None, profiles=profiles)


def test_find_executable_returns_first_existing_candidate(tmp_path: Path) -> None:
    missing = tmp_path / "missing.exe"
    existing = tmp_path / "browser.exe"
    existing.write_bytes(b"")
    browser = StubChromeBrowser(tmp_path)
    browser.executable_candidates = lambda: (missing, existing)  # type: ignore[method-assign]

    assert browser.find_executable() == existing


def test_discover_marks_browser_installed_when_profiles_exist(tmp_path: Path) -> None:
    (tmp_path / "Default").mkdir()

    snapshot = StubChromeBrowser(tmp_path).discover()

    assert snapshot.installed is True
    assert snapshot.version is None
    assert [profile.name for profile in snapshot.profiles] == ["Default"]


def test_chromium_profile_filter_rejects_guest_and_unrelated_directories() -> None:
    browser = ChromeBrowser()

    assert browser.should_keep_profile("Default") is True
    assert browser.should_keep_profile("Profile 12") is True
    assert browser.should_keep_profile("Guest Profile") is False
    assert browser.should_keep_profile("System Profile") is False
    assert browser.should_keep_profile("Crash Reports") is False


def test_profile_size_ignores_cache_directories(tmp_path: Path) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    (profile / "Preferences").write_bytes(b"1234")
    cache = profile / "Cache"
    cache.mkdir()
    (cache / "large.bin").write_bytes(b"x" * 100)

    stats = StubChromeBrowser(tmp_path).profile_storage_stats(profile)

    assert stats.size_bytes == 4
    assert stats.latest_mtime is not None


def test_profile_size_human_formats_expected_units(tmp_path: Path) -> None:
    browser = StubChromeBrowser(tmp_path)

    assert browser.profile_size_human(0) == "0 B"
    assert browser.profile_size_human(1024) == "1.00 KB"
    assert browser.profile_size_human(1024 * 1024) == "1.00 MB"


def test_profile_last_used_keeps_latest_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    older = datetime(2025, 1, 1, tzinfo=UTC)
    newer = datetime(2026, 1, 1, tzinfo=UTC)
    browser = StubChromeBrowser(tmp_path)
    monkeypatch.setattr(browser, "last_used_candidates", lambda *_: (older, newer, None))

    result = browser.profile_last_used(
        tmp_path,
        profile,
        profile,
        ProfileStorageStats(size_bytes=0, latest_mtime=older),
    )

    assert result == newer


def test_sqlite_count_rows_reads_database_without_modifying_it(tmp_path: Path) -> None:
    database = tmp_path / "History"
    create_count_database(database, "urls", 3)

    assert _sqlite_count_rows(database, "SELECT COUNT(*) FROM urls;") == 3
    assert database.exists()


def test_sqlite_count_rows_returns_zero_for_missing_or_corrupt_database(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite"
    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_text("not a sqlite database", encoding="utf-8")

    assert _sqlite_count_rows(missing, "SELECT COUNT(*) FROM rows;") == 0
    assert _sqlite_count_rows(corrupt, "SELECT COUNT(*) FROM rows;") == 0


def test_chromium_cookie_count_prefers_network_database(tmp_path: Path) -> None:
    profile = tmp_path / "Default"
    create_count_database(profile / "Network" / "Cookies", "cookies", 2)
    create_count_database(profile / "Cookies", "cookies", 5)

    count = ChromeBrowser().cookies_count(tmp_path, profile, profile)

    assert count == 2


def test_firefox_counts_bookmarks_history_cookies_and_extensions(tmp_path: Path) -> None:
    profile = tmp_path / "default-release"
    profile.mkdir()
    places = sqlite3.connect(profile / "places.sqlite")
    try:
        places.execute("CREATE TABLE moz_bookmarks (type INTEGER, fk INTEGER)")
        places.executemany(
            "INSERT INTO moz_bookmarks VALUES (?, ?)",
            [(1, 1), (1, 2), (2, None)],
        )
        places.execute("CREATE TABLE moz_historyvisits (id INTEGER)")
        places.executemany("INSERT INTO moz_historyvisits VALUES (?)", [(1,), (2,), (3,)])
        places.commit()
    finally:
        places.close()
    create_count_database(profile / "cookies.sqlite", "moz_cookies", 4)
    extensions = profile / "extensions"
    extensions.mkdir()
    (extensions / "first.xpi").write_bytes(b"")
    (extensions / "second").mkdir()
    (extensions / "ignored.txt").write_text("x", encoding="utf-8")
    browser = FirefoxBrowser()

    assert browser.bookmarks_count(tmp_path, profile, profile) == 2
    assert browser.history_entries(tmp_path, profile, profile) == 3
    assert browser.cookies_count(tmp_path, profile, profile) == 4
    assert browser.extensions_count(tmp_path, profile, profile) == 2


def test_extension_counters_ignore_invalid_entries(tmp_path: Path) -> None:
    chromium = tmp_path / "chromium"
    chromium.mkdir()
    valid = chromium / "extension-a"
    valid.mkdir()
    (valid / "1.0").mkdir()
    (chromium / "file.txt").write_text("x", encoding="utf-8")
    empty = chromium / "empty-extension"
    empty.mkdir()

    firefox = tmp_path / "firefox"
    firefox.mkdir()
    (firefox / "extension.xpi").write_bytes(b"")
    (firefox / "readme.txt").write_text("x", encoding="utf-8")

    assert _count_chromium_extensions(chromium) == 1
    assert _count_firefox_extensions(firefox) == 1


def test_bookmark_loader_returns_metadata_and_nested_folder(tmp_path: Path) -> None:
    bookmarks = tmp_path / "Bookmarks"
    bookmarks.write_text(
        json.dumps(
            {
                "roots": {
                    "bookmark_bar": {
                        "type": "folder",
                        "name": "Bar",
                        "children": [
                            {
                                "type": "folder",
                                "name": "Docs",
                                "children": [
                                    {
                                        "type": "url",
                                        "name": "FSBackup",
                                        "url": "https://example.test",
                                        "date_added": "13348540800000000",
                                    }
                                ],
                            }
                        ],
                    },
                    "managed_bookmarks": {
                        "type": "folder",
                        "children": [
                            {"type": "url", "name": "Managed", "url": "https://managed.test"}
                        ],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    records = _load_chromium_bookmarks(
        bookmarks,
        source="chrome",
        profile_identifier="Default",
    )

    assert len(records) == 1
    assert records[0].title == "FSBackup"
    assert records[0].folder == "Bar/Docs"
    assert records[0].source == "chrome"
    assert records[0].date_added is not None


@pytest.mark.parametrize("payload", ["[]", "{}", '{"roots": []}'])
def test_bookmark_loader_rejects_unexpected_structures(tmp_path: Path, payload: str) -> None:
    bookmarks = tmp_path / "Bookmarks"
    bookmarks.write_text(payload, encoding="utf-8")

    assert _load_chromium_bookmarks(bookmarks, source="chrome", profile_identifier="x") == ()


def test_timestamp_helpers_handle_seconds_milliseconds_and_invalid_values() -> None:
    seconds = _timestamp_to_datetime(1_700_000_000)
    milliseconds = _timestamp_to_datetime(1_700_000_000_000)

    assert seconds == milliseconds
    assert _timestamp_to_datetime(None) is None
    assert _timestamp_to_datetime(float("inf")) is None
    assert _chromium_webkit_timestamp_to_datetime("invalid") is None
    assert _chromium_webkit_timestamp_to_datetime(0) is None


def test_chromium_active_time_reads_local_state(tmp_path: Path) -> None:
    (tmp_path / "Local State").write_text(
        json.dumps(
            {
                "profile": {
                    "info_cache": {
                        "Default": {"active_time": 1_700_000_000.0}
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    assert _chromium_profile_active_time(tmp_path, "Default") == datetime.fromtimestamp(
        1_700_000_000,
        tz=UTC,
    )
    assert _chromium_profile_active_time(tmp_path, "Profile 1") is None


def test_browser_discovery_engine_builds_all_browser_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = BrowserProfileRecord(
        name="Default",
        path=tmp_path / "Default",
        profile_size_bytes=10,
        profile_size_human="10 B",
        last_used=None,
        bookmarks_count=0,
        extensions_count=1,
        history_entries=2,
        cookies_count=3,
    )
    browsers = tuple(
        StaticBrowser(key, empty_snapshot(profile))
        for key in ("chrome", "edge", "firefox", "brave")
    )
    engine = BrowserDiscoveryEngine(browsers=browsers)  # type: ignore[arg-type]
    monkeypatch.setattr(engine, "_platform_name", lambda: "TestOS")

    report = engine.build_report()

    assert report.platform == "TestOS"
    assert report.browsers.chrome.installed is True
    assert report.browsers.edge.profiles[0].history_entries == 2
    assert report.browsers.firefox.profiles[0].bookmarks == []
    assert report.browsers.brave.profiles[0].cookies_count == 3


def test_service_loads_bookmark_details_only_for_chromium(tmp_path: Path) -> None:
    profile_path = tmp_path / "Default"
    profile_path.mkdir()
    (profile_path / "Bookmarks").write_text(
        json.dumps(
            {
                "roots": {
                    "bookmark_bar": {
                        "type": "folder",
                        "children": [
                            {"type": "url", "name": "One", "url": "https://one.test"}
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    engine = BrowserDiscoveryEngine()

    assert len(engine._bookmarks_for_profile("chrome", profile_path)) == 1
    assert len(engine._bookmarks_for_profile("edge", profile_path)) == 1
    assert len(engine._bookmarks_for_profile("brave", profile_path)) == 1
    assert engine._bookmarks_for_profile("firefox", profile_path) == []
