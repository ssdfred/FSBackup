"""Browser backup creation service."""

from __future__ import annotations

import json
import logging
import platform
from datetime import UTC, datetime
from pathlib import Path

from app.main import app
from app.modules.browser_inspector.service import scan

from .models import build_backup_paths, default_backup_root
from .schemas import BackupManifest, BackupMetadata, BrowserBackupEntry


LOGGER = logging.getLogger(__name__)


class BrowserBackupService:
    """Create the initial backup directory structure and manifest files."""

    FORMAT_VERSION = 1

    def __init__(self, backup_root: Path | None = None) -> None:
        self._backup_root = backup_root or default_backup_root()

    def create_backup_structure(self) -> Path:
        """Create a new backup directory and write the manifest files."""

        backup_paths = build_backup_paths(self._backup_root)
        LOGGER.debug("Creating backup directory %s", backup_paths.root)
        backup_paths.root.mkdir(parents=True, exist_ok=False)

        report = scan()
        created_at = datetime.now(UTC)
        manifest = self._build_manifest(report, created_at)
        metadata = self._build_metadata(manifest, created_at)

        self._write_json(backup_paths.manifest_path, manifest)
        self._write_json(backup_paths.metadata_path, metadata)
        return backup_paths.root

    def _build_manifest(self, report, created_at: datetime) -> BackupManifest:
        return BackupManifest(
            format_version=self.FORMAT_VERSION,
            created_at=created_at,
            application=app.title,
            application_version=str(app.version),
            machine_name=platform.node() or "unknown",
            platform=platform.system(),
            browsers=self._browser_entries(report),
        )

    def _build_metadata(self, manifest: BackupManifest, created_at: datetime) -> BackupMetadata:
        profile_count = sum(len(browser.profiles) for browser in manifest.browsers)
        return BackupMetadata(
            browser_count=len(manifest.browsers),
            profile_count=profile_count,
            created_at=created_at,
        )

    def _browser_entries(self, report) -> list[BrowserBackupEntry]:
        browsers = report.browsers
        return [
            BrowserBackupEntry(
                name="Chrome",
                version=browsers.chrome.version,
                profiles=browsers.chrome.profiles,
            ),
            BrowserBackupEntry(
                name="Edge",
                version=browsers.edge.version,
                profiles=browsers.edge.profiles,
            ),
            BrowserBackupEntry(
                name="Firefox",
                version=browsers.firefox.version,
                profiles=browsers.firefox.profiles,
            ),
            BrowserBackupEntry(
                name="Brave",
                version=browsers.brave.version,
                profiles=browsers.brave.profiles,
            ),
        ]

    def _write_json(self, path: Path, model: BackupManifest | BackupMetadata) -> None:
        payload = model.model_dump(mode="json")
        try:
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            LOGGER.warning("Unable to write file %s: %s", path, exc)