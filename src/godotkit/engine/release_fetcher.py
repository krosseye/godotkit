import logging
import platform
from datetime import datetime
from typing import List, Optional

import httpx

from godotkit.constants import RELEASE_FETCHER_TIMEOUT, USER_AGENT

from .version_parsing import CSHARP_URL_VARIANTS, GodotVersion

logger = logging.getLogger("GodotKit.Engine.ReleaseFetcher")


PLATFORMS = ["windows", "linux", "macos"]
ARCHS = ["x86", "x86_64", "arm32", "arm64"]

ARCH_KEYWORDS = {
    "windows": {
        "x86": ["win32"],
        "x86_64": ["win64"],
        "arm64": ["windows_arm64"],
    },
    "linux": {
        "x86": ["x11.32", "x11_32", "linux.x86_32", "linux_x86_32"],
        "x86_64": ["x11.64", "x11_64", "linux.x86_64", "linux_x86_64"],
        "arm32": ["linux.arm32", "linux_arm32"],
        "arm64": ["linux.arm64", "linux_arm64"],
    },
    "macos": {
        "x86": ["osx32", "osx.fat"],
        "x86_64": [
            "osx.64",
            "osx64",
            "osx.fat",
            "macos.universal",
            "osx.universal",
        ],
        "arm64": ["macos.universal", "osx.universal"],
    },
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
        assets: List[GodotAsset],
    ):
        self.version = version
        self.published_at = published_at
        self.assets = assets

    def get_asset(
        self, platform: str, arch: Optional[str] = None, csharp: bool = False
    ) -> Optional[GodotAsset]:
        """
        Retrieves a matching asset based on platform, architecture, and mono status.
        'arch' must be explicitly provided.
        """
        if not arch:
            logging.debug("Cannot find asset: architecture not provided.")
            return None

        keywords = ARCH_KEYWORDS.get(platform, {}).get(arch, [])
        if not keywords:
            logging.warning(
                f"Platform/Architecture combination not supported: {platform}/{arch}"
            )
            return None

        logging.debug(
            f"Searching for asset for version {self.version} on {platform}/{arch} (csharp={csharp}) with keywords: {keywords}"
        )

        for asset in self.assets:
            name = asset.name.lower()
            if csharp != asset.csharp_enabled:
                continue
            if any(k in name for k in keywords):
                logging.debug(f"Found matching asset: {asset.name}")
                return asset

        logging.debug(
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


class GodotFetcher:
    """Handles fetching and caching of Godot release information from GitHub."""

    STABLE_URL = "https://api.github.com/repos/godotengine/godot/releases"
    ALL_URL = "https://api.github.com/repos/godotengine/godot-builds/releases"

    def __init__(self, timeout: float = RELEASE_FETCHER_TIMEOUT):
        self.client = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})
        self.cache: List[GodotRelease] = []
        self._stable_only_cached: Optional[bool] = None

    @staticmethod
    def version_sort_key(tag: str, csharp: bool = False) -> GodotVersion:
        """Converts a release tag like '4.5.1-stable' into a GodotVersion object for sorting."""
        try:
            tag = tag.replace("-stable", "")
            if csharp:
                if tag.startswith("4."):
                    tag += " (.NET)"
                else:
                    tag += " (Mono)"
            return GodotVersion.parse(tag)
        except ValueError:
            logging.warning(
                f"Malformed version tag '{tag}' encountered. Sorting to bottom."
            )
            return GodotVersion(0, 0, 0, channel="dev")

    def fetch_releases(
        self,
        stable_only: bool = True,
        sort_by: str = "version",
        max_releases: Optional[int] = None,
        platform_only: bool = False,
        refresh_cache: bool = False,
    ) -> List[GodotRelease]:
        """
        Fetches Godot releases from GitHub.

        :param stable_only: If True, fetches only the main stable branch releases.
        :param max_releases: Maximum number of releases to fetch.
        :param platform_only: If True, filters releases to only include those with assets for the current system.
        :param refresh_cache: If True, clears the cache before fetching.
        :return: A list of GodotRelease objects.
        """
        if self.cache and not refresh_cache and self._stable_only_cached == stable_only:
            logging.info("Returning cached releases.")
            return self.cache

        source = "stable" if stable_only else "all"
        logging.info(f"Fetching {source} releases from GitHub.")

        url = self.STABLE_URL if stable_only else self.ALL_URL
        releases: List[GodotRelease] = []
        page = 1
        per_page = 30

        user_platform = detect_platform() if platform_only else None
        user_arch = detect_architecture() if platform_only and user_platform else None

        if platform_only:
            logging.info(f"Filtering for platform: {user_platform}/{user_arch}")

        while True:
            request_url = f"{url}?page={page}&per_page={per_page}"
            logging.debug(f"Requesting URL: {request_url}")
            response = self.client.get(request_url)
            response.raise_for_status()
            data = response.json()
            if not data:
                logging.info(f"No more data received after page {page}.")
                break

            logging.debug(f"Processing {len(data)} releases from page {page}.")

            for release in data:
                tag = release.get("tag_name", "N/A")
                published_at = release.get("published_at")

                if not published_at or tag == "N/A":
                    logging.warning(
                        f"Skipping malformed release: tag={tag}, published_at={published_at}"
                    )
                    continue

                published_at = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")

                assets = []
                for a in release.get("assets", []):
                    asset_name_lower = a["name"].lower()
                    csharp_enabled = any(
                        v in asset_name_lower for v in CSHARP_URL_VARIANTS
                    )
                    assets.append(
                        GodotAsset(
                            name=a["name"],
                            url=a["browser_download_url"],
                            size=a["size"],
                            csharp_enabled=csharp_enabled,
                        )
                    )

                godot_release = GodotRelease(
                    version=tag, published_at=published_at, assets=assets
                )

                if user_platform:
                    asset_found = godot_release.get_asset(
                        user_platform, user_arch, csharp=False
                    ) or godot_release.get_asset(user_platform, user_arch, csharp=True)
                    if not asset_found:
                        logging.debug(
                            f"Skipping {tag}: No asset found for {user_platform}/{user_arch}"
                        )
                        continue

                releases.append(godot_release)
                if max_releases and len(releases) >= max_releases:
                    logging.info(f"Reached max_releases limit of {max_releases}.")
                    break

            if max_releases and len(releases) >= max_releases:
                break

            if len(data) < per_page:
                logging.info("Finished fetching all available releases.")
                break

            page += 1

        if sort_by == "version":
            releases.sort(key=lambda r: self.version_sort_key(r.version), reverse=True)
        else:
            releases.sort(key=lambda r: r.published_at, reverse=True)

        logging.info(f"Successfully fetched and cached {len(releases)} releases.")
        self.cache = releases
        self._stable_only_cached = stable_only
        return releases

    def get_download_url(
        self,
        version: str,
        platform_name: Optional[str] = None,
        arch_name: Optional[str] = None,
        mono: bool = False,
    ) -> str:
        """
        Retrieves the direct download URL for a specific version and target.
        """
        platform_name = platform_name or detect_platform()
        arch_name = arch_name or detect_architecture()

        logging.info(
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

        logging.info(f"Found asset URL for {version}: {asset.url}")
        return asset.url
