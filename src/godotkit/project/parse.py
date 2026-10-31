import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional, TypedDict

from filelock import FileLock

from ..common.git import init_repo
from ..engine.version_parsing import GodotVersion

ENGINE_VERSION_FILE = ".godot-version"

GIT_IGNORE_TEMPLATE = """# Godot 4+ specific ignores
.godot/
.nomedia
/android/

# Godot-specific ignores
.import/
export.cfg
export_credentials.cfg
*.tmp

# Imported translations (automatically generated from CSV files)
*.translation

# Mono-specific ignores
.mono/
data_*/
mono_crash.*.json"""

GIT_ATTRIBUTES_TEMPLATE = """# Normalize EOL for all files that Git considers text files.
* text=auto eol=lf"""

GODOT_FILE_HEADER = """; Engine configuration file.
; It's best edited using the editor UI and not directly,
; since the parameters that go here are not all obvious.
;
; Format:
;   [section] ; section goes between []
;   param=value ; assign values to parameters
"""

logger = logging.getLogger(__name__)


class ProjectMetadata(TypedDict, total=False):
    """
    Metadata for a Godot project.

    Attributes:
        name (str): Project name.
        description (str): Project description.
        version (Optional[str]): Project version.
        tags (Optional[list[str]]): List of tags.
        file_path (Path): Absolute path to the project file.
        dir_path (Path): Absolute path to the project directory.
        icon_path (Optional[Path]): Absolute path to the icon file.
        engine_version (Optional[GodotVersion]): Full engine version string.
        engine_version_hint (Optional[float]): Major.minor version.
        compatibility_version (Optional[float]): Minimum compatible Godot version.
    """

    name: str
    description: str
    version: str | None
    tags: list[str] | None
    file_path: Path
    dir_path: Path
    icon_path: Path | None
    engine_version: GodotVersion | None
    engine_version_hint: float | None
    compatibility_version: float | None


def read(project_path: Path) -> ProjectMetadata:
    """Parse a Godot project.godot file and extract metadata.

    Args:
        project_path (Path): Path to the `project.godot` file.

    Returns:
        ProjectMetadata
    """
    logger.debug(f"Attempting to parse Godot project file: {project_path}")
    if not project_path.is_file():
        logger.error(f"Project file not found: {project_path}")
        raise FileNotFoundError(f"Project file not found: {project_path}")

    project_dir = project_path.parent
    name = "Unnamed Project"
    description = "No description provided."
    version = None
    icon_res_path = None
    compatibility_features = None
    tags = None
    in_application_section = False

    with open(project_path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith(";"):
                continue

            if line.startswith("["):
                in_application_section = line == "[application]"
                continue

            if not in_application_section:
                continue

            if line.startswith("config/name="):
                name = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("config/version="):
                version = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("config/description="):
                description = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("config/icon="):
                icon_res_path = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("config/features="):
                match = re.search(r'PackedStringArray\("([^"]+)"\)', line)
                if match:
                    compatibility_features = match.group(1)
            elif line.startswith("config/tags="):
                tags_match = re.search(r"PackedStringArray\((.*?)\)", line)
                tags = (
                    [tag.strip().strip('"') for tag in tags_match.group(1).split(",")]
                    if tags_match
                    else None
                )

    data: ProjectMetadata = {
        "name": name,
        "description": description,
        "file_path": project_path.resolve(),
        "dir_path": project_dir.resolve(),
    }

    if version:
        data["version"] = version
    if tags:
        data["tags"] = tags

    if icon_res_path:
        icon_abs_path = (project_dir / icon_res_path.replace("res://", "")).resolve()
        if icon_abs_path.exists():
            data["icon_path"] = icon_abs_path
        else:
            logger.warning(
                f"Configured icon path '{icon_res_path}' does not exist at {icon_abs_path}"
            )

    version_file_path = project_dir / ENGINE_VERSION_FILE
    if version_file_path.exists():
        with open(version_file_path, "r", encoding="utf-8") as f:
            version_str = f.read().strip()
            engine_version = GodotVersion.parse(version_str)
            data["engine_version"] = engine_version
            data["engine_version_hint"] = engine_version.major_minor

    if compatibility_features:
        data["compatibility_version"] = float(compatibility_features)

    return data


def create(
    project_dir: Path,
    name: str,
    description: str = "A new Godot project.",
    icon_path: Path | None = None,
    engine_version: Optional["GodotVersion"] = None,
    tags: list[str] | None = None,
    git_init: bool = False,
) -> None:
    """Create a new Godot project with optional icon, version, tags, and Git setup.

    Args:
        project_dir (Path): Directory where the project will be created.
        name (str): Name of the project (used for config/name).
        description (str): Optional project description.
        icon_path (Optional[Path]): Optional path to a custom icon file.
        engine_version (Optional[GodotVersion]): Optional Godot engine version.
        tags (Optional[list[str]]): Optional list of tags (requires Godot >= 4.0).
        git_init (bool): Whether to initialize a Git repository.

    Returns:
        None
    """
    logger.info(f"Attempting to create new Godot project at: {project_dir}")
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "addons").mkdir(exist_ok=True)

    icon_filename = None
    if icon_path and icon_path.is_file():
        icon_filename = f"icon{icon_path.suffix}"
        shutil.copy(icon_path, project_dir / icon_filename)

    project_file = project_dir / "project.godot"
    with open(project_file, "w", encoding="utf-8") as f:
        f.write(f"{GODOT_FILE_HEADER}\n\n")
        f.write("[application]\n\n")
        f.write(f'config/name="{name}"\n')
        f.write('config/version="0.1.0"\n')
        f.write(f'config/description="{description}"\n')

        if engine_version:
            major_minor = engine_version.major_minor
            if major_minor >= 4.0:
                f.write(f'config/features=PackedStringArray("{major_minor}")\n')
                if tags:
                    tag_array = ",".join(f'"{tag}"' for tag in tags)
                    f.write(f"config/tags=PackedStringArray({tag_array})\n")

        if icon_filename:
            f.write(f'config/icon="res://{icon_filename}"\n')

        f.write("\n")

    if engine_version:
        with open(project_dir / ENGINE_VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(str(engine_version))

    if git_init:
        logger.info("Git initialization requested.")
        init_repo(project_dir, GIT_IGNORE_TEMPLATE, GIT_ATTRIBUTES_TEMPLATE)

    logger.info(f"Successfully created project at: {project_dir.resolve()}")


def update(project_path: Path, metadata: ProjectMetadata) -> None:
    """
    Updates the project metadata if it differs from the provided metadata.
    Properties missing from the project file are added.

    Args:
        project_path (Path): Path to the project.godot file.
        metadata (ProjectMetadata): The new metadata to apply.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    current_metadata = read(project_path)
    changed = {
        key
        for key, value in metadata.items()
        if value is not None and value != current_metadata.get(key)
    }

    properties: dict[str, str] = {}

    if "name" in changed:
        properties["config/name"] = f'"{metadata["name"]}"'

    if "description" in changed:
        properties["config/description"] = f'"{metadata["description"]}"'

    if "version" in changed:
        properties["config/version"] = f'"{metadata["version"]}"'

    if "tags" in changed:
        tag_array = ",".join(f'"{tag}"' for tag in metadata["tags"] or [])
        properties["config/tags"] = f"PackedStringArray({tag_array})"

    if "compatibility_version" in changed:
        val = metadata["compatibility_version"]
        if isinstance(val, GodotVersion):
            val = val.major_minor
        properties["config/features"] = f'PackedStringArray("{val}")'

    if properties:
        write_properties(project_path, properties)

    icon_path = metadata.get("icon_path")
    if "icon_path" in changed and icon_path is not None:
        set_project_icon(project_path, icon_path)

    engine_version = metadata.get("engine_version")
    if "engine_version" in changed and engine_version is not None:
        set_engine_version(project_path, engine_version)


def write_properties(
    project_path: Path, properties: dict[str, str], category: str = "application"
) -> None:
    """
    Writes properties to the given project file, replacing existing keys and
    adding missing ones (and the section, if absent).

    Args:
        project_path (Path): Path to the project file.
        properties (dict[str, str]): Keys mapped to raw Godot values, e.g.
            `{"config/name": '"My Game"'}`.
        category (str): Section to write the properties into.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    if not project_path.exists():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    def insert_pending(lines: list[str]) -> None:
        # Insert before trailing blank lines so the new keys stay inside the section.
        i = len(lines)
        while i and not lines[i - 1].strip():
            i -= 1
        lines[i:i] = [f"{key}={value}\n" for key, value in pending.items()]
        pending.clear()

    lock_path = project_path.with_suffix(project_path.suffix + ".lock")
    with FileLock(lock_path):
        with open(project_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"

        target_section_header = f"[{category}]"
        pending = dict(properties)
        updated_lines: list[str] = []
        is_inside_target_section = False

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith("[") and stripped_line.endswith("]"):
                if is_inside_target_section and pending:
                    insert_pending(updated_lines)
                is_inside_target_section = stripped_line == target_section_header
            elif is_inside_target_section and "=" in stripped_line:
                key = stripped_line.split("=", 1)[0].strip()
                if key in pending:
                    updated_lines.append(f"{key}={pending.pop(key)}\n")
                    continue

            updated_lines.append(line)

        if pending:
            if not is_inside_target_section:
                updated_lines.append(f"\n{target_section_header}\n")
            insert_pending(updated_lines)

        with tempfile.NamedTemporaryFile(
            "w", delete=False, encoding="utf-8", dir=project_path.parent
        ) as tf:
            temp_name = tf.name
            tf.writelines(updated_lines)

        os.replace(temp_name, project_path)


def set_engine_version(project_path: Path, engine_version: GodotVersion):
    """
    Writes a new engine version to the provided project file.

    Args:
        project_path (Path): Path to the project file.
        engine_version (GodotVersion): New engine version to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    if not project_path.is_file():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    version_file = project_path.parent / ENGINE_VERSION_FILE
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(str(engine_version))


def set_project_icon(project_path: Path, icon_path: Path):
    """
    Copies the provided icon to the project directory.

    Args:
        project_path (Path): Path to the project file.
        icon_path (Path): Path to the icon file.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    project_path = project_path.resolve()
    icon_path = icon_path.resolve()

    if not project_path.is_file():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    if not icon_path.is_file():
        raise FileNotFoundError(f"Source icon file not found: {icon_path}")

    project_root_directory = project_path.parent
    destination_icon_path = project_root_directory / f"icon{icon_path.suffix}"

    if destination_icon_path.exists() and destination_icon_path.samefile(icon_path):
        return

    for p in project_root_directory.glob("icon.*"):
        if p.is_file():
            p.unlink()

    shutil.copy2(icon_path, destination_icon_path)

    write_properties(
        project_path, {"config/icon": f'"res://{destination_icon_path.name}"'}
    )
