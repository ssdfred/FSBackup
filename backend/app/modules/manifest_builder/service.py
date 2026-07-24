from datetime import UTC, datetime

from app.modules.execution_planner.schemas import ExecutionPlan

from .schemas import (
    Manifest,
    ManifestFile,
    ManifestSummary,
)

class ManifestBuilderService:
    @staticmethod
    def build(plan: ExecutionPlan) -> Manifest:
        ...
        summary = ManifestSummary(
    logical_items=plan.logical_items,
    physical_files=plan.physical_files,
    missing_files=plan.missing_files,
    encrypted_items=plan.encrypted_items,
    deduplicated_files=plan.deduplicated_files,
    estimated_size_bytes=plan.estimated_size_bytes,
    warnings=plan.warnings,
)
        files = [
    ManifestFile(
        relative_path=file.relative_path,
        size=file.size,
        mandatory=file.mandatory,
        potentially_locked=file.potentially_locked,
        required_by=file.required_by,
    )
    for file in plan.files
]
        return Manifest(
    created_at=datetime.now(UTC),
    source_root=plan.source_root,
    summary=summary,
    files=files,
)