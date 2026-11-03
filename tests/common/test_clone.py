from pathlib import Path

import pytest

from godotkit.common import clone

URL = "https://example.com/org/demo.git"


def fake_clone(repo_url: str, repo_path: Path, depth: int | None) -> None:
    repo_path.mkdir()
    (repo_path / "file.txt").write_text("new", encoding="utf-8")


def failing_clone(repo_url: str, repo_path: Path, depth: int | None) -> None:
    repo_path.mkdir()
    raise RuntimeError("Git clone failed")


@pytest.fixture
def existing_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "file.txt").write_text("old", encoding="utf-8")
    return repo


@pytest.fixture(autouse=True)
def git_available(mocker):
    mocker.patch("godotkit.common.git.git_installed", return_value=True)


class TestClone:
    def test_clones_into_new_directory(self, tmp_path: Path, mocker):
        mocker.patch("godotkit.common.git._execute_git_clone", side_effect=fake_clone)
        repo = clone(URL, tmp_path)
        assert repo == tmp_path / "demo"
        assert (repo / "file.txt").read_text(encoding="utf-8") == "new"

    def test_existing_without_overwrite_is_skipped(
        self, tmp_path: Path, existing_repo: Path, mocker
    ):
        git = mocker.patch("godotkit.common.git._execute_git_clone")
        assert clone(URL, tmp_path) == existing_repo
        git.assert_not_called()

    def test_overwrite_replaces_existing(
        self, tmp_path: Path, existing_repo: Path, mocker
    ):
        mocker.patch("godotkit.common.git._execute_git_clone", side_effect=fake_clone)
        clone(URL, tmp_path, overwrite=True)
        assert (existing_repo / "file.txt").read_text(encoding="utf-8") == "new"
        assert [p.name for p in tmp_path.iterdir()] == ["demo"]

    def test_failed_overwrite_keeps_existing(
        self, tmp_path: Path, existing_repo: Path, mocker
    ):
        mocker.patch(
            "godotkit.common.git._execute_git_clone", side_effect=failing_clone
        )
        with pytest.raises(RuntimeError):
            clone(URL, tmp_path, overwrite=True)
        assert (existing_repo / "file.txt").read_text(encoding="utf-8") == "old"
        assert [p.name for p in tmp_path.iterdir()] == ["demo"]
