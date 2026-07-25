from pathlib import Path

from app.modules.copy_engine.schemas import CopyRequest, CopyStatus
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)


def build_plan(
    source_root: Path,
    relative_paths: list[str],
) -> ExecutionPlan:
    files = [
        PhysicalFile(
            source_path=str(source_root / relative_path),
            relative_path=relative_path,
            size_bytes=(source_root / relative_path).stat().st_size
            if (source_root / relative_path).is_file()
            else 0,
            required_by=["test.item"],
            mandatory=True,
            exists=(source_root / relative_path).is_file(),
        )
        for relative_path in relative_paths
    ]

    return ExecutionPlan(
        source_root=str(source_root),
        physical_files=files,
        summary=ExecutionPlanSummary(
            logical_items=1,
            physical_files=len(files),
            missing_files=sum(not file.exists for file in files),
            encrypted_items=0,
            estimated_size_bytes=sum(file.size_bytes for file in files),
            deduplicated_files=0,
            warnings=0,
        ),
    )


def execute_plan(plan: ExecutionPlan, destination_root: Path):
    return CopyEngineService.execute(
        CopyRequest(
            execution_plan=plan,
            destination_root=str(destination_root),
        )
    )


def test_execute_copies_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_file = source_root / "profile" / "Preferences"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("settings", encoding="utf-8")

    report = execute_plan(
        build_plan(source_root, ["profile/Preferences"]),
        destination_root,
    )

    copied_file = destination_root / "profile" / "Preferences"
    assert copied_file.read_text(encoding="utf-8") == "settings"
    assert report.summary.total_files == 1
    assert report.summary.copied == 1
    assert report.summary.errors == 0
    assert report.files[0].status == CopyStatus.COPIED


def test_execute_reports_missing_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"

    report = execute_plan(
        build_plan(source_root, ["missing.txt"]),
        destination_root,
    )

    assert report.summary.total_files == 1
    assert report.summary.missing == 1
    assert report.summary.copied == 0
    assert report.files[0].status == CopyStatus.MISSING


def test_execute_skips_existing_file_with_same_size(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "data.txt").write_text("same", encoding="utf-8")
    (destination_root / "data.txt").write_text("same", encoding="utf-8")

    report = execute_plan(
        build_plan(source_root, ["data.txt"]),
        destination_root,
    )

    assert report.summary.skipped == 1
    assert report.summary.copied == 0
    assert report.files[0].status == CopyStatus.SKIPPED


def test_execute_continues_after_missing_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    (source_root / "existing.txt").write_text("content", encoding="utf-8")

    report = execute_plan(
        build_plan(source_root, ["missing.txt", "existing.txt"]),
        destination_root,
    )

    assert report.summary.total_files == 2
    assert report.summary.missing == 1
    assert report.summary.copied == 1
    assert (destination_root / "existing.txt").read_text(
        encoding="utf-8"
    ) == "content"


def test_execute_rejects_path_outside_destination(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    source_file = source_root / "secret.txt"
    source_file.write_text("secret", encoding="utf-8")

    plan = ExecutionPlan(
        source_root=str(source_root),
        physical_files=[
            PhysicalFile(
                source_path=str(source_file),
                relative_path="../secret.txt",
                size_bytes=source_file.stat().st_size,
            )
        ],
        summary=ExecutionPlanSummary(
            logical_items=1,
            physical_files=1,
            missing_files=0,
            encrypted_items=0,
            estimated_size_bytes=source_file.stat().st_size,
            deduplicated_files=0,
            warnings=0,
        ),
    )

    report = execute_plan(plan, destination_root)

    assert report.summary.errors == 1
    assert report.files[0].status == CopyStatus.ERROR
    assert not (tmp_path / "secret.txt").exists()
