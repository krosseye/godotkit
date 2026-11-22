import logging
import re
import shutil
import subprocess
from pathlib import Path

from godotkit.exceptions import GitError

logger = logging.getLogger(__name__)

_GIT_INSTALLED: bool | None = None


def git_installed() -> bool:
    """
    Checks if Git is installed on the system.

    Returns:
        True if Git is installed, False otherwise.
    """
    global _GIT_INSTALLED

    if _GIT_INSTALLED is not None:
        return _GIT_INSTALLED
    else:
        git_path = shutil.which("git")
        if git_path is None:
            logger.warning("Git is not installed or not found in PATH.")
            _GIT_INSTALLED = False
            return False

        logger.debug("Git found at: %s", git_path)
        _GIT_INSTALLED = True
        return True


def init_repo(
    dir_path: Path,
    gitignore: str | None = None,
    gitattributes: str | None = None,
    initial_branch: str = "main",
) -> None:
    """
    Initializes a Git repository in the given directory.

    Args:
        dir_path: The directory where the repository will be initialized.
        gitignore: Optional content for the .gitignore file.
        gitattributes: Optional content for the .gitattributes file.
        initial_branch: The name to use for the initial branch.

    Raises:
        ValueError: If `initial_branch` isn't a valid branch name.
        GitError: If Git is not installed or `git init` fails.
        OSError: If the directory or the Git files can't be written.
    """
    if not re.match(r"^[a-zA-Z0-9_\-\./]+$", initial_branch):
        raise ValueError(f"Invalid branch name: {initial_branch!r}")
    if not git_installed():
        raise GitError("Git is not installed")

    dir_path.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "init", "-b", initial_branch],
            cwd=dir_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"git init failed: {e.stderr.strip()}") from e
    except FileNotFoundError as e:
        raise GitError("Git command not found during execution") from e
    logger.info("Initialized Git repository in %s", dir_path)

    if gitignore:
        (dir_path / ".gitignore").write_text(gitignore, encoding="utf-8", newline="\n")
    if gitattributes:
        (dir_path / ".gitattributes").write_text(
            gitattributes, encoding="utf-8", newline="\n"
        )
