"""Tests for manifest generation."""

from __future__ import annotations

from datetime import UTC

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)
from app.modules.manifest_builder.service import (
    ManifestBuilderError,
    ManifestBuilderService,
)


def build_plan(*files: PhysicalFile) -> ExecutionPlan:
    return ExecutionPlan(
        source_root="E:/",
        physical_files=list(files),
        summary=ExecutionPlanSummary(
            logical_items=2,
            physical_files=len(files),
            missing_files=sum(not file.exists for file in files),
            encrypted_items=1,
            estimated_size_bytes=sum(file.size_bytes for file in files if file.exists),
            deduplicated_files=1,
            warnings=2,
        ),
    )


def physical_file(
    relative_path: str,
    *,
    exists: bool = True,
    required_by: list[str] | None = None,
) -> PhysicalFile:
    return PhysicalFile(
        source_path=f"E:/{relative_path}",
        relative_path=relative_path,
        size_bytes=42,
        required_by=required_by or ["browser.profile"],
        mandatory=True,
        exists=exists,
        potentially_locked=True,
    )


def test_build_creates_deterministic_manifest() -> None:
    plan = build_plan(
        physical_file("Users/Fred/Z.txt", required_by=["z", "a", "z"]),
        physical_file("Users\\Fred\\a.txt"),
    )

    manifest = ManifestBuilderService().build(plan)

    assert manifest.format_version == 1
    assert manifest.created_at.tzinfo == UTC
    assert manifest.source_root == "E:/"
    assert [file.relative_path for file in manifest.files] == [
        "Users/Fred/a.txt",
        "Users/Fred/Z.txt",
    ]
    assert manifest.files[1].required_by == ["a", "z"]
    assert manifest.files[1].size == 42
    assert manifest.files[1].mandatory is True
    assert manifest.files[1].potentially_locked is True


def test_build_preserves_execution_summary() -> None:
    plan = build_plan(
        physical_file("existing.txt"),
        physical_file("missing.txt", exists=False),
    )

    manifest = ManifestBuilderService().build(plan)

    assert manifest.summary == plan.summary
    assert [file.relative_path for file in manifest.files] == ["existing.txt"]


@pytest.mark.parametrize(
    "relative_path",
    [
        "",
        ".",
        "../secret.txt",
        "folder/../secret.txt",
        "/absolute.txt",
        "C:/absolute.txt",
        "C:\\absolute.txt",
    ],
)
def test_build_rejects_unsafe_relative_paths(relative_path: str) -> None:
    plan = build_plan(physical_file(relative_path))

    with pytest.raises(ManifestBuilderError, match="Chemin relatif invalide"):
        ManifestBuilderService().build(plan)


def test_api_builds_manifest() -> None:
    client = TestClient(app)
    plan = build_plan(physical_file("Users/Fred/file.txt"))

    response = client.post(
        "/api/v1/manifests/build",
        json=plan.model_dump(mode="json"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_root"] == "E:/"
    assert payload["files"][0]["relative_path"] == "Users/Fred/file.txt"


def test_api_returns_bad_request_for_unsafe_path() -> None:
    client = TestClient(app)
    plan = build_plan(physical_file("../secret.txt"))

    response = client.post(
        "/api/v1/manifests/build",
        json=plan.model_dump(mode="json"),
    )

    assert response.status_code == 400
    assert "Chemin relatif invalide" in response.json()["detail"]
