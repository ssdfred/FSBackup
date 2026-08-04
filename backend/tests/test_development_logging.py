import json
from pathlib import Path

from pydantic import SecretStr

from app.core.development_logging import DevelopmentLogService
from app.modules.backup_orchestrator.schemas import (
    BackupRunReport,
    BackupRunRequest,
)
from app.modules.encryption_engine.schemas import EncryptionSettings


def test_backup_logs_are_written_without_password(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSBACKUP_LOG_DIR", str(tmp_path / "logs"))
    request = BackupRunRequest(
        source_root="D:\\",
        destination_directory="G:\\Sauvegardes",
        archive_name="poste",
        encryption=EncryptionSettings(password=SecretStr("secret-test")),
    )
    report = BackupRunReport(
        success=False,
        copied_files=12,
        warnings=["cache verrouillé ignoré"],
        error="[WinError 362] fournisseur cloud indisponible",
    )

    execution_id = DevelopmentLogService.start_backup(request)
    DevelopmentLogService.finish_backup(execution_id, request, report)

    global_log = tmp_path / "logs" / "fsbackup.log"
    execution_log = tmp_path / "logs" / "executions" / f"{execution_id}.json"
    assert global_log.is_file()
    assert execution_log.is_file()

    global_text = global_log.read_text(encoding="utf-8")
    execution_text = execution_log.read_text(encoding="utf-8")
    assert "backup_started" in global_text
    assert "backup_finished" in global_text
    assert "WinError 362" in global_text
    assert "secret-test" not in global_text
    assert "secret-test" not in execution_text

    payload = json.loads(execution_text)
    assert payload["execution_id"] == execution_id
    assert payload["request"]["encrypted"] is True
    assert "encryption" not in payload["request"]
    assert payload["report"]["success"] is False
    assert payload["report"]["copied_files"] == 12
