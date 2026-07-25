from os import urandom
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
    assert encryption.container_version == 2
    assert encryption.chunk_count == 1
    assert decryption.success is True
    assert decryption.container_version == 2
    assert restored.read_bytes() == source.read_bytes()
    assert EncryptionEngineService.is_encrypted_file(encrypted) is True
    assert encrypted.read_bytes().startswith(b"FSBE2")


def test_large_payload_is_processed_in_multiple_chunks(tmp_path: Path) -> None:
    source = tmp_path / "large.fsb"
    encrypted = tmp_path / "large.fsbe"
    restored = tmp_path / "large-restored.fsb"
    payload = (b"FSBackup-streaming-test" * 8000) + urandom(1000)
    source.write_bytes(payload)

    encryption = EncryptionEngineService.encrypt_file(
        source,
        encrypted,
        EncryptionSettings(password=PASSWORD, chunk_size=64 * 1024),
    )
    decryption = EncryptionEngineService.decrypt_file(
        encrypted,
        restored,
        DecryptionSettings(password=PASSWORD),
    )

    assert encryption.success is True
    assert encryption.chunk_count > 1
    assert decryption.success is True
    assert decryption.chunk_count == encryption.chunk_count
    assert restored.read_bytes() == payload


def test_empty_payload_is_authenticated(tmp_path: Path) -> None:
    source = tmp_path / "empty.fsb"
    encrypted = tmp_path / "empty.fsbe"
    restored = tmp_path / "empty-restored.fsb"
    source.write_bytes(b"")

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
    assert encryption.chunk_count == 1
    assert decryption.success is True
    assert restored.read_bytes() == b""


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


def test_encryption_refuses_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "backup.fsb"
    encrypted = tmp_path / "backup.fsbe"
    source.write_bytes(b"secret")
    encrypted.write_bytes(b"existing")

    report = EncryptionEngineService.encrypt_file(
        source,
        encrypted,
        EncryptionSettings(password=PASSWORD),
    )

    assert report.success is False
    assert report.error == "Destination file already exists."
    assert encrypted.read_bytes() == b"existing"


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


def test_legacy_fsbe1_container_remains_readable(tmp_path: Path) -> None:
    encrypted = tmp_path / "legacy.fsbe"
    restored = tmp_path / "legacy-restored.fsb"
    plaintext = b"legacy encrypted archive"
    salt = urandom(EncryptionEngineService.SALT_SIZE)
    nonce = urandom(EncryptionEngineService.NONCE_SIZE)
    key = EncryptionEngineService._derive_key(PASSWORD, salt)
    ciphertext = AESGCM(key).encrypt(
        nonce,
        plaintext,
        b"FSBackup:FSBE:1",
    )
    encrypted.write_bytes(
        EncryptionEngineService.MAGIC_V1 + salt + nonce + ciphertext
    )

    report = EncryptionEngineService.decrypt_file(
        encrypted,
        restored,
        DecryptionSettings(password=PASSWORD),
    )

    assert report.success is True
    assert report.container_version == 1
    assert restored.read_bytes() == plaintext
    assert EncryptionEngineService.is_encrypted_file(encrypted) is True
