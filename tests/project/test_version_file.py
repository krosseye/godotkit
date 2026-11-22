from pathlib import Path

import pytest

from godotkit.engine import GodotVersion
from godotkit.exceptions import VersionFileError
from godotkit.project.parse import (
    create,
    read,
    read_engine_version,
    set_engine_version,
)


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    create(tmp_path, "Demo")
    return tmp_path / "project.godot"


def write_pin(project_file: Path, data: bytes) -> None:
    (project_file.parent / ".godot-version").write_bytes(data)


class TestVersionFile:
    def test_writes_one_canonical_line(self, project_file: Path):
        set_engine_version(project_file, GodotVersion(4, 4, 0, "rc", 2, True))
        pin = project_file.parent / ".godot-version"
        assert pin.read_bytes() == b"4.4.rc2.mono\n"
        assert read_engine_version(project_file) == GodotVersion(4, 4, 0, "rc", 2, True)

    def test_missing_file_is_none(self, project_file: Path):
        assert read_engine_version(project_file) is None
        assert "engine_version" not in read(project_file)

    @pytest.mark.parametrize(
        "data",
        [
            b"4.3.stable.mono\n",
            b"\xef\xbb\xbf4.3 (.NET)\r\n",
            b"\n# pinned for the jam\n  4.3-stable-mono  \nnote=ignored\n",
            b"4.3.0 mono",
        ],
        ids=[
            "canonical",
            "bom-crlf-old-form",
            "comments-and-extra-lines",
            "no-newline",
        ],
    )
    def test_reads_tolerantly(self, project_file: Path, data: bytes):
        write_pin(project_file, data)
        expected = GodotVersion(4, 3, csharp_enabled=True)
        assert read_engine_version(project_file) == expected
        assert read(project_file)["engine_version"] == expected

    @pytest.mark.parametrize(
        "data",
        [
            b"",
            b"# only a comment\n\n",
            b"latest\n",
            "4.3\r\n".encode("utf-16"),  # Windows PowerShell 5.1 `echo 4.3 >`
        ],
        ids=["empty", "only-comments", "not-a-version", "utf-16"],
    )
    def test_malformed_file_raises(self, project_file: Path, data: bytes):
        write_pin(project_file, data)
        with pytest.raises(VersionFileError, match=".godot-version"):
            read_engine_version(project_file)
        with pytest.raises(ValueError):
            read(project_file)


class TestFeatureTag:
    def test_create_writes_major_minor_feature(self, tmp_path: Path):
        create(
            tmp_path, "Demo", engine_version=GodotVersion(4, 3, 1, csharp_enabled=True)
        )
        text = (tmp_path / "project.godot").read_text("utf-8")
        assert 'config/features=PackedStringArray("4.3")' in text

    def test_full_config_feature_reads_as_major_minor(self, tmp_path: Path):
        path = tmp_path / "project.godot"
        path.write_text(
            '[application]\nconfig/features=PackedStringArray("4.3.stable.mono")\n',
            "utf-8",
        )
        assert read(path)["compatibility_version"] == GodotVersion(4, 3)
