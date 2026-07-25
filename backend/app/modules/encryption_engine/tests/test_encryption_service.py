from pathlib import Path

from app.modules.encryption_engine.schemas import (
    DecryptionSettings,
    EncryptionSettings,
)
from app.modules.encryption_engine.service import EncryptionEngineService


PASSWORD = "test-password-123"


def test_encrypt_and_decrypt_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "backup.fsb"
    encrypted = tmp_path / "backup.fsbe"
    restored = tmp_path / "restored.fsb"
    source.write_bytes(b"FSBackup archive payload" * 100)

    encryption = EncryptionEngineService.encrypt_file(
        source,
        encrypted,
        EncryptionSettings(password=PASSWORD),
    )
    decryption = EncryptionEngineService.decrypt_file(
        encrypted,
        restored,
        DecryptionSettings(password=PASSWORD),
    )

    assert encryption.success is True
    assert decryption.success is True
    assert restored.read_bytes() == source.read_bytes()
    assert EncryptionEngineService.is_encrypted_file(encrypted) is True


def test_wrong_password_does_not_create_plaintext(tmp_path: Path) -> None:
    source = tmp_path / "backup.fsb"
    encrypted = tmp_path / "backup.fsbe"
    restored = tmp_path / "restored.fsb"
    source.write_bytes(b"secret")
    EncryptionEngineService.encrypt_file(
        source,
        encrypted,
        EncryptionSettings(password=PASSWORD),
    )

    report = EncryptionEngineService.decrypt_file(
        encrypted,
        restored,
        DecryptionSettings(password="wrong-password"),
    )

    assert report.success is False
    assert report.error == "Invalid password or encrypted file integrity check failed."
    assert not restored.exists()


def test_tampered_payload_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "backup.fsb"
    encrypted = tmp_path / "backup.fsbe"
    restored = tmp_path / "restored.fsb"
    source.write_bytes(b"secret")
    EncryptionEngineService.encrypt_file(
        source,
        encrypted,
        EncryptionSettings(password=PASSWORD),
    )
    payload = bytearray(encrypted.read_bytes())
    payload[-1] ^= 1
    encrypted.write_bytes(payload)

    report = EncryptionEngineService.decrypt_file(
        encrypted,
        restored,
        DecryptionSettings(password=PASSWORD),
    )

    assert report.success is False
    assert not restored.exists()


def test_decryption_refuses_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "backup.fsb"
    encrypted = tmp_path / "backup.fsbe"
    restored = tmp_path / "restored.fsb"
    source.write_bytes(b"secret")
    restored.write_bytes(b"existing")
    EncryptionEngineService.encrypt_file(
        source,
        encrypted,
        EncryptionSettings(password=PASSWORD),
    )

    report = EncryptionEngineService.decrypt_file(
        encrypted,
        restored,
        DecryptionSettings(password=PASSWORD),
    )

    assert report.success is False
    assert report.error == "Destination file already exists."
    assert restored.read_bytes() == b"existing"
