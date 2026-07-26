"""Build a Windows recovery plan with personal, selected and legacy data."""

from __future__ import annotations

import os
from pathlib import Path

from app.modules.source_discovery.diagnostic import diagnose_windows_source
from app.modules.source_discovery.root_inventory import SYSTEM_ROOTS

from .schemas import ExecutionItem, ExecutionPlan, ExecutionPlanSummary, PhysicalFile
from .service import ExecutionPlannerService


class WindowsExecutionPlannerService:
    """Combine detected application data with explicitly recoverable folders."""

    @classmethod
    def build_plan(
        cls,
        source_root: str | Path,
        selected_item_ids: list[str] | None = None,
        selected_additional_paths: list[str] | None = None,
        selected_recovery_paths: list[str] | None = None,
    ) -> ExecutionPlan:
        base_plan = ExecutionPlannerService().build_plan(source_root, selected_item_ids)
        root = Path(base_plan.source_root).resolve(strict=True)
        files_by_path = {
            Path(item.source_path).resolve(strict=False): item
            for item in base_plan.physical_files
        }
        items = list(base_plan.items)
        warnings = list(base_plan.warnings)

        diagnostic = diagnose_windows_source(root)
        for user in diagnostic.users:
            for folder in user.folders:
                if not folder.present:
                    continue
                cls._append_directory(
                    root=root,
                    directory=Path(folder.path),
                    logical_id=f"personal:{user.name}:{folder.name}",
                    category="personal_folder",
                    application_name="Données personnelles Windows",
                    user_name=user.name,
                    profile_name=folder.name,
                    files_by_path=files_by_path,
                    items=items,
                    warnings=warnings,
                )

        for raw_path in dict.fromkeys(selected_additional_paths or []):
            candidate = Path(raw_path).expanduser().resolve(strict=True)
            cls._validate_additional_path(root, candidate)
            cls._append_directory(
                root=root,
                directory=candidate,
                logical_id=f"additional:{candidate.relative_to(root)}",
                category="selected_project",
                application_name="Dossier supplémentaire sélectionné",
                user_name="local",
                profile_name=candidate.name,
                files_by_path=files_by_path,
                items=items,
                warnings=warnings,
            )

        for raw_path in dict.fromkeys(selected_recovery_paths or []):
            candidate = Path(raw_path).expanduser().resolve(strict=True)
            cls._validate_recovery_path(root, candidate)
            cls._append_directory(
                root=root,
                directory=candidate,
                logical_id=f"recovery:{candidate.relative_to(root)}",
                category="selected_recovery_data",
                application_name="Données de récupération sélectionnées",
                user_name=cls._recovery_user_name(root, candidate),
                profile_name=candidate.name,
                files_by_path=files_by_path,
                items=items,
                warnings=warnings,
            )

        physical_files = sorted(
            files_by_path.values(), key=lambda item: item.relative_path.casefold()
        )
        summary = ExecutionPlanSummary(
            logical_items=len(items),
            physical_files=len(physical_files),
            missing_files=sum(1 for item in physical_files if not item.exists),
            encrypted_items=sum(1 for item in items if item.encrypted),
            estimated_size_bytes=sum(
                item.size_bytes for item in physical_files if item.exists
            ),
            deduplicated_files=base_plan.summary.deduplicated_files,
            warnings=len(warnings),
        )
        return ExecutionPlan(
            source_root=str(root),
            items=items,
            physical_files=physical_files,
            summary=summary,
            warnings=warnings,
        )

    @staticmethod
    def _validate_additional_path(root: Path, candidate: Path) -> None:
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"Dossier supplémentaire hors de la source : {candidate}"
            ) from exc
        if candidate == root:
            raise ValueError("La racine complète ne peut pas être ajoutée manuellement.")
        top_level = relative.parts[0].casefold() if relative.parts else ""
        is_programdata_child = top_level == "programdata" and len(relative.parts) >= 2
        if top_level in SYSTEM_ROOTS and not is_programdata_child:
            raise ValueError(
                f"Dossier système non sélectionnable manuellement : {candidate}"
            )
        if not candidate.is_dir():
            raise ValueError(f"Dossier supplémentaire invalide : {candidate}")

    @staticmethod
    def _validate_recovery_path(root: Path, candidate: Path) -> None:
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"Donnée de récupération hors de la source : {candidate}"
            ) from exc
        if not candidate.is_dir() or candidate == root:
            raise ValueError(f"Donnée de récupération invalide : {candidate}")

        parts = [part.casefold() for part in relative.parts]
        current_profile = len(parts) >= 2 and parts[0] in {"users", "utilisateurs"}
        old_profile = (
            len(parts) >= 3
            and parts[0] == "windows.old"
            and parts[1] in {"users", "utilisateurs"}
        )
        if not (current_profile or old_profile):
            raise ValueError(
                "Les données de récupération doivent appartenir à un profil "
                f"utilisateur courant ou à Windows.old : {candidate}"
            )

    @staticmethod
    def _recovery_user_name(root: Path, candidate: Path) -> str:
        parts = candidate.relative_to(root).parts
        if parts and parts[0].casefold() == "windows.old" and len(parts) >= 3:
            return parts[2]
        return parts[1] if len(parts) >= 2 else "local"

    @classmethod
    def _append_directory(
        cls,
        *,
        root: Path,
        directory: Path,
        logical_id: str,
        category: str,
        application_name: str,
        user_name: str,
        profile_name: str,
        files_by_path: dict[Path, PhysicalFile],
        items: list[ExecutionItem],
        warnings: list[str],
    ) -> None:
        item_files: list[str] = []
        try:
            walker = os.walk(directory, topdown=True, followlinks=False)
            for current_root, directories, filenames in walker:
                current = Path(current_root)
                safe_directories: list[str] = []
                for name in directories:
                    child = current / name
                    try:
                        if not child.is_symlink():
                            safe_directories.append(name)
                    except OSError as exc:
                        warnings.append(f"Dossier ignoré : {child} ({exc})")
                directories[:] = safe_directories

                for filename in filenames:
                    candidate = current / filename
                    try:
                        if candidate.is_symlink() or not candidate.is_file():
                            continue
                        resolved = candidate.resolve(strict=True)
                        relative = resolved.relative_to(root)
                        size_bytes = resolved.stat().st_size
                    except (OSError, ValueError) as exc:
                        warnings.append(f"Fichier ignoré : {candidate} ({exc})")
                        continue

                    existing = files_by_path.get(resolved)
                    if existing is not None:
                        if logical_id not in existing.required_by:
                            existing.required_by.append(logical_id)
                            existing.required_by.sort()
                        item_files.append(existing.source_path)
                        continue

                    physical = PhysicalFile(
                        source_path=str(resolved),
                        relative_path=str(relative),
                        size_bytes=size_bytes,
                        required_by=[logical_id],
                    )
                    files_by_path[resolved] = physical
                    item_files.append(physical.source_path)
        except OSError as exc:
            warnings.append(f"Impossible de parcourir {directory} : {exc}")

        items.append(
            ExecutionItem(
                logical_id=logical_id,
                category=category,
                application_key=category,
                application_name=application_name,
                user_name=user_name,
                profile_name=profile_name,
                files=sorted(set(item_files), key=str.casefold),
            )
        )


__all__ = ["WindowsExecutionPlannerService"]
