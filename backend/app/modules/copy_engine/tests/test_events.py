from pathlib import Path
from uuid import uuid4

from app.modules.copy_engine.events import (
    CopyEvent,
    CopyEventBus,
    CopyEventType,
)
from app.modules.copy_engine.schemas import CopyRequest, CopyStatus
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)


def build_plan(source_root: Path, relative_paths: list[str]) -> ExecutionPlan:
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


def test_event_bus_subscribe_unsubscribe_and_order() -> None:
    bus = CopyEventBus()
    received: list[CopyEventType] = []

    def listener(event: CopyEvent) -> None:
        received.append(event.event_type)

    bus.subscribe(listener)
    identifier = uuid4()
    bus.publish(
        CopyEvent(
            event_type=CopyEventType.COPY_STARTED,
            execution_id=identifier,
        )
    )
    bus.publish(
        CopyEvent(
            event_type=CopyEventType.COPY_FINISHED,
            execution_id=identifier,
        )
    )
    bus.unsubscribe(listener)
    bus.publish(
        CopyEvent(
            event_type=CopyEventType.FILE_STARTED,
            execution_id=identifier,
        )
    )

    assert received == [
        CopyEventType.COPY_STARTED,
        CopyEventType.COPY_FINISHED,
    ]


def test_listener_failure_is_isolated() -> None:
    bus = CopyEventBus()
    received: list[CopyEventType] = []

    def failing_listener(event: CopyEvent) -> None:
        raise RuntimeError(event.event_type)

    bus.subscribe(failing_listener)
    bus.subscribe(lambda event: received.append(event.event_type))
    bus.publish(
        CopyEvent(
            event_type=CopyEventType.COPY_STARTED,
            execution_id=uuid4(),
        )
    )

    assert received == [CopyEventType.COPY_STARTED]
    assert len(bus.listener_errors) == 1


def test_copy_engine_publishes_coherent_events(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "copy.txt").write_text("copy", encoding="utf-8")
    (source_root / "skip.txt").write_text("same", encoding="utf-8")
    (destination_root / "skip.txt").write_text("same", encoding="utf-8")

    events: list[CopyEvent] = []
    bus = CopyEventBus()
    bus.subscribe(events.append)
    report = CopyEngineService.execute(
        CopyRequest(
            execution_plan=build_plan(
                source_root,
                ["copy.txt", "skip.txt", "missing.txt"],
            ),
            destination_root=str(destination_root),
        ),
        event_bus=bus,
    )

    assert [event.event_type for event in events] == [
        CopyEventType.COPY_STARTED,
        CopyEventType.FILE_STARTED,
        CopyEventType.FILE_COPIED,
        CopyEventType.FILE_STARTED,
        CopyEventType.FILE_SKIPPED,
        CopyEventType.FILE_STARTED,
        CopyEventType.FILE_MISSING,
        CopyEventType.COPY_FINISHED,
    ]
    assert all(event.execution_id == report.execution_id for event in events)
    terminal = [
        event
        for event in events
        if event.event_type
        in {
            CopyEventType.FILE_COPIED,
            CopyEventType.FILE_SKIPPED,
            CopyEventType.FILE_MISSING,
            CopyEventType.FILE_ERROR,
        }
    ]
    assert [event.file_status for event in terminal] == [
        CopyStatus.COPIED,
        CopyStatus.SKIPPED,
        CopyStatus.MISSING,
    ]
    finished = events[-1]
    assert finished.metadata["success"] is report.success
    assert finished.metadata["total_files"] == report.summary.total_files
    assert finished.metadata["copied"] == report.summary.copied
    assert finished.metadata["skipped"] == report.summary.skipped
    assert finished.metadata["missing"] == report.summary.missing
    assert finished.metadata["errors"] == report.summary.errors
    assert finished.metadata["total_bytes"] == report.summary.total_bytes


def test_listener_failure_does_not_change_copy_result(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    source_file = source_root / "data.txt"
    source_file.write_text("content", encoding="utf-8")
    bus = CopyEventBus()

    def failing_listener(event: CopyEvent) -> None:
        raise RuntimeError(event.event_type)

    bus.subscribe(failing_listener)
    report = CopyEngineService.execute(
        CopyRequest(
            execution_plan=build_plan(source_root, ["data.txt"]),
            destination_root=str(destination_root),
        ),
        event_bus=bus,
    )

    assert report.success is True
    assert report.summary.copied == 1
    assert (destination_root / "data.txt").read_text(
        encoding="utf-8"
    ) == "content"
    assert len(bus.listener_errors) == 4
