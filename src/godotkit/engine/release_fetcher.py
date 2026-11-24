import io
import json
import logging
import os
import platform
import tarfile
import time
from dataclasses import replace
from datetime import UTC, date, datetime
from importlib.resources import files
from pathlib import Path
from typing import Self

import httpx

from godotkit.constants import RELEASE_CACHE_TTL, RELEASE_FETCHER_TIMEOUT, USER_AGENT
from godotkit.exceptions import (
    AssetNotFoundError,
    DownloadError,
    ReleaseNotFoundError,
)

from .version_parsing import CSHARP_MARKER, GodotVersion

logger = logging.getLogger(__name__)

# Editor builds the release files don't list, by tag: {name: SHA-512 or null}
# shortcut: null hashes (2.1 to 3.2.2-beta1, 3.2.4-beta2) install unverified
# fix: bake them by hashing those downloads once
OVERRIDES: dict[str, dict[str, str | None]] = json.loads(
    files(__package__).joinpath("overrides.json").read_text(encoding="utf-8")
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
    """A downloadable release file. `sha512` is its published hex checksum, or None."""

    def __init__(
        self,
        name: str,
        url: str,
        sha512: str | None = None,
        csharp_enabled: bool = False,
    ):
        self.name = name
        self.url = url
        self.sha512 = sha512
        self.csharp_enabled = csharp_enabled

    def __repr__(self):
        return f"<GodotAsset {self.name!r}, csharp={self.csharp_enabled}>"


class GodotRelease:
    """A single Godot release, e.g. the `4.3-stable` tag.

    `version` is parsed from `tag`. A release covers both the standard and .NET
    builds, so `version.csharp_enabled` is always False; use `get_asset(...,
    csharp=True)` for the .NET build.

    `published_at` is the release day (UTC).

    Raises:
        ValueError: If `tag` isn't a valid Godot version tag.
    """

    def __init__(
        self,
        tag: str,
        published_at: date,
        assets: list[GodotAsset],
    ):
        self.tag = tag
        self.version = GodotVersion.from_tag(tag)
        self.published_at = published_at
        self.assets = assets

    def get_asset(
        self,
        platform: str | None = None,
        arch: str | None = None,
        csharp: bool = False,
    ) -> GodotAsset | None:
        """Returns this release's editor build for a target, or None if it has none.

        Args:
            platform: One of `PLATFORMS`. Defaults to `detect_platform()`.
            arch: One of `ARCHS`. Defaults to `detect_architecture()`.
            csharp: True for the .NET build.

        Raises:
            ValueError: If `platform` or `arch` isn't a known name.
        """
        platform = platform or detect_platform()
        arch = arch or detect_architecture()
        if platform not in PLATFORMS or arch not in ARCHS:
            raise ValueError(f"Unknown platform or architecture: {platform}/{arch}")

        suffixes = ASSET_SUFFIXES.get((platform, arch, csharp))
        if not suffixes:
            logger.debug("Godot has no editor build for %s/%s.", platform, arch)
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
        return f"<GodotRelease {self.tag}, published={self.published_at}>"


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
    """Handles fetching and caching of Godot release information.

    Releases come from godot-builds' `releases/*.json`, downloaded
    with `OVERRIDES` applied. They're cached in `cache_dir` for
    `cache_ttl` seconds.

    `fetched_at` is when the cached release list was downloaded (timezone-aware
    UTC), or None before the first fetch.

    Use it as a context manager, or call `close()` when done.
    """

    ARCHIVE_URL = (
        "https://codeload.github.com/godotengine/godot-builds/tar.gz/refs/heads/main"
    )
    DOWNLOAD_URL = (
        "https://github.com/godotengine/godot-builds/releases/download/{tag}/{name}"
    )

    def __init__(
        self,
        timeout: float = RELEASE_FETCHER_TIMEOUT,
        cache_dir: Path | None = None,
        cache_ttl: float = RELEASE_CACHE_TTL,
    ):
        self.client = httpx.Client(
            timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        )
        self.cache_dir = cache_dir or default_cache_dir()
        self.cache_ttl = cache_ttl
        self.cache: list[GodotRelease] = []
        self.fetched_at: datetime | None = None

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
        platform: str | None = None,
        arch: str | None = None,
        refresh_cache: bool = False,
    ) -> list[GodotRelease]:
        """
        Fetches Godot releases.

        Args:
            stable_only: If True, returns only stable releases.
            sort_by: "version" (newest version first) else newest release date first.
            max_releases: Maximum number of releases to return.
            platform: Keep only releases with a standard or .NET editor build
                for this target. If only one of `platform`/`arch` is given, the
                other defaults to this machine. Neither: no filtering.
            arch: See `platform`.
            refresh_cache: If True, ignores the memory and disk caches.
        Returns:
            A list of GodotRelease objects.

        Raises:
            ValueError: If `platform` or `arch` isn't a known name.
            DownloadError: If the release list couldn't be downloaded or read.
        """
        if refresh_cache or not self.cache:
            self.cache = self._fetch_all(use_disk_cache=not refresh_cache)
        else:
            logger.info("Using cached releases.")

        releases = self.cache
        if stable_only:
            releases = [r for r in releases if r.version.is_stable]
        if platform or arch:
            platform = platform or detect_platform()
            arch = arch or detect_architecture()
            logger.info("Filtering for %s/%s.", platform, arch)
            releases = [
                r
                for r in releases
                if r.get_asset(platform, arch) or r.get_asset(platform, arch, True)
            ]

        if sort_by == "version":
            releases = sorted(releases, key=lambda r: r.version, reverse=True)
        else:
            releases = sorted(
                releases, key=lambda r: (r.published_at, r.version), reverse=True
            )

        return releases[:max_releases] if max_releases else releases

    def _fetch_all(self, use_disk_cache: bool = True) -> list[GodotRelease]:
        cache_file = self.cache_dir / "godot_builds.json"

        data = self._read_disk_cache(cache_file) if use_disk_cache else None
        if data is None:
            data = self._download(self.ARCHIVE_URL)
            self.fetched_at = datetime.now(UTC)
            self._write_disk_cache(cache_file, data)
        else:
            logger.info("Using disk-cached releases from %s.", cache_file)

        releases: list[GodotRelease] = []
        for release in data:
            tag = release["tag"]
            timestamp = release["release_date"]
            if not isinstance(timestamp, int):
                logger.warning("Skipping release %s: it has no release date.", tag)
                continue
            published_at = datetime.fromtimestamp(timestamp, UTC).date()

            extra = OVERRIDES.get(tag, {})
            checksums = {**extra, **release["files"]}
            checksums.update({n: h for n, h in extra.items() if h})
            assets = [
                GodotAsset(
                    name=name,
                    url=self.DOWNLOAD_URL.format(tag=tag, name=name),
                    sha512=sha512,
                    csharp_enabled=f"_{CSHARP_MARKER}" in name.lower(),
                )
                for name, sha512 in checksums.items()
            ]

            try:
                releases.append(GodotRelease(tag, published_at, assets))
            except ValueError:
                # Known and permanent (e.g. 2.0.4.1-stable) so not worth a warning
                logger.debug("Skipping release with malformed tag %r.", tag)

        logger.info("Successfully loaded %d releases.", len(releases))
        return releases

    def _download(self, url: str) -> list[dict]:
        """Downloads the godot-builds archive and reads its `releases/*.json`.

        Each release becomes `{"tag", "release_date", "files": {name: sha512}}`.
        """
        logger.info("Fetching releases from %s.", url)
        data: list[dict] = []
        try:
            response = self.client.get(url)
            response.raise_for_status()
            with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
                for member in tar:
                    path = Path(member.name)
                    if not (
                        member.isfile()
                        and path.parent.name == "releases"
                        and path.name.startswith("godot-")
                        and path.suffix == ".json"
                    ):
                        continue
                    # Older files hold a commit hash in "git_reference".
                    tag = path.stem.removeprefix("godot-")
                    try:
                        raw = json.load(tar.extractfile(member))  # type: ignore[arg-type]
                        files = {
                            f["filename"]: f["checksum"].lower()
                            for f in raw.get("files") or []
                        }
                    except (ValueError, KeyError, TypeError, AttributeError) as e:
                        logger.warning("Skipping unreadable %s: %s", path.name, e)
                        continue
                    data.append(
                        {
                            "tag": tag,
                            "release_date": raw.get("release_date"),
                            "files": files,
                        }
                    )
        except (httpx.HTTPError, tarfile.TarError) as e:
            raise DownloadError(
                f"Couldn't fetch the release list from {url}: {e}"
            ) from e

        return data

    def _read_disk_cache(self, path: Path) -> list[dict] | None:
        try:
            mtime = path.stat().st_mtime
            if time.time() - mtime > self.cache_ttl:
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        self.fetched_at = datetime.fromtimestamp(mtime, UTC)
        return data

    @staticmethod
    def _write_disk_cache(path: Path, data: list[dict]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(path)
        except OSError as e:
            logger.warning("Could not write release cache %s: %s", path, e)

    def find_asset(
        self,
        version: GodotVersion,
        platform: str | None = None,
        arch: str | None = None,
    ) -> GodotAsset:
        """Finds the editor build of `version` for a target.

        Fetches releases first if none are cached. `version.csharp_enabled`
        picks the .NET build.

        Args:
            version: The version to find, e.g. `GodotVersion.parse("4.3")`.
            platform: One of `PLATFORMS`. Defaults to `detect_platform()`.
            arch: One of `ARCHS`. Defaults to `detect_architecture()`.

        Raises:
            ReleaseNotFoundError: If no release has this version. Call
                `fetch_releases(refresh_cache=True)` first if it's brand new.
            AssetNotFoundError: If the release has no build for this target.
            DownloadError: If the release list couldn't be downloaded or read.
            ValueError: If `platform` or `arch` isn't a known name.
        """
        if not self.cache:
            self.fetch_releases()

        wanted = replace(version, csharp_enabled=False)
        release = next((r for r in self.cache if r.version == wanted), None)
        if not release:
            raise ReleaseNotFoundError(f"No Godot release found for {wanted}.")

        asset = release.get_asset(platform, arch, version.csharp_enabled)
        if not asset:
            raise AssetNotFoundError(
                f"Godot {version} has no editor build for "
                f"{platform or detect_platform()}/{arch or detect_architecture()}."
            )

        logger.info("Found %s for %s.", asset.url, version)
        if asset.sha512 is None:
            logger.warning("%s has no published checksum to verify.", asset.name)
        return asset
