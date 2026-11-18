import json
import logging
import os
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Self

import httpx

from godotkit.constants import RELEASE_CACHE_TTL, RELEASE_FETCHER_TIMEOUT, USER_AGENT

from .version_parsing import CSHARP_URL_VARIANTS, GodotVersion

logger = logging.getLogger(__name__)


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
    """Represents a single Godot release version."""

    def __init__(
        self,
        version: str,
        published_at: datetime,
        assets: list[GodotAsset],
    ):
        self.version = version
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
                f"Platform/Architecture combination not supported: {platform}/{arch}"
            )
            return None

        by_name = {asset.name: asset for asset in self.assets}
        for suffix in suffixes:
            asset = by_name.get(f"Godot_v{self.version}_{suffix}")
            if asset:
                logger.debug(f"Found matching asset: {asset.name}")
                return asset

        logger.debug(
            f"No matching asset found for {self.version} on {platform}/{arch} (csharp={csharp})"
        )
        return None

    def __repr__(self):
        return f"<GodotRelease {self.version}, published={self.published_at.date()}>"


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
        raise RuntimeError(f"Unsupported platform detected: {system}")


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
        raise RuntimeError(f"Unsupported CPU architecture detected: {machine}")

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

    STABLE_URL = "https://api.github.com/repos/godotengine/godot/releases"
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
        self._stable_only_cached: bool | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Closes the underlying HTTP client."""
        self.client.close()

    @staticmethod
    def version_sort_key(tag: str, csharp: bool = False) -> GodotVersion:
        """Converts a release tag like '4.5.1-stable' into a GodotVersion object for sorting."""
        try:
            return GodotVersion.from_tag(tag, csharp)
        except ValueError:
            logger.warning(
                f"Malformed version tag '{tag}' encountered. Sorting to bottom."
            )
            return GodotVersion(0, 0, 0, channel="dev")

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
            stable_only: If True, fetches only the main stable branch releases.
            sort_by: "version" (newest version first) else newest publish date first.
            max_releases: Maximum number of releases to return.
            platform_only: If True, filters releases to only include those with assets for the current system.
            refresh_cache: If True, clears the cache before fetching.
        Returns:
            A list of GodotRelease objects.
        """
        if refresh_cache or not self.cache or self._stable_only_cached != stable_only:
            self.cache = self._fetch_all(stable_only, use_disk_cache=not refresh_cache)
            self._stable_only_cached = stable_only
        else:
            logger.info("Using cached releases.")

        releases = self.cache
        if platform_only:
            user_platform = detect_platform()
            user_arch = detect_architecture()
            logger.info(f"Filtering for platform: {user_platform}/{user_arch}")
            releases = [
                r
                for r in releases
                if r.get_asset(user_platform, user_arch, csharp=False)
                or r.get_asset(user_platform, user_arch, csharp=True)
            ]

        if sort_by == "version":
            releases = sorted(
                releases, key=lambda r: self.version_sort_key(r.version), reverse=True
            )
        else:
            releases = sorted(releases, key=lambda r: r.published_at, reverse=True)

        return releases[:max_releases] if max_releases else releases

    def _fetch_all(
        self, stable_only: bool, use_disk_cache: bool = True
    ) -> list[GodotRelease]:
        source = "stable" if stable_only else "all"
        cache_file = self.cache_dir / f"releases_{source}.json"

        data = self._read_disk_cache(cache_file) if use_disk_cache else None
        if data is None:
            data = self._download(self.STABLE_URL if stable_only else self.ALL_URL)
            self._write_disk_cache(cache_file, data)
        else:
            logger.info(f"Using disk-cached {source} releases from {cache_file}.")

        releases: list[GodotRelease] = []
        for release in data:
            tag = release.get("tag_name")
            published_at = release.get("published_at")

            if not published_at or not tag:
                logger.warning(
                    f"Skipping malformed release: tag={tag}, published_at={published_at}"
                )
                continue

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

            releases.append(
                GodotRelease(version=tag, published_at=published_at, assets=assets)
            )

        logger.info(f"Successfully loaded {len(releases)} releases.")
        return releases

    def _download(self, url: str) -> list[dict]:
        """Downloads every release page, keeping only the fields we parse."""
        logger.info(f"Fetching releases from {url}.")
        data: list[dict] = []
        page = 1
        per_page = 100

        while True:
            request_url = f"{url}?page={page}&per_page={per_page}"
            logger.debug(f"Requesting URL: {request_url}")
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
            logger.warning(f"Could not write release cache {path}: {e}")

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
            f"Attempting to find download URL for version {version} on {platform_name}/{arch_name}, mono={mono}"
        )

        release = next((r for r in self.cache if r.version == version), None)
        if not release:
            cache_type = "stable" if self._stable_only_cached else "all"
            raise ValueError(
                f"Version {version} not found in current {cache_type} cache. "
                "You may need to call fetch_releases(stable_only=False) to update the cache."
            )

        asset = release.get_asset(platform_name, arch_name, mono)
        if not asset:
            raise ValueError(
                f"No download found for {platform_name} {arch_name} mono={mono} in version {version}"
            )

        logger.info(f"Found asset URL for {version}: {asset.url}")
        return asset.url
