from pathlib import Path

from godotkit.common import open_directory as open_dir
from godotkit.common import remove_directory


def open_directory(project_dir: Path) -> None:
    """
    Opens the given project directory in the native file manager.

    Args:
        project_dir (Path): The path to the directory to open.

    Raises:
        ValueError: If the provided path is not a valid project directory.
        NotImplementedError: If the current platform is unsupported.
    """
    open_dir(project_dir)


def remove(project_path: Path) -> None:
    """
    Recursively removes the provided project directory.

    Args:
        project_path (Path): The '.godot' project file path.

    Raises:
        ValueError: If the path does not exist or is not a directory.
        OSError: If an OS-related error occurs during deletion.
        PermissionError: If the process lacks permission to delete files or subdirectories.
    """
    remove_directory(project_path)
