from pathlib import Path

from app.modules.backup_retention.schemas import (
    RetentionArchiveDecision,
    RetentionDecision,
    RetentionSimulationReport,
    RetentionSimulationSummary,
)
from app.modules.backup_retention_executor.schemas import RetentionExecutionRequest
from app.modules.backup_retention_executor.service import BackupRetentionExecutorService


def build_simulation(path: Path) -> RetentionSimulationReport:
    return RetentionSimulationReport(
        decisions=[
            RetentionArchiveDecision(
                path=str(path),
                name=path.name,
                decision=RetentionDecision.DELETE,
                reason="Outside retention windows.",
                size_bytes=path.stat().st_size,
            )
        ],
        summary=RetentionSimulationSummary(
            total=1,
            keep=0,
            delete=1,
            protect=0,
            reclaimable_bytes=path.stat().st_size,
        ),
    )


def test_execute_requires_exact_confirmation(tmp_path: Path) -> None:
    archive = tmp_path / "backup.fsb"
    archive.write_bytes(b"archive")

    report = BackupRetentionExecutorService.execute(
        RetentionExecutionRequest(
            simulation=build_simulation(archive),
            confirmation="non",
        )
    )

    assert report.success is False
    assert report.confirmed is False
    assert archive.exists() is True


def test_execute_deletes_only_confirmed_archive(tmp_path: Path) -> None:
    archive = tmp_path / "backup.fsb"
    archive.write_bytes(b"archive")

    report = BackupRetentionExecutorService.execute(
        RetentionExecutionRequest(
            simulation=build_simulation(archive),
            confirmation=BackupRetentionExecutorService.CONFIRMATION,
        )
    )

    assert report.success is True
    assert report.summary.deleted == 1
    assert report.summary.reclaimed_bytes == 7
    assert archive.exists() is False
