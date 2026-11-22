from pathlib import Path

import pytest

from godotkit.engine import utils as engine_utils
from godotkit.project import utils as project_utils


@pytest.fixture
def launched(mocker):
    calls: list[list[str]] = []
    mocker.patch.object(engine_utils, "launch_daemon_command", calls.append)
    mocker.patch.object(project_utils, "launch_daemon_command", calls.append)
    return calls


@pytest.fixture
def binary(tmp_path: Path) -> Path:
    path = tmp_path / "godot.exe"
    path.touch()
    return path


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    path = tmp_path / "game" / "project.godot"
    path.parent.mkdir()
    path.touch()
    return path


def test_engine_start(binary: Path, launched):
    engine_utils.start(binary)
    assert launched == [[str(binary)]]


def test_project_start_passes_path(binary: Path, project_file: Path, launched):
    project_utils.start(binary, project_file)
    assert launched == [[str(binary), "--path", str(project_file.parent), "--editor"]]


@pytest.mark.parametrize(
    "start",
    [
        lambda b, p: engine_utils.start(b.with_name("missing.exe")),
        lambda b, p: project_utils.start(b.with_name("missing.exe"), p),
        lambda b, p: project_utils.start(b, p.with_name("missing.godot")),
    ],
    ids=["engine binary", "project binary", "project file"],
)
def test_missing_file_raises(binary: Path, project_file: Path, launched, start):
    with pytest.raises(FileNotFoundError):
        start(binary, project_file)
    assert launched == []


def test_launch_failure_propagates(binary: Path, project_file: Path):
    # Unmocked: a non-executable file makes Popen itself raise.
    binary.write_text("not a program")
    with pytest.raises(OSError):
        engine_utils.start(binary)
    with pytest.raises(OSError):
        project_utils.start(binary, project_file)
