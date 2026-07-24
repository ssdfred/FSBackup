"""Build physical execution plans from logical backup plans."""

from __future__ import annotations

from pathlib import Path

from app.modules.backup_planner.schemas import BackupPlan
from app.modules.backup_planner.service import BackupPlannerService

from .resolver import DependencyResolver, FileDependency
from .schemas import (
    ExecutionItem,
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)


class ExecutionPlannerError(ValueError):
    """Raised when an execution plan cannot be generated safely."""


class ExecutionPlannerService:
    """Transform a logical backup plan into a physical execution plan."""

    def __init__(
        self,
        backup_planner_service: BackupPlannerService | None = None,
        dependency_resolver: DependencyResolver | None = None,
    ) -> None:
        self.backup_planner_service = (
            backup_planner_service or BackupPlannerService()
        )
        self.dependency_resolver = (
            dependency_resolver or DependencyResolver()
        )

    def build_plan(
        self,
        source_root: str | Path,
        selected_item_ids: list[str] | None = None,
    ) -> ExecutionPlan:
        """Build a read-only physical execution plan."""

        backup_plan = self.backup_planner_service.build_plan(source_root)
        root = Path(backup_plan.source_root).resolve(strict=True)

        available_items = self._collect_available_items(backup_plan)
        selected_ids = self._select_item_ids(
            available_items=available_items,
            selected_item_ids=selected_item_ids,
        )

        execution_items: list[ExecutionItem] = []
        physical_files: dict[Path, PhysicalFile] = {}
        global_warnings: list[str] = []
        deduplicated_files = 0

        for logical_id in selected_ids:
            item_context = available_items[logical_id]
            execution_item, duplicate_count = self._resolve_item(
                root=root,
                logical_id=logical_id,
                item_context=item_context,
                physical_files=physical_files,
            )

            execution_items.append(execution_item)
            deduplicated_files += duplicate_count
            global_warnings.extend(execution_item.warnings)

        ordered_files = sorted(
            physical_files.values(),
            key=lambda file: file.relative_path.casefold(),
        )

        summary = self._build_summary(
            execution_items=execution_items,
            physical_files=ordered_files,
            deduplicated_files=deduplicated_files,
            warnings=global_warnings,
        )

        return ExecutionPlan(
            source_root=str(root),
            items=execution_items,
            physical_files=ordered_files,
            summary=summary,
            warnings=global_warnings,
        )

    @staticmethod
    def _collect_available_items(
        backup_plan: BackupPlan,
    ) -> dict[str, dict[str, object]]:
        """Flatten logical backup items with their application context."""

        available_items: dict[str, dict[str, object]] = {}

        for user in backup_plan.users:
            for application in user.applications:
                for profile in application.profiles:
                    for item in profile.items:
                        available_items[item.id] = {
                            "item": item,
                            "user_name": user.name,
                            "application_key": application.key,
                            "application_name": application.name,
                            "profile_name": profile.name,
                            "profile_path": profile.source_path,
                        }

        return available_items

    @staticmethod
    def _select_item_ids(
        *,
        available_items: dict[str, dict[str, object]],
        selected_item_ids: list[str] | None,
    ) -> list[str]:
        """Validate and normalize the selected logical item identifiers."""

        if selected_item_ids is None:
            return sorted(
                logical_id
                for logical_id, context in available_items.items()
                if context["item"].selected
            )

        unique_ids = list(dict.fromkeys(selected_item_ids))

        unknown_ids = [
            logical_id
            for logical_id in unique_ids
            if logical_id not in available_items
        ]

        if unknown_ids:
            unknown_list = ", ".join(sorted(unknown_ids))
            raise ExecutionPlannerError(
                f"Identifiants de sauvegarde inconnus : {unknown_list}"
            )

        return sorted(unique_ids)

    def _resolve_item(
        self,
        *,
        root: Path,
        logical_id: str,
        item_context: dict[str, object],
        physical_files: dict[Path, PhysicalFile],
    ) -> tuple[ExecutionItem, int]:
        """Resolve one logical item and merge duplicate physical files."""

        item = item_context["item"]
        application_key = str(item_context["application_key"])
        profile_path = Path(str(item_context["profile_path"]))

        dependencies = self.dependency_resolver.resolve(
            application_key=application_key,
            category=item.category,
            profile_path=profile_path,
        )

        execution_file_paths: list[str] = []
        warnings: list[str] = []
        duplicate_count = 0

        for candidate, dependency in dependencies:
            physical_file, warning = self._build_physical_file(
                root=root,
                candidate=candidate,
                dependency=dependency,
                logical_id=logical_id,
            )

            if warning:
                warnings.append(warning)

            if physical_file is None:
                continue

            normalized_path = Path(physical_file.source_path).resolve(
                strict=False
            )

            existing_file = physical_files.get(normalized_path)

            if existing_file is not None:
                if logical_id not in existing_file.required_by:
                    existing_file.required_by.append(logical_id)
                    existing_file.required_by.sort()

                existing_file.mandatory = (
                    existing_file.mandatory or physical_file.mandatory
                )
                existing_file.potentially_locked = (
                    existing_file.potentially_locked
                    or physical_file.potentially_locked
                )

                for file_warning in physical_file.warnings:
                    if file_warning not in existing_file.warnings:
                        existing_file.warnings.append(file_warning)

                execution_file_paths.append(existing_file.source_path)
                duplicate_count += 1
                continue

            physical_files[normalized_path] = physical_file
            execution_file_paths.append(physical_file.source_path)

        return (
            ExecutionItem(
                logical_id=logical_id,
                category=item.category,
                application_key=application_key,
                application_name=str(
                    item_context["application_name"]
                ),
                user_name=str(item_context["user_name"]),
                profile_name=str(item_context["profile_name"]),
                encrypted=item.encrypted,
                files=sorted(
                    set(execution_file_paths),
                    key=str.casefold,
                ),
                warnings=warnings,
            ),
            duplicate_count,
        )

    def _build_physical_file(
        self,
        *,
        root: Path,
        candidate: Path,
        dependency: FileDependency,
        logical_id: str,
    ) -> tuple[PhysicalFile | None, str | None]:
        """Inspect one dependency while enforcing source-root isolation."""

        try:
            normalized_candidate = candidate.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            warning = (
                f"Impossible de résoudre le chemin {candidate} : {exc}"
            )
            return None, warning

        if not self._is_inside_root(root, normalized_candidate):
            warning = (
                "Chemin ignoré car situé hors de la source : "
                f"{normalized_candidate}"
            )
            return None, warning

        exists = normalized_candidate.exists()

        if not exists and not dependency.mandatory:
            return None, None

        warnings: list[str] = []

        if not exists:
            warning = (
                f"Dépendance obligatoire absente pour {logical_id} : "
                f"{normalized_candidate}"
            )
            warnings.append(warning)
        elif normalized_candidate.is_symlink():
            try:
                target = normalized_candidate.resolve(strict=True)
            except OSError as exc:
                warning = (
                    f"Lien symbolique illisible ignoré : "
                    f"{normalized_candidate} ({exc})"
                )
                return None, warning

            if not self._is_inside_root(root, target):
                warning = (
                    "Lien symbolique ignoré car sa cible est hors "
                    f"de la source : {normalized_candidate}"
                )
                return None, warning

        size_bytes = self._measure_path(normalized_candidate)

        try:
            relative_path = normalized_candidate.relative_to(root)
        except ValueError:
            warning = (
                "Chemin ignoré car impossible à rendre relatif à la "
                f"source : {normalized_candidate}"
            )
            return None, warning

        physical_file = PhysicalFile(
            source_path=str(normalized_candidate),
            relative_path=str(relative_path),
            size_bytes=size_bytes,
            required_by=[logical_id],
            mandatory=dependency.mandatory,
            exists=exists,
            potentially_locked=dependency.potentially_locked,
            warnings=warnings,
        )

        return physical_file, warnings[0] if warnings else None

    @staticmethod
    def _measure_path(path: Path) -> int:
        """Return the total byte size of a file or directory."""

        try:
            if path.is_file():
                return path.stat().st_size

            if not path.is_dir():
                return 0
        except OSError:
            return 0

        total_size = 0

        try:
            candidates = path.rglob("*")
        except OSError:
            return 0

        for candidate in candidates:
            try:
                if candidate.is_file():
                    total_size += candidate.stat().st_size
            except OSError:
                continue

        return total_size

    @staticmethod
    def _is_inside_root(root: Path, candidate: Path) -> bool:
        """Return whether a candidate path stays inside the source root."""

        try:
            candidate.relative_to(root)
        except ValueError:
            return False

        return True

    @staticmethod
    def _build_summary(
        *,
        execution_items: list[ExecutionItem],
        physical_files: list[PhysicalFile],
        deduplicated_files: int,
        warnings: list[str],
    ) -> ExecutionPlanSummary:
        """Calculate execution-plan statistics."""

        return ExecutionPlanSummary(
            logical_items=len(execution_items),
            physical_files=len(physical_files),
            missing_files=sum(
                1 for file in physical_files if not file.exists
            ),
            encrypted_items=sum(
                1 for item in execution_items if item.encrypted
            ),
            estimated_size_bytes=sum(
                file.size_bytes
                for file in physical_files
                if file.exists
            ),
            deduplicated_files=deduplicated_files,
            warnings=len(warnings),
        )


def build_execution_plan(
    source_root: str | Path,
    selected_item_ids: list[str] | None = None,
) -> ExecutionPlan:
    """Convenience entry point used by the API."""

    return ExecutionPlannerService().build_plan(
        source_root=source_root,
        selected_item_ids=selected_item_ids,
    )