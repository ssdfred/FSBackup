from pathlib import Path


WEB_UI = Path(__file__).parents[1] / "app" / "web_ui"


def test_validation_report_displays_real_backup_metrics() -> None:
    script = (WEB_UI / "backup_validation_report.js").read_text(encoding="utf-8")

    assert "Taille originale" in script
    assert "Taille de l’archive" in script
    assert "Espace économisé" in script
    assert "Gain de compression" in script
    assert "Durée de création" in script
    assert "Fichiers exclus" in script
    assert "Volume exclu" in script
    assert "Chiffrement" in script
    assert "archive_report" in script
    assert "integrity_report" in script
    assert "excluded_size_bytes" in script


def test_validation_report_wraps_existing_report_without_replacing_it() -> None:
    script = (WEB_UI / "backup_validation_report.js").read_text(encoding="utf-8")

    assert 'typeof window.renderReport!=="function"' in script
    assert "const originalRenderReport=window.renderReport" in script
    assert "originalRenderReport(data,verified)" in script
    assert "renderValidationDetails(data,verified)" in script
    assert "fsbackupValidationReportInstalled" in script


def test_drives_loads_versioned_validation_report_module() -> None:
    drives = (WEB_UI / "drives.js").read_text(encoding="utf-8")

    assert 'UI_MODULE_VERSION="10.8.1"' in drives
    assert 'loadOptionalModule("/app/backup_validation_report.js"' in drives
    assert "data-fsbackup-validation-report" in drives
