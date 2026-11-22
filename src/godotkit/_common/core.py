import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def run_utility_command(
    command: list[str],
    working_dir: Path | None = None,
    timeout: int | None = None,
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
        FileNotFoundError: If the working directory does not exist.
    """
    cmd_str = " ".join(command)
    logger.debug("Executing utility command: %s", cmd_str)

    if working_dir is not None and not working_dir.is_dir():
        raise FileNotFoundError(f"Invalid working directory: {working_dir}")

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
    working_dir: Path | None = None,
    output: Path | None = None,
) -> subprocess.Popen:
    """Launches a system command in a non-blocking, detached manner.

    Args:
        command (List[str]): Command and arguments, e.g. ['xdg-open', 'file.pdf'].
        working_dir (Optional[Path]): Working directory for the command.
        output (Optional[Path]): File that receives stdout and stderr (overwritten).
            Discarded when omitted.

    Returns:
        The started process.

    Raises:
        FileNotFoundError: If the working directory does not exist.
        OSError: If the command or the output file can't be opened.
    """
    logger.debug("Launching background command: %s", " ".join(command))

    if working_dir is not None and not working_dir.is_dir():
        raise FileNotFoundError(f"Invalid working directory: {working_dir}")

    if sys.platform == "win32":
        flags = {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
        }
    else:
        flags = {"start_new_session": True}

    with open(output or os.devnull, "wb") as out:
        return subprocess.Popen(
            command,
            cwd=working_dir,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            **flags,  # type: ignore[call-overload]
        )
