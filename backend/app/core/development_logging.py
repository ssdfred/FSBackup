from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


class DevelopmentLogService:
    """Write development diagnostics without exposing backup passwords."""

    @classmethod
    def start_backup(cls, request: BaseModel) -> str:
        execution_id = str(uuid4())
        cls._append_event(
            execution_id,
            "backup_started",
            {
                "source_root": getattr(request, "source_root", None),
                "source_mode": str(getattr(request, "source_mode", "")),
                "destination_directory": getattr(
                    request, "destination_directory", None
                ),
                "archive_name": getattr(request, "archive_name", None),
                "verify_integrity": getattr(request, "verify_integrity", None),
                "encrypted": getattr(request, "encryption", None) is not None,
                "selected_item_ids": getattr(request, "selected_item_ids", None),
                "selected_additional_paths": getattr(
                    request, "selected_additional_paths", []
                ),
                "selected_recovery_paths": getattr(
                    request, "selected_recovery_paths", []
                ),
                "approved_exclusion_count": len(
                    getattr(request, "approved_exclusions", [])
                ),
            },
        )
        return execution_id

    @classmethod
    def finish_backup(
        cls,
        execution_id: str,
        request: BaseModel,
        report: BaseModel,
    ) -> None:
        report_data = report.model_dump(mode="json")
        payload = {
            "execution_id": execution_id,
            "created_at": cls._timestamp(),
            "request": cls._safe_request(request),
            "report": report_data,
        }
        cls._write_execution_report(execution_id, payload)
        cls._append_event(
            execution_id,
            "backup_finished",
            {
                "success": report_data.get("success"),
                "archive_path": report_data.get("archive_path"),
                "copied_files": report_data.get("copied_files"),
                "excluded_files": report_data.get("excluded_files"),
                "warning_count": len(report_data.get("warnings") or []),
                "error": report_data.get("error"),
                "execution_report": str(
                    cls._execution_directory() / f"{execution_id}.json"
                ),
            },
        )

    @classmethod
    def _safe_request(cls, request: BaseModel) -> dict[str, Any]:
        data = request.model_dump(mode="json", exclude={"encryption"})
        data["encrypted"] = getattr(request, "encryption", None) is not None
        return data

    @classmethod
    def _append_event(
        cls,
        execution_id: str,
        event: str,
        details: dict[str, Any],
    ) -> None:
        try:
            log_directory = cls._log_directory()
            log_directory.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": cls._timestamp(),
                "execution_id": execution_id,
                "event": event,
                "details": details,
            }
            with (log_directory / "fsbackup.log").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            # Development logging must never break a backup.
            return

    @classmethod
    def _write_execution_report(
        cls,
        execution_id: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            directory = cls._execution_directory()
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{execution_id}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat()

    @classmethod
    def _execution_directory(cls) -> Path:
        return cls._log_directory() / "executions"

    @staticmethod
    def _log_directory() -> Path:
        configured = os.getenv("FSBACKUP_LOG_DIR")
        if configured:
            return Path(configured).expanduser()
        return Path(__file__).resolve().parents[2] / "logs"
