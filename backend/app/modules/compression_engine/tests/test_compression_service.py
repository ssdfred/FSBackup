from zipfile import ZIP_DEFLATED, ZIP_STORED

from app.modules.compression_engine.schemas import (
    CompressionMethod,
    CompressionSettings,
)
from app.modules.compression_engine.service import CompressionEngineService


def test_zip_options_for_deflated_compression() -> None:
    settings = CompressionSettings(
        method=CompressionMethod.DEFLATED,
        level=9,
    )

    assert CompressionEngineService.zip_options(settings) == {
        "compression": ZIP_DEFLATED,
        "compresslevel": 9,
    }


def test_zip_options_for_stored_compression_omit_level() -> None:
    settings = CompressionSettings(
        method=CompressionMethod.STORED,
        level=6,
    )

    assert CompressionEngineService.zip_options(settings) == {
        "compression": ZIP_STORED,
    }


def test_build_metrics_for_compressed_payload() -> None:
    metrics = CompressionEngineService.build_metrics(
        settings=CompressionSettings(level=6),
        original_size=1000,
        compressed_size=250,
    )

    assert metrics.original_size == 1000
    assert metrics.compressed_size == 250
    assert metrics.saved_bytes == 750
    assert metrics.ratio == 0.25


def test_build_metrics_for_empty_payload() -> None:
    metrics = CompressionEngineService.build_metrics(
        settings=CompressionSettings(),
        original_size=0,
        compressed_size=0,
    )

    assert metrics.saved_bytes == 0
    assert metrics.ratio == 0.0
