from pathlib import Path

import pytest

from app.modules.backup_set.service import BackupSetService
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)


def build_plan(source_root: Path, sizes: list[int]) -> ExecutionPlan:
    files = [
        PhysicalFile(
            source_path=str(source_root / f"file-{index}.bin"),
            relative_path=f"file-{index}.bin",
            size_bytes=size,
        )
        for index, size in enumerate(sizes, start=1)
    ]
    return ExecutionPlan(
        source_root=str(source_root),
        physical_files=files,
        summary=ExecutionPlanSummary(
            physical_files=len(files),
            estimated_size_bytes=sum(sizes),
        ),
    )


def test_split_plan_respects_maximum_size_between_files(tmp_path: Path) -> None:
    segments = BackupSetService.split_plan(build_plan(tmp_path, [4, 4, 2]), 6)

    assert [len(segment.physical_files) for segment in segments] == [1, 2]
    assert [segment.summary.estimated_size_bytes for segment in segments] == [4, 6]


def test_split_plan_keeps_oversized_file_in_autonomous_segment(tmp_path: Path) -> None:
    segments = BackupSetService.split_plan(build_plan(tmp_path, [10, 2]), 5)

    assert [segment.summary.estimated_size_bytes for segment in segments] == [10, 2]


def test_split_plan_rejects_invalid_size(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        BackupSetService.split_plan(build_plan(tmp_path, [1]), 0)
