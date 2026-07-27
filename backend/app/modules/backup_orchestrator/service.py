from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.archive_engine.schemas import ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
from app.modules.copy_engine.schemas import CopyRequest
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.schemas import (
    ExecutionItem,
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)
from app.modules.execution_planner.windows_service import WindowsExecutionPlannerService
from app.modules.integrity_engine.schemas import IntegrityRequest
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
            # Les dossiers temporaires proposés à l'exclusion peuvent disparaître
            # entre le diagnostic et le lancement. Une exclusion devenue absente
            # ne doit pas faire échouer toute la sauvegarde.
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
