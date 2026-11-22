import subprocess
from pathlib import Path

import pytest

from godotkit._common import init_repo
from godotkit.exceptions import GitError


def test_invalid_branch_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        init_repo(tmp_path, initial_branch="bad branch")


def test_missing_git_raises(tmp_path: Path, mocker):
    mocker.patch("godotkit._common.git.git_installed", return_value=False)
    with pytest.raises(GitError, match="not installed"):
        init_repo(tmp_path)


def test_git_failure_raises(tmp_path: Path, mocker):
    mocker.patch("godotkit._common.git.git_installed", return_value=True)
    error = subprocess.CalledProcessError(128, ["git", "init"], stderr="fatal: nope\n")
    mocker.patch("godotkit._common.git.subprocess.run", side_effect=error)
    with pytest.raises(GitError, match="fatal: nope"):
        init_repo(tmp_path, gitignore="*.tmp")
    assert not (tmp_path / ".gitignore").exists()
