"""Strictly read-only diagnostic of a selected Windows disk."""

from __future__ import annotations

import os
from pathlib import Path

from .diagnostic_schemas import (
    BackupEstimate,
    DetectedApplication,
    FolderEstimate,
    MessagingProfileDiagnostic,
    UserProfileDiagnostic,
    WindowsDiagnosticReport,
    WindowsDirectoryMarker,
    WindowsSystemInformation,
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

APPLICATION_PATHS = {
    "git": ("Git", ("Program Files/Git", "Program Files (x86)/Git")),
    "vscode": ("Visual Studio Code", ("Program Files/Microsoft VS Code",)),
    "visual_studio": ("Visual Studio", ("Program Files/Microsoft Visual Studio",)),
    "jetbrains": ("JetBrains", ("Program Files/JetBrains",)),
    "docker": ("Docker Desktop", ("Program Files/Docker", "ProgramData/DockerDesktop")),
    "nodejs": ("Node.js", ("Program Files/nodejs",)),
    "python": ("Python", ("Program Files/Python", "Program Files/Python313", "Program Files/Python312", "Program Files/Python311")),
    "java": ("Java", ("Program Files/Java", "Program Files/Eclipse Adoptium")),
    "android_studio": ("Android Studio", ("Program Files/Android/Android Studio",)),
    "winscp": ("WinSCP", ("Program Files/WinSCP", "Program Files (x86)/WinSCP")),
    "filezilla": ("FileZilla", ("Program Files/FileZilla FTP Client", "Program Files (x86)/FileZilla FTP Client")),
    "steam": ("Steam", ("Program Files (x86)/Steam", "Program Files/Steam")),
    "discord": ("Discord", ("ProgramData/Discord",)),
}

USER_APPLICATION_PATHS = {
    "vscode": ("Visual Studio Code", ("AppData/Local/Programs/Microsoft VS Code",)),
    "jetbrains": ("JetBrains", ("AppData/Local/JetBrains", "AppData/Roaming/JetBrains")),
    "docker": ("Docker Desktop", ("AppData/Roaming/Docker", "AppData/Local/Docker")),
    "python": ("Python", ("AppData/Local/Programs/Python",)),
    "android_studio": ("Android Studio", ("AppData/Local/Google/AndroidStudio",)),
    "winscp": ("WinSCP", ("AppData/Roaming/Microsoft/Windows/Start Menu/Programs/WinSCP",)),
    "filezilla": ("FileZilla", ("AppData/Roaming/FileZilla",)),
    "steam": ("Steam", ("AppData/Local/Steam",)),
    "discord": ("Discord", ("AppData/Local/Discord", "AppData/Roaming/discord")),
}

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


def _system_information(root: Path, warnings: list[str]) -> WindowsSystemInformation:
    """Return only information that can be inferred reliably from the disk layout."""

    architecture = "64 bits" if (root / "Program Files (x86)").is_dir() else None
    windows_directory = root / "Windows"
    system_size = None
    if windows_directory.is_dir():
        system_size, _, local_warnings = _safe_directory_estimate(windows_directory)
        warnings.extend(local_warnings)
    return WindowsSystemInformation(
        architecture=architecture,
        system_size_bytes=system_size,
    )


def _discover_messaging(profile: Path) -> list[MessagingProfileDiagnostic]:
    definitions = (
        ("Thunderbird", (profile / "AppData/Roaming/Thunderbird/Profiles",)),
        (
            "Outlook",
            (
                profile / "Documents/Outlook Files",
                profile / "AppData/Local/Microsoft/Outlook",
            ),
        ),
    )
    reports: list[MessagingProfileDiagnostic] = []
    for client, candidates in definitions:
        paths: list[str] = []
        size_bytes = 0
        file_count = 0
        warnings: list[str] = []
        for candidate in candidates:
            try:
                present = candidate.is_dir()
            except OSError as exc:
                warnings.append(f"Impossible d'inspecter {candidate} : {exc}")
                continue
            if not present:
                continue
            paths.append(str(candidate))
            size, files, local_warnings = _safe_directory_estimate(candidate)
            size_bytes += size
            file_count += files
            warnings.extend(local_warnings)
        if paths:
            reports.append(
                MessagingProfileDiagnostic(
                    client=client,
                    user_name=profile.name,
                    paths=paths,
                    size_bytes=size_bytes,
                    file_count=file_count,
                    warnings=warnings,
                )
            )
    return reports


def _discover_applications(root: Path, profiles: list[Path]) -> list[DetectedApplication]:
    detected: dict[str, DetectedApplication] = {}

    def register(key: str, name: str, candidate: Path) -> None:
        try:
            present = candidate.is_dir() or candidate.is_file()
        except OSError:
            return
        if not present:
            return
        application = detected.setdefault(key, DetectedApplication(key=key, name=name))
        path = str(candidate)
        if path not in application.detected_paths:
            application.detected_paths.append(path)

    for key, (name, paths) in APPLICATION_PATHS.items():
        for relative_path in paths:
            register(key, name, root / Path(relative_path))

    for profile in profiles:
        for key, (name, paths) in USER_APPLICATION_PATHS.items():
            for relative_path in paths:
                register(key, name, profile / Path(relative_path))

    return sorted(detected.values(), key=lambda item: item.name.casefold())


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
    profile_paths: list[Path] = []
    messaging_profiles: list[MessagingProfileDiagnostic] = []
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
        profile_paths.append(profile)
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
        messaging_profiles.extend(_discover_messaging(profile))
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
        system=_system_information(root, warnings),
        users=users,
        detected_browsers=sorted(detected_browsers),
        messaging_profiles=messaging_profiles,
        applications=_discover_applications(root, profile_paths),
        estimate=estimate,
        warnings=warnings,
    )


__all__ = ["SourceDiscoveryError", "diagnose_windows_source"]
