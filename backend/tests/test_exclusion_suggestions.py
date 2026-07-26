from pathlib import Path

from app.modules.source_discovery.exclusions import suggest_exclusions
from app.modules.source_discovery.service import SourceDiscoveryService


def _allow_test_root(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda self, source_root: root,
    )


def test_suggestions_are_disabled_and_context_aware(tmp_path, monkeypatch):
    _allow_test_root(monkeypatch, tmp_path)

    project = tmp_path / "Users" / "fred" / "Projects" / "webapp"
    node_modules = project / "node_modules"
    node_modules.mkdir(parents=True)
    (project / "package.json").write_text("{}", encoding="utf-8")
    (node_modules / "package.js").write_text("x", encoding="utf-8")

    python_project = tmp_path / "Users" / "fred" / "Projects" / "api"
    venv = python_project / ".venv"
    venv.mkdir(parents=True)
    (python_project / "pyproject.toml").write_text("[project]", encoding="utf-8")
    (venv / "python.exe").write_bytes(b"python")

    report = suggest_exclusions(tmp_path)

    assert {item.pattern for item in report.suggestions} == {"node_modules", ".venv"}
    assert all(item.selected is False for item in report.suggestions)
    assert all(item.risk == "faible" for item in report.suggestions)
    assert report.total_suggested_file_count == 2
    assert report.selected_size_bytes == 0


def test_node_modules_without_package_json_is_not_suggested(tmp_path, monkeypatch):
    _allow_test_root(monkeypatch, tmp_path)
    (tmp_path / "Users" / "fred" / "orphan" / "node_modules").mkdir(parents=True)

    report = suggest_exclusions(tmp_path)

    assert report.suggestions == []


def test_git_is_suggested_only_when_remote_exists(tmp_path, monkeypatch):
    _allow_test_root(monkeypatch, tmp_path)
    remote_git = tmp_path / "Users" / "fred" / "remote" / ".git"
    remote_git.mkdir(parents=True)
    (remote_git / "config").write_text(
        '[remote "origin"]\n\turl = https://example.test/repo.git\n',
        encoding="utf-8",
    )
    local_git = tmp_path / "Users" / "fred" / "local" / ".git"
    local_git.mkdir(parents=True)
    (local_git / "config").write_text("[core]\n", encoding="utf-8")

    report = suggest_exclusions(tmp_path)

    assert len(report.suggestions) == 1
    suggestion = report.suggestions[0]
    assert suggestion.pattern == ".git"
    assert suggestion.risk == "moyen"
    assert suggestion.prerequisites == ["dépôt distant configuré"]


def test_personal_folders_are_never_suggested(tmp_path, monkeypatch):
    _allow_test_root(monkeypatch, tmp_path)
    user = tmp_path / "Users" / "fred"
    for folder in ("Documents", "Desktop", "Pictures", "Downloads", "AppData"):
        path = user / folder
        path.mkdir(parents=True)
        (path / "personal.txt").write_text("important", encoding="utf-8")

    report = suggest_exclusions(tmp_path)

    assert report.suggestions == []
