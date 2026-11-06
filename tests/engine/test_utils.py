import os
import stat
import zipfile
from contextlib import nullcontext
from pathlib import Path

import pytest

from godotkit.engine.utils import download_and_extract, find_binary

ELF = b"\x7fELF" + b"\0" * 12
DOWNLOAD_URL = "https://godotengine.org/download/godot.zip"


def make_zip(path: Path, entries: dict[str, tuple[bytes, int]]) -> bytes:
    """Builds a zip as Godot's are built: on Unix, with modes in external_attr."""
    with zipfile.ZipFile(path, "w") as zf:
        for name, (data, mode) in entries.items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(info, data)
    return path.read_bytes()


@pytest.fixture
def serve(mocker):
    """Makes download_and_extract 'download' the given bytes."""

    def _serve(payload: bytes) -> None:
        response = mocker.MagicMock()
        response.headers = {"Content-Length": str(len(payload))}
        response.iter_bytes.return_value = [payload]
        mocker.patch(
            "godotkit.engine.utils.httpx.stream", return_value=nullcontext(response)
        )

    return _serve


class TestDownloadAndExtract:
    @pytest.mark.skipif(os.name != "posix", reason="Unix permissions only")
    def test_keeps_executable_bit(self, tmp_path: Path, serve):
        serve(
            make_zip(
                tmp_path / "godot.zip",
                {"Godot_v4.3-stable_linux.x86_64": (ELF, 0o755)},
            )
        )
        download_and_extract(DOWNLOAD_URL, tmp_path / "install")

        binary = tmp_path / "install" / "Godot_v4.3-stable_linux.x86_64"
        assert os.access(binary, os.X_OK)

    def test_flattens_single_wrapper_folder(self, tmp_path: Path, serve):
        serve(
            make_zip(
                tmp_path / "godot.zip",
                {
                    "Godot_mono/Godot_v4.3-stable_mono_linux.x86_64": (ELF, 0o755),
                    "Godot_mono/GodotSharp/Api/GodotSharp.dll": (b"dll", 0o644),
                },
            )
        )
        download_and_extract(DOWNLOAD_URL, tmp_path / "install")

        install = tmp_path / "install"
        assert (install / "Godot_v4.3-stable_mono_linux.x86_64").is_file()
        assert (install / "GodotSharp" / "Api" / "GodotSharp.dll").is_file()

    def test_keeps_app_bundle_intact(self, tmp_path: Path, serve):
        serve(
            make_zip(
                tmp_path / "godot.zip",
                {"Godot.app/Contents/MacOS/Godot": (b"macho", 0o755)},
            )
        )
        download_and_extract(DOWNLOAD_URL, tmp_path / "install")

        assert (
            tmp_path / "install" / "Godot.app" / "Contents" / "MacOS" / "Godot"
        ).is_file()


class TestFindBinary:
    def test_windows_skips_console_exe(self, tmp_path: Path, mocker):
        mocker.patch("platform.system", return_value="Windows")
        (tmp_path / "GodotSharp").mkdir()
        (tmp_path / "Godot_v4.3-stable_mono_win64_console.exe").write_bytes(b"MZ")
        assert find_binary(tmp_path) is None

        binary = tmp_path / "Godot_v4.3-stable_mono_win64.exe"
        binary.write_bytes(b"MZ")
        assert find_binary(tmp_path) == binary.resolve()

    def test_linux_picks_elf_and_skips_godotsharp(self, tmp_path: Path, mocker):
        mocker.patch("platform.system", return_value="Linux")
        (tmp_path / "GodotSharp").mkdir()
        (tmp_path / "GodotSharp" / "libgodotsharp.so").write_bytes(ELF)
        (tmp_path / "Godot_notes.txt").write_text("not a binary")
        binary = tmp_path / "Godot_v3.6-stable_x11.64"
        binary.write_bytes(ELF)

        assert find_binary(tmp_path) == binary.resolve()

    def test_linux_without_binary_returns_none(self, tmp_path: Path, mocker):
        mocker.patch("platform.system", return_value="Linux")
        (tmp_path / "Godot.txt").write_text("not a binary")
        assert find_binary(tmp_path) is None

    @pytest.mark.parametrize("app", ["Godot.app", "Godot_mono.app"])
    def test_macos_picks_app_executable(self, tmp_path: Path, mocker, app):
        mocker.patch("platform.system", return_value="Darwin")
        binary = tmp_path / app / "Contents" / "MacOS" / "Godot"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"macho")

        assert find_binary(tmp_path) == binary.resolve()
