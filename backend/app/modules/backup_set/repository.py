import json
from pathlib import Path

from .schemas import BackupSetManifest


class BackupSetRepository:
    MANIFEST_NAME = "backup-set.json"

    @classmethod
    def manifest_path(cls, directory: Path) -> Path:
        return directory / cls.MANIFEST_NAME

    @classmethod
    def load(cls, directory: Path) -> BackupSetManifest | None:
        path = cls.manifest_path(directory)
        if not path.is_file():
            return None
        return BackupSetManifest.model_validate_json(path.read_text(encoding="utf-8"))

    @classmethod
    def save(cls, directory: Path, manifest: BackupSetManifest) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = cls.manifest_path(directory)
        temporary_path = path.with_suffix(".json.tmp")
        payload = json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        temporary_path.write_text(payload, encoding="utf-8")
        temporary_path.replace(path)
        return path
