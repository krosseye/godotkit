import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional, TypedDict

from filelock import FileLock

from .._common.git import git_installed, init_repo
from ..engine.version_parsing import GodotVersion
from ..exceptions import GitError, VersionFileError

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

_STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"', re.DOTALL)
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r"}


logger = logging.getLogger(__name__)


def _quote(value: str) -> str:
    """Formats a Python string as a Godot string literal."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _unquote(value: str) -> str:
    """Parses a Godot string literal; returns unquoted values unchanged."""
    match = _STRING_RE.fullmatch(value)
    if not match:
        return value
    return re.sub(
        r"\\(.)",
        lambda m: _ESCAPES.get(m.group(1), m.group(1)),
        match.group(1),
        flags=re.DOTALL,
    )


def _packed(values: list[str]) -> str:
    return f"PackedStringArray({', '.join(_quote(v) for v in values)})"


def _packed_strings(value: str) -> list[str]:
    return [_unquote(m.group(0)) for m in _STRING_RE.finditer(value)]


def _read_section(project_path: Path, section: str = "application") -> dict[str, str]:
    """Returns the raw (still quoted) values of one section, keyed by property."""
    header = f"[{section}]"
    values: dict[str, str] = {}
    in_section = False

    lines = iter(project_path.read_text(encoding="utf-8").splitlines())
    for raw_line in lines:
        line = raw_line.strip()

        if not line or line.startswith(";"):
            continue

        if line.startswith("["):
            in_section = line == header
            continue

        key, _, value = line.partition("=")
        while _is_unterminated(value) and (next_line := next(lines, None)) is not None:
            value += "\n" + next_line

        if in_section:
            values[key.strip()] = value.strip()

    return values


def _parse_version(feature: str) -> GodotVersion | None:
    try:
        return GodotVersion.parse(feature)
    except ValueError:
        return None


def _features_version(features: list[str]) -> GodotVersion | None:
    """The version entry of config/features, e.g. 4.3 in ("4.3", "Forward Plus")."""
    return next((v.major_minor for f in features if (v := _parse_version(f))), None)


def _feature_tag(version: GodotVersion) -> str:
    """The `config/features` entry Godot writes for a version, e.g. "4.3"."""
    return f"{version.major}.{version.minor}"


def _is_unterminated(value: str) -> bool:
    """True if `value` opens a string literal that has not been closed yet."""
    return '"' in _STRING_RE.sub("", value)


class ProjectMetadata(TypedDict, total=False):
    """
    Metadata for a Godot project.

    Attributes:
        name (Optional[str]): Project name.
        description (Optional[str]): Project description.
        version (Optional[str]): Project version.
        tags (Optional[list[str]]): List of tags.
        file_path (Path): Absolute path to the project file (read-only).
        dir_path (Path): Absolute path to the project directory (read-only).
        icon_path (Optional[Path]): Absolute path to the icon file.
        engine_version (Optional[GodotVersion]): Full engine version string.
        compatibility_version (Optional[GodotVersion]): Minimum compatible Godot version.
    """

    name: str | None
    description: str | None
    version: str | None
    tags: list[str] | None
    file_path: Path
    dir_path: Path
    icon_path: Path | None
    engine_version: GodotVersion | None
    compatibility_version: GodotVersion | None


def read(project_path: Path) -> ProjectMetadata:
    """Parse a Godot project.godot file and extract metadata.

    Args:
        project_path (Path): Path to the `project.godot` file.

    Returns:
        ProjectMetadata

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
        VersionFileError: If the project's `.godot-version` is malformed.
    """
    data = _read_project_file(project_path)
    engine_version = read_engine_version(project_path)
    if engine_version:
        data["engine_version"] = engine_version
    return data


def _read_project_file(project_path: Path) -> ProjectMetadata:
    """`read()` without the `.godot-version` pin."""
    logger.debug("Attempting to parse Godot project file: %s", project_path)
    if not project_path.is_file():
        logger.error("Project file not found: %s", project_path)
        raise FileNotFoundError(f"Project file not found: {project_path}")

    project_dir = project_path.parent
    values = _read_section(project_path)

    def text(key: str) -> str | None:
        return _unquote(values[key]) if key in values else None

    name = text("config/name")
    description = text("config/description")
    version = text("config/version")
    icon_res_path = text("config/icon")
    tags = _packed_strings(values.get("config/tags", "")) or None
    compatibility_version = _features_version(
        _packed_strings(values.get("config/features", ""))
    )

    data: ProjectMetadata = {
        "file_path": project_path.resolve(),
        "dir_path": project_dir.resolve(),
    }

    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
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
                "Configured icon path '%s' does not exist at %s",
                icon_res_path,
                icon_abs_path,
            )

    if compatibility_version:
        data["compatibility_version"] = compatibility_version

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

    Raises:
        FileExistsError: If `project_dir` already contains a project.godot file.
        GitError: If `git_init` is set and Git is missing (checked before
            anything is written) or `git init` fails.
    """
    logger.info("Attempting to create new Godot project at: %s", project_dir)
    project_file = project_dir / "project.godot"
    if project_file.exists():
        raise FileExistsError(f"Project file already exists: {project_file}")
    if git_init and not git_installed():
        raise GitError("Git is not installed")

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "addons").mkdir(exist_ok=True)

    icon_filename = None
    if icon_path and icon_path.is_file():
        icon_filename = f"icon{icon_path.suffix}"
        shutil.copy(icon_path, project_dir / icon_filename)

    with open(project_file, "x", encoding="utf-8", newline="\n") as f:
        f.write(f"{GODOT_FILE_HEADER}\n\n")
        f.write("[application]\n\n")
        f.write(f"config/name={_quote(name)}\n")
        f.write(f"config/description={_quote(description)}\n")

        if engine_version and engine_version.major >= 4:
            f.write(
                f'config/features=PackedStringArray("{_feature_tag(engine_version)}")\n'
            )
            if tags:
                f.write(f"config/tags={_packed(tags)}\n")

        if icon_filename:
            f.write(f"config/icon={_quote(f'res://{icon_filename}')}\n")

        f.write("\n")

    if engine_version:
        set_engine_version(project_file, engine_version)

    if git_init:
        logger.info("Git initialization requested.")
        init_repo(project_dir, GIT_IGNORE_TEMPLATE, GIT_ATTRIBUTES_TEMPLATE)

    logger.info("Successfully created project at: %s", project_dir.resolve())


def update(project_path: Path, metadata: ProjectMetadata) -> None:
    """
    Writes the fields in `metadata` that differ from the project file.

    A key left out of `metadata` leaves that field alone. A key set to `None`
    clears it (the property is removed from `project.godot`).

    The `.godot-version` pin is only read by `read()`, never here, so a
    malformed pin doesn't block other edits, and setting `engine_version`
    (or clearing it) repairs one.

    Args:
        project_path (Path): Path to the project.godot file.
        metadata (ProjectMetadata): The fields to change.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    current_metadata = _read_project_file(project_path)
    changed = {
        key for key, value in metadata.items() if value != current_metadata.get(key)
    }
    if "engine_version" in metadata:
        changed.add("engine_version")

    def text(value: str | None) -> str | None:
        return None if value is None else _quote(value)

    properties: dict[str, str | None] = {}

    if "name" in changed:
        properties["config/name"] = text(metadata["name"])

    if "description" in changed:
        properties["config/description"] = text(metadata["description"])

    if "version" in changed:
        properties["config/version"] = text(metadata["version"])

    if "tags" in changed:
        tags = metadata["tags"]
        properties["config/tags"] = None if tags is None else _packed(tags)

    if "compatibility_version" in changed:
        val = metadata["compatibility_version"]
        existing = _packed_strings(
            _read_section(project_path).get("config/features", "")
        )
        features = [f for f in existing if _parse_version(f) is None]
        if val is not None:
            features.insert(0, _feature_tag(val))
        properties["config/features"] = _packed(features) if features else None

    if "icon_path" in changed and metadata["icon_path"] is None:
        properties["config/icon"] = None

    if properties:
        write_properties(project_path, properties)

    icon_path = metadata.get("icon_path")
    if "icon_path" in changed and icon_path is not None:
        set_project_icon(project_path, icon_path)

    if "engine_version" in changed:
        engine_version = metadata["engine_version"]
        if engine_version is None:
            (project_path.parent / ENGINE_VERSION_FILE).unlink(missing_ok=True)
        else:
            set_engine_version(project_path, engine_version)


def write_properties(
    project_path: Path,
    properties: dict[str, str | None],
    category: str = "application",
) -> None:
    """
    Writes properties to the given project file, replacing existing keys and
    adding missing ones (and the section, if absent). A `None` value removes
    the key.

    Args:
        project_path (Path): Path to the project file.
        properties (dict[str, str | None]): Keys mapped to raw Godot values,
            e.g. `{"config/name": '"My Game"'}`, or `None` to remove the key.
        category (str): Section to write the properties into.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    if not project_path.exists():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    def insert_pending(lines: list[str]) -> None:
        i = len(lines)
        while i and not lines[i - 1].strip():
            i -= 1
        lines[i:i] = [
            f"{key}={value}{nl}" for key, value in pending.items() if value is not None
        ]
        pending.clear()

    lock_path = project_path.with_suffix(project_path.suffix + ".lock")
    with FileLock(lock_path):
        with open(project_path, "r", encoding="utf-8", newline="") as f:
            lines = f.readlines()

        nl = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += nl

        target_section_header = f"[{category}]"
        pending = dict(properties)
        updated_lines: list[str] = []
        is_inside_target_section = False

        i = 0
        while i < len(lines):
            line = lines[i]
            i += 1
            stripped_line = line.strip()

            if stripped_line.startswith("[") and stripped_line.endswith("]"):
                if is_inside_target_section and pending:
                    insert_pending(updated_lines)
                is_inside_target_section = stripped_line == target_section_header
                updated_lines.append(line)
                continue

            block = [line]
            key, sep, value = stripped_line.partition("=")
            while sep and _is_unterminated(value) and i < len(lines):
                value += lines[i]
                block.append(lines[i])
                i += 1

            key = key.strip()
            if is_inside_target_section and sep and key in pending:
                new_value = pending.pop(key)
                if new_value is not None:
                    updated_lines.append(f"{key}={new_value}{nl}")
            else:
                updated_lines.extend(block)

        if any(v is not None for v in pending.values()):
            if not is_inside_target_section:
                updated_lines.append(f"{nl}{target_section_header}{nl}")
            insert_pending(updated_lines)

        with tempfile.NamedTemporaryFile(
            "w", delete=False, encoding="utf-8", newline="", dir=project_path.parent
        ) as tf:
            temp_name = tf.name
            tf.writelines(updated_lines)

        os.replace(temp_name, project_path)


def read_engine_version(project_path: Path) -> GodotVersion | None:
    """
    Reads the engine version pinned in the project's `.godot-version` file.

    The version is the first line that isn't blank or a `#` comment (later lines are
    ignored).

    Args:
        project_path (Path): Path to the project file.

    Returns:
        The pinned version, or None if the project has no `.godot-version`.

    Raises:
        VersionFileError: If the file isn't UTF-8 or holds no valid version.
    """
    version_file = project_path.parent / ENGINE_VERSION_FILE
    try:
        text = version_file.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None
    except UnicodeDecodeError as e:
        raise VersionFileError(f"{version_file} is not UTF-8") from e

    lines = (line.strip() for line in text.splitlines())
    line = next((x for x in lines if x and not x.startswith("#")), None)
    if line is None:
        raise VersionFileError(f"{version_file} has no version")
    try:
        return GodotVersion.parse(line)
    except ValueError as e:
        raise VersionFileError(f"{version_file}: {e}") from e


def set_engine_version(project_path: Path, engine_version: GodotVersion):
    """
    Pins an engine version in the project's `.godot-version` file.

    Writes the canonical form, e.g. `4.3.stable.mono`, on one line.

    Args:
        project_path (Path): Path to the project file.
        engine_version (GodotVersion): New engine version to write.

    Raises:
        FileNotFoundError: If the provided path is not a valid file.
    """
    if not project_path.is_file():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    version_file = project_path.parent / ENGINE_VERSION_FILE
    with open(version_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{engine_version}\n")


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
        project_path, {"config/icon": _quote(f"res://{destination_icon_path.name}")}
    )
