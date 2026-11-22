import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from godotkit.engine import utils as engine_utils
from godotkit.project import GodotProject

Launches = list[tuple[list[str], Path | None]]


@pytest.fixture
def launched(mocker: MockerFixture) -> Launches:
    calls: Launches = []
    mocker.patch.object(
        engine_utils,
        "launch_daemon_command",
        lambda command, output=None: calls.append((command, output)),
    )
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
    engine_utils.start(binary, ["--verbose"])
    assert launched == [([str(binary), "--verbose"], None)]


def test_project_start_passes_path_and_output(
    binary: Path, project_file: Path, tmp_path: Path, launched
):
    log = tmp_path / "godot.log"
    GodotProject(project_file).start(binary, output=log)
    command = [str(binary), "--path", str(project_file.parent), "--editor"]
    assert launched == [(command, log)]


@pytest.mark.parametrize(
    "kwargs",
    [
        lambda b, p: {"binary_path": b.with_name("missing.exe")},
        lambda b, p: {"binary_path": b, "project": p.with_name("missing.godot")},
    ],
    ids=["binary", "project file"],
)
def test_missing_file_raises(binary: Path, project_file: Path, launched, kwargs):
    with pytest.raises(FileNotFoundError):
        engine_utils.start(**kwargs(binary, project_file))
    assert launched == []


def test_launch_failure_propagates(binary: Path):
    # Unmocked: a non-executable file makes Popen itself raise.
    binary.write_text("not a program")
    with pytest.raises(OSError):
        engine_utils.start(binary)


def test_output_is_captured(tmp_path: Path):
    log = tmp_path / "out.log"
    script = "import sys; print('out'); print('err', file=sys.stderr)"
    process = engine_utils.start(Path(sys.executable), ["-c", script], output=log)
    assert process.wait(timeout=10) == 0
    assert sorted(log.read_text().split()) == ["err", "out"]
