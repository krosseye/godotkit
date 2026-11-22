from pathlib import Path

from godotkit.common import launch_daemon_command, remove_directory
from godotkit.common import open_directory as open_dir


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


def start(binary_path: Path, project_path: Path) -> None:
    """
    Launches the provided project file with the given Godot Engine.

    Args:
        binary_path (Path): The path to the Godot Engine binary.
        project_path (Path): The '.godot' project file path.

    Raises:
        FileNotFoundError: If `binary_path` or `project_path` is not a file.
        OSError: If the binary can't be started.
    """
    if not binary_path.is_file():
        raise FileNotFoundError(f"Godot binary not found: {binary_path}")
    if not project_path.is_file():
        raise FileNotFoundError(f"Project file not found: {project_path}")
    launch_daemon_command(
        [str(binary_path), "--path", str(project_path.parent), "--editor"]
    )


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
