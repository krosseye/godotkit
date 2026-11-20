class GodotkitError(Exception):
    """Base class for errors raised when a godotkit operation fails."""


class DownloadError(GodotkitError):
    """A release download failed."""


class ExtractError(GodotkitError):
    """A downloaded release could not be extracted."""


class GitError(GodotkitError, RuntimeError):
    """A git command failed, or git is not installed."""
