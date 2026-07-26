"""Read-only and conservative exclusion suggestion engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .diagnostic import _safe_directory_estimate
from .exclusion_schemas import (
    ExclusionCategory,
    ExclusionRisk,
    ExclusionSuggestion,
    ExclusionSuggestionReport,
)
from .service import SourceDiscoveryService


@dataclass(frozen=True, slots=True)
class Rule:
    pattern: str
    category: ExclusionCategory
    risk: ExclusionRisk
    reason: str


RULES = {
    "node_modules": Rule(
        "node_modules",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Dépendances Node.js généralement recréables avec le gestionnaire de paquets.",
    ),
    ".venv": Rule(
        ".venv",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Environnement Python local généralement recréable depuis les dépendances.",
    ),
    "venv": Rule(
        "venv",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Environnement Python local généralement recréable depuis les dépendances.",
    ),
    ".tox": Rule(
        ".tox",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Environnements de test tox généralement recréables.",
    ),
    ".pytest_cache": Rule(
        ".pytest_cache",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Cache de tests Python recréable.",
    ),
    ".mypy_cache": Rule(
        ".mypy_cache",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Cache d'analyse statique recréable.",
    ),
    ".next": Rule(
        ".next",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Sortie de compilation Next.js généralement recréable.",
    ),
    ".nuxt": Rule(
        ".nuxt",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Sortie de compilation Nuxt généralement recréable.",
    ),
    "target": Rule(
        "target",
        ExclusionCategory.RECREATABLE,
        ExclusionRisk.LOW,
        "Sortie de compilation généralement recréable.",
    ),
    ".git": Rule(
        ".git",
        ExclusionCategory.REVIEW,
        ExclusionRisk.MEDIUM,
        "Historique Git récupérable uniquement si le dépôt distant est à jour.",
    ),
    "vendor": Rule(
        "vendor",
        ExclusionCategory.REVIEW,
        ExclusionRisk.MEDIUM,
        "Dépendances Composer généralement recréables depuis composer.lock.",
    ),
    ".idea": Rule(
        ".idea",
        ExclusionCategory.REVIEW,
        ExclusionRisk.MEDIUM,
        "Configuration locale JetBrains pouvant contenir des réglages utiles.",
    ),
    ".vscode": Rule(
        ".vscode",
        ExclusionCategory.REVIEW,
        ExclusionRisk.MEDIUM,
        "Configuration locale VS Code pouvant contenir des réglages de projet.",
    ),
    ".vs": Rule(
        ".vs",
        ExclusionCategory.REVIEW,
        ExclusionRisk.MEDIUM,
        "Cache et configuration locale Visual Studio à examiner.",
    ),
}

DEPENDENCY_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "uv.lock",
)

SKIPPED_ROOTS = {
    "$recycle.bin",
    "system volume information",
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
}


def _contains_any(parent: Path, names: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for name in names:
        try:
            if (parent / name).is_file():
                found.append(name)
        except OSError:
            continue
    return found


def _git_has_remote(path: Path) -> bool:
    config = path / "config"
    try:
        if not config.is_file():
            return False
        text = config.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return '[remote "' in text and "url =" in text


def _eligible(candidate: Path, rule: Rule) -> tuple[bool, list[str], list[str]]:
    parent = candidate.parent
    prerequisites: list[str] = []
    warnings: list[str] = []

    if rule.pattern == "node_modules":
        prerequisites = _contains_any(parent, ("package.json",))
        return bool(prerequisites), prerequisites, warnings

    if rule.pattern in {".venv", "venv", ".tox"}:
        prerequisites = _contains_any(parent, DEPENDENCY_FILES)
        return bool(prerequisites), prerequisites, warnings

    if rule.pattern == "vendor":
        prerequisites = _contains_any(parent, ("composer.json", "composer.lock"))
        return "composer.json" in prerequisites, prerequisites, warnings

    if rule.pattern == ".git":
        if not _git_has_remote(candidate):
            warnings.append("Aucun dépôt distant détecté : exclusion non proposée.")
            return False, prerequisites, warnings
        prerequisites.append("dépôt distant configuré")

    return True, prerequisites, warnings


def suggest_exclusions(source_root: str | Path) -> ExclusionSuggestionReport:
    """Inspect a source without writing and return disabled-by-default suggestions."""

    root = SourceDiscoveryService()._validate_source_root(source_root)
    suggestions: list[ExclusionSuggestion] = []
    warnings: list[str] = []

    def onerror(error: OSError) -> None:
        warnings.append(f"Impossible de parcourir un dossier : {error}")

    for current_root, directories, _files in os.walk(
        root,
        topdown=True,
        followlinks=False,
        onerror=onerror,
    ):
        current = Path(current_root)
        filtered: list[str] = []
        for directory in directories:
            candidate = current / directory
            normalized = directory.casefold()
            try:
                if candidate.is_symlink():
                    continue
            except OSError as exc:
                warnings.append(f"Impossible d'inspecter {candidate} : {exc}")
                continue

            if current == root and normalized in SKIPPED_ROOTS:
                filtered.append(directory)
                continue

            rule = RULES.get(directory)
            if rule is None:
                filtered.append(directory)
                continue

            eligible, prerequisites, local_warnings = _eligible(candidate, rule)
            warnings.extend(local_warnings)
            if not eligible:
                filtered.append(directory)
                continue

            size_bytes, file_count, estimate_warnings = _safe_directory_estimate(candidate)
            suggestions.append(
                ExclusionSuggestion(
                    path=str(candidate),
                    pattern=rule.pattern,
                    category=rule.category,
                    size_bytes=size_bytes,
                    file_count=file_count,
                    reason=rule.reason,
                    risk=rule.risk,
                    selected=False,
                    prerequisites=prerequisites,
                    warnings=estimate_warnings,
                )
            )
            # Do not scan inside an already suggested directory.

        directories[:] = filtered

    suggestions.sort(key=lambda item: (item.risk, item.path.casefold()))
    return ExclusionSuggestionReport(
        source_root=str(root),
        suggestions=suggestions,
        total_suggested_size_bytes=sum(item.size_bytes for item in suggestions),
        total_suggested_file_count=sum(item.file_count for item in suggestions),
        selected_size_bytes=0,
        estimated_size_after_exclusions_bytes=None,
        warnings=warnings,
    )


__all__ = ["suggest_exclusions"]
