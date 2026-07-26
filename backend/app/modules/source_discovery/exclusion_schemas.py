"""Schemas for read-only backup exclusion suggestions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ExclusionRisk(StrEnum):
    LOW = "faible"
    MEDIUM = "moyen"
    HIGH = "élevé"


class ExclusionCategory(StrEnum):
    RECREATABLE = "généralement_recréable"
    REVIEW = "à_examiner"
    SENSITIVE = "sensible"


class ExclusionSuggestion(BaseModel):
    path: str
    pattern: str
    category: ExclusionCategory
    size_bytes: int = 0
    file_count: int = 0
    reason: str
    risk: ExclusionRisk
    selected: bool = False
    prerequisites: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExclusionSuggestionRequest(BaseModel):
    source_root: str = Field(min_length=1)


class ExclusionSuggestionReport(BaseModel):
    source_root: str
    suggestions: list[ExclusionSuggestion] = Field(default_factory=list)
    total_suggested_size_bytes: int = 0
    total_suggested_file_count: int = 0
    selected_size_bytes: int = 0
    estimated_size_after_exclusions_bytes: int | None = None
    warnings: list[str] = Field(default_factory=list)
