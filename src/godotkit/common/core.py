import logging
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def open_directory(path: Path) -> None:
    """
    Opens the given directory in the native file manager.

    Args:
        path (Path): The path to the directory to open.

    Raises:
        ValueError: If the provided path is not a valid directory.
        NotImplementedError: If the current platform is unsupported.
    """
    if not path.is_dir():
        raise ValueError("Invalid directory path")

    current_platform = platform.system().lower()
    quoted_path = shlex.quote(str(path))

    if current_platform == "windows":
        if hasattr(os, "startfile"):
            os.startfile(str(path))
        else:
            run_utility_command(["cmd", "/C", "start", quoted_path])
    elif current_platform == "darwin":
        run_utility_command(["open", quoted_path])
    elif current_platform == "linux":
        run_utility_command(["xdg-open", quoted_path])
    else:
        raise NotImplementedError(f"Unsupported platform: {current_platform}")


def remove_directory(dir_path: Path) -> None:
    """Recursively deletes a directory and all its contents.

    Args:
        dir_path (Path): Path to the directory to delete.

    Raises:
        ValueError: If the path does not exist or is not a directory.
        OSError: If an OS-related error occurs during deletion.
        PermissionError: If the process lacks permission to delete files or subdirectories.
    """
    if not dir_path.is_dir():
        msg = f"Invalid directory path: '{dir_path}'"
        logger.error(msg)
        raise ValueError(msg)
    try:
        shutil.rmtree(dir_path)
        logger.info("Removed directory '%s'", dir_path)
    except Exception:
        logger.exception("Failed to remove directory '%s'", dir_path)
        raise


def run_utility_command(
    command: list[str],
    working_dir: Optional[Path] = None,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    """Runs a system command, waits for it to complete, and captures output.

    Args:
        command (List[str]): Command and arguments, e.g. ['ls', '-l'].
        working_dir (Optional[Path]): Working directory for the command.
        timeout (Optional[int]): Timeout in seconds.

    Returns:
        subprocess.CompletedProcess: Result object containing stdout, stderr, and return code.

    Raises:
        subprocess.CalledProcessError: If the command fails (non-zero return code).
        subprocess.TimeoutExpired: If the command times out.
        ValueError: If the working directory is invalid.
    """
    cmd_str = " ".join(command)
    logger.debug("Executing utility command: %s", cmd_str)

    if working_dir is not None and not working_dir.is_dir():
        raise ValueError(f"Invalid working directory: {working_dir}")

    return subprocess.run(
        command,
        cwd=None if working_dir is None else str(working_dir),
        timeout=timeout,
        check=True,
        capture_output=True,
        text=True,
    )


def launch_daemon_command(
    command: list[str],
    working_dir: Optional[Path] = None,
) -> None:
    """Launches a system command in a non-blocking, detached manner.

    Args:
        command (List[str]): Command and arguments, e.g. ['xdg-open', 'file.pdf'].
        working_dir (Optional[Path]): Working directory for the command.

    Raises:
        ValueError: If the working directory is invalid.
    """
    cmd_str = " ".join(command)
    logger.debug("Launching background command: %s", cmd_str)

    if working_dir is not None and not working_dir.is_dir():
        raise ValueError(f"Invalid working directory: {working_dir}")

    if os.name == "nt":
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
        subprocess.Popen(
            command,
            cwd=None if working_dir is None else str(working_dir),
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            command,
            cwd=None if working_dir is None else str(working_dir),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
