import shutil
from pathlib import Path

import pytest

from godotkit.common import remove_directory


@pytest.fixture
def dummy_dir_with_content(tmp_path: Path) -> Path:
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "some_file.txt").touch()
    sub_dir = test_dir / "sub_dir"
    sub_dir.mkdir()
    (sub_dir / "another_file.log").touch()
    return test_dir


class TestRemoveDirectory:
    def test_remove_directory_successfully_deletes_dir(
        self, dummy_dir_with_content: Path
    ):
        assert dummy_dir_with_content.exists()
        remove_directory(dummy_dir_with_content)
        assert not dummy_dir_with_content.exists()

    def test_remove_non_existent_directory_raises_valueerror(self, tmp_path: Path):
        invalid_path = tmp_path / "not_a_dir"
        with pytest.raises(ValueError, match="Invalid directory path"):
            remove_directory(invalid_path)

    def test_remove_file_instead_of_dir_raises_valueerror(self, tmp_path: Path):
        file_path = tmp_path / "a_file.txt"
        file_path.touch()
        with pytest.raises(ValueError, match="Invalid directory path"):
            remove_directory(file_path)

    def test_remove_directory_permission_error_raises_permissionerror(
        self, dummy_dir_with_content: Path, mocker
    ):
        mocker.patch.object(shutil, "rmtree", side_effect=PermissionError)
        with pytest.raises(PermissionError):
            remove_directory(dummy_dir_with_content)

    def test_remove_directory_os_error_raises_oserror(
        self, dummy_dir_with_content: Path, mocker
    ):
        mocker.patch.object(shutil, "rmtree", side_effect=OSError)
        with pytest.raises(OSError):
            remove_directory(dummy_dir_with_content)
