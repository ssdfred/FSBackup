from datetime import UTC, datetime
from pathlib import Path
from shutil import copy2
from time import perf_counter
from uuid import UUID, uuid4

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
                    destination_root=destination_root,
                    relative_path=physical_file.relative_path,
                )
            except ValueError as exc:
                result = CopyFileResult(
                    source=str(source),
                    destination=str(destination_root),
                    status=CopyStatus.ERROR,
                    duration_ms=CopyEngineService._duration_ms(file_started_at),
                    error=str(exc),
                )
                results.append(result)
                CopyEngineService._publish_file_event(
                    event_bus,
                    execution_id,
                    result,
                )
                continue

            if not physical_file.exists or not source.is_file():
                result = CopyFileResult(
                    source=str(source),
                    destination=str(destination),
                    status=CopyStatus.MISSING,
                    duration_ms=CopyEngineService._duration_ms(file_started_at),
                    error="Source file does not exist.",
                )
                results.append(result)
                CopyEngineService._publish_file_event(
                    event_bus,
                    execution_id,
                    result,
                )
                continue

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
                    results.append(result)
                    CopyEngineService._publish_file_event(
                        event_bus,
                        execution_id,
                        result,
                    )
                    continue

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
                results.append(result)
                CopyEngineService._publish_file_event(
                    event_bus,
                    execution_id,
                    result,
                )
            except OSError as exc:
                result = CopyFileResult(
                    source=str(source),
                    destination=str(destination),
                    status=CopyStatus.ERROR,
                    duration_ms=CopyEngineService._duration_ms(file_started_at),
                    error=str(exc),
                )
                results.append(result)
                CopyEngineService._publish_file_event(
                    event_bus,
                    execution_id,
                    result,
                )

        duration_ms = CopyEngineService._duration_ms(execution_started_at)
        finished_at = datetime.now(UTC)
        summary = CopyEngineService._build_summary(results, duration_ms)
        warnings, errors = CopyEngineService._build_issues(results)
        report = CopyReport(
            execution_id=execution_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            success=summary.missing == 0 and summary.errors == 0,
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
            copied=sum(
                result.status == CopyStatus.COPIED for result in results
            ),
            skipped=sum(
                result.status == CopyStatus.SKIPPED for result in results
            ),
            missing=sum(
                result.status == CopyStatus.MISSING for result in results
            ),
            errors=sum(
                result.status == CopyStatus.ERROR for result in results
            ),
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
