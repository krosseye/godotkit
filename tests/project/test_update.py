from pathlib import Path

import pytest

from godotkit.engine import GodotVersion
from godotkit.project import GodotProject
from godotkit.project.parse import create, read, update, write_properties


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
