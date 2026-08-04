from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.archive_engine.schemas import ArchiveReport, ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
from app.modules.backup_set.repository import BackupSetRepository
from app.modules.backup_set.schemas import BackupSegmentStatus
from app.modules.backup_set.service import BackupSetService
from app.modules.copy_engine.schemas import CopyRequest, CopyStatus
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.schemas import (
    ExecutionItem,
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)
from app.modules.execution_planner.windows_service import WindowsExecutionPlannerService
from app.modules.integrity_engine.schemas import IntegrityReport, IntegrityRequest
from app.modules.integrity_engine.service import IntegrityEngineService
from app.modules.manifest_builder.schemas import ManifestExclusion
from app.modules.manifest_builder.service import ManifestBuilderService

from .schemas import BackupRunReport, BackupRunRequest, BackupSourceMode


class BackupOrchestratorService:
    @classmethod
    def run(cls, request: BackupRunRequest) -> BackupRunReport:
        try:
            execution_plan = cls._build_execution_plan(request)
            execution_plan, excluded_files, excluded_size = cls._apply_exclusions(
                execution_plan, request
            )
            if request.segmented:
                return cls._run_segmented(
                    request=request,
                    execution_plan=execution_plan,
                    excluded_files=excluded_files,
                    excluded_size=excluded_size,
                )
            with TemporaryDirectory(prefix="fsbackup-") as workspace:
                copy_report = CopyEngineService.execute(
                    CopyRequest(
                        execution_plan=execution_plan,
                        destination_root=workspace,
                    )
                )
                warnings = [issue.message for issue in copy_report.warnings]
                if not copy_report.success:
                    error = (
                        copy_report.errors[0].message
                        if copy_report.errors
                        else "Copy failed."
                    )
                    return BackupRunReport(
                        success=False,
                        copied_files=copy_report.summary.copied,
                        excluded_files=excluded_files,
                        excluded_size_bytes=excluded_size,
                        warnings=warnings,
                        error=error,
                        copy_report=copy_report,
                    )

                execution_plan = cls._retain_copied_files(
                    execution_plan,
                    copy_report.files,
                )
                exclusions = [
                    ManifestExclusion(
                        path=item.path,
                        reason=item.reason,
                        risk=item.risk,
                        approved_by_user=item.approved_by_user,
                    )
                    for item in request.approved_exclusions
                ]
                manifest = ManifestBuilderService().build(execution_plan, exclusions)
                archive_report = ArchiveEngineService.create(
                    ArchiveRequest(
                        source_directory=workspace,
                        destination_directory=request.destination_directory,
                        archive_name=request.archive_name,
                        manifest=manifest,
                        compression=request.compression,
                        encryption=request.encryption,
                    )
                )
                if not archive_report.success:
                    return BackupRunReport(
                        success=False,
                        copied_files=copy_report.summary.copied,
                        excluded_files=excluded_files,
                        excluded_size_bytes=excluded_size,
                        warnings=warnings,
                        error=archive_report.error,
                        copy_report=copy_report,
                        archive_report=archive_report,
                    )

                integrity_report = None
                if request.verify_integrity:
                    password = (
                        request.encryption.password if request.encryption else None
                    )
                    integrity_report = IntegrityEngineService.verify(
                        IntegrityRequest(
                            archive_path=archive_report.archive_path,
                            password=password,
                        )
                    )
                    if not integrity_report.valid:
                        Path(archive_report.archive_path).unlink(missing_ok=True)
                        return BackupRunReport(
                            success=False,
                            copied_files=copy_report.summary.copied,
                            excluded_files=excluded_files,
                            excluded_size_bytes=excluded_size,
                            warnings=warnings + integrity_report.warnings,
                            error="Archive integrity verification failed.",
                            copy_report=copy_report,
                            archive_report=archive_report,
                            integrity_report=integrity_report,
                        )

                return BackupRunReport(
                    success=True,
                    archive_path=archive_report.archive_path,
                    copied_files=copy_report.summary.copied,
                    excluded_files=excluded_files,
                    excluded_size_bytes=excluded_size,
                    warnings=warnings,
                    copy_report=copy_report,
                    archive_report=archive_report,
                    integrity_report=integrity_report,
                )
        except (OSError, ValueError) as exc:
            return BackupRunReport(success=False, error=str(exc))

    @classmethod
    def _run_segmented(
        cls,
        request: BackupRunRequest,
        execution_plan: ExecutionPlan,
        excluded_files: int,
        excluded_size: int,
    ) -> BackupRunReport:
        plans = BackupSetService.split_plan(
            execution_plan,
            request.segment_size_bytes,
        )
        backup_set_directory = BackupSetService.directory(
            request.destination_directory,
            request.archive_name,
        )
        existing = (
            BackupSetRepository.load(backup_set_directory)
            if request.resume
            else None
        )
        if existing is not None:
            BackupSetService.validate_existing(
                existing,
                execution_plan.source_root,
                request.encryption is not None,
            )
        backup_set = BackupSetService.prepare_manifest(
            existing=existing,
            archive_name=request.archive_name,
            source_root=execution_plan.source_root,
            segment_size_bytes=request.segment_size_bytes,
            encrypted=request.encryption is not None,
            plans=plans,
        )
        manifest_path = BackupSetRepository.save(backup_set_directory, backup_set)
        archive_paths: list[str] = []
        warnings: list[str] = []
        copied_files = 0
        resumed_segments = 0
        last_copy_report = None
        last_archive_report = None

        for plan, segment in zip(plans, backup_set.segments, strict=True):
            archive_path = backup_set_directory / segment.archive_name
            if request.resume and cls._is_reusable_segment(
                archive_path,
                segment.sha256,
                request,
            ):
                archive_paths.append(str(archive_path))
                copied_files += segment.file_count
                resumed_segments += 1
                continue

            segment.status = BackupSegmentStatus.RUNNING
            segment.error = None
            backup_set.complete = False
            backup_set.updated_at = datetime.now(UTC)
            BackupSetRepository.save(backup_set_directory, backup_set)

            with TemporaryDirectory(prefix="fsbackup-segment-") as workspace:
                copy_report = CopyEngineService.execute(
                    CopyRequest(
                        execution_plan=plan,
                        destination_root=workspace,
                    )
                )
                last_copy_report = copy_report
                copied_files += copy_report.summary.copied
                warnings.extend(issue.message for issue in copy_report.warnings)
                if not copy_report.success:
                    error = (
                        copy_report.errors[0].message
                        if copy_report.errors
                        else "Segment copy failed."
                    )
                    return cls._segmented_failure(
                        backup_set=backup_set,
                        backup_set_directory=backup_set_directory,
                        manifest_path=manifest_path,
                        segment=segment,
                        error=error,
                        copied_files=copied_files,
                        excluded_files=excluded_files,
                        excluded_size=excluded_size,
                        warnings=warnings,
                        archive_paths=archive_paths,
                        resumed_segments=resumed_segments,
                        copy_report=copy_report,
                    )

                retained_plan = cls._retain_copied_files(plan, copy_report.files)
                manifest = ManifestBuilderService().build(
                    retained_plan,
                    cls._manifest_exclusions(request),
                )
                archive_report = ArchiveEngineService.create(
                    ArchiveRequest(
                        source_directory=workspace,
                        destination_directory=str(backup_set_directory),
                        archive_name=segment.archive_name,
                        manifest=manifest,
                        compression=request.compression,
                        encryption=request.encryption,
                    )
                )
                last_archive_report = archive_report
                if not archive_report.success:
                    return cls._segmented_failure(
                        backup_set=backup_set,
                        backup_set_directory=backup_set_directory,
                        manifest_path=manifest_path,
                        segment=segment,
                        error=archive_report.error or "Segment archive failed.",
                        copied_files=copied_files,
                        excluded_files=excluded_files,
                        excluded_size=excluded_size,
                        warnings=warnings,
                        archive_paths=archive_paths,
                        resumed_segments=resumed_segments,
                        copy_report=copy_report,
                        archive_report=archive_report,
                    )

                integrity_report = IntegrityEngineService.verify(
                    IntegrityRequest(
                        archive_path=archive_report.archive_path,
                        password=(
                            request.encryption.password
                            if request.encryption is not None
                            else None
                        ),
                    )
                )
                if not integrity_report.valid:
                    Path(archive_report.archive_path).unlink(missing_ok=True)
                    return cls._segmented_failure(
                        backup_set=backup_set,
                        backup_set_directory=backup_set_directory,
                        manifest_path=manifest_path,
                        segment=segment,
                        error="Segment integrity verification failed.",
                        copied_files=copied_files,
                        excluded_files=excluded_files,
                        excluded_size=excluded_size,
                        warnings=warnings + integrity_report.warnings,
                        archive_paths=archive_paths,
                        resumed_segments=resumed_segments,
                        copy_report=copy_report,
                        archive_report=archive_report,
                        integrity_report=integrity_report,
                    )

            segment.status = BackupSegmentStatus.COMPLETED
            segment.file_count = last_archive_report.file_count
            segment.archive_size_bytes = last_archive_report.archive_size
            segment.duration_ms = last_archive_report.duration_ms
            segment.sha256 = BackupSetService.file_sha256(archive_path)
            segment.error = None
            archive_paths.append(str(archive_path))
            backup_set.updated_at = datetime.now(UTC)
            BackupSetRepository.save(backup_set_directory, backup_set)

        backup_set.complete = True
        backup_set.updated_at = datetime.now(UTC)
        BackupSetRepository.save(backup_set_directory, backup_set)
        aggregate_archive_report = cls._aggregate_segment_archive_report(
            backup_set,
            manifest_path,
            request,
        )
        aggregate_integrity_report = cls._aggregate_segment_integrity_report(
            backup_set,
            manifest_path,
        )
        return BackupRunReport(
            success=True,
            archive_path=str(manifest_path),
            backup_set_path=str(manifest_path),
            archive_paths=archive_paths,
            copied_files=copied_files,
            excluded_files=excluded_files,
            excluded_size_bytes=excluded_size,
            warnings=warnings,
            copy_report=last_copy_report,
            archive_report=aggregate_archive_report,
            integrity_report=aggregate_integrity_report,
            total_segments=len(backup_set.segments),
            completed_segments=len(backup_set.segments),
            resumed_segments=resumed_segments,
        )

    @staticmethod
    def _aggregate_segment_archive_report(
        backup_set,
        manifest_path: Path,
        request: BackupRunRequest,
    ) -> ArchiveReport:
        original_size = sum(segment.size_bytes for segment in backup_set.segments)
        archive_size = sum(
            segment.archive_size_bytes for segment in backup_set.segments
        )
        return ArchiveReport(
            archive_path=str(manifest_path),
            file_count=sum(segment.file_count for segment in backup_set.segments),
            archive_size=archive_size,
            original_size=original_size,
            saved_bytes=max(original_size - archive_size, 0),
            compression_ratio=(
                round(archive_size / original_size, 4) if original_size else 0.0
            ),
            compression_method=request.compression.method,
            compression_level=request.compression.level,
            encrypted=request.encryption is not None,
            duration_ms=sum(segment.duration_ms for segment in backup_set.segments),
            success=True,
        )

    @staticmethod
    def _aggregate_segment_integrity_report(
        backup_set,
        manifest_path: Path,
    ) -> IntegrityReport:
        return IntegrityReport(
            archive_path=str(manifest_path),
            valid=True,
            checked_file_count=sum(
                segment.file_count for segment in backup_set.segments
            ),
            duration_ms=0,
        )

    @staticmethod
    def _is_reusable_segment(
        archive_path: Path,
        expected_sha256: str | None,
        request: BackupRunRequest,
    ) -> bool:
        if expected_sha256 is None or not archive_path.is_file():
            return False
        if BackupSetService.file_sha256(archive_path) != expected_sha256:
            return False
        integrity = IntegrityEngineService.verify(
            IntegrityRequest(
                archive_path=str(archive_path),
                password=(
                    request.encryption.password
                    if request.encryption is not None
                    else None
                ),
            )
        )
        return integrity.valid

    @staticmethod
    def _segmented_failure(
        backup_set,
        backup_set_directory: Path,
        manifest_path: Path,
        segment,
        error: str,
        copied_files: int,
        excluded_files: int,
        excluded_size: int,
        warnings: list[str],
        archive_paths: list[str],
        resumed_segments: int,
        copy_report=None,
        archive_report=None,
        integrity_report=None,
    ) -> BackupRunReport:
        segment.status = BackupSegmentStatus.FAILED
        segment.error = error
        backup_set.complete = False
        backup_set.updated_at = datetime.now(UTC)
        BackupSetRepository.save(backup_set_directory, backup_set)
        return BackupRunReport(
            success=False,
            backup_set_path=str(manifest_path),
            archive_paths=archive_paths,
            copied_files=copied_files,
            excluded_files=excluded_files,
            excluded_size_bytes=excluded_size,
            warnings=warnings,
            error=error,
            copy_report=copy_report,
            archive_report=archive_report,
            integrity_report=integrity_report,
            total_segments=len(backup_set.segments),
            completed_segments=sum(
                item.status == BackupSegmentStatus.COMPLETED
                for item in backup_set.segments
            ),
            resumed_segments=resumed_segments,
        )

    @staticmethod
    def _manifest_exclusions(
        request: BackupRunRequest,
    ) -> list[ManifestExclusion]:
        return [
            ManifestExclusion(
                path=item.path,
                reason=item.reason,
                risk=item.risk,
                approved_by_user=item.approved_by_user,
            )
            for item in request.approved_exclusions
        ]

    @classmethod
    def _build_execution_plan(cls, request: BackupRunRequest) -> ExecutionPlan:
        if request.source_mode == BackupSourceMode.CUSTOM_FOLDER:
            return cls._build_custom_folder_plan(request.source_root)
        return WindowsExecutionPlannerService.build_plan(
            request.source_root,
            request.selected_item_ids,
            request.selected_additional_paths,
            request.selected_recovery_paths,
        )

    @staticmethod
    def _retain_copied_files(
        execution_plan: ExecutionPlan,
        copy_results: list,
    ) -> ExecutionPlan:
        retained_sources = {
            result.source
            for result in copy_results
            if result.status in {CopyStatus.COPIED, CopyStatus.SKIPPED}
        }
        retained = [
            physical_file
            for physical_file in execution_plan.physical_files
            if physical_file.source_path in retained_sources
        ]
        missing_count = len(execution_plan.physical_files) - len(retained)
        summary = execution_plan.summary.model_copy(
            update={
                "physical_files": len(retained),
                "missing_files": missing_count,
                "estimated_size_bytes": sum(item.size_bytes for item in retained),
            }
        )
        warnings = list(execution_plan.warnings)
        if missing_count:
            warnings.append(
                f"{missing_count} fichier(s) volatil(s) disparu(s) pendant la copie."
            )
        return execution_plan.model_copy(
            update={
                "physical_files": retained,
                "summary": summary,
                "warnings": warnings,
            }
        )

    @staticmethod
    def _apply_exclusions(
        execution_plan: ExecutionPlan,
        request: BackupRunRequest,
    ) -> tuple[ExecutionPlan, int, int]:
        if not request.approved_exclusions:
            return execution_plan, 0, 0
        if not request.exclusions_confirmed:
            raise ValueError(
                "Les exclusions sélectionnées doivent être confirmées explicitement."
            )
        if any(not item.approved_by_user for item in request.approved_exclusions):
            raise ValueError("Chaque exclusion doit être approuvée par l'utilisateur.")

        source_root = Path(execution_plan.source_root).resolve(strict=True)
        excluded_roots: list[Path] = []
        for exclusion in request.approved_exclusions:
            candidate = Path(exclusion.path).expanduser().resolve(strict=False)
            try:
                candidate.relative_to(source_root)
            except ValueError as exc:
                raise ValueError(
                    f"Exclusion hors de la source interdite : {candidate}"
                ) from exc
            if candidate == source_root:
                raise ValueError(
                    "La racine complète de la source ne peut pas être exclue."
                )
            excluded_roots.append(candidate)

        kept: list[PhysicalFile] = []
        excluded: list[PhysicalFile] = []
        for physical_file in execution_plan.physical_files:
            candidate = Path(physical_file.source_path).resolve(strict=False)
            if any(
                candidate == excluded_root or excluded_root in candidate.parents
                for excluded_root in excluded_roots
            ):
                excluded.append(physical_file)
            else:
                kept.append(physical_file)

        summary = execution_plan.summary.model_copy(
            update={
                "physical_files": len(kept),
                "estimated_size_bytes": sum(item.size_bytes for item in kept),
            }
        )
        filtered_plan = execution_plan.model_copy(
            update={
                "physical_files": kept,
                "summary": summary,
                "warnings": execution_plan.warnings
                + [
                    f"{len(excluded)} fichier(s) exclus après confirmation utilisateur."
                ],
            }
        )
        return (
            filtered_plan,
            len(excluded),
            sum(item.size_bytes for item in excluded),
        )

    @staticmethod
    def _build_custom_folder_plan(source_root: str) -> ExecutionPlan:
        root = Path(source_root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"La source n'est pas un dossier : {root}")

        physical_files: list[PhysicalFile] = []
        warnings: list[str] = []
        for candidate in sorted(root.rglob("*"), key=lambda path: str(path).casefold()):
            try:
                if candidate.is_symlink():
                    warnings.append(f"Lien symbolique ignoré : {candidate}")
                    continue
                if not candidate.is_file():
                    continue
                resolved = candidate.resolve(strict=True)
                relative_path = resolved.relative_to(root)
                size_bytes = resolved.stat().st_size
            except (OSError, ValueError) as exc:
                warnings.append(f"Fichier ignoré : {candidate} ({exc})")
                continue

            physical_files.append(
                PhysicalFile(
                    source_path=str(resolved),
                    relative_path=str(relative_path),
                    size_bytes=size_bytes,
                    required_by=["custom-folder"],
                )
            )

        item = ExecutionItem(
            logical_id="custom-folder",
            category="custom_folder",
            application_key="custom_folder",
            application_name="Dossier personnalisé",
            user_name="local",
            profile_name=root.name or str(root),
            files=[file.source_path for file in physical_files],
            warnings=warnings,
        )
        summary = ExecutionPlanSummary(
            logical_items=1,
            physical_files=len(physical_files),
            estimated_size_bytes=sum(file.size_bytes for file in physical_files),
            warnings=len(warnings),
        )
        return ExecutionPlan(
            source_root=str(root),
            items=[item],
            physical_files=physical_files,
            summary=summary,
            warnings=warnings,
        )
