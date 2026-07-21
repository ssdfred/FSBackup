"""Browser discovery orchestration for the Browser Inspector API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
import platform
from pathlib import Path

from .models import (
    BraveBrowser,
    BrowserBase,
    BrowserSnapshot,
    ChromeBrowser,
    EdgeBrowser,
    FirefoxBrowser,
    _load_chromium_bookmarks,
)
from .schemas import Bookmark, BrowserInfo, BrowserProfile, BrowserReport, BrowsersReport


LOGGER = logging.getLogger(__name__)


class BrowserDiscoveryEngine:
    """Collect browser discovery results using browser-specific classes."""

    def __init__(self, browsers: tuple[BrowserBase, ...] | None = None) -> None:
        self._browsers = browsers or (
            ChromeBrowser(),
            EdgeBrowser(),
            FirefoxBrowser(),
            BraveBrowser(),
        )

    def build_report(self) -> BrowserReport:
        """Build the API report payload."""

        LOGGER.debug("Building browser discovery report")
        browser_results = {
            browser.key: self._to_schema(browser.key, browser.discover())
            for browser in self._browsers
        }

        return BrowserReport(
            generated_at=datetime.now(UTC),
            platform=self._platform_name(),
            browsers=BrowsersReport(
                chrome=browser_results["chrome"],
                edge=browser_results["edge"],
                firefox=browser_results["firefox"],
                brave=browser_results["brave"],
            ),
        )

    def _to_schema(self, browser_key: str, snapshot: BrowserSnapshot) -> BrowserInfo:
        profiles = [
            BrowserProfile(
                name=profile.name,
                path=str(profile.path),
                profile_size_bytes=profile.profile_size_bytes,
                profile_size_human=profile.profile_size_human,
                last_used=profile.last_used,
                bookmarks_count=profile.bookmarks_count,
                bookmarks=self._bookmarks_for_profile(browser_key, profile.path),
                extensions_count=profile.extensions_count,
                history_entries=profile.history_entries,
                cookies_count=profile.cookies_count,
            )
            for profile in snapshot.profiles
        ]
        return BrowserInfo(
            installed=snapshot.installed,
            version=snapshot.version,
            profiles=profiles,
        )

    def _bookmarks_for_profile(self, browser_key: str, profile_path: Path) -> list[Bookmark]:
        if browser_key not in {"chrome", "edge", "brave"}:
            return []

        bookmark_records = _load_chromium_bookmarks(
            profile_path / "Bookmarks",
            source=browser_key,
            profile_identifier=str(profile_path),
        )
        return [
            Bookmark(
                id=record.id,
                title=record.title,
                url=record.url,
                folder=record.folder,
                source=record.source,
                date_added=record.date_added,
                date_modified=record.date_modified,
            )
            for record in bookmark_records
        ]

    def _platform_name(self) -> str:
        return platform.system()


ENGINE = BrowserDiscoveryEngine()


def scan() -> BrowserReport:
    """Public entrypoint used by the FastAPI route."""

    return ENGINE.build_report()