"""Unmocked: these spawn real processes on whichever OS runs them."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from godotkit._common import launch_daemon_command, run_utility_command

WRITE_CWD = (
    "import os, time; time.sleep({delay}); "
    "open('marker.tmp', 'w').write(os.getcwd()); "
    "os.replace('marker.tmp', 'marker.txt')"
)


def wait_for(path: Path, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            pytest.fail(f"{path.name} was not written within {timeout}s")
        time.sleep(0.1)


class TestRunUtilityCommand:
    def test_captures_output_in_working_dir(self, tmp_path: Path):
        result = run_utility_command(
            [sys.executable, "-c", "import os; print(os.getcwd())"],
            working_dir=tmp_path,
        )
        assert Path(result.stdout.strip()).samefile(tmp_path)

    def test_nonzero_exit_raises(self):
        with pytest.raises(subprocess.CalledProcessError) as exc:
            run_utility_command([sys.executable, "-c", "import sys; sys.exit(3)"])
        assert exc.value.returncode == 3


class TestLaunchDaemonCommand:
    def test_returns_immediately_and_child_runs_in_working_dir(self, tmp_path: Path):
        marker = tmp_path / "marker.txt"

        launch_daemon_command(
            [sys.executable, "-c", WRITE_CWD.format(delay=2)], working_dir=tmp_path
        )

        assert not marker.exists()
        wait_for(marker)
        assert Path(marker.read_text()).samefile(tmp_path)

    def test_invalid_working_dir_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="Invalid working directory"):
            launch_daemon_command([sys.executable], working_dir=tmp_path / "missing")
