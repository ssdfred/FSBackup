from pathlib import Path

import pytest

from app.modules.backup_orchestrator.schemas import ApprovedExclusion, BackupRunRequest
from app.modules.backup_orchestrator.service import BackupOrchestratorService
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)
from app.modules.manifest_builder.schemas import ManifestExclusion
from app.modules.manifest_builder.service import ManifestBuilderService


def _plan(root: Path) -> ExecutionPlan:
    included = root / "Documents" / "important.txt"
    excluded = root / "project" / "node_modules" / "package.js"
    included.parent.mkdir(parents=True)
    excluded.parent.mkdir(parents=True)
    included.write_text("important", encoding="utf-8")
    excluded.write_text("dependency", encoding="utf-8")
    files = [
        PhysicalFile(
            source_path=str(included),
            relative_path="Documents/important.txt",
            size_bytes=included.stat().st_size,
        ),
        PhysicalFile(
            source_path=str(excluded),
            relative_path="project/node_modules/package.js",
            size_bytes=excluded.stat().st_size,
        ),
    ]
    return ExecutionPlan(
        source_root=str(root),
        physical_files=files,
        summary=ExecutionPlanSummary(
            physical_files=2,
            estimated_size_bytes=sum(item.size_bytes for item in files),
        ),
    )


def _request(root: Path, *, confirmed: bool) -> BackupRunRequest:
    return BackupRunRequest(
        source_root=str(root),
        destination_directory=str(root / "backup"),
        archive_name="test",
        exclusions_confirmed=confirmed,
        approved_exclusions=[
            ApprovedExclusion(
                path=str(root / "project" / "node_modules"),
                reason="Dépendances Node.js recréables",
                risk="faible",
            )
        ],
    )


def test_exclusions_require_separate_confirmation(tmp_path):
    plan = _plan(tmp_path)

    with pytest.raises(ValueError, match="confirmées explicitement"):
        BackupOrchestratorService._apply_exclusions(
            plan,
            _request(tmp_path, confirmed=False),
        )


def test_confirmed_exclusion_filters_only_matching_files(tmp_path):
    plan = _plan(tmp_path)

    filtered, excluded_files, excluded_size = BackupOrchestratorService._apply_exclusions(
        plan,
        _request(tmp_path, confirmed=True),
    )

    assert excluded_files == 1
    assert excluded_size == len("dependency")
    assert [item.relative_path for item in filtered.physical_files] == [
        "Documents/important.txt"
    ]
    assert filtered.summary.physical_files == 1


def test_exclusion_outside_source_is_rejected(tmp_path):
    plan = _plan(tmp_path)
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    request = _request(tmp_path, confirmed=True)
    request.approved_exclusions[0].path = str(outside)

    with pytest.raises(ValueError, match="hors de la source"):
        BackupOrchestratorService._apply_exclusions(plan, request)


def test_manifest_records_user_approved_exclusions(tmp_path):
    plan = _plan(tmp_path)
    exclusion = ManifestExclusion(
        path=str(tmp_path / "project" / "node_modules"),
        reason="Dépendances Node.js recréables",
        risk="faible",
        approved_by_user=True,
    )

    manifest = ManifestBuilderService().build(plan, [exclusion])

    assert manifest.exclusions == [exclusion]
    assert manifest.exclusions[0].approved_by_user is True
