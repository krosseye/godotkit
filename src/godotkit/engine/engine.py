from pathlib import Path

from godotkit.project.utils import start as start_project

from .utils import find_binary, open_directory, remove, start
from .version_parsing import GodotVersion


class GodotEngine:
    def __init__(self, version: GodotVersion, engine_dir: Path):
        """
        Raises:
            FileNotFoundError: If `engine_dir` is missing or has no Godot binary.
        """
        self.version = version
        self.directory_path = engine_dir

        bin_file = find_binary(engine_dir)
        if bin_file:
            self.binary_path = bin_file
        else:
            raise FileNotFoundError(f"Cannot find Godot binary in {engine_dir}")

    def start(self) -> None:
        """
        Launches the Godot Engine executable.

        Raises:
            FileNotFoundError: If the binary is gone.
            OSError: If the binary can't be started.
        """
        start(self.binary_path)

    def start_project(self, project_path: Path) -> None:
        """
        Launches the provided project file with this version of the Godot Engine.

        Args:
            project_path (Path): The '.godot' project file path.

        Raises:
            FileNotFoundError: If the binary or the project file is missing.
            OSError: If the binary can't be started.
        """
        start_project(self.binary_path, project_path)

    def open_directory(self) -> None:
        """
        Opens the engine directory in the native file manager.

        Raises:
            ValueError: If the path is not a valid directory.
            NotImplementedError: If the current platform is unsupported.
        """
        open_directory(self.directory_path)

    def remove(self) -> None:
        """
        Recursively removes the Godot Engine installation directory.

        Raises:
            ValueError: If the path does not exist or is not a directory.
            OSError: If an OS-related error occurs during deletion.
            PermissionError: If the process lacks permission to delete files or subdirectories.
        """
        remove(self.directory_path)
