"""Edge-case tests for browser discovery helpers."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.modules.browser_inspector import models
from app.modules.browser_inspector.models import (
    ChromeBrowser,
    FirefoxBrowser,
    _chromium_profile_active_time,
    _count_chromium_extensions,
    _count_firefox_extensions,
    _environment_path,
    _sqlite_count_rows,
)


class ControlledChromeBrowser(ChromeBrowser):
    """Chrome implementation with controlled roots."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def profile_roots(self) -> tuple[Path, ...]:
        return (self.root,)

    def executable_candidates(self) -> tuple[Path, ...]:
        return ()


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


def test_discover_marks_browser_absent_without_executable_or_profile(
    tmp_path: Path,
) -> None:
    snapshot = ControlledChromeBrowser(tmp_path / "missing").discover()

    assert snapshot.installed is False
    assert snapshot.version is None
    assert snapshot.profiles == ()


def test_get_profiles_ignores_files_and_sorts_profiles(tmp_path: Path) -> None:
    (tmp_path / "Profile 2").mkdir()
    (tmp_path / "Default").mkdir()
    (tmp_path / "Profile 1").mkdir()
    (tmp_path / "Profile 3").write_text("not a directory", encoding="utf-8")

    profiles = ControlledChromeBrowser(tmp_path).get_profiles()

    assert [profile.name for profile in profiles] == [
        "Default",
        "Profile 1",
        "Profile 2",
    ]


def test_cookie_count_falls_back_to_legacy_database(tmp_path: Path) -> None:
    profile = tmp_path / "Default"
    create_count_database(profile / "Cookies", "cookies", 4)

    assert ChromeBrowser().cookies_count(tmp_path, profile, profile) == 4


def test_cookie_count_returns_zero_when_database_is_absent(tmp_path: Path) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()

    assert ChromeBrowser().cookies_count(tmp_path, profile, profile) == 0


def test_firefox_missing_databases_and_extensions_return_zero(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "default-release"
    profile.mkdir()
    browser = FirefoxBrowser()

    assert browser.bookmarks_count(tmp_path, profile, profile) == 0
    assert browser.history_entries(tmp_path, profile, profile) == 0
    assert browser.cookies_count(tmp_path, profile, profile) == 0
    assert browser.extensions_count(tmp_path, profile, profile) == 0


def test_sqlite_count_rows_returns_zero_for_missing_table(tmp_path: Path) -> None:
    database = tmp_path / "database.sqlite"
    create_count_database(database, "existing_table", 1)

    assert _sqlite_count_rows(database, "SELECT COUNT(*) FROM missing_table;") == 0


def test_sqlite_count_rows_handles_unexpected_row_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "database.sqlite"
    database.write_bytes(b"placeholder")

    class Cursor:
        def fetchone(self) -> tuple[str]:
            return ("invalid",)

    class Connection:
        def execute(self, query: str) -> Cursor:
            assert query == "SELECT COUNT(*) FROM rows;"
            return Cursor()

        def close(self) -> None:
            return None

    monkeypatch.setattr(models, "open_sqlite_readonly", lambda _: Connection())

    assert _sqlite_count_rows(database, "SELECT COUNT(*) FROM rows;") == 0


def test_environment_path_prefers_variable_and_uses_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = tmp_path / "configured"
    fallback = tmp_path / "fallback"
    monkeypatch.setenv("FSBACKUP_TEST_PATH", str(configured))

    assert _environment_path("FSBACKUP_TEST_PATH", fallback) == configured

    monkeypatch.delenv("FSBACKUP_TEST_PATH")
    assert _environment_path("FSBACKUP_TEST_PATH", fallback) == fallback


def test_platform_specific_paths_are_empty_outside_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(models, "_current_platform", lambda: "linux")

    assert ChromeBrowser().profile_roots() == ()
    assert ChromeBrowser().executable_candidates() == ()
    assert FirefoxBrowser().profile_roots() == ()
    assert FirefoxBrowser().executable_candidates() == ()


@pytest.mark.parametrize(
    "payload",
    [
        "{invalid",
        json.dumps({"profile": {"info_cache": {"Default": {}}}}),
        json.dumps(
            {
                "profile": {
                    "info_cache": {
                        "Default": {"active_time": "invalid"},
                    }
                }
            }
        ),
    ],
)
def test_chromium_active_time_rejects_invalid_local_state(
    tmp_path: Path,
    payload: str,
) -> None:
    (tmp_path / "Local State").write_text(payload, encoding="utf-8")

    assert _chromium_profile_active_time(tmp_path, "Default") is None


def test_extension_counters_return_zero_when_roots_are_absent(
    tmp_path: Path,
) -> None:
    assert _count_chromium_extensions(tmp_path / "missing-chromium") == 0
    assert _count_firefox_extensions(tmp_path / "missing-firefox") == 0


def test_profile_storage_stats_returns_zero_for_missing_profile(
    tmp_path: Path,
) -> None:
    stats = ControlledChromeBrowser(tmp_path).profile_storage_stats(
        tmp_path / "missing"
    )

    assert stats.size_bytes == 0
    assert stats.latest_mtime is None
