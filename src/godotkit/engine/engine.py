import subprocess
from pathlib import Path

from .utils import find_binary, start
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

    def start(self, *, output: Path | None = None) -> subprocess.Popen:
        """
        Launches the Godot Engine executable.

        Args:
            output (Optional[Path]): File that receives Godot's stdout and stderr.

        Raises:
            FileNotFoundError: If the binary is gone.
            OSError: If the binary can't be started.
        """
        return start(self.binary_path, output=output)

    def start_project(
        self, project_path: Path, *, output: Path | None = None
    ) -> subprocess.Popen:
        """
        Opens the provided project in this version's editor.

        Args:
            project_path (Path): The '.godot' project file path.
            output (Optional[Path]): File that receives Godot's stdout and stderr.

        Raises:
            FileNotFoundError: If the binary or the project file is missing.
            OSError: If the binary can't be started.
        """
        return start(self.binary_path, project=project_path, output=output)
