from pathlib import Path

import pytest

from app.modules.execution_planner.windows_service import WindowsExecutionPlannerService


def test_recovery_rejects_path_outside_source(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(ValueError, match="hors de la source"):
        WindowsExecutionPlannerService._validate_recovery_path(root, outside)
