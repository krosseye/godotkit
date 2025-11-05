import os
import platform
import shlex
from pathlib import Path

import pytest

from godotkit.common import open_directory


@pytest.fixture
def dummy_dir(tmp_path: Path) -> Path:
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    return test_dir


class TestOpenDirectory:
    @pytest.mark.parametrize(
        "platform_name, expected_command",
        [
            ("Windows", ["cmd", "/C", "start"]),
            ("Darwin", ["open"]),
            ("Linux", ["xdg-open"]),
        ],
    )
    def test_open_directory_via_run_command(
        self,
        dummy_dir: Path,
        monkeypatch,
        mocker,
        platform_name: str,
        expected_command: list[str],
    ):
        monkeypatch.setattr(platform, "system", lambda: platform_name)

        mock_run_command = mocker.patch("godotkit.common.core.run_command")

        if platform_name == "Windows":
            monkeypatch.delattr(os, "startfile", raising=False)

        open_directory(dummy_dir)

        quoted_path = shlex.quote(str(dummy_dir))
        mock_run_command.assert_called_once_with(expected_command + [quoted_path])

    def test_open_directory_windows_preferred_path(
        self, dummy_dir: Path, monkeypatch, mocker
    ):
        monkeypatch.setattr(platform, "system", lambda: "Windows")

        mock_startfile = mocker.patch("godotkit.common.core.os.startfile", create=True)
        monkeypatch.setattr(os, "startfile", mock_startfile)

        open_directory(dummy_dir)

        mock_startfile.assert_called_once_with(str(dummy_dir))

        mock_run_command = mocker.patch("godotkit.common.core.run_command")
        mock_run_command.assert_not_called()

    def test_open_directory_with_invalid_path_raises_valueerror(self, tmp_path: Path):
        invalid_path = tmp_path / "not_a_dir"
        with pytest.raises(ValueError, match="Invalid directory path"):
            open_directory(invalid_path)

    def test_open_directory_on_unsupported_platform_raises_notimplementederror(
        self, dummy_dir: Path, monkeypatch
    ):
        monkeypatch.setattr(platform, "system", lambda: "FreeBSD")
        with pytest.raises(NotImplementedError, match="Unsupported platform: freebsd"):
            open_directory(dummy_dir)
