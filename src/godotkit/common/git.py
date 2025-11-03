import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

from godotkit.constants import GIT_CLONE_TIMEOUT

logger = logging.getLogger(__name__)


def git_installed() -> bool:
    """
    Checks if Git is installed on the system.

    Returns:
        True if Git is installed, False otherwise.
    """
    git_path = shutil.which("git")
    if git_path is None:
        logger.warning("Git is not installed or not found in PATH.")
        return False

    logger.debug("Git found at: %s", git_path)
    return True


def clone(
    repo_url: str,
    output_dir: Union[str, Path],
    repo_name: Optional[str] = None,
    overwrite: bool = False,
    depth: Optional[int] = None,
) -> Path:
    """
    Clones a Git repository into a specified output directory.

    Args:
        repo_url: The URL of the Git repository to clone.
        output_dir: The directory where the repository will be cloned into.
        repo_name: Optional name for the cloned directory. Defaults to the repository's name from the URL.
        overwrite: If True, removes the existing directory before cloning. If False and directory exists, skips.
        depth: Optional integer for a shallow clone ('--depth').

    Raises:
        Exception: If Git is not installed or the Git command fails unexpectedly.
        ValueError: If a repository name cannot be extracted from the URL.
        RuntimeError: For specific issues during cleanup or the clone process.

    Returns:
        The Path object to the newly cloned (or existing) repository directory.
    """
    if not git_installed():
        logger.error("Clone aborted: Git is not installed.")
        raise Exception("Git is not installed")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    final_repo_name = _get_repo_name(repo_url, repo_name)
    repo_path = output_dir / final_repo_name
    logger.debug("Target repository path: %s", repo_path)

    if not _handle_existing_repo(repo_path, overwrite):
        logger.info("Clone skipped, returning existing path: %s", repo_path)
        return repo_path

    _execute_git_clone(repo_url, repo_path, depth)

    logger.info("Successfully cloned repository to: %s", repo_path)
    return repo_path


def _get_repo_name(repo_url: str, repo_name: Optional[str]) -> str:
    if repo_name:
        logger.debug("Using user-provided repository name: %s", repo_name)
        return repo_name

    parsed_url = urlparse(repo_url)
    path_stem = Path(parsed_url.path).stem

    if not path_stem:
        logger.debug(
            "Failed to extract name using Path.stem, trying manual split on path: %s",
            parsed_url.path,
        )
        path_stem = parsed_url.path.rstrip("/").split("/")[-1]

    if not path_stem:
        logger.error("Could not extract a valid repository name from URL: %s", repo_url)
        raise ValueError(
            f"Could not extract a valid repository name from URL: {repo_url}"
        )

    return path_stem


def _handle_existing_repo(repo_path: Path, overwrite: bool) -> bool:
    if not repo_path.exists():
        logger.debug("Target path %s does not exist, proceeding with clone.", repo_path)
        return True

    if not overwrite:
        logger.info(
            "Directory %s exists and overwrite=False. Skipping clone.", repo_path
        )
        return False

    logger.warning(
        "Directory %s exists. Attempting removal for overwrite...", repo_path
    )
    try:
        shutil.rmtree(repo_path)
        logger.info("Successfully removed existing directory: %s", repo_path)
        return True
    except PermissionError as e:
        logger.error("Permission error removing directory %s: %s", repo_path, e)
        raise PermissionError(
            f"Failed to remove existing directory {repo_path} due to permission error."
        ) from e
    except shutil.Error as e:
        logger.error("Shutil error removing directory %s: %s", repo_path, e)
        raise RuntimeError(
            f"Failed to remove existing directory {repo_path}: shutil error."
        ) from e
    except Exception as e:
        logger.error("Unexpected error during removal of %s: %s", repo_path, e)
        raise RuntimeError(f"Unexpected error during removal of {repo_path}: {e}")


def _execute_git_clone(repo_url: str, repo_path: Path, depth: Optional[int]) -> None:
    command = ["git", "clone"]
    if depth is not None and depth > 0:
        command.extend(["--depth", str(depth)])

    command.extend([repo_url, str(repo_path)])

    logger.debug("Executing git command: %s", " ".join(command))

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=GIT_CLONE_TIMEOUT,
        )
        logger.debug("Git clone finished. Stdout: %s", result.stdout.strip())
        logger.debug("Git clone finished. Stderr: %s", result.stderr.strip())
    except subprocess.CalledProcessError as e:
        logger.error(
            "Git clone failed with return code %d: %s", e.returncode, e.stderr.strip()
        )
        raise RuntimeError(
            f"Git clone failed for '{repo_url}': {e.stderr.strip()}"
        ) from e
    except FileNotFoundError:
        logger.critical("Git executable not found in PATH during execution.")
        raise Exception("Git command not found during execution")
    except subprocess.TimeoutExpired:
        logger.error(
            "Git clone timed out after %d seconds for '%s'.",
            GIT_CLONE_TIMEOUT,
            repo_url,
        )
        raise RuntimeError(f"Git clone timed out for '{repo_url}'.")
    except Exception as e:
        logger.critical("Unexpected exception during git clone: %s", e)
        raise Exception(f"Unexpected error during cloning: {e}")
