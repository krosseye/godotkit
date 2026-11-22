class GodotkitError(Exception):
    """Base class for errors raised when a godotkit operation fails."""


class DownloadError(GodotkitError):
    """A release download failed."""


class DownloadCancelled(GodotkitError):
    """A download was stopped by its `cancel` callback."""


class ExtractError(GodotkitError):
    """A downloaded release could not be extracted."""


class ReleaseNotFoundError(GodotkitError):
    """No Godot release matches the requested version."""


class AssetNotFoundError(GodotkitError):
    """The release exists, but has no editor build for the requested target."""


class VersionFileError(GodotkitError, ValueError):
    """A project's `.godot-version` file holds no valid version."""


class GitError(GodotkitError, RuntimeError):
    """A git command failed, or git is not installed."""
