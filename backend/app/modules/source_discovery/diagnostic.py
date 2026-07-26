"""Strictly read-only diagnostic of a selected Windows disk."""

from __future__ import annotations

import os
from pathlib import Path

from .diagnostic_schemas import (
    BackupEstimate,
    FolderEstimate,
    UserProfileDiagnostic,
    WindowsDiagnosticReport,
    WindowsDirectoryMarker,
)
from .service import BROWSER_DEFINITIONS, SourceDiscoveryError, SourceDiscoveryService

WINDOWS_MARKERS = (
    ("Windows", True),
    ("Users", True),
    ("ProgramData", True),
    ("Program Files", True),
    ("Program Files (x86)", False),
)

PERSONAL_FOLDER_ALIASES = (
    ("Documents", ("Documents",)),
    ("Images", ("Pictures", "Images")),
    ("Musique", ("Music", "Musique")),
    ("Vidéos", ("Videos", "Vidéos")),
    ("Bureau", ("Desktop", "Bureau")),
    ("Téléchargements", ("Downloads", "Téléchargements")),
)

SYSTEM_USER_NAMES = SourceDiscoveryService._should_ignore_user


def _safe_directory_estimate(path: Path) -> tuple[int, int, list[str]]:
    """Estimate one directory while isolating every local filesystem error."""

    total_size = 0
    total_files = 0
    warnings: list[str] = []

    try:
        walker = os.walk(path, topdown=True, followlinks=False)
        for current_root, directories, files in walker:
            current = Path(current_root)

            readable_directories: list[str] = []
            for directory in directories:
                candidate = current / directory
                try:
                    if candidate.is_symlink():
                        continue
                    readable_directories.append(directory)
                except OSError as exc:
                    warnings.append(f"Impossible d'inspecter {candidate} : {exc}")
            directories[:] = readable_directories

            for filename in files:
                candidate = current / filename
                try:
                    if candidate.is_symlink() or not candidate.is_file():
                        continue
                    total_size += candidate.stat().st_size
                    total_files += 1
                except OSError as exc:
                    warnings.append(f"Impossible de mesurer {candidate} : {exc}")
    except OSError as exc:
        warnings.append(f"Impossible de parcourir {path} : {exc}")

    return total_size, total_files, warnings


def _resolve_personal_folder(profile: Path, aliases: tuple[str, ...]) -> Path:
    for alias in aliases:
        candidate = profile / alias
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            continue
    return profile / aliases[0]


def _discover_browsers(profile: Path) -> list[str]:
    browsers: list[str] = []
    for definition in BROWSER_DEFINITIONS:
        candidate = profile.joinpath(*definition.profile_root_parts)
        try:
            if candidate.is_dir():
                browsers.append(definition.name)
        except OSError:
            continue
    return browsers


def diagnose_windows_source(source_root: str | Path) -> WindowsDiagnosticReport:
    """Build an independent read-only diagnostic for a Windows disk root."""

    root = SourceDiscoveryService()._validate_source_root(source_root)
    warnings: list[str] = []

    markers: list[WindowsDirectoryMarker] = []
    for name, required in WINDOWS_MARKERS:
        marker_path = root / name
        try:
            present = marker_path.is_dir()
        except OSError as exc:
            present = False
            warnings.append(f"Impossible d'inspecter {marker_path} : {exc}")
        markers.append(
            WindowsDirectoryMarker(
                name=name,
                path=str(marker_path),
                present=present,
                required=required,
            )
        )

    required_markers = [marker for marker in markers if marker.required]
    present_required = sum(marker.present for marker in required_markers)
    windows_detected = present_required >= 2 and any(
        marker.name == "Windows" and marker.present for marker in markers
    )
    confidence = (
        "élevée"
        if present_required == len(required_markers)
        else "moyenne"
        if windows_detected
        else "faible"
    )

    users: list[UserProfileDiagnostic] = []
    detected_browsers: set[str] = set()
    users_root = root / "Users"

    try:
        user_candidates = sorted(users_root.iterdir(), key=lambda item: item.name.casefold())
    except (OSError, PermissionError) as exc:
        user_candidates = []
        warnings.append(f"Impossible de lire {users_root} : {exc}")

    for profile in user_candidates:
        try:
            if not profile.is_dir() or SYSTEM_USER_NAMES(profile.name):
                continue
        except OSError as exc:
            warnings.append(f"Impossible d'inspecter {profile} : {exc}")
            continue

        folders: list[FolderEstimate] = []
        profile_size = 0
        profile_files = 0

        for display_name, aliases in PERSONAL_FOLDER_ALIASES:
            folder = _resolve_personal_folder(profile, aliases)
            try:
                present = folder.is_dir()
            except OSError as exc:
                present = False
                folder_warnings = [f"Impossible d'inspecter {folder} : {exc}"]
            else:
                folder_warnings = []

            size_bytes = 0
            file_count = 0
            if present:
                size_bytes, file_count, estimate_warnings = _safe_directory_estimate(folder)
                folder_warnings.extend(estimate_warnings)

            profile_size += size_bytes
            profile_files += file_count
            folders.append(
                FolderEstimate(
                    name=display_name,
                    path=str(folder),
                    present=present,
                    size_bytes=size_bytes,
                    file_count=file_count,
                    warnings=folder_warnings,
                )
            )

        profile_browsers = _discover_browsers(profile)
        detected_browsers.update(profile_browsers)
        users.append(
            UserProfileDiagnostic(
                name=profile.name,
                path=str(profile),
                folders=folders,
                total_size_bytes=profile_size,
                total_file_count=profile_files,
            )
        )

    total_size = sum(user.total_size_bytes for user in users)
    total_files = sum(user.total_file_count for user in users)
    estimate = BackupEstimate(
        total_size_bytes=total_size,
        total_file_count=total_files,
        required_free_space_bytes=total_size,
        duration_seconds=None,
    )

    return WindowsDiagnosticReport(
        source_root=str(root),
        windows_detected=windows_detected,
        confidence=confidence,
        markers=markers,
        users=users,
        detected_browsers=sorted(detected_browsers),
        estimate=estimate,
        warnings=warnings,
    )


__all__ = ["SourceDiscoveryError", "diagnose_windows_source"]
