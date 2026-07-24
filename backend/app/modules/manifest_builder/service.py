"""Build deterministic backup manifests from execution plans."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath

from app.modules.execution_planner.schemas import ExecutionPlan, PhysicalFile

from .schemas import Manifest, ManifestFile, ManifestSummary


class ManifestBuilderError(ValueError):
    """Raised when an execution plan cannot produce a safe manifest."""


class ManifestBuilderService:
    """Transform a read-only execution plan into a copy manifest."""

    def build(self, execution_plan: ExecutionPlan) -> Manifest:
        """Create a deterministic manifest without touching source files."""

        files = [
            self._build_file(physical_file)
            for physical_file in execution_plan.physical_files
            if physical_file.exists
        ]
        files.sort(key=lambda item: item.relative_path.casefold())

        summary = execution_plan.summary
        return Manifest(
            created_at=datetime.now(UTC),
            source_root=execution_plan.source_root,
            summary=ManifestSummary(
                logical_items=summary.logical_items,
                physical_files=summary.physical_files,
                missing_files=summary.missing_files,
                encrypted_items=summary.encrypted_items,
                deduplicated_files=summary.deduplicated_files,
                estimated_size_bytes=summary.estimated_size_bytes,
                warnings=summary.warnings,
            ),
            files=files,
        )

    @staticmethod
    def _build_file(physical_file: PhysicalFile) -> ManifestFile:
        relative_path = ManifestBuilderService._normalize_relative_path(
            physical_file.relative_path
        )
        return ManifestFile(
            relative_path=relative_path,
            size=physical_file.size_bytes,
            mandatory=physical_file.mandatory,
            potentially_locked=physical_file.potentially_locked,
            required_by=sorted(set(physical_file.required_by), key=str.casefold),
        )

    @staticmethod
    def _normalize_relative_path(value: str) -> str:
        candidate = value.strip().replace("\\", "/")
        windows_path = PureWindowsPath(candidate)
        posix_path = PurePosixPath(candidate)

        if (
            not candidate
            or windows_path.is_absolute()
            or windows_path.drive
            or posix_path.is_absolute()
            or any(part in {"", ".", ".."} for part in posix_path.parts)
        ):
            raise ManifestBuilderError(
                f"Chemin relatif invalide dans le plan d'exécution : {value!r}"
            )

        return posix_path.as_posix()
