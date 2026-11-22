import subprocess
from pathlib import Path

from ..engine.utils import start
from ..engine.version_parsing import GodotVersion
from .parse import ProjectMetadata, read, update


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
            VersionFileError: If the project's `.godot-version` is malformed.
        """
        self._file_path = file_path

        if not self._file_path.is_file():
            raise FileNotFoundError(f"Project file not found: {self._file_path}")

        self.metadata: ProjectMetadata = read(self._file_path)

    def update(self, metadata: ProjectMetadata) -> None:
        """
        Writes the given fields to the project, then re-reads it into `metadata`.

        A key left out leaves that field alone; a key set to `None` clears it.

        Args:
            metadata (ProjectMetadata): The fields to change.

        Raises:
            FileNotFoundError: If the project file no longer exists.
            VersionFileError: If the project's `.godot-version` is malformed
                and `metadata` doesn't set `engine_version`.
        """
        update(self._file_path, metadata)
        self.metadata = read(self._file_path)

    @property
    def name(self) -> str | None:
        """
        Returns the name of the project.
        """
        return self.metadata.get("name")

    @name.setter
    def name(self, value: str | None) -> None:
        """
        Sets the name of the project.
        """
        self.update({"name": value})

    @property
    def description(self) -> str | None:
        """
        Returns the description of the project.
        """
        return self.metadata.get("description")

    @description.setter
    def description(self, value: str | None) -> None:
        """
        Sets the description of the project.
        """
        self.update({"description": value})

    @property
    def version(self) -> str | None:
        """
        Returns the version of the project.
        """
        return self.metadata.get("version")

    @version.setter
    def version(self, value: str | None) -> None:
        """
        Sets the version of the project.
        """
        self.update({"version": value})

    @property
    def tags(self) -> list[str] | None:
        """
        Returns the list of tags associated with the project.
        """
        return self.metadata.get("tags")

    @tags.setter
    def tags(self, value: list[str] | None) -> None:
        """
        Sets the list of tags associated with the project.
        """
        self.update({"tags": value})

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
    def engine_version(self, value: GodotVersion | None) -> None:
        """
        Sets the engine version associated with the project.
        """
        self.update({"engine_version": value})

    @property
    def compatibility_version(self) -> GodotVersion | None:
        """
        Returns the compatibility version associated with the project.
        """
        return self.metadata.get("compatibility_version")

    @compatibility_version.setter
    def compatibility_version(self, value: GodotVersion | None) -> None:
        """
        Sets the compatibility version associated with the project.
        """
        self.update({"compatibility_version": value})

    def start(
        self, binary_path: Path, *, output: Path | None = None
    ) -> subprocess.Popen:
        """
        Opens the project in the editor of the provided Godot Engine binary.

        Args:
            binary_path (Path): Path to the Godot Engine binary.
            output (Optional[Path]): File that receives Godot's stdout and stderr.

        Raises:
            FileNotFoundError: If the binary or the project file is missing.
            OSError: If the binary can't be started.
        """
        return start(binary_path, project=self._file_path, output=output)
