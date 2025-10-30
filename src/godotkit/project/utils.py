import subprocess
from pathlib import Path

from godotkit import common


def open_directory(project_dir: Path) -> None:
    """
    Opens the given project directory in the native file manager.

    Args:
        project_dir (Path): The path to the directory to open.

    Raises:
        ValueError: If the provided path is not a valid project directory.
        NotImplementedError: If the current platform is unsupported.
    """
    common.open_directory(project_dir)


def start(binary_path: Path, project_path: Path) -> None:
    """
    Launches the provided project file with the given Godot Engine.

    Args:
        binary_path (Path): The path to the Godot Engine binary.
        project_path (Path): The '.godot' project file path.

    Raises:
        ValueError: If the provided path is not a valid file.
    """
    if not binary_path.is_file():
        raise ValueError("Invalid binary file path")

    if project_path.is_dir() or not str(project_path).endswith(".godot"):
        raise ValueError("Invalid project file path")

    try:
        command: list[str] = []
        command.append(str(binary_path))
        command.append("-e")
        subprocess.Popen(command, cwd=project_path.parent)
    except Exception as e:
        print(f"Failed to launch Godot Engine: {e}")
