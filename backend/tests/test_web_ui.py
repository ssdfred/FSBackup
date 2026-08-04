from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_redirects_to_web_interface() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/app/"


def test_favicon_is_served() -> None:
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in response.text
    assert "FSBackup" in response.text


def test_dashboard_page_is_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert "FSBackup" in response.text
    assert "Tableau de bord" in response.text
    assert "/app/app.js" in response.text


def test_critical_backup_modules_are_pinned_in_the_page() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert "/app/capacity.js?v=10.8.10" in response.text
    assert "/app/root_inventory.js?v=10.8.10" in response.text
    assert "/app/exclusion_payload.js?v=10.8.10" in response.text
    assert "/app/backup_validation_report.js?v=10.8.10" in response.text
    assert "/app/drive_capacity_bridge.js?v=10.8.10" in response.text
    assert "/app/backup_layout.js?v=10.8.10" in response.text
    assert "/app/exclusion_confirmation_summary.js?v=10.8.10" in response.text
    assert "/app/source_mode_cleanup.js?v=10.8.10" in response.text
    assert "/app/custom_folder_capacity.js?v=10.8.10" in response.text
    assert "/app/exclusion_summary_layout.js?v=10.8.10" in response.text
    assert response.headers["cache-control"].startswith("no-store")


def test_new_backup_form_is_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert 'id="backup-form"' in response.text
    assert 'id="source-mode"' in response.text
    assert 'value="windows_disk"' in response.text
    assert 'value="custom_folder"' in response.text
    assert 'id="source-root"' in response.text
    assert 'id="custom-source-root"' in response.text
    assert 'id="backup-destination-mode"' in response.text
    assert 'id="backup-destination-drive"' in response.text
    assert 'id="backup-destination-subdirectory"' in response.text
    assert 'id="backup-destination-custom"' in response.text
    assert 'id="destination-directory"' in response.text
    assert "/app/drives.js" in response.text
    assert 'id="enable-encryption"' in response.text
    assert 'id="verify-integrity"' in response.text
    assert 'id="enable-segmentation"' in response.text
    assert 'id="segment-size"' in response.text
    assert 'class="segment-setting"' in response.text
    assert "/app/segmentation.css" in response.text


def test_backup_progress_and_report_are_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert 'id="backup-progress"' in response.text
    assert 'id="progress-bar"' in response.text
    assert 'id="backup-report"' in response.text
    assert 'id="report-path"' in response.text
    assert 'id="report-integrity"' in response.text


def test_backup_catalog_screen_is_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert 'id="archives-view"' in response.text
    assert 'id="catalog-form"' in response.text
    assert 'id="catalog-location-mode"' in response.text
    assert 'id="catalog-drive"' in response.text
    assert 'id="catalog-subdirectory"' in response.text
    assert 'id="catalog-custom-directory"' in response.text
    assert 'id="catalog-directory"' in response.text
    assert 'id="catalog-summary"' in response.text
    assert 'id="catalog-list"' in response.text


def test_restore_screen_is_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert 'id="restore-view"' in response.text
    assert 'id="restore-form"' in response.text
    assert 'id="restore-archive-mode"' in response.text
    assert 'id="restore-archive-drive"' in response.text
    assert 'id="restore-archive-relative"' in response.text
    assert 'id="restore-archive"' in response.text
    assert 'id="restore-destination-mode"' in response.text
    assert 'id="restore-destination-drive"' in response.text
    assert 'id="restore-destination-subdirectory"' in response.text
    assert 'id="restore-destination"' in response.text
    assert 'id="restore-overwrite"' in response.text
    assert 'id="restore-report"' in response.text
    assert "/app/restore.js" in response.text


def test_retention_screen_is_served() -> None:
    response = client.get("/app/")

    assert response.status_code == 200
    assert 'id="retention-view"' in response.text
    assert 'id="retention-form"' in response.text
    assert 'id="retention-location-mode"' in response.text
    assert 'id="retention-drive"' in response.text
    assert 'id="retention-subdirectory"' in response.text
    assert 'id="retention-custom-directory"' in response.text
    assert 'id="retention-directory"' in response.text
    assert 'id="retention-summary"' in response.text
    assert 'id="retention-confirmation"' in response.text
    assert 'id="execute-retention"' in response.text
    assert "/app/retention.js" in response.text


def test_dashboard_assets_are_served() -> None:
    stylesheet = client.get("/app/styles.css")
    segmentation_stylesheet = client.get("/app/segmentation.css")
    script = client.get("/app/app.js")
    drives_script = client.get("/app/drives.js")
    restore_script = client.get("/app/restore.js")
    retention_script = client.get("/app/retention.js")
    layout_script = client.get("/app/backup_layout.js")
    exclusion_summary_script = client.get("/app/exclusion_confirmation_summary.js")
    source_cleanup_script = client.get("/app/source_mode_cleanup.js")
    custom_folder_script = client.get("/app/custom_folder_capacity.js")
    exclusion_layout_script = client.get("/app/exclusion_summary_layout.js")

    assert stylesheet.status_code == 200
    assert "capability-grid" in stylesheet.text
    assert "form-panel" in stylesheet.text
    assert "progress-panel" in stylesheet.text
    assert "report-panel" in stylesheet.text
    assert "archive-list" in stylesheet.text
    assert "archive-status" in stylesheet.text
    assert segmentation_stylesheet.status_code == 200
    assert ".segment-setting" in segmentation_stylesheet.text
    assert script.status_code == 200
    assert "/api/v1/dashboard/summary" in script.text
    assert "/api/v1/backup/run" in script.text
    assert "/api/v1/backups/catalog" in script.text
    assert "source_mode" in script.text
    assert "custom_folder" in script.text
    assert "verify_integrity" in script.text
    assert "setProgress" in script.text
    assert "renderReport" in script.text
    assert "renderCatalog" in script.text
    assert "formatBytes" in script.text
    assert "data-restore-archive" in script.text
    assert "prepareRestoreFromCatalog" in script.text
    assert 'mode.value="custom"' in script.text
    assert drives_script.status_code == 200
    assert "/api/v1/sources/drives" in drives_script.text
    assert "systemDrive" in drives_script.text
    assert "bindLocation" in drives_script.text
    assert "backup-destination-drive" in drives_script.text
    assert "catalog-drive" in drives_script.text
    assert "restore-archive-drive" in drives_script.text
    assert "restore-destination-drive" in drives_script.text
    assert "retention-drive" in drives_script.text
    assert restore_script.status_code == 200
    assert "/api/v1/restore/run" in restore_script.text
    assert "integrity_report" in restore_script.text
    assert "restored_files" in restore_script.text
    assert retention_script.status_code == 200
    assert "/api/v1/backups/retention/simulate" in retention_script.text
    assert "/api/v1/backups/retention/execute" in retention_script.text
    assert "SUPPRIMER LES SAUVEGARDES SÉLECTIONNÉES" in retention_script.text
    assert "reclaimable_bytes" in retention_script.text
    assert layout_script.status_code == 200
    assert "root-inventory" in layout_script.text
    assert "exclusion-suggestions" in layout_script.text
    assert "backup-capacity-diagnostic" in layout_script.text
    assert exclusion_summary_script.status_code == 200
    assert "exclusion(s) sélectionnée(s)" in exclusion_summary_script.text
    assert "Économie réellement déduite du plan" in exclusion_summary_script.text
    assert source_cleanup_script.status_code == 200
    assert "source-mode" in source_cleanup_script.text
    assert "root-inventory" in source_cleanup_script.text
    assert "backup-capacity-diagnostic" in source_cleanup_script.text
    assert custom_folder_script.status_code == 200
    assert "/api/v1/sources/folder-diagnostic" in custom_folder_script.text
    assert "Plan final estimé" in custom_folder_script.text
    assert "Destination compatible" in custom_folder_script.text
    assert exclusion_layout_script.status_code == 200
    assert "placeSummaryBelowExclusionList" in exclusion_layout_script.text
    assert "insertAdjacentElement" in exclusion_layout_script.text
