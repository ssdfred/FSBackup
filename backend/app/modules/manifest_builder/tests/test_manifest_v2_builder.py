"""Tests for Manifest V2 generation from execution plans."""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.execution_planner.schemas import (
    ExecutionItem,
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)
from app.modules.manifest_builder.service import ManifestV2Builder


NOW = datetime(2026, 7, 24, 16, 0, tzinfo=UTC)


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        source_root="E:/",
        items=[
            ExecutionItem(
                logical_id="chrome.default.bookmarks",
                category="bookmarks",
                application_key="chrome",
                application_name="Google Chrome",
                user_name="Fred",
                profile_name="Default",
                files=["E:/Users/Fred/Bookmarks"],
            ),
            ExecutionItem(
                logical_id="chrome.profile-1.passwords",
                category="passwords",
                application_key="chrome",
                application_name="Google Chrome",
                user_name="Fred",
                profile_name="Profile 1",
                encrypted=True,
                files=["E:/Users/Fred/Login Data"],
            ),
        ],
        physical_files=[
            PhysicalFile(
                source_path="E:/Users/Fred/Z.txt",
                relative_path="Users/Fred/Z.txt",
                size_bytes=12,
                required_by=["chrome.default.bookmarks"],
                mandatory=True,
            ),
            PhysicalFile(
                source_path="E:/Users/Fred/a.txt",
                relative_path="Users\\Fred\\a.txt",
                size_bytes=8,
                required_by=["chrome.profile-1.passwords"],
                mandatory=True,
                potentially_locked=True,
            ),
            PhysicalFile(
                source_path="E:/Users/Fred/missing.txt",
                relative_path="Users/Fred/missing.txt",
                exists=False,
                mandatory=True,
            ),
        ],
        summary=ExecutionPlanSummary(
            logical_items=2,
            physical_files=3,
            missing_files=1,
            encrypted_items=1,
            estimated_size_bytes=20,
            warnings=1,
        ),
        warnings=["Fichier obligatoire absent", "Fichier obligatoire absent"],
    )


def test_builder_creates_versioned_execution_contract() -> None:
    identifiers = iter(["manifest-001", "execution-001"])
    builder = ManifestV2Builder(
        application_version="0.2.0",
        clock=lambda: NOW,
        identifier_factory=lambda: next(identifiers),
    )

    manifest = builder.build(_plan())

    assert manifest.header.format_version == 2
    assert manifest.header.manifest_id == "manifest-001"
    assert manifest.header.created_at == NOW
    assert manifest.header.application_version == "0.2.0"
    assert manifest.execution.execution_id == "execution-001"
    assert manifest.execution.started_at == NOW
    assert manifest.execution.status == "planned"
    assert manifest.execution.warnings == ["Fichier obligatoire absent"]


def test_builder_normalizes_files_and_excludes_missing_entries() -> None:
    identifiers = iter(["manifest-001", "execution-001"])
    manifest = ManifestV2Builder(
        clock=lambda: NOW,
        identifier_factory=lambda: next(identifiers),
    ).build(_plan())

    assert [file.relative_path for file in manifest.files] == [
        "Users/Fred/a.txt",
        "Users/Fred/Z.txt",
    ]
    assert manifest.files[0].potentially_locked is True
    assert manifest.integrity.expected_files == 2


def test_builder_projects_sources_browsers_and_statistics() -> None:
    identifiers = iter(["manifest-001", "execution-001"])
    manifest = ManifestV2Builder(
        clock=lambda: NOW,
        identifier_factory=lambda: next(identifiers),
    ).build(_plan())

    assert [source.source_id for source in manifest.sources] == [
        "chrome.default.bookmarks",
        "chrome.profile-1.passwords",
    ]
    assert manifest.sources[1].metadata["encrypted"] is True
    assert len(manifest.browsers) == 1
    assert manifest.browsers[0].name == "Google Chrome"
    assert manifest.browsers[0].profile_names == ["Default", "Profile 1"]
    assert manifest.statistics.source_count == 2
    assert manifest.statistics.logical_items == 2
    assert manifest.statistics.physical_files == 3
    assert manifest.statistics.missing_files == 1
    assert manifest.statistics.total_size_bytes == 20
