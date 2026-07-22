"""Tests for read-only Chromium bookmark discovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.browser_inspector.models import (
    ChromeBrowser,
    ChromiumBrowserBase,
    EdgeBrowser,
    _count_chromium_bookmarks,
)


def _folder(name: str, children: list[dict[str, object]]) -> dict[str, object]:
    return {"type": "folder", "name": name, "children": children}


def _bookmark(name: str, url: str) -> dict[str, str]:
    return {"type": "url", "name": name, "url": url}


def _write_bookmarks(
    profile_path: Path,
    roots: dict[str, object],
) -> Path:
    profile_path.mkdir(parents=True)
    bookmarks_path = profile_path / "Bookmarks"
    bookmarks_path.write_text(json.dumps({"roots": roots}), encoding="utf-8")
    return bookmarks_path


def test_profile_without_bookmarks_file_returns_zero(tmp_path: Path) -> None:
    assert _count_chromium_bookmarks(tmp_path / "Default" / "Bookmarks") == 0


def test_valid_bookmarks_file_counts_url_entries(tmp_path: Path) -> None:
    bookmarks_path = _write_bookmarks(
        tmp_path / "Default",
        {"bookmark_bar": _folder("Bookmarks bar", [_bookmark("One", "https://one.test")])},
    )

    assert _count_chromium_bookmarks(bookmarks_path) == 1


def test_nested_folders_are_counted_recursively(tmp_path: Path) -> None:
    bookmarks_path = _write_bookmarks(
        tmp_path / "Default",
        {
            "bookmark_bar": _folder(
                "Bookmarks bar",
                [
                    _bookmark("One", "https://one.test"),
                    _folder(
                        "Nested",
                        [
                            _bookmark("Two", "https://two.test"),
                            _folder(
                                "Deep",
                                [_bookmark("Three", "https://three.test")],
                            ),
                        ],
                    ),
                ],
            )
        },
    )

    assert _count_chromium_bookmarks(bookmarks_path) == 3


def test_supported_roots_are_combined_and_missing_roots_are_tolerated(
    tmp_path: Path,
) -> None:
    bookmarks_path = _write_bookmarks(
        tmp_path / "Default",
        {
            "bookmark_bar": _folder("Bookmarks bar", [_bookmark("One", "https://one.test")]),
            "other": _folder("Other bookmarks", [_bookmark("Two", "https://two.test")]),
            "synced": _folder("Mobile bookmarks", [_bookmark("Three", "https://three.test")]),
        },
    )

    assert _count_chromium_bookmarks(bookmarks_path) == 3


@pytest.mark.parametrize("payload", ["{invalid", "\ufeff{\"roots\": {}}"])
def test_invalid_json_or_encoding_returns_zero(tmp_path: Path, payload: str) -> None:
    bookmarks_path = tmp_path / "Bookmarks"
    bookmarks_path.write_text(payload, encoding="utf-8")

    assert _count_chromium_bookmarks(bookmarks_path) == 0


@pytest.mark.parametrize("browser_type", [ChromeBrowser, EdgeBrowser])
def test_bookmarks_can_be_read_while_browser_profile_is_open(
    tmp_path: Path,
    browser_type: type[ChromeBrowser] | type[EdgeBrowser],
) -> None:
    profile_path = tmp_path / "Default"
    bookmarks_path = _write_bookmarks(
        profile_path,
        {"bookmark_bar": _folder("Bookmarks bar", [_bookmark("One", "https://one.test")])},
    )

    with bookmarks_path.open("rb"):
        assert browser_type().bookmarks_count(tmp_path, profile_path, profile_path) == 1


class _TestChromiumBrowser(ChromiumBrowserBase):
    key = "test"
    display_name = "Test Chromium"
    executable_name = "test.exe"
    executable_root_parts = ()
    profile_root_parts = ()

    def __init__(self, profile_root: Path) -> None:
        self._profile_root = profile_root

    def profile_roots(self) -> tuple[Path, ...]:
        return (self._profile_root,)

    def executable_candidates(self) -> tuple[Path, ...]:
        return ()


def test_multiple_chromium_profiles_use_their_own_bookmarks_file(
    tmp_path: Path,
) -> None:
    _write_bookmarks(
        tmp_path / "Default",
        {"bookmark_bar": _folder("Bookmarks bar", [_bookmark("One", "https://one.test")])},
    )
    _write_bookmarks(
        tmp_path / "Profile 1",
        {
            "other": _folder(
                "Other bookmarks",
                [
                    _bookmark("Two", "https://two.test"),
                    _bookmark("Three", "https://three.test"),
                ],
            )
        },
    )

    profiles = _TestChromiumBrowser(tmp_path).get_profiles()

    assert [(profile.name, profile.bookmarks_count) for profile in profiles] == [
        ("Default", 1),
        ("Profile 1", 2),
    ]
