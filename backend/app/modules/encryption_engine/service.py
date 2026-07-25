from __future__ import annotations

import struct
from math import ceil
from os import urandom
from pathlib import Path
from time import perf_counter

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .schemas import DecryptionSettings, EncryptionReport, EncryptionSettings


class EncryptionEngineService:
    MAGIC_V1 = b"FSBE1"
    MAGIC_V2 = b"FSBE2"
    MAGIC = MAGIC_V2
    SALT_SIZE = 16
    NONCE_SIZE = 12
    NONCE_PREFIX_SIZE = 8
    KEY_SIZE = 32
    TAG_SIZE = 16
    HEADER_V2 = struct.Struct(">16s8sIQ")
    LENGTH_FIELD = struct.Struct(">I")

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
        if destination.exists() and not settings.overwrite:
            return cls._failure(source, destination, started_at, "Destination file already exists.")

        input_size = source.stat().st_size
        chunk_count = 0

        try:
            salt = urandom(cls.SALT_SIZE)
            nonce_prefix = urandom(cls.NONCE_PREFIX_SIZE)
            key = cls._derive_key(settings.password.get_secret_value(), salt)
            cipher = AESGCM(key)
            destination.parent.mkdir(parents=True, exist_ok=True)

            with source.open("rb") as source_stream, destination.open("wb") as output:
                output.write(cls.MAGIC_V2)
                output.write(
                    cls.HEADER_V2.pack(
                        salt,
                        nonce_prefix,
                        settings.chunk_size,
                        input_size,
                    )
                )

                while True:
                    plaintext = source_stream.read(settings.chunk_size)
                    if not plaintext and (input_size > 0 or chunk_count > 0):
                        break

                    ciphertext = cipher.encrypt(
                        cls._chunk_nonce(nonce_prefix, chunk_count),
                        plaintext,
                        cls._chunk_aad(settings.associated_data, chunk_count),
                    )
                    output.write(cls.LENGTH_FIELD.pack(len(ciphertext)))
                    output.write(ciphertext)
                    chunk_count += 1

                    if input_size == 0:
                        break

            return EncryptionReport(
                source_path=str(source),
                destination_path=str(destination),
                input_size=input_size,
                output_size=destination.stat().st_size,
                chunk_count=chunk_count,
                container_version=2,
                duration_ms=cls._duration_ms(started_at),
                success=True,
            )
        except (OSError, OverflowError, ValueError) as exc:
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
            with source.open("rb") as stream:
                magic = stream.read(len(cls.MAGIC_V2))

            if magic == cls.MAGIC_V2:
                return cls._decrypt_v2(source, destination, settings, started_at)
            if magic == cls.MAGIC_V1:
                return cls._decrypt_v1(source, destination, settings, started_at)
            raise ValueError("File is not a supported encrypted FSB container.")
        except (InvalidTag, OSError, ValueError) as exc:
            destination.unlink(missing_ok=True)
            return cls._decryption_failure(source, destination, started_at, exc)

    @classmethod
    def _decrypt_v2(
        cls,
        source: Path,
        destination: Path,
        settings: DecryptionSettings,
        started_at: float,
    ) -> EncryptionReport:
        destination.parent.mkdir(parents=True, exist_ok=True)
        chunk_count = 0
        output_size = 0

        try:
            with source.open("rb") as stream:
                if stream.read(len(cls.MAGIC_V2)) != cls.MAGIC_V2:
                    raise ValueError("File is not a supported FSBE2 container.")

                header = stream.read(cls.HEADER_V2.size)
                if len(header) != cls.HEADER_V2.size:
                    raise ValueError("Encrypted container header is truncated.")
                salt, nonce_prefix, chunk_size, original_size = cls.HEADER_V2.unpack(header)
                if not 64 * 1024 <= chunk_size <= 16 * 1024 * 1024:
                    raise ValueError("Encrypted container chunk size is invalid.")

                expected_chunks = max(1, ceil(original_size / chunk_size))
                key = cls._derive_key(settings.password.get_secret_value(), salt)
                cipher = AESGCM(key)

                with destination.open("wb") as output:
                    for counter in range(expected_chunks):
                        length_payload = stream.read(cls.LENGTH_FIELD.size)
                        if len(length_payload) != cls.LENGTH_FIELD.size:
                            raise ValueError("Encrypted container is truncated.")
                        (ciphertext_size,) = cls.LENGTH_FIELD.unpack(length_payload)
                        if not cls.TAG_SIZE <= ciphertext_size <= chunk_size + cls.TAG_SIZE:
                            raise ValueError("Encrypted chunk size is invalid.")

                        ciphertext = stream.read(ciphertext_size)
                        if len(ciphertext) != ciphertext_size:
                            raise ValueError("Encrypted container is truncated.")
                        plaintext = cipher.decrypt(
                            cls._chunk_nonce(nonce_prefix, counter),
                            ciphertext,
                            cls._chunk_aad(settings.associated_data, counter),
                        )
                        output.write(plaintext)
                        output_size += len(plaintext)
                        chunk_count += 1

                    if stream.read(1):
                        raise ValueError("Encrypted container contains trailing data.")
                    if output_size != original_size:
                        raise ValueError("Decrypted archive size does not match the header.")

            return EncryptionReport(
                source_path=str(source),
                destination_path=str(destination),
                input_size=source.stat().st_size,
                output_size=output_size,
                chunk_count=chunk_count,
                container_version=2,
                duration_ms=cls._duration_ms(started_at),
                success=True,
            )
        except (InvalidTag, OSError, ValueError):
            destination.unlink(missing_ok=True)
            raise

    @classmethod
    def _decrypt_v1(
        cls,
        source: Path,
        destination: Path,
        settings: DecryptionSettings,
        started_at: float,
    ) -> EncryptionReport:
        payload = source.read_bytes()
        minimum_size = len(cls.MAGIC_V1) + cls.SALT_SIZE + cls.NONCE_SIZE + cls.TAG_SIZE
        if len(payload) < minimum_size or not payload.startswith(cls.MAGIC_V1):
            raise ValueError("File is not a supported encrypted FSB container.")

        offset = len(cls.MAGIC_V1)
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
            chunk_count=1,
            container_version=1,
            duration_ms=cls._duration_ms(started_at),
            success=True,
        )

    @classmethod
    def is_encrypted_file(cls, path: str | Path) -> bool:
        source = Path(path)
        if not source.is_file():
            return False
        try:
            with source.open("rb") as stream:
                magic = stream.read(len(cls.MAGIC_V2))
            return magic in {cls.MAGIC_V1, cls.MAGIC_V2}
        except OSError:
            return False

    @classmethod
    def _derive_key(cls, password: str, salt: bytes) -> bytes:
        return Scrypt(salt=salt, length=cls.KEY_SIZE, n=2**14, r=8, p=1).derive(
            password.encode("utf-8")
        )

    @classmethod
    def _chunk_nonce(cls, nonce_prefix: bytes, counter: int) -> bytes:
        if counter >= 2**32:
            raise OverflowError("Encrypted container exceeds the supported chunk count.")
        return nonce_prefix + counter.to_bytes(4, "big")

    @staticmethod
    def _chunk_aad(associated_data: str, counter: int) -> bytes:
        return associated_data.encode("utf-8") + b":" + counter.to_bytes(4, "big")

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    @classmethod
    def _decryption_failure(
        cls,
        source: Path,
        destination: Path,
        started_at: float,
        exc: Exception,
    ) -> EncryptionReport:
        error = "Invalid password or encrypted file integrity check failed."
        if not isinstance(exc, InvalidTag):
            error = str(exc)
        return cls._failure(source, destination, started_at, error)

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
