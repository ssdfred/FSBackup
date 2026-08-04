from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)

from .schemas import BackupSegment, BackupSegmentStatus, BackupSetManifest


class BackupSetService:
    @staticmethod
    def directory(destination_directory: str, archive_name: str) -> Path:
        normalized_name = Path(archive_name).stem.strip()
        if not normalized_name:
            raise ValueError("Backup-set name cannot be empty.")
        return Path(destination_directory).resolve() / normalized_name

    @classmethod
    def split_plan(
        cls,
        execution_plan: ExecutionPlan,
        segment_size_bytes: int,
    ) -> list[ExecutionPlan]:
        if segment_size_bytes < 1:
            raise ValueError("Segment size must be greater than zero.")

        ordered_files = sorted(
            execution_plan.physical_files,
            key=lambda item: item.relative_path.casefold(),
        )
        groups: list[list[PhysicalFile]] = []
        current: list[PhysicalFile] = []
        current_size = 0
        for physical_file in ordered_files:
            if current and current_size + physical_file.size_bytes > segment_size_bytes:
                groups.append(current)
                current = []
                current_size = 0
            current.append(physical_file)
            current_size += physical_file.size_bytes
        if current or not groups:
            groups.append(current)

        return [cls._segment_plan(execution_plan, files) for files in groups]

    @staticmethod
    def prepare_manifest(
        existing: BackupSetManifest | None,
        archive_name: str,
        source_root: str,
        segment_size_bytes: int,
        encrypted: bool,
        plans: list[ExecutionPlan],
    ) -> BackupSetManifest:
        now = datetime.now(UTC)
        base_name = Path(archive_name).stem
        previous_segments = {
            segment.index: segment
            for segment in existing.segments
        } if existing is not None else {}
        segments: list[BackupSegment] = []
        suffix = ".fsbe" if encrypted else ".fsb"
        for index, plan in enumerate(plans, start=1):
            fingerprint = BackupSetService.plan_fingerprint(plan)
            previous = previous_segments.get(index)
            if previous is not None and previous.plan_fingerprint == fingerprint:
                segments.append(previous)
                continue
            segments.append(
                BackupSegment(
                    index=index,
                    name=f"Lot {index} sur {len(plans)}",
                    archive_name=f"{base_name}-part-{index:04d}{suffix}",
                    plan_fingerprint=fingerprint,
                    file_count=len(plan.physical_files),
                    size_bytes=sum(item.size_bytes for item in plan.physical_files),
                )
            )

        return BackupSetManifest(
            backup_set_id=(existing.backup_set_id if existing else str(uuid4())),
            archive_name=base_name,
            source_root=source_root,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            segment_size_bytes=segment_size_bytes,
            encrypted=encrypted,
            complete=bool(segments) and all(
                segment.status == BackupSegmentStatus.COMPLETED
                for segment in segments
            ),
            segments=segments,
            warnings=list(existing.warnings) if existing else [],
        )

    @staticmethod
    def validate_existing(
        manifest: BackupSetManifest,
        source_root: str,
        encrypted: bool,
    ) -> None:
        if Path(manifest.source_root).resolve() != Path(source_root).resolve():
            raise ValueError("Existing backup set belongs to another source.")
        if manifest.encrypted != encrypted:
            raise ValueError("Existing backup set uses different encryption settings.")

    @staticmethod
    def plan_fingerprint(execution_plan: ExecutionPlan) -> str:
        digest = sha256()
        for physical_file in execution_plan.physical_files:
            digest.update(physical_file.relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(physical_file.size_bytes).encode("ascii"))
            digest.update(b"\n")
        return digest.hexdigest()

    @staticmethod
    def file_sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _segment_plan(
        execution_plan: ExecutionPlan,
        files: list[PhysicalFile],
    ) -> ExecutionPlan:
        sources = {item.source_path for item in files}
        items = [
            item.model_copy(
                update={
                    "files": [path for path in item.files if path in sources],
                }
            )
            for item in execution_plan.items
            if any(path in sources for path in item.files)
        ]
        summary = ExecutionPlanSummary(
            logical_items=len(items),
            physical_files=len(files),
            missing_files=sum(not item.exists for item in files),
            encrypted_items=sum(item.encrypted for item in items),
            estimated_size_bytes=sum(item.size_bytes for item in files),
            deduplicated_files=0,
            warnings=sum(len(item.warnings) for item in files),
        )
        return execution_plan.model_copy(
            update={
                "items": items,
                "physical_files": files,
                "summary": summary,
            }
        )
