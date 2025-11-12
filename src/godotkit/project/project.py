from pathlib import Path
from typing import Optional, Union

from godotkit.project.utils import open_directory

from ..engine.version_parsing import GodotVersion
from .parse import (
    ProjectMetadata,
    read,
    set_compatibility_version,
    set_description,
    set_engine_version,
    set_name,
    set_tags,
    set_version,
)
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
        set_name(self._file_path, value)
        self.metadata["name"] = value

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
        set_description(self._file_path, value)
        self.metadata["description"] = value

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
        set_version(self._file_path, value)
        self.metadata["version"] = value

    @property
    def tags(self) -> Optional[list[str]]:
        """
        Returns the list of tags associated with the project.
        """
        return self.metadata.get("tags")

    @tags.setter
    def tags(self, value: list[str]) -> None:
        """
        Sets the list of tags associated with the project.
        """
        set_tags(self._file_path, value)
        self.metadata["tags"] = value

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
    def icon_path(self) -> Optional[Path]:
        """
        Returns the path to the project icon.
        """
        return self.metadata.get("icon_path")

    @property
    def engine_version(self) -> Optional[GodotVersion]:
        """
        Returns the engine version associated with the project.
        """
        return self.metadata.get("engine_version")

    @engine_version.setter
    def engine_version(self, value: GodotVersion) -> None:
        """
        Sets the engine version associated with the project.
        """
        set_engine_version(self._file_path, value)
        self.metadata["engine_version"] = value
        self.metadata["engine_version_hint"] = value.major_minor

    @property
    def engine_version_hint(self) -> Optional[float]:
        """
        Returns the major.minor version of the engine associated with the project.
        """
        return self.metadata.get("engine_version_hint")

    @property
    def compatibility_version(self) -> Optional[float]:
        """
        Returns the compatibility version associated with the project.
        """
        return self.metadata.get("compatibility_version")

    @compatibility_version.setter
    def compatibility_version(self, value: Union[GodotVersion, float]) -> None:
        """
        Sets the compatibility version associated with the project.
        """
        if isinstance(value, GodotVersion):
            value = value.major_minor

        set_compatibility_version(self._file_path, value)
        self.metadata["compatibility_version"] = value

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
