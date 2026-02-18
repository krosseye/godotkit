import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional, TypedDict, Union

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
    version: Optional[str]
    tags: Optional[list[str]]
    file_path: Path
    dir_path: Path
    icon_path: Optional[Path]
    engine_version: Optional[GodotVersion]
    engine_version_hint: Optional[float]
    compatibility_version: Optional[float]


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
    icon_path: Optional[Path] = None,
    engine_version: Optional["GodotVersion"] = None,
    tags: Optional[list[str]] = None,
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

    Args:
        project_path (Path): Path to the project.godot file.
        metadata (ProjectMetadata): The new metadata to apply.
    """
    current_metadata = read(project_path)

    updates: dict[str, str] = {}

    if "name" in metadata and metadata["name"] != current_metadata.get("name"):
        updates["config/name="] = f'config/name="{metadata["name"]}"\n'

    if "description" in metadata and metadata["description"] != current_metadata.get(
        "description"
    ):
        updates["config/description="] = (
            f'config/description="{metadata["description"]}"\n'
        )

    if "version" in metadata and metadata["version"] != current_metadata.get("version"):
        if metadata["version"] is not None:
            updates["config/version="] = f'config/version="{metadata["version"]}"\n'

    if "tags" in metadata and metadata["tags"] != current_metadata.get("tags"):
        if metadata["tags"] is not None:
            tag_array = ",".join(f'"{tag}"' for tag in metadata["tags"])
            updates["config/tags="] = f"config/tags=PackedStringArray({tag_array})\n"

    if "compatibility_version" in metadata and metadata[
        "compatibility_version"
    ] != current_metadata.get("compatibility_version"):
        val = metadata["compatibility_version"]
        if val is not None:
            if isinstance(val, GodotVersion):
                val = val.major_minor
            updates["config/features="] = (
                f'config/features=PackedStringArray("{val}")\n'
            )

    if updates:
        if not project_path.exists():
            raise FileNotFoundError(f"Project file not found: {project_path}")

        lock_path = project_path.with_suffix(project_path.suffix + ".lock")
        with FileLock(lock_path):
            with open(project_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with tempfile.NamedTemporaryFile(
                "w", delete=False, encoding="utf-8", dir=project_path.parent
            ) as tf:
                temp_name = tf.name
                for line in lines:
                    for key, value in updates.items():
                        if line.startswith(key):
                            tf.write(value)
                            break
                    else:
                        tf.write(line)
            os.replace(temp_name, project_path)

    if "icon_path" in metadata and metadata["icon_path"] != current_metadata.get(
        "icon_path"
    ):
        if metadata["icon_path"] is not None:
            set_project_icon(project_path, metadata["icon_path"])

    if "engine_version" in metadata and metadata[
        "engine_version"
    ] != current_metadata.get("engine_version"):
        if metadata["engine_version"] is not None:
            set_engine_version(project_path, metadata["engine_version"])


def write_property(
    project_path: Path, key: str, value: str, category: str = "application"
):
    """
    Writes a property to the given project file.

    Args:
        project_path (Path): Path to the project file.
        key (str): Key of the property to write.
        value (str): Value of the property to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    if not project_path.exists():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    lock_path = project_path.with_suffix(project_path.suffix + ".lock")
    lock = FileLock(lock_path)

    with lock:
        with open(project_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated_lines = []
        target_section_header = f"[{category}]"
        is_inside_target_section = False
        setting_was_found_and_updated = False

        formatted_setting_line = f'{key}="{value}"\n'

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith("[") and stripped_line.endswith("]"):
                if is_inside_target_section and not setting_was_found_and_updated:
                    updated_lines.append(formatted_setting_line)
                    setting_was_found_and_updated = True

                is_inside_target_section = stripped_line == target_section_header

            if is_inside_target_section and stripped_line.startswith(key):
                updated_lines.append(formatted_setting_line)
                setting_was_found_and_updated = True
            else:
                updated_lines.append(line)

        if not setting_was_found_and_updated:
            if is_inside_target_section:
                updated_lines.append(formatted_setting_line)
            else:
                updated_lines.append(f"\n{target_section_header}\n")
                updated_lines.append(formatted_setting_line)

        with tempfile.NamedTemporaryFile(
            "w", delete=False, encoding="utf-8", dir=project_path.parent
        ) as tf:
            temp_name = tf.name
            tf.writelines(updated_lines)

        os.replace(temp_name, project_path)


def set_name(project_path: Path, name: str):
    """
    Writes a new name to the provided project file.

    Args:
        project_path (Path): Path to the project file.
        name (str): New name to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    write_property(project_path, "config/name=", f'config/name="{name}"\n')


def set_description(project_path: Path, description: str):
    """
    Writes a new description to the provided project file.

    Args:
        project_path (Path): Path to the project file.
        description (str): New description to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    write_property(
        project_path, "config/description=", f'config/description="{description}"\n'
    )


def set_version(project_path: Path, version: str):
    """
    Writes a new version to the provided project file.

    Args:
        project_path (Path): Path to the project file.
        version (str): New version to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    write_property(project_path, "config/version=", f'config/version="{version}"\n')


def set_tags(project_path: Path, tags: list[str]):
    """
    Writes new tags to the provided project file.

    Args:
        project_path (Path): Path to the project file.
        tags (list[str]): New tags to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    tag_array = ",".join(f'"{tag}"' for tag in tags)
    write_property(
        project_path, "config/tags=", f"config/tags=PackedStringArray({tag_array})\n"
    )


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

    version_file = project_path.parent / ".godot-version"
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(str(engine_version))


def set_compatibility_version(
    project_path: Path, engine_version: Union[GodotVersion, float]
):
    """
    Writes a new compatibility version to the provided project file.

    Args:
        project_path (Path): Path to the project file.
        engine_version (Union[GodotVersion, float]): New compatibility version to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    if isinstance(engine_version, GodotVersion):
        engine_version = engine_version.major_minor

    write_property(
        project_path,
        "config/features=",
        f'config/features=PackedStringArray("{engine_version}")\n',
    )


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

    godot_internal_resource_path = f"res://{destination_icon_path.name}"
    write_property(project_path, "config/icon", godot_internal_resource_path)
