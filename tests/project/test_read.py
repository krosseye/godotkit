from pathlib import Path

import pytest

from godotkit.engine import GodotVersion
from godotkit.project.parse import read, update

# As written by the Godot editor: multi-line strings keep literal newlines.
GODOT_WRITTEN = """\
; Engine configuration file.

[application]

config/name="Demo"
config/description="First line
[not a section]
Last \\"quoted\\" line"
config/tags=PackedStringArray("2d", "rpg")
config/features=PackedStringArray("4.3", "Forward Plus")

[rendering]

foo=1
"""


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    path = tmp_path / "project.godot"
    path.write_text(GODOT_WRITTEN, encoding="utf-8")
    return path


class TestRead:
    def test_multiline_string_is_read_whole(self, project_file: Path):
        data = read(project_file)
        assert data["description"] == 'First line\n[not a section]\nLast "quoted" line'
        assert data["tags"] == ["2d", "rpg"]

    def test_compatibility_version_from_multi_entry_features(self, project_file: Path):
        assert read(project_file)["compatibility_version"] == GodotVersion(4, 3)

    def test_compatibility_version_need_not_be_first(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text(
            '[application]\nconfig/features=PackedStringArray("C#", "4.4")\n', "utf-8"
        )
        assert read(path)["compatibility_version"] == GodotVersion(4, 4)

    def test_features_without_version_are_absent(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text(
            '[application]\nconfig/features=PackedStringArray("Mobile")\n', "utf-8"
        )
        assert "compatibility_version" not in read(path)

    def test_empty_tags_are_absent(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text("[application]\nconfig/tags=PackedStringArray()\n", "utf-8")
        assert "tags" not in read(path)

    def test_replacing_multiline_value_leaves_no_residue(self, project_file: Path):
        update(project_file, {"description": "Test update"})

        text = project_file.read_text(encoding="utf-8")
        assert "First line" not in text and "Last" not in text
        assert "[not a section]" not in text
        data = read(project_file)
        assert data["description"] == "Test update"
        assert data["tags"] == ["2d", "rpg"]
        assert "foo=1" in text
