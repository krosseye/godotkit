from pathlib import Path

import pytest

from godotkit.engine import GodotVersion
from godotkit.project.parse import create, read


class TestCreate:
    @pytest.mark.parametrize(
        "engine_version, expected",
        [
            (GodotVersion(4, 10, 1), GodotVersion(4, 10)),
            (GodotVersion(4, 0, 0, "rc", 1), GodotVersion(4, 0)),
            (GodotVersion(4, 0, csharp_enabled=True), GodotVersion(4, 0)),
        ],
    )
    def test_writes_features_for_godot_4(
        self, tmp_path: Path, engine_version, expected
    ):
        create(tmp_path, "Demo", engine_version=engine_version)
        data = read(tmp_path / "project.godot")
        assert data["compatibility_version"] == expected
        assert data["engine_version"] == engine_version

    def test_refuses_to_overwrite_existing_project(self, tmp_path: Path):
        project_file = tmp_path / "project.godot"
        project_file.write_text('[application]\nconfig/name="My Game"\n', "utf-8")

        with pytest.raises(FileExistsError):
            create(tmp_path, "Other")
        assert read(project_file)["name"] == "My Game"

    def test_special_characters_round_trip(self, tmp_path: Path):
        name = 'My "First" Game \\ v2'
        description = 'Line one\nLine "two"'
        create(
            tmp_path, name, description, tags=["a,b"], engine_version=GodotVersion(4, 3)
        )

        data = read(tmp_path / "project.godot")
        assert data["name"] == name
        assert data["description"] == description
        assert data["tags"] == ["a,b"]

    def test_skips_features_for_godot_3(self, tmp_path: Path):
        create(tmp_path, "Demo", engine_version=GodotVersion(3, 6))
        assert "compatibility_version" not in read(tmp_path / "project.godot")
