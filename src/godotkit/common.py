import os
import platform
import subprocess
from pathlib import Path

from godotkit import __version__

USER_AGENT = f"GodotKit v{__version__} (Python: v{platform.python_version()}, Platform: {platform.system()})"


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
    if current_platform == "windows":
        os.startfile(path)
    elif current_platform == "darwin":
        subprocess.Popen(["open", path])
    elif current_platform == "linux":
        subprocess.Popen(["xdg-open", path])
    else:
        raise NotImplementedError(f"Unsupported platform: {current_platform}")
