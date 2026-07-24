"""Tests for the versioned Manifest V2 contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.modules.manifest_builder.schemas import (
    ExecutionInfo,
    IntegrityInfo,
    Manifest,
    ManifestFile,
    ManifestHeader,
    ManifestSummary,
    ManifestV2,
    SourceInfo,
    Statistics,
)


NOW = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def _build_manifest_v2() -> ManifestV2:
    return ManifestV2(
        header=ManifestHeader(
            manifest_id="manifest-001",
            created_at=NOW,
            application_version="0.2.0",
        ),
        execution=ExecutionInfo(
            execution_id="execution-001",
            started_at=NOW,
        ),
    )


def test_manifest_v2_uses_safe_defaults() -> None:
    """Optional collections and aggregate sections must be initialized safely."""

    manifest = _build_manifest_v2()

    assert manifest.header.format_version == 2
    assert manifest.header.application == "FSBackup"
    assert manifest.execution.status == "planned"
    assert manifest.sources == []
    assert manifest.browsers == []
    assert manifest.files == []
    assert manifest.statistics == Statistics()
    assert manifest.integrity == IntegrityInfo()
    assert manifest.metadata.tags == []
    assert manifest.metadata.custom == {}


def test_manifest_v2_serializes_as_json_compatible_payload() -> None:
    """The contract must produce a stable JSON-compatible representation."""

    manifest = _build_manifest_v2()
    payload = manifest.model_dump(mode="json")

    assert payload["header"]["format_version"] == 2
    assert payload["header"]["created_at"] == "2026-07-24T12:00:00Z"
    assert payload["execution"]["status"] == "planned"
    assert payload["statistics"]["physical_files"] == 0
    assert payload["integrity"]["algorithm"] == "sha256"


def test_manifest_v2_rejects_an_invalid_format_version() -> None:
    """A V2 document must never accept another format version."""

    with pytest.raises(ValidationError):
        ManifestHeader(
            format_version=1,
            manifest_id="manifest-001",
            created_at=NOW,
            application_version="0.2.0",
        )


def test_manifest_v2_rejects_negative_statistics() -> None:
    """Counts and sizes cannot become negative."""

    with pytest.raises(ValidationError):
        Statistics(copied_files=-1)

    with pytest.raises(ValidationError):
        ManifestFile(
            relative_path="Users/Fred/Bookmarks",
            size=-1,
            mandatory=True,
            potentially_locked=False,
        )


def test_manifest_v2_supports_sources_and_execution_results() -> None:
    """The contract must carry source identity and execution diagnostics."""

    manifest = _build_manifest_v2()
    manifest.sources.append(
        SourceInfo(
            source_id="chrome-default",
            provider="browser",
            source_type="chromium_profile",
            display_name="Chrome Default",
            original_path="C:/Users/Fred/AppData/Local/Google/Chrome/User Data/Default",
            required=True,
        )
    )
    manifest.execution.status = "partial"
    manifest.execution.warnings.append("Bookmarks file missing")

    assert manifest.sources[0].provider == "browser"
    assert manifest.sources[0].required is True
    assert manifest.execution.status == "partial"
    assert manifest.execution.warnings == ["Bookmarks file missing"]


def test_manifest_v1_remains_readable() -> None:
    """Introducing V2 must not break the existing Manifest V1 contract."""

    manifest = Manifest(
        created_at=NOW,
        source_root="C:/",
        summary=ManifestSummary(
            logical_items=1,
            physical_files=1,
            missing_files=0,
            encrypted_items=0,
            deduplicated_files=0,
            estimated_size_bytes=128,
            warnings=0,
        ),
        files=[
            ManifestFile(
                relative_path="Users/Fred/Bookmarks",
                size=128,
                mandatory=True,
                potentially_locked=False,
            )
        ],
    )

    assert manifest.format_version == 1
    assert manifest.files[0].relative_path == "Users/Fred/Bookmarks"
