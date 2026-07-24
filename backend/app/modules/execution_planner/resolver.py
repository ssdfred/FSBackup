"""Resolve logical backup items into physical source paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileDependency:
    """Definition of one physical dependency."""

    relative_path: str
    mandatory: bool = False
    from_profile_root: bool = True
    potentially_locked: bool = False


CHROMIUM_DEPENDENCIES: dict[str, tuple[FileDependency, ...]] = {
    "bookmarks": (
        FileDependency("Bookmarks", mandatory=True),
        FileDependency("Bookmarks.bak"),
        FileDependency("Favicons", potentially_locked=True),
        FileDependency("Favicons-journal", potentially_locked=True),
    ),
    "passwords": (
        FileDependency(
            "Login Data",
            mandatory=True,
            potentially_locked=True,
        ),
        FileDependency(
            "Login Data-journal",
            potentially_locked=True,
        ),
        FileDependency(
            "Local State",
            mandatory=True,
            from_profile_root=False,
        ),
    ),
    "cookies": (
        FileDependency(
            "Cookies",
            potentially_locked=True,
        ),
        FileDependency(
            "Cookies-journal",
            potentially_locked=True,
        ),
        FileDependency(
            "Network/Cookies",
            mandatory=True,
            potentially_locked=True,
        ),
        FileDependency(
            "Network/Cookies-journal",
            potentially_locked=True,
        ),
        FileDependency(
            "Local State",
            mandatory=True,
            from_profile_root=False,
        ),
    ),
    "autofill": (
        FileDependency(
            "Web Data",
            mandatory=True,
            potentially_locked=True,
        ),
        FileDependency(
            "Web Data-journal",
            potentially_locked=True,
        ),
        FileDependency(
            "Local State",
            from_profile_root=False,
        ),
    ),
    "extensions": (
        FileDependency("Extensions", mandatory=True),
        FileDependency("Extension State"),
        FileDependency("Local Extension Settings"),
        FileDependency("Sync Extension Settings"),
        FileDependency("Preferences"),
        FileDependency("Secure Preferences"),
    ),
    "preferences": (
        FileDependency("Preferences", mandatory=True),
        FileDependency("Secure Preferences"),
        FileDependency(
            "Local State",
            from_profile_root=False,
        ),
    ),
    "sessions": (
        FileDependency("Sessions"),
        FileDependency("Current Session"),
        FileDependency("Current Tabs"),
        FileDependency("Last Session"),
        FileDependency("Last Tabs"),
    ),
    "history": (
        FileDependency(
            "History",
            mandatory=True,
            potentially_locked=True,
        ),
        FileDependency(
            "History-journal",
            potentially_locked=True,
        ),
        FileDependency("Visited Links"),
    ),
    "cache": (
        FileDependency("Cache"),
        FileDependency("Network/Cache"),
    ),
    "code_cache": (
        FileDependency("Code Cache"),
    ),
    "gpu_cache": (
        FileDependency("GPUCache"),
        FileDependency("DawnCache"),
        FileDependency("GrShaderCache"),
        FileDependency("ShaderCache"),
    ),
    "crash_reports": (
        FileDependency("Crashpad"),
    ),
}


FIREFOX_DEPENDENCIES: dict[str, tuple[FileDependency, ...]] = {
    "bookmarks": (
        FileDependency(
            "places.sqlite",
            mandatory=True,
            potentially_locked=True,
        ),
        FileDependency(
            "favicons.sqlite",
            potentially_locked=True,
        ),
        FileDependency("bookmarkbackups"),
    ),
    "passwords": (
        FileDependency("logins.json", mandatory=True),
        FileDependency("key4.db", mandatory=True),
        FileDependency("cert9.db"),
    ),
    "cookies": (
        FileDependency(
            "cookies.sqlite",
            mandatory=True,
            potentially_locked=True,
        ),
    ),
    "autofill": (
        FileDependency(
            "formhistory.sqlite",
            mandatory=True,
            potentially_locked=True,
        ),
    ),
    "extensions": (
        FileDependency("extensions"),
        FileDependency("extensions.json", mandatory=True),
        FileDependency("extension-preferences.json"),
        FileDependency("extension-settings.json"),
    ),
    "preferences": (
        FileDependency("prefs.js", mandatory=True),
        FileDependency("user.js"),
        FileDependency("containers.json"),
        FileDependency(
            "permissions.sqlite",
            potentially_locked=True,
        ),
    ),
    "sessions": (
        FileDependency("sessionstore.jsonlz4"),
        FileDependency("sessionstore-backups"),
    ),
    "history": (
        FileDependency(
            "places.sqlite",
            mandatory=True,
            potentially_locked=True,
        ),
        FileDependency(
            "favicons.sqlite",
            potentially_locked=True,
        ),
    ),
    "cache": (
        FileDependency("cache2"),
        FileDependency("startupCache"),
    ),
    "code_cache": (
        FileDependency("shader-cache"),
    ),
    "gpu_cache": (
        FileDependency("datareporting"),
    ),
    "crash_reports": (
        FileDependency("crashes"),
        FileDependency("minidumps"),
    ),
}


class DependencyResolver:
    """Resolve physical dependencies for supported applications."""

    def resolve(
        self,
        *,
        application_key: str,
        category: str,
        profile_path: str | Path,
    ) -> list[tuple[Path, FileDependency]]:
        """Resolve the configured dependencies for one logical item."""

        profile_root = Path(profile_path)

        if application_key == "firefox":
            dependencies = FIREFOX_DEPENDENCIES.get(category, ())
            browser_root = profile_root
        else:
            dependencies = CHROMIUM_DEPENDENCIES.get(category, ())
            browser_root = profile_root.parent

        resolved: list[tuple[Path, FileDependency]] = []

        for dependency in dependencies:
            base_path = (
                profile_root
                if dependency.from_profile_root
                else browser_root
            )

            candidate = base_path.joinpath(
                *dependency.relative_path.split("/")
            )

            resolved.append((candidate, dependency))

        return resolved