from datetime import UTC, datetime, timedelta

from app.modules.backup_catalog.schemas import BackupArchiveStatus

from .schemas import (
    RetentionArchiveDecision,
    RetentionDecision,
    RetentionSimulationReport,
    RetentionSimulationRequest,
    RetentionSimulationSummary,
)


class BackupRetentionService:
    @staticmethod
    def simulate(request: RetentionSimulationRequest) -> RetentionSimulationReport:
        archives = request.catalog.archives
        valid = [item for item in archives if item.status == BackupArchiveStatus.VALID]
        valid.sort(key=lambda item: item.created_at or item.modified_at, reverse=True)
        keep_paths: dict[str, str] = {}

        for item in valid[: request.policy.keep_last]:
            keep_paths[item.path] = "Parmi les sauvegardes les plus récentes."

        now = datetime.now(UTC)
        BackupRetentionService._keep_bucketed(
            valid,
            keep_paths,
            now - timedelta(days=request.policy.keep_daily_days),
            lambda value: value.date().isoformat(),
            "Point de conservation quotidien.",
        )
        BackupRetentionService._keep_bucketed(
            valid,
            keep_paths,
            now - timedelta(weeks=request.policy.keep_weekly_weeks),
            lambda value: f"{value.isocalendar().year}-W{value.isocalendar().week:02d}",
            "Point de conservation hebdomadaire.",
        )
        month_limit = BackupRetentionService._subtract_months(
            now, request.policy.keep_monthly_months
        )
        BackupRetentionService._keep_bucketed(
            valid,
            keep_paths,
            month_limit,
            lambda value: f"{value.year:04d}-{value.month:02d}",
            "Point de conservation mensuel.",
        )

        decisions: list[RetentionArchiveDecision] = []
        for item in archives:
            if item.backup_set:
                decision = RetentionDecision.PROTECT
                reason = (
                    "Les jeux fractionnés sont protégés contre une suppression "
                    "partielle."
                )
            elif item.status != BackupArchiveStatus.VALID:
                decision = RetentionDecision.PROTECT
                reason = "Cette archive ne peut pas être évaluée en toute sécurité."
            elif item.path in keep_paths:
                decision = RetentionDecision.KEEP
                reason = keep_paths[item.path]
            else:
                decision = RetentionDecision.DELETE
                reason = "En dehors des périodes de conservation configurées."
            decisions.append(
                RetentionArchiveDecision(
                    path=item.path,
                    name=item.name,
                    decision=decision,
                    reason=reason,
                    size_bytes=item.size_bytes,
                )
            )

        return RetentionSimulationReport(
            decisions=decisions,
            summary=RetentionSimulationSummary(
                total=len(decisions),
                keep=sum(item.decision == RetentionDecision.KEEP for item in decisions),
                delete=sum(item.decision == RetentionDecision.DELETE for item in decisions),
                protect=sum(
                    item.decision == RetentionDecision.PROTECT for item in decisions
                ),
                reclaimable_bytes=sum(
                    item.size_bytes
                    for item in decisions
                    if item.decision == RetentionDecision.DELETE
                ),
            ),
        )

    @staticmethod
    def _keep_bucketed(archives, keep_paths, lower_bound, bucket_key, reason) -> None:
        seen: set[str] = set()
        for item in archives:
            created_at = item.created_at or item.modified_at
            if created_at < lower_bound:
                continue
            bucket = bucket_key(created_at)
            if bucket in seen:
                continue
            seen.add(bucket)
            keep_paths.setdefault(item.path, reason)

    @staticmethod
    def _subtract_months(value: datetime, months: int) -> datetime:
        total = value.year * 12 + value.month - 1 - months
        year, month_index = divmod(total, 12)
        return value.replace(year=year, month=month_index + 1, day=1)
