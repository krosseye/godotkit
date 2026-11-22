class GodotkitError(Exception):
    """Base class for errors raised when a godotkit operation fails."""


class DownloadError(GodotkitError):
    """A release download failed."""


class ExtractError(GodotkitError):
    """A downloaded release could not be extracted."""


class ReleaseNotFoundError(GodotkitError):
    """No Godot release matches the requested version."""


class AssetNotFoundError(GodotkitError):
    """The release exists, but has no editor build for the requested target."""


class GitError(GodotkitError, RuntimeError):
    """A git command failed, or git is not installed."""
