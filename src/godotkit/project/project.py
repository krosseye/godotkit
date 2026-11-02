from pathlib import Path
from typing import cast

from godotkit.project.utils import open_directory

from ..engine.version_parsing import GodotVersion
from .parse import ProjectMetadata, read, update
from .utils import remove, start


class GodotProject:
    """
    Represents a Godot project, providing utilities to manage and interact with it.
    """

    def __init__(self, file_path: Path) -> None:
        """
        Initializes a GodotProject instance.

        Args:
            file_path (Path): Path to the project.godot file.

        Raises:
            FileNotFoundError: If the provided path is not a valid file.
        """
        self._file_path = file_path

        if not self._file_path.is_file():
            raise FileNotFoundError(f"Project file not found: {self._file_path}")

        self.metadata: ProjectMetadata = read(self._file_path)

    def _update(self, **changes) -> None:
        update(self._file_path, cast(ProjectMetadata, changes))
        self.metadata = read(self._file_path)

    @property
    def name(self) -> str:
        """
        Returns the name of the project.
        """
        return self.metadata.get("name") or "Unnamed Project"

    @name.setter
    def name(self, value: str) -> None:
        """
        Sets the name of the project.
        """
        self._update(name=value)

    @property
    def description(self) -> str:
        """
        Returns the description of the project.
        """
        return self.metadata.get("description") or "No description provided."

    @description.setter
    def description(self, value: str) -> None:
        """
        Sets the description of the project.
        """
        self._update(description=value)

    @property
    def version(self) -> str:
        """
        Returns the version of the project.
        """
        return self.metadata.get("version") or "0.1.0"

    @version.setter
    def version(self, value: str) -> None:
        """
        Sets the version of the project.
        """
        self._update(version=value)

    @property
    def tags(self) -> list[str] | None:
        """
        Returns the list of tags associated with the project.
        """
        return self.metadata.get("tags")

    @tags.setter
    def tags(self, value: list[str]) -> None:
        """
        Sets the list of tags associated with the project.
        """
        self._update(tags=value)

    @property
    def file_path(self) -> Path:
        """
        Returns the path to the project.godot file.
        """
        return self._file_path

    @property
    def dir_path(self) -> Path:
        """
        Returns the path to the project directory.
        """
        return self._file_path.parent

    @property
    def icon_path(self) -> Path | None:
        """
        Returns the path to the project icon.
        """
        return self.metadata.get("icon_path")

    @property
    def engine_version(self) -> GodotVersion | None:
        """
        Returns the engine version associated with the project.
        """
        return self.metadata.get("engine_version")

    @engine_version.setter
    def engine_version(self, value: GodotVersion) -> None:
        """
        Sets the engine version associated with the project.
        """
        self._update(engine_version=value)

    @property
    def compatibility_version(self) -> GodotVersion | None:
        """
        Returns the compatibility version associated with the project.
        """
        return self.metadata.get("compatibility_version")

    @compatibility_version.setter
    def compatibility_version(self, value: GodotVersion) -> None:
        """
        Sets the compatibility version associated with the project.
        """
        self._update(compatibility_version=value)

    def start(self, binary_path: Path) -> None:
        """
        Launches the project with the provided Godot Engine binary.

        Args:
            binary_path (Path): Path to the Godot Engine binary.

        Raises:
            FileNotFoundError: If the provided path is not a valid file.
        """
        start(binary_path, self._file_path)

    def open_directory(self) -> None:
        """
        Opens the project directory in the native file manager.

        Raises:
            ValueError: If the path is not a valid project directory.
            NotImplementedError: If the current platform is unsupported.
        """
        open_directory(self.dir_path)

    def remove(self) -> None:
        """
        Recursively removes the project directory.

        Raises:
            ValueError: If the path does not exist or is not a directory.
            OSError: If an OS-related error occurs during deletion.
            PermissionError: If the process lacks permission to delete files or subdirectories.
        """
        remove(self.dir_path)
