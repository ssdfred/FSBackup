"""Conservative read-only inventory of a selected Windows volume root."""

from __future__ import annotations

from pathlib import Path

from .diagnostic import (
    PERSONAL_FOLDER_ALIASES,
    _resolve_personal_folder,
    _safe_directory_estimate,
)
from .root_inventory_schemas import (
    RootEntryCategory,
    RootInventoryEntry,
    RootInventoryReport,
    WindowsRecoveryProfile,
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
            "Ancienne installation Windows à analyser séparément avant "
            "toute récupération.",
        )
    if normalized in SYSTEM_ROOTS:
        return (
            RootEntryCategory.SYSTEM,
            "Élément système ou technique non inclus automatiquement "
            "dans une sauvegarde de données.",
        )
    if normalized in PERSONAL_ROOTS:
        return (
            RootEntryCategory.PERSONAL,
            "Dossier personnel visible directement à la racine du lecteur.",
        )
    return (
        RootEntryCategory.REVIEW,
        "Dossier applicatif, projet ou donnée personnalisée à examiner "
        "manuellement.",
    )


def _profile_report(profile: Path, profile_kind: str) -> WindowsRecoveryProfile:
    warnings: list[str] = []
    standard_size = 0
    standard_files = 0
    for _display_name, aliases in PERSONAL_FOLDER_ALIASES:
        folder = _resolve_personal_folder(profile, aliases)
        try:
            if not folder.is_dir():
                continue
        except OSError:
            continue
        size, files, local_warnings = _safe_directory_estimate(folder)
        standard_size += size
        standard_files += files
        warnings.extend(local_warnings)

    total_size, total_files, total_warnings = _safe_directory_estimate(profile)
    warnings.extend(total_warnings)
    return WindowsRecoveryProfile(
        name=profile.name,
        path=str(profile),
        profile_kind=profile_kind,
        standard_size_bytes=standard_size,
        standard_file_count=standard_files,
        total_size_bytes=total_size,
        total_file_count=total_files,
        additional_size_bytes=max(total_size - standard_size, 0),
        additional_file_count=max(total_files - standard_files, 0),
        warnings=warnings,
    )


def _windows_profiles(
    users_root: Path, profile_kind: str
) -> tuple[list[WindowsRecoveryProfile], list[str]]:
    profiles: list[WindowsRecoveryProfile] = []
    warnings: list[str] = []
    try:
        candidates = sorted(users_root.iterdir(), key=lambda item: item.name.casefold())
    except OSError as exc:
        return profiles, [f"Impossible de lire les profils de {users_root} : {exc}"]

    for profile in candidates:
        try:
            ignored = SourceDiscoveryService._should_ignore_user(profile.name)
            if not profile.is_dir() or ignored:
                continue
        except OSError as exc:
            warnings.append(f"Impossible d'inspecter {profile} : {exc}")
            continue
        report = _profile_report(profile, profile_kind)
        profiles.append(report)
        warnings.extend(report.warnings)
    return profiles, warnings


def inventory_root(source_root: str | Path) -> RootInventoryReport:
    """Classify visible root directories and estimate recoverable profiles."""

    root = SourceDiscoveryService()._validate_source_root(source_root)
    entries: list[RootInventoryEntry] = []
    warnings: list[str] = []
    review_size = 0
    review_files = 0

    users_root = root / "Users"
    if not users_root.is_dir():
        users_root = root / "Utilisateurs"
    current_profiles, current_warnings = _windows_profiles(users_root, "current")
    warnings.extend(current_warnings)
    old_profiles: list[WindowsRecoveryProfile] = []

    try:
        candidates = sorted(root.iterdir(), key=lambda item: item.name.casefold())
    except OSError as exc:
        return RootInventoryReport(
            source_root=str(root),
            current_windows_profiles=current_profiles,
            warnings=warnings + [f"Impossible de lire la racine {root} : {exc}"],
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
            old_users = candidate / "Users"
            if not old_users.is_dir():
                old_users = candidate / "Utilisateurs"
            profiles, profile_warnings = _windows_profiles(old_users, "old")
            old_profiles.extend(profiles)
            local_warnings.extend(profile_warnings)
            size_bytes, file_count, estimate_warnings = _safe_directory_estimate(candidate)
            local_warnings.extend(estimate_warnings)

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
    recoverable_profiles = current_profiles + old_profiles
    return RootInventoryReport(
        source_root=str(root),
        entries=entries,
        current_windows_profiles=current_profiles,
        old_windows_profiles=old_profiles,
        review_size_bytes=review_size,
        review_file_count=review_files,
        recoverable_profile_size_bytes=sum(
            profile.total_size_bytes for profile in recoverable_profiles
        ),
        recoverable_profile_file_count=sum(
            profile.total_file_count for profile in recoverable_profiles
        ),
        warnings=warnings,
    )


__all__ = ["inventory_root"]
