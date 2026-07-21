from datetime import datetime

from pydantic import BaseModel, Field


class Bookmark(BaseModel):
    """Bookmark entry returned by the browser discovery engine."""

    id: str
    title: str
    url: str
    folder: str
    source: str
    date_added: datetime | None = None
    date_modified: datetime | None = None


class BrowserProfile(BaseModel):
    """Profile metadata returned by the browser discovery engine."""

    name: str
    path: str
    profile_size_bytes: int
    profile_size_human: str
    last_used: datetime | None = None
    bookmarks_count: int = 0
    bookmarks: list[Bookmark] = Field(default_factory=list)
    extensions_count: int = 0
    history_entries: int = 0
    cookies_count: int = 0


class BrowserInfo(BaseModel):
    """Discovery result for a single browser."""

    installed: bool
    version: str | None = None
    profiles: list[BrowserProfile] = Field(default_factory=list)


class BrowsersReport(BaseModel):
    """Collection of browser discovery results."""

    chrome: BrowserInfo
    edge: BrowserInfo
    firefox: BrowserInfo
    brave: BrowserInfo


class BrowserReport(BaseModel):
    """Top-level discovery payload returned by the API."""

    generated_at: datetime
    platform: str
    browsers: BrowsersReport