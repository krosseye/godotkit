import logging
import os
import platform
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import httpx

from godotkit.common import launch_daemon_command, remove_directory
from godotkit.common import open_directory as open_dir
from godotkit.constants import RELEASE_DOWNLOAD_TIMEOUT, USER_AGENT

from .exceptions import DownloadError, ExtractError

logger = logging.getLogger(__name__)


def _extract_with_modes(zip_ref: zipfile.ZipFile, dest: Path) -> None:
    """Extracts all members, restoring the Unix permissions zipfile drops."""
    for info in zip_ref.infolist():
        path = zip_ref.extract(info, dest)
        mode = (info.external_attr >> 16) & 0o777  # Unix permission bits
        if (
            os.name == "posix"
            and info.create_system == 3  # made on Unix
            and mode
            and not info.is_dir()
        ):
            os.chmod(path, mode)


def find_binary(dir_path: Path) -> Path | None:
    """
    Finds the Godot binary in a given folder.

    Args:
        dir_path (Path): The path to the folder containing the binary.

    Returns:
        The path to the Godot binary if found, otherwise None.

    Raises:
        ValueError: If the provided path is not a valid directory.
        NotImplementedError: If the current platform is not supported.
    """
    folder_path = Path(dir_path)
    if not folder_path.is_dir():
        raise ValueError(f"The provided path '{dir_path}' is not a valid directory.")

    current_platform = platform.system().lower()

    if current_platform == "windows":
        for file in folder_path.glob("Godot*.exe"):
            filename_lower = file.name.lower()
            if not filename_lower.endswith("console.exe"):
                return file.resolve()
        return None

    elif current_platform == "darwin":
        for file in sorted(folder_path.glob("*.app/Contents/MacOS/Godot")):
            if file.is_file():
                return file.resolve()
        return None

    elif current_platform == "linux":
        # Names vary too much by version and arch, so match the ELF header.
        for file in sorted(folder_path.glob("Godot*")):
            if file.is_file():
                with file.open("rb") as f:
                    if f.read(4) == b"\x7fELF":
                        return file.resolve()
        return None
    else:
        raise NotImplementedError(f"Unsupported platform: {current_platform}")


def open_directory(engine_dir: Path) -> None:
    """
    Opens the given engine directory in the native file manager.

    Args:
        engine_dir (Path): The path to the directory to open.

    Raises:
        ValueError: If the provided path is not a valid directory.
        NotImplementedError: If the current platform is unsupported.
    """
    open_dir(engine_dir)


def start(binary_path: Path) -> None:
    """
    Launches the Godot Engine executable found at the given path.

    Args:
        binary_path (Path): The full path to the Godot binary file.

    Raises:
        ValueError: If the provided path is not a valid file.
    """
    if not binary_path.is_file():
        logger.error("Invalid binary file path")
        raise ValueError("Invalid binary file path")

    try:
        command: list[str] = []
        command.append(str(binary_path))
        launch_daemon_command(command)

    except Exception:
        logger.exception("Failed to launch Godot Engine")


def remove(engine_dir: Path) -> None:
    """
    Recursively removes the Godot Engine installation directory.

    Args:
        engine_dir (Path): The path to the directory to remove.

    Raises:
        ValueError: If the path does not exist or is not a directory.
        OSError: If an OS-related error occurs during deletion.
        PermissionError: If the process lacks permission to delete files or subdirectories.
    """
    remove_directory(engine_dir)


def download_and_extract(
    url: str,
    save_path: Path,
    timeout: float = RELEASE_DOWNLOAD_TIMEOUT,
    overwrite: bool = False,
    progress_callback: Callable[[int, int | None], None] | None = None,
) -> None:
    """
    Downloads a zip file from the given URL and extracts its contents.

    Args:
        url: The URL to download the zip file from.
        save_path: The directory path to save the extracted contents to.
        timeout: HTTP request timeout in seconds.
        overwrite: Whether to overwrite existing files on extraction.
        progress_callback: Optional callback(progress_bytes, total_bytes) to track download progress.

    Raises:
        DownloadError: On network or write failure.
        ExtractError: On invalid or failed zip extraction.
        ValueError: If the zip is empty.
    """
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        temp_zip = tmp_path / "download.zip"
        temp_extract = tmp_path / "extract"

        # Download phase
        try:
            with httpx.stream(
                "GET", url, headers=headers, follow_redirects=True, timeout=timeout
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise DownloadError(
                        f"HTTP error: {e.response.status_code} {e.response.reason_phrase} for URL: {url}"
                    ) from e

                total_bytes = int(response.headers.get("Content-Length", 0)) or None
                downloaded = 0

                try:
                    with temp_zip.open("wb") as f:
                        for chunk in response.iter_bytes():
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_bytes)
                except OSError as e:
                    raise DownloadError(f"Failed to write to {temp_zip}: {e}") from e

        except httpx.RequestError as e:
            raise DownloadError(f"Network error during download from {url}: {e}") from e
        except Exception as e:
            if not isinstance(e, DownloadError):
                raise DownloadError(f"Unexpected error during download: {e}") from e
            raise

        # Extract phase
        try:
            if not zipfile.is_zipfile(temp_zip):
                raise ExtractError(
                    f"File downloaded from {url} is not a valid zip file."
                )

            with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                members = zip_ref.namelist()
                if not members:
                    raise ValueError(f"The zip file from {url} is empty.")

                temp_extract.mkdir(parents=True, exist_ok=True)
                _extract_with_modes(zip_ref, temp_extract)

            extracted_items = list(temp_extract.iterdir())

            if (
                len(extracted_items) == 1
                and extracted_items[0].is_dir()
                and extracted_items[0].suffix != ".app"
            ):
                source_dir = extracted_items[0]
            else:
                source_dir = temp_extract

            for item in source_dir.iterdir():
                dest = save_path / item.name
                if dest.exists():
                    if overwrite:
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    else:
                        continue
                shutil.move(str(item), str(dest))

        except zipfile.BadZipFile as e:
            raise ExtractError(
                f"The downloaded file is not a valid zip archive: {e}"
            ) from e
        except (OSError, shutil.Error) as e:
            raise ExtractError(f"Error during extraction or file move: {e}") from e
