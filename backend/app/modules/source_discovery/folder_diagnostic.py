"""Read-only diagnostic for a custom backup folder."""

from __future__ import annotations

import os
from pathlib import Path
import shutil

from .diagnostic_schemas import (
    CustomFolderDiagnosticReport,
    DiskUsageDiagnostic,
)
from .service import SourceDiscoveryError


def _scan_folder(root: Path) -> tuple[int, int, list[str]]:
    size_bytes = 0
    file_count = 0
    warnings: list[str] = []

    def on_error(error: OSError) -> None:
        warnings.append(str(error))

    for current_root, directory_names, file_names in os.walk(
        root,
        topdown=True,
        onerror=on_error,
        followlinks=False,
    ):
        current = Path(current_root)
        directory_names[:] = [
            name for name in directory_names if not (current / name).is_symlink()
        ]
        for file_name in file_names:
            path = current / file_name
            try:
                if path.is_symlink():
                    continue
                size_bytes += path.stat().st_size
                file_count += 1
            except OSError as exc:
                warnings.append(f"{path}: {exc}")

    return size_bytes, file_count, warnings


def _disk_usage(path: Path) -> DiskUsageDiagnostic:
    usage = shutil.disk_usage(path)
    return DiskUsageDiagnostic(
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
    )


def diagnose_custom_folder(
    source_root: str,
    destination_root: str | None = None,
) -> CustomFolderDiagnosticReport:
    source = Path(source_root).expanduser()
    if not source.exists():
        raise SourceDiscoveryError(f"Le dossier source n'existe pas : {source}")
    if not source.is_dir():
        raise SourceDiscoveryError(f"La source n'est pas un dossier : {source}")

    size_bytes, file_count, warnings = _scan_folder(source)
    try:
        source_disk = _disk_usage(source)
    except OSError as exc:
        source_disk = DiskUsageDiagnostic()
        warnings.append(f"Impossible de mesurer le lecteur source : {exc}")

    destination_disk = DiskUsageDiagnostic()
    normalized_destination: str | None = None
    if destination_root:
        destination = Path(destination_root).expanduser()
        normalized_destination = str(destination)
        probe = destination
        while not probe.exists() and probe.parent != probe:
            probe = probe.parent
        try:
            destination_disk = _disk_usage(probe)
        except OSError as exc:
            warnings.append(f"Impossible de mesurer la destination : {exc}")

    return CustomFolderDiagnosticReport(
        source_root=str(source),
        destination_root=normalized_destination,
        size_bytes=size_bytes,
        file_count=file_count,
        source_disk=source_disk,
        destination_disk=destination_disk,
        warnings=warnings,
    )
