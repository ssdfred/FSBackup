from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BACKUP_DIRECTORY_NAME = "backup"
BACKUP_DIRECTORY_PREFIX = "backup_"


@dataclass(frozen=True, slots=True)
class BackupPaths:
    """Filesystem layout for a backup directory."""

    root: Path
    manifest_path: Path
    metadata_path: Path


def project_root() -> Path:
    """Return the project root directory."""

    return Path(__file__).resolve().parents[4]


def default_backup_root() -> Path:
    """Return the default backup root directory."""

    return project_root() / BACKUP_DIRECTORY_NAME


def next_backup_root(base_root: Path | None = None) -> Path:
    """Return the next available backup directory without overwriting existing data."""

    target = base_root or default_backup_root()
    if not target.exists():
        return target

    index = 1
    while True:
        candidate = target.with_name(f"{target.name}_{index:03d}")
        if not candidate.exists():
            return candidate
        index += 1


def build_backup_paths(base_root: Path | None = None) -> BackupPaths:
    """Build the full filesystem layout for a new backup."""

    root = next_backup_root(base_root)
    return BackupPaths(
        root=root,
        manifest_path=root / "manifest.json",
        metadata_path=root / "metadata.json",
    )