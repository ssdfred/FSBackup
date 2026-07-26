"""Build deterministic backup manifests from execution plans."""

from __future__ import annotations

import platform
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from uuid import uuid4

from app.modules.execution_planner.schemas import ExecutionPlan, PhysicalFile

from .schemas import (
    BrowserInfo,
    ExecutionInfo,
    IntegrityInfo,
    Manifest,
    ManifestExclusion,
    ManifestFile,
    ManifestHeader,
    ManifestSummary,
    ManifestV2,
    SourceInfo,
    Statistics,
)


class ManifestBuilderError(ValueError):
    """Raised when an execution plan cannot produce a safe manifest."""


class ManifestBuilderService:
    """Transform a read-only execution plan into a legacy V1 manifest."""

    def build(
        self,
        execution_plan: ExecutionPlan,
        exclusions: list[ManifestExclusion] | None = None,
    ) -> Manifest:
        """Create a deterministic V1 manifest without touching source files."""

        files = self._build_files(execution_plan)
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
            exclusions=exclusions or [],
        )

    @classmethod
    def _build_files(cls, execution_plan: ExecutionPlan) -> list[ManifestFile]:
        files = [
            cls._build_file(physical_file)
            for physical_file in execution_plan.physical_files
            if physical_file.exists
        ]
        files.sort(key=lambda item: item.relative_path.casefold())
        return files

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
            candidate in {"", ".", ".."}
            or windows_path.is_absolute()
            or windows_path.drive
            or posix_path.is_absolute()
            or any(part == ".." for part in posix_path.parts)
        ):
            raise ManifestBuilderError(
                f"Chemin relatif invalide dans le plan d'exécution : {value!r}"
            )

        return posix_path.as_posix()


class ManifestV2Builder:
    """Build the versioned execution contract used by FSBackup engines."""

    def __init__(
        self,
        *,
        application_version: str = "0.1.0",
        clock: Callable[[], datetime] | None = None,
        identifier_factory: Callable[[], str] | None = None,
    ) -> None:
        self._application_version = application_version
        self._clock = clock or (lambda: datetime.now(UTC))
        self._identifier_factory = identifier_factory or (lambda: str(uuid4()))

    def build(self, execution_plan: ExecutionPlan) -> ManifestV2:
        """Create a Manifest V2 without additional filesystem access."""

        created_at = self._clock()
        files = ManifestBuilderService._build_files(execution_plan)
        sources = self._build_sources(execution_plan)
        browsers = self._build_browsers(execution_plan)
        summary = execution_plan.summary

        return ManifestV2(
            header=ManifestHeader(
                manifest_id=self._identifier_factory(),
                created_at=created_at,
                application_version=self._application_version,
            ),
            execution=ExecutionInfo(
                execution_id=self._identifier_factory(),
                started_at=created_at,
                status="planned",
                machine_name=platform.node() or "unknown",
                platform=platform.system() or "unknown",
                warnings=sorted(set(execution_plan.warnings), key=str.casefold),
            ),
            sources=sources,
            browsers=browsers,
            files=files,
            statistics=Statistics(
                source_count=len(sources),
                logical_items=summary.logical_items,
                physical_files=summary.physical_files,
                missing_files=summary.missing_files,
                total_size_bytes=summary.estimated_size_bytes,
            ),
            integrity=IntegrityInfo(expected_files=len(files)),
        )

    @staticmethod
    def _build_sources(execution_plan: ExecutionPlan) -> list[SourceInfo]:
        sources = [
            SourceInfo(
                source_id=item.logical_id,
                provider="browser",
                source_type=item.category,
                display_name=(
                    f"{item.application_name} / {item.profile_name} / {item.category}"
                ),
                original_path=execution_plan.source_root,
                required=True,
                metadata={
                    "application_key": item.application_key,
                    "user_name": item.user_name,
                    "profile_name": item.profile_name,
                    "encrypted": item.encrypted,
                },
            )
            for item in execution_plan.items
        ]
        sources.sort(key=lambda item: item.source_id.casefold())
        return sources

    @staticmethod
    def _build_browsers(execution_plan: ExecutionPlan) -> list[BrowserInfo]:
        grouped: dict[str, dict[str, object]] = {}
        for item in execution_plan.items:
            entry = grouped.setdefault(
                item.application_key,
                {
                    "name": item.application_name,
                    "profiles": set(),
                },
            )
            profiles = entry["profiles"]
            if isinstance(profiles, set):
                profiles.add(item.profile_name)

        browsers = [
            BrowserInfo(
                name=str(entry["name"]),
                profile_names=sorted(entry["profiles"], key=str.casefold),
                metadata={"application_key": application_key},
            )
            for application_key, entry in grouped.items()
        ]
        browsers.sort(key=lambda item: item.name.casefold())
        return browsers
