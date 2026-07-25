from zipfile import ZIP_DEFLATED, ZIP_STORED

from .schemas import CompressionMethod, CompressionMetrics, CompressionSettings


class CompressionEngineService:
    _ZIP_METHODS = {
        CompressionMethod.STORED: ZIP_STORED,
        CompressionMethod.DEFLATED: ZIP_DEFLATED,
    }

    @classmethod
    def zip_options(cls, settings: CompressionSettings) -> dict[str, int]:
        options = {"compression": cls._ZIP_METHODS[settings.method]}
        if settings.method == CompressionMethod.DEFLATED:
            options["compresslevel"] = settings.level
        return options

    @staticmethod
    def build_metrics(
        settings: CompressionSettings,
        original_size: int,
        compressed_size: int,
    ) -> CompressionMetrics:
        saved_bytes = max(original_size - compressed_size, 0)
        ratio = compressed_size / original_size if original_size else 0.0
        return CompressionMetrics(
            method=settings.method,
            level=settings.level,
            original_size=original_size,
            compressed_size=compressed_size,
            saved_bytes=saved_bytes,
            ratio=round(ratio, 4),
        )
