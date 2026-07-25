from pathlib import Path

from app.modules.backup_retention.schemas import RetentionDecision

from .schemas import (
    RetentionExecutionReport,
    RetentionExecutionRequest,
    RetentionExecutionSummary,
    RetentionFileResult,
)


class BackupRetentionExecutorService:
    CONFIRMATION = "SUPPRIMER LES SAUVEGARDES SÉLECTIONNÉES"

    @classmethod
    def execute(cls, request: RetentionExecutionRequest) -> RetentionExecutionReport:
        candidates = [
            item
            for item in request.simulation.decisions
            if item.decision == RetentionDecision.DELETE
        ]
        if request.confirmation != cls.CONFIRMATION:
            return cls._report(
                candidates,
                [],
                confirmed=False,
                error="Exact deletion confirmation is required.",
            )

        results: list[RetentionFileResult] = []
        for candidate in candidates:
            path = Path(candidate.path)
            try:
                if path.suffix.lower() not in {".fsb", ".fsbe"}:
                    raise ValueError("Only FSBackup archives can be deleted.")
                if not path.is_file():
                    raise FileNotFoundError("Archive does not exist.")
                actual_size = path.stat().st_size
                path.unlink()
                results.append(
                    RetentionFileResult(
                        path=str(path),
                        deleted=True,
                        size_bytes=actual_size,
                    )
                )
            except (OSError, ValueError) as exc:
                results.append(
                    RetentionFileResult(
                        path=str(path),
                        deleted=False,
                        size_bytes=candidate.size_bytes,
                        error=str(exc),
                    )
                )
        return cls._report(candidates, results, confirmed=True)

    @staticmethod
    def _report(candidates, results, confirmed, error=None) -> RetentionExecutionReport:
        deleted = sum(item.deleted for item in results)
        failed = sum(not item.deleted for item in results)
        return RetentionExecutionReport(
            success=confirmed and failed == 0,
            confirmed=confirmed,
            files=results,
            summary=RetentionExecutionSummary(
                requested=len(candidates),
                deleted=deleted,
                failed=failed,
                reclaimed_bytes=sum(
                    item.size_bytes for item in results if item.deleted
                ),
            ),
            error=error,
        )
