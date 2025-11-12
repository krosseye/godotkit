from pathlib import Path

from godotkit.project.utils import start as start_project

from .utils import find_binary, open_directory, remove, start
from .version_parsing import GodotVersion


class GodotEngine:
    def __init__(self, version: GodotVersion, engine_dir: Path):
        self.version = version
        self.directory_path = engine_dir

        bin_file = find_binary(engine_dir)
        if bin_file:
            self.binary_path = bin_file
        else:
            raise ValueError("Cannot find Godot binary")

    def start(self) -> None:
        """
        Launches the Godot Engine executable.

        Raises:
            ValueError: If the provided path is not a valid file.
        """
        start(self.binary_path)

    def start_project(self, project_path: Path) -> None:
        """
        Launches the provided project file with this version of the Godot Engine.

        Args:
            project_path (Path): The '.godot' project file path.

        Raises:
            ValueError: If the provided path is not a valid file.
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
