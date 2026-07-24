from pathlib import Path
from shutil import copy2
from time import perf_counter

from .schemas import (
    CopyFileResult,
    CopyReport,
    CopyRequest,
    CopyStatus,
    CopySummary,
)


class CopyEngineService:
    @staticmethod
    def execute(request: CopyRequest) -> CopyReport:
        execution_started_at = perf_counter()

        source_root = Path(request.manifest.source_root)
        destination_root = Path(request.destination_root)

        results: list[CopyFileResult] = []

        for manifest_file in request.manifest.files:
            file_started_at = perf_counter()

            relative_path = Path(manifest_file.relative_path)
            source = source_root / relative_path
            destination = destination_root / relative_path

            if not source.is_file():
                results.append(
                    CopyFileResult(
                        source=str(source),
                        destination=str(destination),
                        status=CopyStatus.MISSING,
                        duration_ms=CopyEngineService._duration_ms(
                            file_started_at
                        ),
                        error="Source file does not exist.",
                    )
                )
                continue

            try:
                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                if CopyEngineService._is_identical(
                    source=source,
                    destination=destination,
                ):
                    results.append(
                        CopyFileResult(
                            source=str(source),
                            destination=str(destination),
                            status=CopyStatus.SKIPPED,
                            size=source.stat().st_size,
                            duration_ms=CopyEngineService._duration_ms(
                                file_started_at
                            ),
                        )
                    )
                    continue

                copy2(source, destination)

                source_size = source.stat().st_size
                destination_size = destination.stat().st_size

                if source_size != destination_size:
                    raise OSError(
                        "Copied file size does not match source file size."
                    )

                results.append(
                    CopyFileResult(
                        source=str(source),
                        destination=str(destination),
                        status=CopyStatus.COPIED,
                        size=destination_size,
                        duration_ms=CopyEngineService._duration_ms(
                            file_started_at
                        ),
                    )
                )

            except OSError as exc:
                results.append(
                    CopyFileResult(
                        source=str(source),
                        destination=str(destination),
                        status=CopyStatus.ERROR,
                        duration_ms=CopyEngineService._duration_ms(
                            file_started_at
                        ),
                        error=str(exc),
                    )
                )

        return CopyReport(
            summary=CopyEngineService._build_summary(
                results=results,
                duration_ms=CopyEngineService._duration_ms(
                    execution_started_at
                ),
            ),
            files=results,
        )

    @staticmethod
    def _is_identical(
        source: Path,
        destination: Path,
    ) -> bool:
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
                result.status == CopyStatus.COPIED
                for result in results
            ),
            skipped=sum(
                result.status == CopyStatus.SKIPPED
                for result in results
            ),
            missing=sum(
                result.status == CopyStatus.MISSING
                for result in results
            ),
            errors=sum(
                result.status == CopyStatus.ERROR
                for result in results
            ),
            total_bytes=sum(
                result.size
                for result in results
                if result.status == CopyStatus.COPIED
            ),
            duration_ms=duration_ms,
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)