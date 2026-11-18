from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("godotkit")
except PackageNotFoundError:
    __version__ = "0.0.0"
