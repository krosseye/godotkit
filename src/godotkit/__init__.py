from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("godotkit")
except PackageNotFoundError:
    __version__ = "0.1.0"

from . import engine, project

__all__ = ["engine", "project"]
