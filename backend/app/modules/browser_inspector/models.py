from __future__ import annotations

import hashlib
import ctypes
import json
import logging
import os
import platform
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar, Iterable


LOGGER = logging.getLogger(__name__)
WINDOWS = "windows"
IGNORED_SIZE_DIRECTORIES = frozenset(
    {
        "Cache",
        "Code Cache",
        "GPUCache",
        "ShaderCache",
        "Crashpad",
        "GrShaderCache",
        "DawnCache",
    },
)


@dataclass(frozen=True, slots=True)
class BrowserProfileRecord:
    """File-system representation of a browser profile."""

    name: str
    path: Path
    profile_size_bytes: int
    profile_size_human: str
    last_used: datetime | None
    bookmarks_count: int
    extensions_count: int
    history_entries: int
    cookies_count: int


@dataclass(frozen=True, slots=True)
class BookmarkRecord:
    """Internal representation of a Chromium bookmark."""

    id: str
    title: str
    url: str
    folder: str
    source: str
    date_added: datetime | None
    date_modified: datetime | None


@dataclass(frozen=True, slots=True)
class ProfileStorageStats:
    """Aggregate storage statistics for a profile directory."""

    size_bytes: int
    latest_mtime: datetime | None


@dataclass(frozen=True, slots=True)
class BrowserSnapshot:
    """Low-level discovery result for a browser."""

    installed: bool
    version: str | None
    profiles: tuple[BrowserProfileRecord, ...]


class BrowserBase(ABC):
    """Abstract browser discovery contract."""

    key: ClassVar[str]
    display_name: ClassVar[str]

    @abstractmethod
    def profile_roots(self) -> tuple[Path, ...]:
        """Return root directories that may contain browser profiles."""

    @abstractmethod
    def executable_candidates(self) -> tuple[Path, ...]:
        """Return executable candidates used to determine installation state."""

    def discover(self) -> BrowserSnapshot:
        """Collect the discovery snapshot for the browser."""

        executable = self.find_executable()
        profiles = tuple(self.get_profiles())
        installed = executable is not None or bool(profiles)
        version = self.get_version(executable)

        LOGGER.debug("Discovered browser %s: installed=%s", self.key, installed)
        return BrowserSnapshot(
            installed=installed,
            version=version,
            profiles=profiles,
        )

    def find_executable(self) -> Path | None:
        """Return the first executable candidate that exists."""

        for candidate in self.executable_candidates():
            if candidate.exists():
                return candidate
        return None

    def get_version(self, executable: Path | None = None) -> str | None:
        """Read the installed version, if it can be resolved safely."""

        resolved_executable = executable or self.find_executable()
        if resolved_executable is None:
            return None

        if _current_platform() == WINDOWS:
            return _read_windows_file_version(resolved_executable)

        return None

    def get_profiles(self) -> list[BrowserProfileRecord]:
        """Enumerate browser profiles from all known roots."""

        profiles: list[BrowserProfileRecord] = []
        for root in self.profile_roots():
            if not root.exists():
                continue

            for entry in self.iter_profile_entries(root):
                if not entry.is_dir():
                    continue
                if not self.should_keep_profile(entry.name):
                    continue
                profiles.append(self.build_profile_record(root, entry))

        profiles.sort(key=lambda profile: (profile.name.lower(), str(profile.path).lower()))
        return profiles

    def iter_profile_entries(self, root: Path) -> Iterable[Path]:
        """Return candidate profile directories for a root."""

        return root.iterdir()

    def should_keep_profile(self, profile_name: str) -> bool:
        """Decide whether a directory is a meaningful profile."""

        return True

    def profile_name(self, profile_entry: Path) -> str:
        """Return the public profile name."""

        return profile_entry.name

    def profile_path(self, root: Path, profile_entry: Path) -> Path:
        """Return the public profile path."""

        return profile_entry

    def build_profile_record(self, root: Path, profile_entry: Path) -> BrowserProfileRecord:
        """Create the public record for one profile."""

        profile_path = self.profile_path(root, profile_entry)
        storage_stats = self.profile_storage_stats(profile_path)
        last_used = self.profile_last_used(root, profile_entry, profile_path, storage_stats)

        return BrowserProfileRecord(
            name=self.profile_name(profile_entry),
            path=profile_path,
            profile_size_bytes=storage_stats.size_bytes,
            profile_size_human=self.profile_size_human(storage_stats.size_bytes),
            last_used=last_used,
            bookmarks_count=self.bookmarks_count(root, profile_entry, profile_path),
            extensions_count=self.extensions_count(root, profile_entry, profile_path),
            history_entries=self.history_entries(root, profile_entry, profile_path),
            cookies_count=self.cookies_count(root, profile_entry, profile_path),
        )

    def profile_storage_stats(self, profile_path: Path) -> ProfileStorageStats:
        """Compute size and latest modification time for a profile."""

        size_bytes = 0
        latest_timestamp: float | None = None

        if profile_path.exists():
            latest_timestamp = profile_path.stat().st_mtime

        for file_path in self._iter_profile_files(profile_path):
            try:
                file_stat = file_path.stat()
            except OSError:
                continue

            size_bytes += file_stat.st_size
            if latest_timestamp is None or file_stat.st_mtime > latest_timestamp:
                latest_timestamp = file_stat.st_mtime

        return ProfileStorageStats(
            size_bytes=size_bytes,
            latest_mtime=_timestamp_to_datetime(latest_timestamp),
        )

    def profile_last_used(
        self,
        root: Path,
        profile_entry: Path,
        profile_path: Path,
        storage_stats: ProfileStorageStats,
    ) -> datetime | None:
        """Return the last activity timestamp for a profile."""

        latest_timestamp = storage_stats.latest_mtime
        for candidate in self.last_used_candidates(root, profile_entry, profile_path):
            if candidate is not None and (latest_timestamp is None or candidate > latest_timestamp):
                latest_timestamp = candidate
        return latest_timestamp

    def last_used_candidates(
        self,
        root: Path,
        profile_entry: Path,
        profile_path: Path,
    ) -> Iterable[datetime | None]:
        """Browser-specific timestamp candidates for last usage."""

        return ()

    def bookmarks_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        """Count bookmarks available in the profile."""

        return 0

    def extensions_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        """Count browser extensions available in the profile."""

        return 0

    def history_entries(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        """Count entries in the browser history database."""

        return 0

    def cookies_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        """Count cookies available in the profile."""

        return 0

    def profile_size_human(self, size_bytes: int) -> str:
        """Render a human-readable profile size."""

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} B"
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size_bytes} B"

    def _iter_profile_files(self, profile_path: Path) -> Iterable[Path]:
        """Yield profile files while skipping cache directories."""

        if not profile_path.exists():
            return ()

        def generator() -> Iterable[Path]:
            for root, directories, files in os.walk(profile_path, topdown=True):
                directories[:] = [
                    directory
                    for directory in directories
                    if directory not in self.profile_size_ignored_directories()
                ]
                root_path = Path(root)
                for file_name in files:
                    yield root_path / file_name

        return generator()

    def profile_size_ignored_directories(self) -> frozenset[str]:
        """Return directories that should be excluded from size calculation."""

        return IGNORED_SIZE_DIRECTORIES


class ChromiumBrowserBase(BrowserBase):
    """Shared logic for Chromium-based browsers."""

    excluded_profiles: ClassVar[frozenset[str]] = frozenset({"System Profile", "Guest Profile"})
    executable_name: ClassVar[str]
    executable_root_parts: ClassVar[tuple[str, ...]]
    profile_root_parts: ClassVar[tuple[str, ...]]

    def executable_candidates(self) -> tuple[Path, ...]:
        if _current_platform() != WINDOWS:
            return tuple()

        return _windows_executable_candidates(
            executable_name=self.executable_name,
            executable_root_parts=self.executable_root_parts,
        )

    def profile_roots(self) -> tuple[Path, ...]:
        if _current_platform() != WINDOWS:
            return tuple()

        return (_local_app_data_path(*self.profile_root_parts),)

    def should_keep_profile(self, profile_name: str) -> bool:
        return profile_name not in self.excluded_profiles and (
            profile_name == "Default" or profile_name.startswith("Profile ")
        )

    def last_used_candidates(
        self,
        root: Path,
        profile_entry: Path,
        profile_path: Path,
    ) -> Iterable[datetime | None]:
        yield _chromium_profile_active_time(root, profile_entry.name)

    def bookmarks_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        bookmarks_file = profile_path / "Bookmarks"
        return _count_chromium_bookmarks(bookmarks_file)

    def extensions_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        extensions_root = profile_path / "Extensions"
        return _count_chromium_extensions(extensions_root)

    def history_entries(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        return _sqlite_count_rows(profile_path / "History", "SELECT COUNT(*) FROM urls;")

    def cookies_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        for candidate in (
            profile_path / "Network" / "Cookies",
            profile_path / "Cookies",
        ):
            if candidate.exists():
                return _sqlite_count_rows(candidate, "SELECT COUNT(*) FROM cookies;")

        LOGGER.debug("Cookies absent for profile %s", profile_path)
        return 0


class ChromeBrowser(ChromiumBrowserBase):
    """Google Chrome discovery."""

    key = "chrome"
    display_name = "Google Chrome"
    executable_name = "chrome.exe"
    executable_root_parts = ("Google", "Chrome", "Application")
    profile_root_parts = ("Google", "Chrome", "User Data")


class EdgeBrowser(ChromiumBrowserBase):
    """Microsoft Edge discovery."""

    key = "edge"
    display_name = "Microsoft Edge"
    executable_name = "msedge.exe"
    executable_root_parts = ("Microsoft", "Edge", "Application")
    profile_root_parts = ("Microsoft", "Edge", "User Data")


class BraveBrowser(ChromiumBrowserBase):
    """Brave browser discovery."""

    key = "brave"
    display_name = "Brave"
    executable_name = "brave.exe"
    executable_root_parts = ("BraveSoftware", "Brave-Browser", "Application")
    profile_root_parts = ("BraveSoftware", "Brave-Browser", "User Data")


class FirefoxBrowser(BrowserBase):
    """Mozilla Firefox discovery."""

    key = "firefox"
    display_name = "Mozilla Firefox"

    def executable_candidates(self) -> tuple[Path, ...]:
        if _current_platform() != WINDOWS:
            return tuple()

        return _windows_executable_candidates(
            executable_name="firefox.exe",
            executable_root_parts=("Mozilla Firefox",),
        )

    def profile_roots(self) -> tuple[Path, ...]:
        if _current_platform() != WINDOWS:
            return tuple()

        return (_roaming_app_data_path("Mozilla", "Firefox", "Profiles"),)

    def last_used_candidates(
        self,
        root: Path,
        profile_entry: Path,
        profile_path: Path,
    ) -> Iterable[datetime | None]:
        for candidate in (
            profile_path / "prefs.js",
            profile_path / "places.sqlite",
            profile_path / "cookies.sqlite",
            profile_path / "extensions.json",
        ):
            yield _path_mtime(candidate)

    def bookmarks_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        return _sqlite_count_rows(
            profile_path / "places.sqlite",
            "SELECT COUNT(*) FROM moz_bookmarks WHERE type = 1 AND fk IS NOT NULL;",
        )

    def extensions_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        extensions_root = profile_path / "extensions"
        return _count_firefox_extensions(extensions_root)

    def history_entries(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        return _sqlite_count_rows(
            profile_path / "places.sqlite",
            "SELECT COUNT(*) FROM moz_historyvisits;",
        )

    def cookies_count(self, root: Path, profile_entry: Path, profile_path: Path) -> int:
        return _sqlite_count_rows(profile_path / "cookies.sqlite", "SELECT COUNT(*) FROM moz_cookies;")


def _current_platform() -> str:
    return platform.system().lower()


def _environment_path(variable_name: str, fallback: Path) -> Path:
    value = os.environ.get(variable_name)
    return Path(value) if value else fallback


def _home_path() -> Path:
    return Path.home()


def _local_app_data_path(*parts: str) -> Path:
    base = _environment_path(
        "LOCALAPPDATA",
        _home_path() / "AppData" / "Local",
    )
    return base.joinpath(*parts)


def _roaming_app_data_path(*parts: str) -> Path:
    base = _environment_path(
        "APPDATA",
        _home_path() / "AppData" / "Roaming",
    )
    return base.joinpath(*parts)


def _program_files_path(variable_name: str, fallback: Path) -> Path:
    return _environment_path(variable_name, fallback)


def _windows_executable_candidates(
    *,
    executable_name: str,
    executable_root_parts: tuple[str, ...],
) -> tuple[Path, ...]:
    program_files = _program_files_path("PROGRAMFILES", Path(r"C:\Program Files"))
    program_files_x86 = _program_files_path(
        "PROGRAMFILES(X86)",
        Path(r"C:\Program Files (x86)"),
    )
    return (
        program_files.joinpath(*executable_root_parts, executable_name),
        program_files_x86.joinpath(*executable_root_parts, executable_name),
    )


def _timestamp_to_datetime(timestamp: float | None) -> datetime | None:
    if timestamp is None:
        return None

    normalized_timestamp = timestamp / 1000.0 if timestamp > 10_000_000_000 else timestamp
    try:
        return datetime.fromtimestamp(normalized_timestamp, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _path_mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return None


def _read_windows_file_version(path: Path) -> str | None:
    """Read the file version from Windows metadata without launching the browser."""

    try:
        from ctypes import wintypes

        version_dll = ctypes.windll.version
        version_size = version_dll.GetFileVersionInfoSizeW(str(path), None)
        if not version_size:
            return None

        version_buffer = ctypes.create_string_buffer(version_size)
        if not version_dll.GetFileVersionInfoW(str(path), 0, version_size, version_buffer):
            return None

        value_pointer = ctypes.c_void_p()
        value_length = wintypes.UINT()
        if not version_dll.VerQueryValueW(
            version_buffer,
            "\\",
            ctypes.byref(value_pointer),
            ctypes.byref(value_length),
        ):
            return None

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD),
                ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD),
                ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD),
                ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD),
                ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]

        file_info = ctypes.cast(
            value_pointer.value,
            ctypes.POINTER(VS_FIXEDFILEINFO),
        ).contents
        major = file_info.dwFileVersionMS >> 16
        minor = file_info.dwFileVersionMS & 0xFFFF
        build = file_info.dwFileVersionLS >> 16
        revision = file_info.dwFileVersionLS & 0xFFFF
        return f"{major}.{minor}.{build}.{revision}"
    except Exception:
        return None


def open_sqlite_readonly(path: Path) -> sqlite3.Connection:
    """Open a SQLite database in read-only mode."""

    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro",
        uri=True,
        timeout=0.5,
    )
    connection.execute("PRAGMA query_only = ON;")
    return connection


def _sqlite_count_rows(database_path: Path, query: str) -> int:
    if not database_path.exists():
        return 0

    connection: sqlite3.Connection | None = None
    try:
        connection = open_sqlite_readonly(database_path)
        row = connection.execute(query).fetchone()
    except (PermissionError, OSError) as exc:
        LOGGER.warning("Unable to open SQLite database %s: %s", database_path, exc)
        return 0
    except sqlite3.OperationalError as exc:
        message = str(exc).lower()
        if "locked" in message or "busy" in message:
            LOGGER.debug("SQLite database is locked: %s", database_path)
        elif "unable to open database" in message or "unable to open" in message:
            LOGGER.warning("Unable to open SQLite database %s: %s", database_path, exc)
        elif "malformed" in message or "corrupt" in message or "not a database" in message:
            LOGGER.warning("SQLite database is corrupt: %s", database_path)
        else:
            LOGGER.warning("Unexpected SQLite error for %s: %s", database_path, exc)
        return 0
    except sqlite3.DatabaseError as exc:
        message = str(exc).lower()
        if "malformed" in message or "corrupt" in message or "not a database" in message:
            LOGGER.warning("SQLite database is corrupt: %s", database_path)
        else:
            LOGGER.warning("Unexpected SQLite error for %s: %s", database_path, exc)
        return 0
    except sqlite3.Error as exc:
        LOGGER.warning("Unexpected SQLite error for %s: %s", database_path, exc)
        return 0
    finally:
        if connection is not None:
            connection.close()

    if not row:
        return 0

    try:
        return int(row[0] or 0)
    except (TypeError, ValueError):
        LOGGER.warning("Unexpected SQLite row format for %s", database_path)
        return 0

    return 0


def _count_chromium_bookmarks(bookmarks_path: Path) -> int:
    return len(_load_chromium_bookmarks(bookmarks_path, source="chromium", profile_identifier=str(bookmarks_path.parent)))


def _load_chromium_bookmarks(
    bookmarks_path: Path,
    *,
    source: str,
    profile_identifier: str,
) -> tuple[BookmarkRecord, ...]:
    if not bookmarks_path.exists():
        LOGGER.debug("Bookmarks absent for profile file %s", bookmarks_path)
        return ()

    try:
        data = json.loads(bookmarks_path.read_text(encoding="utf-8"))
    except OSError as exc:
        LOGGER.warning("Unable to read Chromium bookmarks %s: %s", bookmarks_path, exc)
        return ()
    except json.JSONDecodeError as exc:
        LOGGER.debug("Invalid Chromium bookmarks JSON in %s: %s", bookmarks_path, exc)
        return ()

    if not isinstance(data, dict):
        LOGGER.debug("Unexpected Chromium bookmarks structure in %s", bookmarks_path)
        return ()

    roots = data.get("roots")
    if not isinstance(roots, dict):
        LOGGER.debug("Unexpected Chromium bookmarks structure in %s", bookmarks_path)
        return ()

    bookmarks: list[BookmarkRecord] = []

    def visit(node: object, folder_parts: tuple[str, ...]) -> None:
        if not isinstance(node, dict):
            return

        node_type = node.get("type")
        if node_type == "url":
            title = str(node.get("name") or node.get("title") or "")
            url = str(node.get("url") or "")
            folder = "/".join(folder_parts)
            bookmark_id = hashlib.sha1(
                f"{profile_identifier}|{url}|{title}".encode("utf-8")
            ).hexdigest()
            bookmarks.append(
                BookmarkRecord(
                    id=bookmark_id,
                    title=title,
                    url=url,
                    folder=folder,
                    source=source,
                    date_added=_chromium_webkit_timestamp_to_datetime(node.get("date_added")),
                    date_modified=_chromium_webkit_timestamp_to_datetime(node.get("date_modified")),
                )
            )
            return

        children = node.get("children")
        if isinstance(children, list):
            next_folder_parts = folder_parts
            folder_name = str(node.get("name") or node.get("title") or "").strip()
            if folder_name:
                next_folder_parts = folder_parts + (folder_name,)
            for child in children:
                visit(child, next_folder_parts)

    for root_name, root_node in roots.items():
        if root_name == "managed_bookmarks":
            continue
        visit(root_node, tuple())

    return tuple(bookmarks)


def _chromium_webkit_timestamp_to_datetime(timestamp: object) -> datetime | None:
    if timestamp in (None, "", 0, "0"):
        return None

    try:
        microseconds = int(str(timestamp))
    except (TypeError, ValueError):
        return None

    if microseconds <= 0:
        return None

    try:
        return datetime(1601, 1, 1, tzinfo=UTC) + timedelta(microseconds=microseconds)
    except (OverflowError, OSError, ValueError):
        return None


def _count_chromium_extensions(extensions_root: Path) -> int:
    if not extensions_root.exists():
        return 0

    count = 0
    try:
        for extension_folder in extensions_root.iterdir():
            if not extension_folder.is_dir():
                continue
            if any(child.is_dir() for child in extension_folder.iterdir()):
                count += 1
    except OSError:
        return 0
    return count


def _count_firefox_extensions(extensions_root: Path) -> int:
    if not extensions_root.exists():
        return 0

    count = 0
    try:
        for entry in extensions_root.iterdir():
            if entry.is_dir() or entry.suffix.lower() == ".xpi":
                count += 1
    except OSError:
        return 0
    return count


def _chromium_profile_active_time(root: Path, profile_name: str) -> datetime | None:
    local_state_path = root / "Local State"
    if not local_state_path.exists():
        return None

    try:
        data = json.loads(local_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    active_time = (
        data.get("profile", {})
        .get("info_cache", {})
        .get(profile_name, {})
        .get("active_time")
    )
    if active_time is None:
        return None

    try:
        return _timestamp_to_datetime(float(active_time))
    except (TypeError, ValueError):
        return None
