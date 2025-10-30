from pathlib import Path

from godotkit.engine import GodotVersion
from godotkit.engine.utils import find_binary, open_directory, remove, start
from godotkit.project.utils import start as start_project


class GodotEngine:
    def __init__(self, version: GodotVersion, engine_dir: Path):
        self.version = version
        self.directory_path = engine_dir

        bin_dir = find_binary(engine_dir)
        if bin_dir:
            self.binary_path = bin_dir
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
            ValueError: If the path is not a valid directory.
        """
        remove(self.directory_path)
