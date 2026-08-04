from datetime import UTC, datetime
from pathlib import Path
from shutil import copy2
from time import perf_counter
from uuid import UUID, uuid4

from app.modules.execution_planner.schemas import PhysicalFile

from .events import CopyEvent, CopyEventBus, CopyEventType
from .schemas import (
    CopyFileResult,
    CopyIssue,
    CopyIssueSeverity,
    CopyReport,
    CopyRequest,
    CopyStatus,
    CopySummary,
)


class CopyEngineService:
    LOCKED_CACHE_DIRECTORIES = {
        "code cache",
        "dxccache",
        "gpucache",
        "shadercache",
    }

    @staticmethod
    def execute(
        request: CopyRequest,
        event_bus: CopyEventBus | None = None,
    ) -> CopyReport:
        execution_id = uuid4()
        started_at = datetime.now(UTC)
        execution_started_at = perf_counter()
        destination_root = Path(request.destination_root).resolve()
        results: list[CopyFileResult] = []

        CopyEngineService._publish(
            event_bus,
            CopyEvent(
                event_type=CopyEventType.COPY_STARTED,
                execution_id=execution_id,
                metadata={
                    "destination_root": str(destination_root),
                    "planned_files": len(request.execution_plan.physical_files),
                },
            ),
        )

        for physical_file in request.execution_plan.physical_files:
            result = CopyEngineService._copy_file(
                physical_file,
                destination_root,
                execution_id,
                event_bus,
            )
            results.append(result)

        duration_ms = CopyEngineService._duration_ms(execution_started_at)
        finished_at = datetime.now(UTC)
        summary = CopyEngineService._build_summary(results, duration_ms)
        warnings, errors = CopyEngineService._build_issues(results)
        report = CopyReport(
            execution_id=execution_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            success=summary.errors == 0,
            summary=summary,
            files=results,
            warnings=warnings,
            errors=errors,
            metadata={
                "destination_root": str(destination_root),
                "planned_files": len(request.execution_plan.physical_files),
            },
        )

        CopyEngineService._publish(
            event_bus,
            CopyEvent(
                event_type=CopyEventType.COPY_FINISHED,
                execution_id=execution_id,
                duration_ms=duration_ms,
                metadata={
                    "success": report.success,
                    "total_files": summary.total_files,
                    "copied": summary.copied,
                    "skipped": summary.skipped,
                    "missing": summary.missing,
                    "errors": summary.errors,
                    "total_bytes": summary.total_bytes,
                },
            ),
        )
        return report

    @staticmethod
    def _copy_file(
        physical_file: PhysicalFile,
        destination_root: Path,
        execution_id: UUID,
        event_bus: CopyEventBus | None,
    ) -> CopyFileResult:
        file_started_at = perf_counter()
        source = Path(physical_file.source_path)
        CopyEngineService._publish(
            event_bus,
            CopyEvent(
                event_type=CopyEventType.FILE_STARTED,
                execution_id=execution_id,
                source=str(source),
            ),
        )

        try:
            destination = CopyEngineService._safe_destination(
                destination_root,
                physical_file.relative_path,
            )
        except ValueError as exc:
            return CopyEngineService._finish_file(
                event_bus,
                execution_id,
                CopyFileResult(
                    source=str(source),
                    destination=str(destination_root),
                    status=CopyStatus.ERROR,
                    duration_ms=CopyEngineService._duration_ms(file_started_at),
                    error=str(exc),
                ),
            )

        if not physical_file.exists or not source.is_file():
            return CopyEngineService._missing_result(
                source,
                destination,
                file_started_at,
                execution_id,
                event_bus,
                "Source file does not exist.",
            )

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if CopyEngineService._is_identical(source, destination):
                result = CopyFileResult(
                    source=str(source),
                    destination=str(destination),
                    status=CopyStatus.SKIPPED,
                    size=source.stat().st_size,
                    duration_ms=CopyEngineService._duration_ms(file_started_at),
                )
            else:
                copy2(source, destination)
                source_size = source.stat().st_size
                destination_size = destination.stat().st_size
                if source_size != destination_size:
                    raise OSError(
                        "Copied file size does not match source file size."
                    )
                result = CopyFileResult(
                    source=str(source),
                    destination=str(destination),
                    status=CopyStatus.COPIED,
                    size=destination_size,
                    duration_ms=CopyEngineService._duration_ms(file_started_at),
                )
        except FileNotFoundError:
            return CopyEngineService._missing_result(
                source,
                destination,
                file_started_at,
                execution_id,
                event_bus,
                "Source file disappeared during backup.",
            )
        except PermissionError as exc:
            if CopyEngineService._is_tolerable_locked_file(
                physical_file,
                source,
            ):
                return CopyEngineService._missing_result(
                    source,
                    destination,
                    file_started_at,
                    execution_id,
                    event_bus,
                    f"Fichier de cache verrouillé ignoré : {exc}",
                )
            result = CopyFileResult(
                source=str(source),
                destination=str(destination),
                status=CopyStatus.ERROR,
                duration_ms=CopyEngineService._duration_ms(file_started_at),
                error=str(exc),
            )
        except OSError as exc:
            if CopyEngineService._is_unavailable_onedrive_placeholder(exc, source):
                return CopyEngineService._missing_result(
                    source,
                    destination,
                    file_started_at,
                    execution_id,
                    event_bus,
                    "Fichier OneDrive disponible uniquement dans le cloud ignoré "
                    f"(WinError 362) : {source}",
                )
            if CopyEngineService._is_unavailable_virtualbox_log(exc, source):
                return CopyEngineService._missing_result(
                    source,
                    destination,
                    file_started_at,
                    execution_id,
                    event_bus,
                    "Journal VirtualBox indisponible ignoré "
                    f"(WinError 433) : {source}",
                )
            result = CopyFileResult(
                source=str(source),
                destination=str(destination),
                status=CopyStatus.ERROR,
                duration_ms=CopyEngineService._duration_ms(file_started_at),
                error=str(exc),
            )

        return CopyEngineService._finish_file(
            event_bus,
            execution_id,
            result,
        )

    @classmethod
    def _is_tolerable_locked_file(
        cls,
        physical_file: PhysicalFile,
        source: Path,
    ) -> bool:
        if physical_file.potentially_locked:
            return True
        lowered_parts = {part.casefold() for part in source.parts}
        return bool(lowered_parts & cls.LOCKED_CACHE_DIRECTORIES)

    @staticmethod
    def _is_unavailable_onedrive_placeholder(exc: OSError, source: Path) -> bool:
        return (
            getattr(exc, "winerror", None) == 362
            and any(part.casefold() == "onedrive" for part in source.parts)
        )

    @staticmethod
    def _is_unavailable_virtualbox_log(exc: OSError, source: Path) -> bool:
        lowered_parts = [part.casefold() for part in source.parts]
        try:
            virtualbox_index = lowered_parts.index("virtualbox vms")
            logs_index = lowered_parts.index("logs", virtualbox_index + 1)
        except ValueError:
            return False
        return (
            getattr(exc, "winerror", None) == 433
            and logs_index > virtualbox_index
        )

    @staticmethod
    def _missing_result(
        source: Path,
        destination: Path,
        started_at: float,
        execution_id: UUID,
        event_bus: CopyEventBus | None,
        error: str,
    ) -> CopyFileResult:
        return CopyEngineService._finish_file(
            event_bus,
            execution_id,
            CopyFileResult(
                source=str(source),
                destination=str(destination),
                status=CopyStatus.MISSING,
                duration_ms=CopyEngineService._duration_ms(started_at),
                error=error,
            ),
        )

    @staticmethod
    def _finish_file(
        event_bus: CopyEventBus | None,
        execution_id: UUID,
        result: CopyFileResult,
    ) -> CopyFileResult:
        CopyEngineService._publish_file_event(
            event_bus,
            execution_id,
            result,
        )
        return result

    @staticmethod
    def _publish(
        event_bus: CopyEventBus | None,
        event: CopyEvent,
    ) -> None:
        if event_bus is not None:
            event_bus.publish(event)

    @staticmethod
    def _publish_file_event(
        event_bus: CopyEventBus | None,
        execution_id: UUID,
        result: CopyFileResult,
    ) -> None:
        event_types = {
            CopyStatus.COPIED: CopyEventType.FILE_COPIED,
            CopyStatus.SKIPPED: CopyEventType.FILE_SKIPPED,
            CopyStatus.MISSING: CopyEventType.FILE_MISSING,
            CopyStatus.ERROR: CopyEventType.FILE_ERROR,
        }
        CopyEngineService._publish(
            event_bus,
            CopyEvent(
                event_type=event_types[result.status],
                execution_id=execution_id,
                source=result.source,
                destination=result.destination,
                file_status=result.status,
                size=result.size,
                duration_ms=result.duration_ms,
                message=result.error,
            ),
        )

    @staticmethod
    def _safe_destination(
        destination_root: Path,
        relative_path: str,
    ) -> Path:
        candidate = (destination_root / relative_path).resolve()
        if not candidate.is_relative_to(destination_root):
            raise ValueError("Destination path escapes destination root.")
        return candidate

    @staticmethod
    def _is_identical(source: Path, destination: Path) -> bool:
        if not destination.is_file():
            return False
        return source.stat().st_size == destination.stat().st_size

    @staticmethod
    def _build_summary(
        results: list[CopyFileResult],
        duration_ms: int,
    ) -> CopySummary:
        return CopySummary(
            total_files=len(results),
            copied=sum(result.status == CopyStatus.COPIED for result in results),
            skipped=sum(result.status == CopyStatus.SKIPPED for result in results),
            missing=sum(result.status == CopyStatus.MISSING for result in results),
            errors=sum(result.status == CopyStatus.ERROR for result in results),
            total_bytes=sum(
                result.size
                for result in results
                if result.status == CopyStatus.COPIED
            ),
            duration_ms=duration_ms,
        )

    @staticmethod
    def _build_issues(
        results: list[CopyFileResult],
    ) -> tuple[list[CopyIssue], list[CopyIssue]]:
        warnings: list[CopyIssue] = []
        errors: list[CopyIssue] = []
        for result in results:
            if result.status == CopyStatus.MISSING:
                warnings.append(
                    CopyIssue(
                        severity=CopyIssueSeverity.WARNING,
                        code="source_missing",
                        message=result.error or "Source file is missing.",
                        source=result.source,
                        destination=result.destination,
                    )
                )
            elif result.status == CopyStatus.ERROR:
                errors.append(
                    CopyIssue(
                        severity=CopyIssueSeverity.ERROR,
                        code="copy_failed",
                        message=result.error or "File copy failed.",
                        source=result.source,
                        destination=result.destination,
                    )
                )
        return warnings, errors

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)
