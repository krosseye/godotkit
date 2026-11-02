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

    def test_skips_features_for_godot_3(self, tmp_path: Path):
        create(tmp_path, "Demo", engine_version=GodotVersion(3, 6))
        assert "compatibility_version" not in read(tmp_path / "project.godot")
