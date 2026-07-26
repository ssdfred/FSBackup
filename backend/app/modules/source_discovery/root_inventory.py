"""Conservative read-only inventory of a selected Windows volume root."""

from __future__ import annotations

from pathlib import Path

from .diagnostic import PERSONAL_FOLDER_ALIASES, _resolve_personal_folder, _safe_directory_estimate
from .root_inventory_schemas import (
    OldWindowsProfile,
    RootEntryCategory,
    RootInventoryEntry,
    RootInventoryReport,
)
from .service import SourceDiscoveryService

SYSTEM_ROOTS = {
    "$recycle.bin",
    "$getcurrent",
    "$sysreset",
    "$windows.~bt",
    "$windows.~ws",
    "boot",
    "documents and settings",
    "msocache",
    "onedrivetemp",
    "perflogs",
    "program files",
    "program files (x86)",
    "programdata",
    "programmes",
    "programmes (x86)",
    "recovery",
    "system volume information",
    "temp",
    "users",
    "utilisateurs",
    "windows",
}

PERSONAL_ROOTS = {
    "documents",
    "downloads",
    "téléchargements",
    "desktop",
    "bureau",
    "pictures",
    "images",
    "music",
    "musique",
    "videos",
    "vidéos",
}


def _classify(name: str) -> tuple[RootEntryCategory, str]:
    normalized = name.casefold()
    if normalized == "windows.old":
        return (
            RootEntryCategory.OLD_WINDOWS,
            "Ancienne installation Windows à analyser séparément avant toute récupération.",
        )
    if normalized in SYSTEM_ROOTS:
        return (
            RootEntryCategory.SYSTEM,
            "Élément système ou technique non inclus automatiquement dans une sauvegarde de données.",
        )
    if normalized in PERSONAL_ROOTS:
        return (
            RootEntryCategory.PERSONAL,
            "Dossier personnel visible directement à la racine du lecteur.",
        )
    return (
        RootEntryCategory.REVIEW,
        "Dossier applicatif, projet ou donnée personnalisée à examiner manuellement.",
    )


def _old_windows_profiles(old_windows: Path) -> tuple[list[OldWindowsProfile], list[str]]:
    profiles: list[OldWindowsProfile] = []
    warnings: list[str] = []
    users_root = old_windows / "Users"
    if not users_root.is_dir():
        users_root = old_windows / "Utilisateurs"
    try:
        candidates = sorted(users_root.iterdir(), key=lambda item: item.name.casefold())
    except OSError as exc:
        return profiles, [f"Impossible de lire les profils de {old_windows} : {exc}"]

    for profile in candidates:
        try:
            if not profile.is_dir() or SourceDiscoveryService._should_ignore_user(profile.name):
                continue
        except OSError as exc:
            warnings.append(f"Impossible d'inspecter {profile} : {exc}")
            continue
        size_bytes = 0
        file_count = 0
        for _display_name, aliases in PERSONAL_FOLDER_ALIASES:
            folder = _resolve_personal_folder(profile, aliases)
            try:
                if not folder.is_dir():
                    continue
            except OSError:
                continue
            size, files, local_warnings = _safe_directory_estimate(folder)
            size_bytes += size
            file_count += files
            warnings.extend(local_warnings)
        profiles.append(
            OldWindowsProfile(
                name=profile.name,
                path=str(profile),
                personal_size_bytes=size_bytes,
                personal_file_count=file_count,
            )
        )
    return profiles, warnings


def inventory_root(source_root: str | Path) -> RootInventoryReport:
    """Classify visible root directories without changing or following links."""

    root = SourceDiscoveryService()._validate_source_root(source_root)
    entries: list[RootInventoryEntry] = []
    old_profiles: list[OldWindowsProfile] = []
    warnings: list[str] = []
    review_size = 0
    review_files = 0

    try:
        candidates = sorted(root.iterdir(), key=lambda item: item.name.casefold())
    except OSError as exc:
        return RootInventoryReport(
            source_root=str(root),
            warnings=[f"Impossible de lire la racine {root} : {exc}"],
        )

    for candidate in candidates:
        try:
            if candidate.is_symlink() or not candidate.is_dir():
                continue
        except OSError as exc:
            warnings.append(f"Impossible d'inspecter {candidate} : {exc}")
            continue

        category, reason = _classify(candidate.name)
        size_bytes: int | None = None
        file_count: int | None = None
        local_warnings: list[str] = []

        if category in {RootEntryCategory.REVIEW, RootEntryCategory.PERSONAL}:
            size_bytes, file_count, local_warnings = _safe_directory_estimate(candidate)
            review_size += size_bytes
            review_files += file_count
        elif category == RootEntryCategory.OLD_WINDOWS:
            profiles, profile_warnings = _old_windows_profiles(candidate)
            old_profiles.extend(profiles)
            local_warnings.extend(profile_warnings)
            size_bytes = sum(profile.personal_size_bytes for profile in profiles)
            file_count = sum(profile.personal_file_count for profile in profiles)

        entries.append(
            RootInventoryEntry(
                name=candidate.name,
                path=str(candidate),
                category=category,
                reason=reason,
                included_by_default=False,
                size_bytes=size_bytes,
                file_count=file_count,
                warnings=local_warnings,
            )
        )

    entries.sort(key=lambda item: (item.category, item.name.casefold()))
    return RootInventoryReport(
        source_root=str(root),
        entries=entries,
        old_windows_profiles=old_profiles,
        review_size_bytes=review_size,
        review_file_count=review_files,
        warnings=warnings,
    )


__all__ = ["inventory_root"]
