from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .schemas import CopyStatus


class CopyEventType(StrEnum):
    COPY_STARTED = "copy_started"
    FILE_STARTED = "file_started"
    FILE_COPIED = "file_copied"
    FILE_SKIPPED = "file_skipped"
    FILE_MISSING = "file_missing"
    FILE_ERROR = "file_error"
    COPY_FINISHED = "copy_finished"


class CopyEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: CopyEventType
    execution_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str | None = None
    destination: str | None = None
    file_status: CopyStatus | None = None
    size: int | None = None
    duration_ms: int | None = None
    message: str | None = None
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)


CopyEventListener = Callable[[CopyEvent], None]


class CopyEventBus:
    def __init__(self) -> None:
        self._listeners: list[CopyEventListener] = []
        self._listener_errors: list[Exception] = []

    @property
    def listener_errors(self) -> tuple[Exception, ...]:
        return tuple(self._listener_errors)

    def subscribe(self, listener: CopyEventListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: CopyEventListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def publish(self, event: CopyEvent) -> None:
        for listener in tuple(self._listeners):
            try:
                listener(event)
            except Exception as exc:
                self._listener_errors.append(exc)
