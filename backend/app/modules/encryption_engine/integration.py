from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import SecretStr

from .schemas import DecryptionSettings
from .service import EncryptionEngineService


class EncryptedArchiveError(ValueError):
    """Raised when an encrypted archive cannot be opened safely."""


@contextmanager
def resolved_archive_path(
    archive_path: str | Path,
    password: SecretStr | None = None,
) -> Iterator[Path]:
    source = Path(archive_path)
    if not EncryptionEngineService.is_encrypted_file(source):
        yield source
        return

    if password is None:
        raise EncryptedArchiveError("Password is required for encrypted archive.")

    with TemporaryDirectory(prefix="fsbackup-") as temporary_directory:
        decrypted_path = Path(temporary_directory) / "archive.fsb"
        report = EncryptionEngineService.decrypt_file(
            source_path=source,
            destination_path=decrypted_path,
            settings=DecryptionSettings(password=password),
        )
        if not report.success:
            raise EncryptedArchiveError(report.error or "Unable to decrypt archive.")
        yield decrypted_path
