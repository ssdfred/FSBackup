from __future__ import annotations

from os import urandom
from pathlib import Path
from time import perf_counter

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .schemas import DecryptionSettings, EncryptionReport, EncryptionSettings


class EncryptionEngineService:
    MAGIC = b"FSBE1"
    SALT_SIZE = 16
    NONCE_SIZE = 12
    KEY_SIZE = 32

    @classmethod
    def encrypt_file(
        cls,
        source_path: str | Path,
        destination_path: str | Path,
        settings: EncryptionSettings,
    ) -> EncryptionReport:
        started_at = perf_counter()
        source = Path(source_path)
        destination = Path(destination_path)

        if not source.is_file():
            return cls._failure(source, destination, started_at, "Source file does not exist.")

        try:
            plaintext = source.read_bytes()
            salt = urandom(cls.SALT_SIZE)
            nonce = urandom(cls.NONCE_SIZE)
            key = cls._derive_key(settings.password.get_secret_value(), salt)
            ciphertext = AESGCM(key).encrypt(
                nonce,
                plaintext,
                settings.associated_data.encode("utf-8"),
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(cls.MAGIC + salt + nonce + ciphertext)
            return EncryptionReport(
                source_path=str(source),
                destination_path=str(destination),
                input_size=len(plaintext),
                output_size=destination.stat().st_size,
                duration_ms=cls._duration_ms(started_at),
                success=True,
            )
        except OSError as exc:
            destination.unlink(missing_ok=True)
            return cls._failure(source, destination, started_at, str(exc))

    @classmethod
    def decrypt_file(
        cls,
        source_path: str | Path,
        destination_path: str | Path,
        settings: DecryptionSettings,
    ) -> EncryptionReport:
        started_at = perf_counter()
        source = Path(source_path)
        destination = Path(destination_path)

        if not source.is_file():
            return cls._failure(source, destination, started_at, "Encrypted file does not exist.")
        if destination.exists() and not settings.overwrite:
            return cls._failure(source, destination, started_at, "Destination file already exists.")

        try:
            payload = source.read_bytes()
            minimum_size = len(cls.MAGIC) + cls.SALT_SIZE + cls.NONCE_SIZE + 16
            if len(payload) < minimum_size or not payload.startswith(cls.MAGIC):
                raise ValueError("File is not a supported encrypted FSB container.")

            offset = len(cls.MAGIC)
            salt = payload[offset : offset + cls.SALT_SIZE]
            offset += cls.SALT_SIZE
            nonce = payload[offset : offset + cls.NONCE_SIZE]
            ciphertext = payload[offset + cls.NONCE_SIZE :]
            key = cls._derive_key(settings.password.get_secret_value(), salt)
            plaintext = AESGCM(key).decrypt(
                nonce,
                ciphertext,
                settings.associated_data.encode("utf-8"),
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(plaintext)
            return EncryptionReport(
                source_path=str(source),
                destination_path=str(destination),
                input_size=len(payload),
                output_size=len(plaintext),
                duration_ms=cls._duration_ms(started_at),
                success=True,
            )
        except (InvalidTag, OSError, ValueError) as exc:
            destination.unlink(missing_ok=True)
            error = "Invalid password or encrypted file integrity check failed."
            if not isinstance(exc, InvalidTag):
                error = str(exc)
            return cls._failure(source, destination, started_at, error)

    @classmethod
    def is_encrypted_file(cls, path: str | Path) -> bool:
        source = Path(path)
        if not source.is_file():
            return False
        try:
            with source.open("rb") as stream:
                return stream.read(len(cls.MAGIC)) == cls.MAGIC
        except OSError:
            return False

    @classmethod
    def _derive_key(cls, password: str, salt: bytes) -> bytes:
        return Scrypt(salt=salt, length=cls.KEY_SIZE, n=2**14, r=8, p=1).derive(
            password.encode("utf-8")
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    @classmethod
    def _failure(
        cls,
        source: Path,
        destination: Path,
        started_at: float,
        error: str,
    ) -> EncryptionReport:
        return EncryptionReport(
            source_path=str(source),
            destination_path=str(destination),
            duration_ms=cls._duration_ms(started_at),
            success=False,
            error=error,
        )
