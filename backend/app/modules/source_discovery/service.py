"""Read-only discovery of browser profiles on Windows disks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .schemas import (
    DataAvailability,
    DiscoveredBrowser,
    DiscoveredBrowserProfile,
    DiscoveredUser,
    SourceDiscoveryReport,
    SourceType,
)

SYSTEM_USER_DIRECTORIES = {
    "all users",
    "default",
    "default user",
    "public",
    "defaultaccount",
    "wdagutilityaccount",
    "codexsandboxoffline",
    "defaultapppool",
    "systemprofile",
    "localservice",
    "networkservice",
}

CHROMIUM_PROFILE_NAMES = {
    "default",
    "guest profile",
    "system profile",
}


@dataclass(frozen=True, slots=True)
class BrowserDefinition:
    """Location and metadata for a browser inside a Windows user profile."""

    key: str
    name: str
    profile_root_parts: tuple[str, ...]
    browser_family: str


BROWSER_DEFINITIONS = (
    BrowserDefinition(
        key="chrome",
        name="Google Chrome",
        profile_root_parts=(
            "AppData",
            "Local",
            "Google",
            "Chrome",
            "User Data",
        ),
        browser_family="chromium",
    ),
    BrowserDefinition(
        key="edge",
        name="Microsoft Edge",
        profile_root_parts=(
            "AppData",
            "Local",
            "Microsoft",
            "Edge",
            "User Data",
        ),
        browser_family="chromium",
    ),
    BrowserDefinition(
        key="brave",
        name="Brave",
        profile_root_parts=(
            "AppData",
            "Local",
            "BraveSoftware",
            "Brave-Browser",
            "User Data",
        ),
        browser_family="chromium",
    ),
    BrowserDefinition(
        key="firefox",
        name="Mozilla Firefox",
        profile_root_parts=(
            "AppData",
            "Roaming",
            "Mozilla",
            "Firefox",
            "Profiles",
        ),
        browser_family="firefox",
    ),
)


class SourceDiscoveryError(ValueError):
    """Raised when a source root cannot safely be inspected."""


class SourceDiscoveryService:
    """Discover Windows users and browser profiles without modifying the source."""

    def discover(self, source_root: str | Path) -> SourceDiscoveryReport:
        """Inspect a Windows disk and return discovered browser profiles."""

        root = self._validate_source_root(source_root)
        warnings: list[str] = []

        windows_detected = self._detect_windows_installation(root)
        users_directory = root / "Users"

        if not users_directory.is_dir():
            return SourceDiscoveryReport(
                source_root=str(root),
                source_type=self._detect_source_type(root),
                windows_detected=windows_detected,
                users_directory=None,
                users=[],
                warnings=[
                    f"Le dossier des utilisateurs est introuvable : "
                    f"{users_directory}"
                ],
            )

        users = self._discover_users(
            root=root,
            users_directory=users_directory,
            warnings=warnings,
        )

        return SourceDiscoveryReport(
            source_root=str(root),
            source_type=self._detect_source_type(root),
            windows_detected=windows_detected,
            users_directory=str(users_directory),
            users=users,
            warnings=warnings,
        )

    def _validate_source_root(self, source_root: str | Path) -> Path:
        """Validate and normalize the source root."""

        raw_root = Path(source_root).expanduser()

        if not raw_root.exists():
            raise SourceDiscoveryError(
                f"La source n'existe pas : {raw_root}"
            )

        if not raw_root.is_dir():
            raise SourceDiscoveryError(
                f"La source n'est pas un dossier : {raw_root}"
            )

        try:
            root = raw_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise SourceDiscoveryError(
                f"Impossible de résoudre la source : {raw_root}"
            ) from exc

        if root.parent != root:
            raise SourceDiscoveryError(
                "source_root doit désigner la racine d'un disque, "
                "par exemple E:\\"
            )

        return root

    @staticmethod
    def _detect_windows_installation(root: Path) -> bool:
        """Check for the usual directories of a Windows installation."""

        return (
            (root / "Windows").is_dir()
            and (root / "Users").is_dir()
        )

    @staticmethod
    def _detect_source_type(root: Path) -> SourceType:
        """Distinguish the current Windows disk from another disk."""

        system_drive = os.environ.get("SystemDrive")

        if system_drive:
            current_root = Path(f"{system_drive}\\")

            try:
                if root == current_root.resolve(strict=False):
                    return SourceType.LOCAL_WINDOWS
            except OSError:
                pass

        return SourceType.WINDOWS_DISK

    @staticmethod
    def _should_ignore_user(user_name: str) -> bool:
        """Return whether a directory belongs to a technical Windows account."""

        normalized_name = user_name.strip().casefold()

        if normalized_name in SYSTEM_USER_DIRECTORIES:
            return True

        # IIS application-pool profiles generally use this prefix.
        if normalized_name.startswith("iis apppool"):
            return True

        # Temporary sandbox accounts created by development tools.
        if normalized_name.startswith("codexsandbox"):
            return True

        return False

    def _discover_users(
        self,
        *,
        root: Path,
        users_directory: Path,
        warnings: list[str],
    ) -> list[DiscoveredUser]:
        """Discover non-system Windows users."""

        users: list[DiscoveredUser] = []

        try:
            candidates = sorted(
                users_directory.iterdir(),
                key=lambda path: path.name.casefold(),
            )
        except PermissionError:
            warnings.append(
                f"Accès refusé au dossier : {users_directory}"
            )
            return users
        except OSError as exc:
            warnings.append(
                f"Impossible de lire {users_directory} : {exc}"
            )
            return users

        for user_path in candidates:
            if self._should_ignore_user(user_path.name):
                continue

            try:
                if not user_path.is_dir():
                    continue
            except OSError as exc:
                warnings.append(
                    f"Impossible d'inspecter {user_path} : {exc}"
                )
                continue

            if not self._is_inside_root(root, user_path):
                warnings.append(
                    "Chemin utilisateur ignoré car hors de la source : "
                    f"{user_path}"
                )
                continue

            browsers = self._discover_browsers(
                root=root,
                user_path=user_path,
                warnings=warnings,
            )

            users.append(
                DiscoveredUser(
                    name=user_path.name,
                    path=str(user_path),
                    browsers=browsers,
                )
            )

        return users

    def _discover_browsers(
        self,
        *,
        root: Path,
        user_path: Path,
        warnings: list[str],
    ) -> list[DiscoveredBrowser]:
        """Discover supported browsers for a Windows user."""

        browsers: list[DiscoveredBrowser] = []

        for definition in BROWSER_DEFINITIONS:
            profile_root = user_path.joinpath(
                *definition.profile_root_parts
            )

            if not self._is_inside_root(root, profile_root):
                warnings.append(
                    "Chemin navigateur ignoré car hors de la source : "
                    f"{profile_root}"
                )
                continue

            try:
                if not profile_root.is_dir():
                    continue
            except OSError as exc:
                warnings.append(
                    f"Impossible d'inspecter {profile_root} : {exc}"
                )
                continue

            profiles = self._discover_profiles(
                root=root,
                profile_root=profile_root,
                browser_family=definition.browser_family,
                warnings=warnings,
            )

            browsers.append(
                DiscoveredBrowser(
                    key=definition.key,
                    name=definition.name,
                    profile_root=str(profile_root),
                    profiles=profiles,
                )
            )

        return browsers

    def _discover_profiles(
        self,
        *,
        root: Path,
        profile_root: Path,
        browser_family: str,
        warnings: list[str],
    ) -> list[DiscoveredBrowserProfile]:
        """Discover profiles inside one browser data directory."""

        try:
            candidates = sorted(
                profile_root.iterdir(),
                key=lambda path: path.name.casefold(),
            )
        except PermissionError:
            warnings.append(
                f"Accès refusé au dossier : {profile_root}"
            )
            return []
        except OSError as exc:
            warnings.append(
                f"Impossible de lire {profile_root} : {exc}"
            )
            return []

        profiles: list[DiscoveredBrowserProfile] = []

        for candidate in candidates:
            try:
                if not candidate.is_dir():
                    continue
            except OSError as exc:
                warnings.append(
                    f"Impossible d'inspecter {candidate} : {exc}"
                )
                continue

            if not self._is_inside_root(root, candidate):
                warnings.append(
                    f"Profil ignoré car hors de la source : {candidate}"
                )
                continue

            if browser_family == "chromium":
                if not self._is_chromium_profile(candidate):
                    continue

                data = self._inspect_chromium_profile(candidate)
            else:
                if not self._is_firefox_profile(candidate):
                    continue

                data = self._inspect_firefox_profile(candidate)

            profiles.append(
                DiscoveredBrowserProfile(
                    name=candidate.name,
                    path=str(candidate),
                    data=data,
                )
            )

        return profiles

    @staticmethod
    def _is_chromium_profile(profile_path: Path) -> bool:
        """Determine whether a directory resembles a Chromium profile."""

        name = profile_path.name.casefold()

        if name in CHROMIUM_PROFILE_NAMES:
            return True

        if name.startswith("profile "):
            return True

        profile_markers = (
            "Preferences",
            "Bookmarks",
            "History",
            "Login Data",
        )

        return any(
            (profile_path / marker).exists()
            for marker in profile_markers
        )

    @staticmethod
    def _is_firefox_profile(profile_path: Path) -> bool:
        """Determine whether a directory resembles a Firefox profile."""

        profile_markers = (
            "prefs.js",
            "places.sqlite",
            "cookies.sqlite",
            "logins.json",
        )

        return any(
            (profile_path / marker).exists()
            for marker in profile_markers
        )

    @staticmethod
    def _inspect_chromium_profile(
        profile_path: Path,
    ) -> DataAvailability:
        """Inspect useful Chromium data without opening database contents."""

        cookies_file = profile_path / "Cookies"
        network_cookies_file = profile_path / "Network" / "Cookies"
        login_data_file = profile_path / "Login Data"

        cookies_available = (
            cookies_file.is_file()
            or network_cookies_file.is_file()
        )
        passwords_available = login_data_file.is_file()

        potentially_encrypted: list[str] = []

        if passwords_available:
            potentially_encrypted.append("passwords")

        if cookies_available:
            potentially_encrypted.append("cookies")

        return DataAvailability(
            bookmarks=(profile_path / "Bookmarks").is_file(),
            history=(profile_path / "History").is_file(),
            cookies=cookies_available,
            passwords=passwords_available,
            autofill=(profile_path / "Web Data").is_file(),
            extensions=(profile_path / "Extensions").is_dir(),
            sessions=(
                (profile_path / "Sessions").is_dir()
                or (profile_path / "Current Session").is_file()
                or (profile_path / "Last Session").is_file()
            ),
            preferences=(
                (profile_path / "Preferences").is_file()
                or (profile_path / "Secure Preferences").is_file()
            ),
            potentially_encrypted=potentially_encrypted,
        )

    @staticmethod
    def _inspect_firefox_profile(
        profile_path: Path,
    ) -> DataAvailability:
        """Inspect useful Firefox data without opening database contents."""

        logins_file = profile_path / "logins.json"
        key_database_file = profile_path / "key4.db"
        cookies_file = profile_path / "cookies.sqlite"

        passwords_available = (
            logins_file.is_file()
            or key_database_file.is_file()
        )
        cookies_available = cookies_file.is_file()

        potentially_encrypted: list[str] = []

        if passwords_available:
            potentially_encrypted.append("passwords")

        if cookies_available:
            potentially_encrypted.append("cookies")

        return DataAvailability(
            bookmarks=(profile_path / "places.sqlite").is_file(),
            history=(profile_path / "places.sqlite").is_file(),
            cookies=cookies_available,
            passwords=passwords_available,
            autofill=(profile_path / "formhistory.sqlite").is_file(),
            extensions=(profile_path / "extensions").is_dir(),
            sessions=(
                (profile_path / "sessionstore.jsonlz4").is_file()
                or (profile_path / "sessionstore-backups").is_dir()
            ),
            preferences=(profile_path / "prefs.js").is_file(),
            potentially_encrypted=potentially_encrypted,
        )

    @staticmethod
    def _is_inside_root(root: Path, candidate: Path) -> bool:
        """Ensure a discovered path remains inside the authorized source."""

        try:
            candidate.resolve(strict=False).relative_to(root)
        except (OSError, RuntimeError, ValueError):
            return False

        return True


def discover_source(source_root: str | Path) -> SourceDiscoveryReport:
    """Convenience entry point used by the API."""

    return SourceDiscoveryService().discover(source_root)