from datetime import UTC, datetime, timedelta

from app.modules.backup_catalog.schemas import (
    BackupArchiveEntry,
    BackupArchiveStatus,
    BackupCatalogReport,
    BackupCatalogSummary,
)
from app.modules.backup_retention.schemas import (
    RetentionDecision,
    RetentionPolicy,
    RetentionSimulationRequest,
)
from app.modules.backup_retention.service import BackupRetentionService


def archive(name: str, age_days: int, status=BackupArchiveStatus.VALID):
    created_at = datetime.now(UTC) - timedelta(days=age_days)
    return BackupArchiveEntry(
        path=f"/archives/{name}",
        name=name,
        encrypted=False,
        size_bytes=100,
        modified_at=created_at,
        status=status,
        created_at=created_at if status == BackupArchiveStatus.VALID else None,
    )


def catalog(entries):
    return BackupCatalogReport(
        directory="/archives",
        archives=entries,
        summary=BackupCatalogSummary(
            total=len(entries),
            valid=sum(item.status == BackupArchiveStatus.VALID for item in entries),
            invalid=sum(item.status == BackupArchiveStatus.INVALID for item in entries),
            password_required=sum(
                item.status == BackupArchiveStatus.PASSWORD_REQUIRED for item in entries
            ),
            encrypted=0,
            total_size_bytes=sum(item.size_bytes for item in entries),
        ),
    )


def test_simulation_keeps_recent_and_marks_old_for_deletion() -> None:
    entries = [archive("recent.fsb", 0), archive("old.fsb", 400)]
    report = BackupRetentionService.simulate(
        RetentionSimulationRequest(
            catalog=catalog(entries),
            policy=RetentionPolicy(
                keep_last=1,
                keep_daily_days=0,
                keep_weekly_weeks=0,
                keep_monthly_months=0,
            ),
        )
    )

    assert report.simulated is True
    assert report.summary.keep == 1
    assert report.summary.delete == 1
    assert report.summary.reclaimable_bytes == 100
    assert report.decisions[0].decision == RetentionDecision.KEEP
    assert report.decisions[1].decision == RetentionDecision.DELETE


def test_simulation_protects_archives_that_cannot_be_evaluated() -> None:
    entries = [archive("broken.fsb", 0, BackupArchiveStatus.INVALID)]
    report = BackupRetentionService.simulate(
        RetentionSimulationRequest(catalog=catalog(entries))
    )

    assert report.summary.protect == 1
    assert report.summary.delete == 0
    assert report.decisions[0].decision == RetentionDecision.PROTECT
