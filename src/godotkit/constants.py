import platform

from godotkit import __name__, __version__

USER_AGENT = f"{__name__} v{__version__} (Python: v{platform.python_version()}, Platform: {platform.system()})"

GIT_CLONE_TIMEOUT = 300
RELEASE_FETCHER_TIMEOUT = 10
RELEASE_DOWNLOAD_TIMEOUT = 30
RSS_FETCHER_TIMEOUT = 10
