"""Pydantic schemas for physical backup execution planning."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExecutionPlanRequest(BaseModel):
    """Request used to generate a physical execution plan."""

    source_root: str = Field(
        ...,
        min_length=1,
        examples=["E:\\"],
        description="Root of the Windows disk to inspect.",
    )
    selected_item_ids: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of logical backup item identifiers to resolve."
        ),
    )


class PhysicalFile(BaseModel):
    """A unique physical file required by one or more logical items."""

    source_path: str
    relative_path: str
    size_bytes: int = Field(default=0, ge=0)
    required_by: list[str] = Field(default_factory=list)
    mandatory: bool = False
    exists: bool = True
    potentially_locked: bool = False
    warnings: list[str] = Field(default_factory=list)


class ExecutionItem(BaseModel):
    """Resolution of one logical item into physical files."""

    logical_id: str
    category: str
    application_key: str
    application_name: str
    user_name: str
    profile_name: str
    encrypted: bool = False
    files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExecutionPlanSummary(BaseModel):
    """Aggregated statistics for an execution plan."""

    logical_items: int = Field(default=0, ge=0)
    physical_files: int = Field(default=0, ge=0)
    missing_files: int = Field(default=0, ge=0)
    encrypted_items: int = Field(default=0, ge=0)
    estimated_size_bytes: int = Field(default=0, ge=0)
    deduplicated_files: int = Field(default=0, ge=0)
    warnings: int = Field(default=0, ge=0)


class ExecutionPlan(BaseModel):
    """Complete physical execution plan."""

    source_root: str
    items: list[ExecutionItem] = Field(default_factory=list)
    physical_files: list[PhysicalFile] = Field(default_factory=list)
    summary: ExecutionPlanSummary
    warnings: list[str] = Field(default_factory=list)