import json
import logging
import os
import platform
import time
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Self

import httpx

from godotkit.constants import RELEASE_CACHE_TTL, RELEASE_FETCHER_TIMEOUT, USER_AGENT

from .version_parsing import CSHARP_URL_VARIANTS, GodotVersion

logger = logging.getLogger(__name__)

RELEASE_DATES: dict[str, str] = json.loads(
    files(__package__).joinpath("release_dates.json").read_text(encoding="utf-8")
)

PLATFORMS = ["windows", "linux", "macos"]
ARCHS = ["x86", "x86_64", "arm32", "arm64"]

# Editor builds are published as "Godot_v{tag}_{suffix}"
ASSET_SUFFIXES: dict[tuple[str, str, bool], tuple[str, ...]] = {
    # --- Windows: one naming scheme ---
    ("windows", "x86", False): ("win32.exe.zip",),
    ("windows", "x86", True): ("mono_win32.zip",),
    ("windows", "x86_64", False): ("win64.exe.zip",),
    ("windows", "x86_64", True): ("mono_win64.zip",),
    ("windows", "arm64", False): ("windows_arm64.exe.zip",),
    ("windows", "arm64", True): ("mono_windows_arm64.zip",),
    # --- Linux: "x11" in 3.x, renamed to "linux" during the 4.0 alphas ---
    ("linux", "x86", False): (
        "linux.x86_32.zip",  # 4.0-alpha15 onward
        "linux.32.zip",  # 4.0-alpha1 to 4.0-alpha14
        "x11.32.zip",  # 3.x
    ),
    ("linux", "x86", True): (
        "mono_linux_x86_32.zip",  # 4.x
        "mono_x11_32.zip",  # 3.x
    ),
    ("linux", "x86_64", False): (
        "linux.x86_64.zip",  # 4.0-alpha15 onward
        "linux.64.zip",  # 4.0-alpha1 to 4.0-alpha14
        "x11.64.zip",  # 3.x
    ),
    ("linux", "x86_64", True): (
        "mono_linux_x86_64.zip",  # 4.x
        "mono_x11_64.zip",  # 3.x
    ),
    ("linux", "arm32", False): ("linux.arm32.zip",),
    ("linux", "arm32", True): ("mono_linux_arm32.zip",),
    ("linux", "arm64", False): ("linux.arm64.zip",),
    ("linux", "arm64", True): ("mono_linux_arm64.zip",),
    # --- macOS: "fat" (Intel 32/64-bit), then Intel-only, then universal
    # (Intel + Apple Silicon), then one build per architecture from 4.8 ---
    ("macos", "x86", False): ("osx.fat.zip",),
    ("macos", "x86", True): ("mono_osx.fat.zip",),
    ("macos", "x86_64", False): (
        "macos.x86_64.zip",  # 4.8-beta1 onward
        "macos.universal.zip",  # 4.0-alpha13 to 4.8-dev7
        "osx.universal.zip",  # 3.2.4-beta2 to 4.0-alpha12
        "osx.64.zip",  # 3.1 to 3.2.4-beta2
        "osx.fat.zip",  # 3.0.x
    ),
    ("macos", "x86_64", True): (
        "mono_macos.x86_64.zip",  # 4.8-beta1 onward
        "mono_macos.universal.zip",  # 4.0-alpha17 to 4.8-dev7
        "mono_osx.universal.zip",  # 3.4 to 3.x
        "mono_osx.64.zip",  # 3.1 to 3.3.x
        "mono_osx_64.zip",  # 3.2-beta2 only
        "mono_osx.fat.zip",  # 3.0.3 to 3.0.6
        "mono_osx64.zip",  # 3.0 to 3.0.2
    ),
    ("macos", "arm64", False): (
        "macos.arm64.zip",  # 4.8-beta1 onward
        "macos.universal.zip",  # 4.0-alpha13 to 4.8-dev7
        "osx.universal.zip",  # 3.2.4-beta2 to 4.0-alpha12
    ),
    ("macos", "arm64", True): (
        "mono_macos.arm64.zip",  # 4.8-beta1 onward
        "mono_macos.universal.zip",  # 4.0-alpha17 to 4.8-dev7
        "mono_osx.universal.zip",  # 3.4 to 3.x
    ),
}


class GodotAsset:
    """Represents a single downloadable release asset."""

    def __init__(self, name: str, url: str, size: int, csharp_enabled: bool = False):
        self.name = name
        self.url = url
        self.size = size
        self.csharp_enabled = csharp_enabled

    def __repr__(self):
        return f"<GodotAsset {self.name!r}, {self.size} bytes, csharp={self.csharp_enabled}>"


class GodotRelease:
    """A single Godot release, e.g. the `4.3-stable` tag.

    `version` is parsed from `tag`. A release covers both the standard and .NET
    builds, so `version.csharp_enabled` is always False; use `get_asset(...,
    csharp=True)` for the .NET build.

    Raises:
        ValueError: If `tag` isn't a valid Godot version tag.
    """

    def __init__(
        self,
        tag: str,
        published_at: datetime,
        assets: list[GodotAsset],
    ):
        self.tag = tag
        self.version = GodotVersion.from_tag(tag)
        self.published_at = published_at
        self.assets = assets

    def get_asset(
        self, platform: str, arch: str | None = None, csharp: bool = False
    ) -> GodotAsset | None:
        """
        Retrieves a matching asset based on platform, architecture, and mono status.
        'arch' must be explicitly provided.
        """
        if not arch:
            logger.debug("Cannot find asset: architecture not provided.")
            return None

        suffixes = ASSET_SUFFIXES.get((platform, arch, csharp))
        if not suffixes:
            logger.warning(
                "Platform/Architecture combination not supported: %s/%s", platform, arch
            )
            return None

        by_name = {asset.name: asset for asset in self.assets}
        for suffix in suffixes:
            asset = by_name.get(f"Godot_v{self.tag}_{suffix}")
            if asset:
                logger.debug("Found matching asset: %s", asset.name)
                return asset

        logger.debug(
            "No matching asset found for %s on %s/%s (csharp=%s)",
            self.tag,
            platform,
            arch,
            csharp,
        )
        return None

    def __repr__(self):
        return f"<GodotRelease {self.tag}, published={self.published_at.date()}>"


def detect_platform() -> str:
    """Detects the current operating system and maps it to a supported platform name."""
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    elif "linux" in system:
        return "linux"
    elif "darwin" in system:
        return "macos"
    else:
        raise NotImplementedError(f"Unsupported platform detected: {system}")


def detect_architecture() -> str:
    """Detects the current CPU architecture and maps it to a supported arch name."""
    machine = platform.machine().lower()
    mapping = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "i686": "x86",
        "i386": "x86",
        "arm64": "arm64",
        "aarch64": "arm64",
        "armv7l": "arm32",
        "armv6l": "arm32",
    }

    arch = mapping.get(machine)
    if not arch:
        raise NotImplementedError(f"Unsupported CPU architecture detected: {machine}")

    return arch


def default_cache_dir() -> Path:
    """Per-user cache directory for godotkit."""
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Caches" / "godotkit"
    base = os.environ.get("LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME")
    return Path(base) / "godotkit" if base else Path.home() / ".cache" / "godotkit"


class GodotFetcher:
    """Handles fetching and caching of Godot release information from GitHub.

    Releases are cached on disk for `RELEASE_CACHE_TTL` seconds. If `GITHUB_TOKEN`
    or `GH_TOKEN` is set, requests are authenticated (5000 req/hour instead of 60).

    Use it as a context manager, or call `close()` when done.
    """

    ALL_URL = "https://api.github.com/repos/godotengine/godot-builds/releases"

    def __init__(
        self,
        timeout: float = RELEASE_FETCHER_TIMEOUT,
        cache_dir: Path | None = None,
    ):
        headers = {"User-Agent": USER_AGENT}
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.Client(timeout=timeout, headers=headers)
        self.cache_dir = cache_dir or default_cache_dir()
        self.cache: list[GodotRelease] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Closes the underlying HTTP client."""
        self.client.close()

    def fetch_releases(
        self,
        stable_only: bool = True,
        sort_by: str = "version",
        max_releases: int | None = None,
        platform_only: bool = False,
        refresh_cache: bool = False,
    ) -> list[GodotRelease]:
        """
        Fetches Godot releases from GitHub.

        Args:
            stable_only: If True, returns only stable releases.
            sort_by: "version" (newest version first) else newest release date first.
            max_releases: Maximum number of releases to return.
            platform_only: If True, filters releases to only include those with assets for the current system.
            refresh_cache: If True, clears the cache before fetching.
        Returns:
            A list of GodotRelease objects.
        """
        if refresh_cache or not self.cache:
            self.cache = self._fetch_all(use_disk_cache=not refresh_cache)
        else:
            logger.info("Using cached releases.")

        releases = self.cache
        if stable_only:
            releases = [r for r in releases if r.version.is_stable]
        if platform_only:
            user_platform = detect_platform()
            user_arch = detect_architecture()
            logger.info("Filtering for platform: %s/%s", user_platform, user_arch)
            releases = [
                r
                for r in releases
                if r.get_asset(user_platform, user_arch, csharp=False)
                or r.get_asset(user_platform, user_arch, csharp=True)
            ]

        if sort_by == "version":
            releases = sorted(releases, key=lambda r: r.version, reverse=True)
        else:
            releases = sorted(
                releases, key=lambda r: (r.published_at, r.version), reverse=True
            )

        return releases[:max_releases] if max_releases else releases

    def _fetch_all(self, use_disk_cache: bool = True) -> list[GodotRelease]:
        cache_file = self.cache_dir / "releases_all.json"

        data = self._read_disk_cache(cache_file) if use_disk_cache else None
        if data is None:
            data = self._download(self.ALL_URL)
            self._write_disk_cache(cache_file, data)
        else:
            logger.info("Using disk-cached releases from %s.", cache_file)

        releases: list[GodotRelease] = []
        for release in data:
            tag = release.get("tag_name")
            published_at = release.get("published_at")

            if not published_at or not tag:
                logger.warning(
                    "Skipping malformed release: tag=%s, published_at=%s",
                    tag,
                    published_at,
                )
                continue

            if tag in RELEASE_DATES:
                published_at = datetime.fromisoformat(RELEASE_DATES[tag])
            else:
                published_at = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")

            assets = []
            for a in release.get("assets", []):
                asset_name_lower = a["name"].lower()
                csharp_enabled = any(v in asset_name_lower for v in CSHARP_URL_VARIANTS)
                assets.append(
                    GodotAsset(
                        name=a["name"],
                        url=a["browser_download_url"],
                        size=a["size"],
                        csharp_enabled=csharp_enabled,
                    )
                )

            try:
                releases.append(GodotRelease(tag, published_at, assets))
            except ValueError:
                # Known and permanent (e.g. 2.0.4.1-stable) so not worth a warning
                logger.debug("Skipping release with malformed tag %r.", tag)

        logger.info("Successfully loaded %d releases.", len(releases))
        return releases

    def _download(self, url: str) -> list[dict]:
        """Downloads every release page, keeping only the fields we parse."""
        logger.info("Fetching releases from %s.", url)
        data: list[dict] = []
        page = 1
        per_page = 100

        while True:
            request_url = f"{url}?page={page}&per_page={per_page}"
            logger.debug("Requesting URL: %s", request_url)
            response = self.client.get(request_url)
            response.raise_for_status()
            page_data = response.json()
            if not page_data:
                break

            data.extend(
                {
                    "tag_name": r.get("tag_name"),
                    "published_at": r.get("published_at"),
                    "assets": [
                        {k: a[k] for k in ("name", "browser_download_url", "size")}
                        for a in r.get("assets", [])
                    ],
                }
                for r in page_data
            )

            if len(page_data) < per_page:
                break
            page += 1

        return data

    @staticmethod
    def _read_disk_cache(path: Path) -> list[dict] | None:
        try:
            if time.time() - path.stat().st_mtime > RELEASE_CACHE_TTL:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write_disk_cache(path: Path, data: list[dict]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(path)
        except OSError as e:
            logger.warning("Could not write release cache %s: %s", path, e)

    def get_download_url(
        self,
        version: str,
        platform_name: str | None = None,
        arch_name: str | None = None,
        mono: bool = False,
    ) -> str:
        """
        Retrieves the direct download URL for a specific version and target.
        """
        platform_name = platform_name or detect_platform()
        arch_name = arch_name or detect_architecture()

        logger.info(
            "Attempting to find download URL for version %s on %s/%s, mono=%s",
            version,
            platform_name,
            arch_name,
            mono,
        )

        release = next((r for r in self.cache if r.tag == version), None)
        if not release:
            raise ValueError(
                f"Version {version} not found. Call fetch_releases() first, "
                "or with refresh_cache=True if it was released recently."
            )

        asset = release.get_asset(platform_name, arch_name, mono)
        if not asset:
            raise ValueError(
                f"No download found for {platform_name} {arch_name} mono={mono} in version {version}"
            )

        logger.info("Found asset URL for %s: %s", version, asset.url)
        return asset.url
