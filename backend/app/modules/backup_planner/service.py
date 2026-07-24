"""Build logical backup plans from Windows source discovery reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.modules.source_discovery.schemas import (
    DiscoveredBrowser,
    DiscoveredBrowserProfile,
)
from app.modules.source_discovery.service import SourceDiscoveryService

from .schemas import (
    BackupApplication,
    BackupItem,
    BackupPlan,
    BackupPlanSummary,
    BackupPriority,
    BackupProfile,
    BackupUser,
)


@dataclass(frozen=True, slots=True)
class LogicalItemDefinition:
    """Definition of a logical application backup item."""

    category: str
    title: str
    priority: BackupPriority
    selected: bool
    reason: str
    encrypted: bool = False


BROWSER_ITEM_DEFINITIONS = (
    LogicalItemDefinition(
        category="bookmarks",
        title="Favoris",
        priority=BackupPriority.CRITICAL,
        selected=True,
        reason="Données personnelles importantes.",
    ),
    LogicalItemDefinition(
        category="passwords",
        title="Mots de passe",
        priority=BackupPriority.CRITICAL,
        selected=True,
        reason="Données d'authentification importantes.",
        encrypted=True,
    ),
    LogicalItemDefinition(
        category="cookies",
        title="Cookies",
        priority=BackupPriority.IMPORTANT,
        selected=True,
        reason="Peut préserver certaines connexions et préférences de sites.",
        encrypted=True,
    ),
    LogicalItemDefinition(
        category="autofill",
        title="Données de saisie automatique",
        priority=BackupPriority.IMPORTANT,
        selected=True,
        reason="Contient les formulaires et données de saisie enregistrées.",
    ),
    LogicalItemDefinition(
        category="extensions",
        title="Extensions",
        priority=BackupPriority.IMPORTANT,
        selected=True,
        reason="Permet d'identifier et de restaurer les extensions installées.",
    ),
    LogicalItemDefinition(
        category="preferences",
        title="Préférences",
        priority=BackupPriority.IMPORTANT,
        selected=True,
        reason="Contient la configuration du profil.",
    ),
    LogicalItemDefinition(
        category="sessions",
        title="Sessions",
        priority=BackupPriority.OPTIONAL,
        selected=True,
        reason="Peut permettre de retrouver les fenêtres et onglets ouverts.",
    ),
    LogicalItemDefinition(
        category="history",
        title="Historique",
        priority=BackupPriority.OPTIONAL,
        selected=True,
        reason="Historique de navigation du profil.",
    ),
)


TEMPORARY_ITEM_DEFINITIONS = (
    LogicalItemDefinition(
        category="cache",
        title="Cache",
        priority=BackupPriority.IGNORE,
        selected=False,
        reason="Données temporaires recréées automatiquement.",
    ),
    LogicalItemDefinition(
        category="code_cache",
        title="Cache du code",
        priority=BackupPriority.IGNORE,
        selected=False,
        reason="Fichiers temporaires d'optimisation du navigateur.",
    ),
    LogicalItemDefinition(
        category="gpu_cache",
        title="Cache graphique",
        priority=BackupPriority.IGNORE,
        selected=False,
        reason="Données graphiques temporaires recréées automatiquement.",
    ),
    LogicalItemDefinition(
        category="crash_reports",
        title="Rapports de plantage",
        priority=BackupPriority.IGNORE,
        selected=False,
        reason="Rapports techniques non nécessaires à la restauration.",
    ),
)


CATEGORY_PATHS: dict[str, dict[str, tuple[str, ...]]] = {
    "chromium": {
        "bookmarks": (
            "Bookmarks",
            "Bookmarks.bak",
            "Favicons",
            "Favicons-journal",
        ),
        "passwords": (
            "Login Data",
            "Login Data-journal",
        ),
        "cookies": (
            "Cookies",
            "Cookies-journal",
            "Network/Cookies",
            "Network/Cookies-journal",
        ),
        "autofill": (
            "Web Data",
            "Web Data-journal",
        ),
        "extensions": (
            "Extensions",
            "Extension State",
            "Local Extension Settings",
            "Sync Extension Settings",
        ),
        "preferences": (
            "Preferences",
            "Secure Preferences",
        ),
        "sessions": (
            "Sessions",
            "Current Session",
            "Current Tabs",
            "Last Session",
            "Last Tabs",
        ),
        "history": (
            "History",
            "History-journal",
            "Visited Links",
        ),
        "cache": (
            "Cache",
            "Network/Cache",
        ),
        "code_cache": (
            "Code Cache",
        ),
        "gpu_cache": (
            "GPUCache",
            "DawnCache",
            "GrShaderCache",
            "ShaderCache",
        ),
        "crash_reports": (
            "Crashpad",
        ),
    },
    "firefox": {
        "bookmarks": (
            "places.sqlite",
            "bookmarkbackups",
            "favicons.sqlite",
        ),
        "passwords": (
            "logins.json",
            "key4.db",
        ),
        "cookies": (
            "cookies.sqlite",
        ),
        "autofill": (
            "formhistory.sqlite",
        ),
        "extensions": (
            "extensions",
            "extensions.json",
            "extension-preferences.json",
        ),
        "preferences": (
            "prefs.js",
            "user.js",
        ),
        "sessions": (
            "sessionstore.jsonlz4",
            "sessionstore-backups",
        ),
        "history": (
            "places.sqlite",
        ),
        "cache": (
            "cache2",
            "startupCache",
        ),
        "code_cache": (
            "shader-cache",
        ),
        "gpu_cache": (
            "datareporting",
        ),
        "crash_reports": (
            "crashes",
            "minidumps",
        ),
    },
}


class BackupPlannerService:
    """Generate an explainable logical backup plan."""

    def __init__(
        self,
        discovery_service: SourceDiscoveryService | None = None,
    ) -> None:
        self.discovery_service = (
            discovery_service or SourceDiscoveryService()
        )

    def build_plan(self, source_root: str | Path) -> BackupPlan:
        """Discover a source and transform it into a backup plan."""

        discovery = self.discovery_service.discover(source_root)

        users: list[BackupUser] = []

        for discovered_user in discovery.users:
            applications = [
                self._build_application(browser)
                for browser in discovered_user.browsers
                if browser.profiles
            ]

            users.append(
                BackupUser(
                    name=discovered_user.name,
                    source_path=discovered_user.path,
                    applications=applications,
                )
            )

        summary = self._build_summary(users)

        return BackupPlan(
            source_root=discovery.source_root,
            source_type=discovery.source_type,
            windows_detected=discovery.windows_detected,
            users=users,
            summary=summary,
            warnings=discovery.warnings,
        )

    def _build_application(
        self,
        browser: DiscoveredBrowser,
    ) -> BackupApplication:
        """Build the plan for one browser."""

        profiles = [
            self._build_profile(browser, profile)
            for profile in browser.profiles
        ]

        return BackupApplication(
            key=browser.key,
            name=browser.name,
            profiles=profiles,
        )

    def _build_profile(
        self,
        browser: DiscoveredBrowser,
        profile: DiscoveredBrowserProfile,
    ) -> BackupProfile:
        """Build logical items for one browser profile."""

        browser_family = self._browser_family(browser.key)
        profile_path = Path(profile.path)
        items: list[BackupItem] = []

        for definition in BROWSER_ITEM_DEFINITIONS:
            if not getattr(profile.data, definition.category, False):
                continue

            size, file_count = self._estimate_item(
                profile_path=profile_path,
                browser_family=browser_family,
                category=definition.category,
            )

            encrypted = (
                definition.encrypted
                or definition.category
                in profile.data.potentially_encrypted
            )

            items.append(
                self._create_item(
                    browser_key=browser.key,
                    profile_name=profile.name,
                    definition=definition,
                    estimated_size_bytes=size,
                    estimated_files=file_count,
                    encrypted=encrypted,
                )
            )

        for definition in TEMPORARY_ITEM_DEFINITIONS:
            size, file_count = self._estimate_item(
                profile_path=profile_path,
                browser_family=browser_family,
                category=definition.category,
            )

            if file_count == 0:
                continue

            items.append(
                self._create_item(
                    browser_key=browser.key,
                    profile_name=profile.name,
                    definition=definition,
                    estimated_size_bytes=size,
                    estimated_files=file_count,
                    encrypted=False,
                )
            )

        return BackupProfile(
            name=profile.name,
            source_path=profile.path,
            items=items,
        )

    @staticmethod
    def _create_item(
        *,
        browser_key: str,
        profile_name: str,
        definition: LogicalItemDefinition,
        estimated_size_bytes: int,
        estimated_files: int,
        encrypted: bool,
    ) -> BackupItem:
        """Create one stable logical backup item."""

        normalized_profile = (
            profile_name.strip()
            .casefold()
            .replace(" ", "-")
            .replace(".", "-")
        )

        return BackupItem(
            id=(
                f"{browser_key}.{normalized_profile}."
                f"{definition.category}"
            ),
            category=definition.category,
            title=definition.title,
            selected=definition.selected,
            priority=definition.priority,
            reason=definition.reason,
            encrypted=encrypted,
            estimated_size_bytes=estimated_size_bytes,
            estimated_files=estimated_files,
        )

    @staticmethod
    def _browser_family(browser_key: str) -> str:
        """Return the storage family used by a browser."""

        if browser_key == "firefox":
            return "firefox"

        return "chromium"

    def _estimate_item(
        self,
        *,
        profile_path: Path,
        browser_family: str,
        category: str,
    ) -> tuple[int, int]:
        """Estimate the size and number of files for a logical item."""

        relative_paths = CATEGORY_PATHS.get(
            browser_family,
            {},
        ).get(category, ())

        total_size = 0
        file_count = 0
        visited_files: set[Path] = set()

        for relative_path in relative_paths:
            candidate = profile_path.joinpath(
                *relative_path.split("/")
            )

            size, count = self._measure_path(
                candidate,
                visited_files,
            )
            total_size += size
            file_count += count

        return total_size, file_count

    def _measure_path(
        self,
        path: Path,
        visited_files: set[Path],
    ) -> tuple[int, int]:
        """Measure a file or directory without modifying it."""

        try:
            if path.is_file():
                resolved = path.resolve(strict=False)

                if resolved in visited_files:
                    return 0, 0

                visited_files.add(resolved)

                try:
                    return path.stat().st_size, 1
                except OSError:
                    return 0, 1

            if not path.is_dir():
                return 0, 0
        except OSError:
            return 0, 0

        total_size = 0
        file_count = 0

        try:
            candidates = path.rglob("*")
        except OSError:
            return 0, 0

        for candidate in candidates:
            try:
                if not candidate.is_file():
                    continue

                resolved = candidate.resolve(strict=False)

                if resolved in visited_files:
                    continue

                visited_files.add(resolved)
                file_count += 1

                try:
                    total_size += candidate.stat().st_size
                except OSError:
                    continue
            except OSError:
                continue

        return total_size, file_count

    @staticmethod
    def _build_summary(
        users: list[BackupUser],
    ) -> BackupPlanSummary:
        """Calculate aggregate plan statistics."""

        applications = 0
        profiles = 0
        items = 0
        selected_items = 0
        excluded_items = 0
        encrypted_items = 0
        estimated_size_bytes = 0
        estimated_files = 0

        for user in users:
            applications += len(user.applications)

            for application in user.applications:
                profiles += len(application.profiles)

                for profile in application.profiles:
                    items += len(profile.items)

                    for item in profile.items:
                        if item.selected:
                            selected_items += 1
                            estimated_size_bytes += (
                                item.estimated_size_bytes
                            )
                            estimated_files += item.estimated_files
                        else:
                            excluded_items += 1

                        if item.encrypted:
                            encrypted_items += 1

        return BackupPlanSummary(
            users=len(users),
            applications=applications,
            profiles=profiles,
            items=items,
            selected_items=selected_items,
            excluded_items=excluded_items,
            encrypted_items=encrypted_items,
            estimated_size_bytes=estimated_size_bytes,
            estimated_files=estimated_files,
        )


def build_backup_plan(source_root: str | Path) -> BackupPlan:
    """Convenience entry point used by the API."""

    return BackupPlannerService().build_plan(source_root)