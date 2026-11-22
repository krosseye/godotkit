from pathlib import Path
from typing import cast

import pytest

from godotkit.engine import GodotVersion
from godotkit.project import GodotProject
from godotkit.project.parse import (
    ProjectMetadata,
    create,
    read,
    update,
    write_properties,
)


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    # No engine version, so create() writes neither tags nor features.
    create(tmp_path, "Demo")
    return tmp_path / "project.godot"


class TestUpdate:
    def test_adds_missing_fields(self, project_file: Path):
        update(
            project_file,
            {"tags": ["a", "b"], "compatibility_version": GodotVersion(4, 3)},
        )
        data = read(project_file)
        assert data["tags"] == ["a", "b"]
        assert data["compatibility_version"] == GodotVersion(4, 3)

    def test_compatibility_version_writes_major_minor_only(self, project_file: Path):
        update(project_file, {"compatibility_version": GodotVersion(4, 10, 2, "rc", 1)})
        assert 'PackedStringArray("4.10")' in project_file.read_text(encoding="utf-8")
        assert read(project_file)["compatibility_version"] == GodotVersion(4, 10)

    def test_compatibility_version_keeps_other_features(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text(
            '[application]\n\nconfig/features=PackedStringArray("4.3", "Forward Plus", "C#")\n',
            "utf-8",
        )
        update(path, {"compatibility_version": GodotVersion(4, 4)})
        assert (
            'config/features=PackedStringArray("4.4", "Forward Plus", "C#")'
            in path.read_text(encoding="utf-8")
        )

    def test_replaces_existing_field_once(self, project_file: Path):
        update(project_file, {"name": "Renamed"})
        text = project_file.read_text(encoding="utf-8")
        assert text.count("config/name=") == 1
        assert read(project_file)["name"] == "Renamed"

    def test_added_field_stays_in_section(self, project_file: Path):
        with open(project_file, "a", encoding="utf-8") as f:
            f.write("[rendering]\n\nfoo=1\n")
        update(project_file, {"tags": ["x"]})
        assert read(project_file)["tags"] == ["x"]

    def test_project_setters(self, project_file: Path):
        project = GodotProject(project_file)
        project.tags = ["t"]
        project.name = "New"
        assert read(project_file)["tags"] == ["t"]
        assert project.name == "New"


class TestMissingAndCleared:
    def test_missing_fields_are_left_out(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text("[application]\n", "utf-8")

        data = read(path)
        project = GodotProject(path)

        for key in ("name", "description", "version"):
            assert key not in data
            assert getattr(project, key) is None

    def test_create_writes_no_version(self, project_file: Path):
        assert "config/version" not in project_file.read_text("utf-8")

    def test_former_placeholder_name_is_written(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text("[application]\n", "utf-8")
        update(path, {"name": "Unnamed Project"})
        assert read(path)["name"] == "Unnamed Project"

    def test_missing_key_leaves_field_alone(self, project_file: Path):
        update(project_file, {"tags": ["a"]})
        update(project_file, {"name": "Other"})
        assert read(project_file)["tags"] == ["a"]

    @pytest.mark.parametrize("key", ["name", "description", "version", "tags"])
    def test_none_clears_property(self, project_file: Path, key: str):
        update(project_file, {"version": "1.0", "tags": ["a"]})

        update(project_file, cast(ProjectMetadata, {key: None}))

        assert key not in read(project_file)
        assert f"config/{key}=" not in project_file.read_text("utf-8")

    def test_none_clears_only_the_version_feature(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text(
            '[application]\n\nconfig/features=PackedStringArray("4.3", "C#")\n', "utf-8"
        )
        update(path, {"compatibility_version": None})
        assert 'config/features=PackedStringArray("C#")' in path.read_text("utf-8")
        assert "compatibility_version" not in read(path)

    def test_none_clears_features_entirely_when_nothing_else(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text('[application]\n\nconfig/features=PackedStringArray("4.3")\n')
        update(path, {"compatibility_version": None})
        assert "config/features" not in path.read_text("utf-8")

    def test_none_clears_engine_version_file(self, tmp_path: Path):
        create(tmp_path, "Demo", engine_version=GodotVersion(4, 3))
        project = GodotProject(tmp_path / "project.godot")

        project.engine_version = None

        assert project.engine_version is None
        assert not (tmp_path / ".godot-version").exists()

    def test_none_clears_icon_but_keeps_file(self, tmp_path: Path):
        icon = tmp_path / "src.png"
        icon.write_bytes(b"png")
        create(tmp_path / "p", "Demo", icon_path=icon)
        path = tmp_path / "p" / "project.godot"

        update(path, {"icon_path": None})

        assert "icon_path" not in read(path)
        assert "config/icon" not in path.read_text("utf-8")
        assert (tmp_path / "p" / "icon.png").exists()

    def test_write_properties_removes_multiline_value(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text(
            '[application]\n\nconfig/description="one\ntwo"\nconfig/name="A"\n',
            "utf-8",
        )
        write_properties(path, {"config/description": None, "config/missing": None})
        assert path.read_text("utf-8") == '[application]\n\nconfig/name="A"\n'


@pytest.mark.parametrize("nl", ["\n", "\r\n"], ids=["lf", "crlf"])
class TestWritePropertiesLineEndings:
    def test_replaced_and_added_keys(self, tmp_path: Path, nl: str):
        path = tmp_path / "project.godot"
        path.write_bytes(f'[application]{nl}config/name="A"{nl}'.encode())

        write_properties(path, {"config/name": '"B"', "config/new": "1"})

        assert path.read_bytes() == (
            f'[application]{nl}config/name="B"{nl}config/new=1{nl}'.encode()
        )

    def test_added_section(self, tmp_path: Path, nl: str):
        path = tmp_path / "project.godot"
        path.write_bytes(f'[application]{nl}config/name="A"'.encode())

        write_properties(path, {"foo": "1"}, category="rendering")

        assert path.read_bytes() == (
            f'[application]{nl}config/name="A"{nl}{nl}[rendering]{nl}foo=1{nl}'.encode()
        )
