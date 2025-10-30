import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

from godotkit.constants import GIT_CLONE_TIMEOUT


def git_installed() -> bool:
    """
    Checks if Git is installed on the system.

    Returns:
        True if Git is installed, False otherwise.
    """
    if shutil.which("git") is None:
        return False
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
        raise Exception("Git is not installed")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    final_repo_name = _get_repo_name(repo_url, repo_name)
    repo_path = output_dir / final_repo_name

    if not _handle_existing_repo(repo_path, overwrite):
        return repo_path

    _execute_git_clone(repo_url, repo_path, depth)

    return repo_path


def _get_repo_name(repo_url: str, repo_name: Optional[str]) -> str:
    if repo_name:
        return repo_name

    parsed_url = urlparse(repo_url)

    path_stem = Path(parsed_url.path).stem

    if not path_stem:
        path_stem = parsed_url.path.rstrip("/").split("/")[-1]

    if not path_stem:
        raise ValueError(
            f"Could not extract a valid repository name from URL: {repo_url}"
        )

    return path_stem


def _handle_existing_repo(repo_path: Path, overwrite: bool) -> bool:
    if not repo_path.exists():
        return True

    if not overwrite:
        print(f"Directory {repo_path} exists. Skipping clone.")
        return False

    print(f"Directory {repo_path} exists. Removing it for overwrite...")
    try:
        shutil.rmtree(repo_path)
        return True
    except PermissionError as e:
        raise PermissionError(
            f"Failed to remove existing directory {repo_path} due to permission error."
        ) from e
    except shutil.Error as e:
        raise RuntimeError(
            f"Failed to remove existing directory {repo_path}: shutil error."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error during removal of {repo_path}: {e}")


def _execute_git_clone(repo_url: str, repo_path: Path, depth: Optional[int]) -> None:
    command = ["git", "clone"]
    if depth is not None and depth > 0:
        command.extend(["--depth", str(depth)])

    command.extend([repo_url, str(repo_path)])

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=GIT_CLONE_TIMEOUT,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Git clone failed for '{repo_url}': {e.stderr.strip()}"
        ) from e
    except FileNotFoundError:
        raise Exception("Git command not found during execution")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Git clone timed out for '{repo_url}'.")
    except Exception as e:
        raise Exception(f"Unexpected error during cloning: {e}")
