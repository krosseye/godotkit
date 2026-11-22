import re
from dataclasses import dataclass, replace
from functools import total_ordering

CHANNEL_STABLE: str = "stable"

VARIANT_STANDARD: str = "Standard"
VARIANT_DOTNET: str = ".NET"
VARIANT_MONO: str = "Mono"

RELEASE_CHANNEL_RANKING = {
    "dev": 0,
    "alpha": 1,
    "beta": 2,
    "rc": 3,
    CHANNEL_STABLE: 4,
}

CSHARP_PARSE_VARIANTS: set[str] = {"mono", "dotnet", ".net"}
CSHARP_URL_VARIANTS: set[str] = {
    "_mono",
    "_dotnet",
    ".net",
}  # For future-proofing; only mono is officially used currently.

URL_VERSION_REGEX = re.compile(r"/download/([^/]+)/")

REGEX_PART_CORE_VERSION: str = r"(?:v)?([0-9]+\.[0-9]+(?:\.[0-9]+)?)"  # Group 1: major.minor(.patch) - e.g., "4.6.2" or "v4.5"
REGEX_PART_RELEASE_CHANNEL: str = r"(?:-(dev|alpha|beta|rc|stable)([1-9][0-9]*)?)?"  # Group 2: channel, Group 3: channel number
REGEX_PART_CSHARP_VARIANT: str = r"(?:\s*\((mono|\.net|dotnet)\))?"  # Group 4: optional variant string (e.g., "(Mono)", "(.NET)")

STRING_PARSE_REGEX = re.compile(
    f"^{REGEX_PART_CORE_VERSION}{REGEX_PART_RELEASE_CHANNEL}{REGEX_PART_CSHARP_VARIANT}$",
    re.IGNORECASE,
)
URL_PARSE_REGEX = re.compile(
    f"^{REGEX_PART_CORE_VERSION}{REGEX_PART_RELEASE_CHANNEL}$",
    re.IGNORECASE,
)


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class GodotVersion:
    """
    An immutable Godot Engine version: major/minor/patch, release channel,
    and C# support (Mono/.NET). Supports parsing from strings and URLs, and
    version comparisons.

    Args:
        major: The major version number (e.g., 4 in 4.1.0).
        minor: The minor version number (e.g., 1 in 4.1.0).
        patch: The patch version number (e.g., 0 in 4.1.0).
        channel: The release channel (e.g., 'stable', 'rc', 'dev').
        channel_num: The sequential number for the channel (e.g., 2 in 'rc2').
        csharp_enabled: True if this is a Mono/.NET variant build.
    """

    major: int
    minor: int
    patch: int = 0
    channel: str = CHANNEL_STABLE
    channel_num: int = 0
    csharp_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel", self.channel.lower())
        if self.channel not in RELEASE_CHANNEL_RANKING:
            raise ValueError(f"Unknown release channel: {self.channel!r}")
        if min(self.major, self.minor, self.patch, self.channel_num) < 0:
            raise ValueError(f"Negative version number in {self!r}")
        if self.is_stable and self.channel_num:
            raise ValueError("A stable version has no channel number")

    def __str__(self) -> str:
        if self.patch > 0:
            base = f"{self.major}.{self.minor}.{self.patch}"
        else:
            base = f"{self.major}.{self.minor}"

        if self.channel != CHANNEL_STABLE:
            base += f"-{self.channel}"
            if self.channel_num > 0:
                base += str(self.channel_num)

        if self.csharp_enabled:
            base += f" ({self.variant})"

        return base

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, GodotVersion):
            return NotImplemented
        return self._key() < other._key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GodotVersion):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    @classmethod
    def parse(cls, version_string: str) -> "GodotVersion":
        """
        Parses a Godot version string into a GodotVersion object.

        Examples of supported strings:
            "4.6-dev2 (.NET)"
            "3.6.2 (Mono)"
            "4.5.1"
            "4.5"

        Args:
            version_string: The string representation of the version.

        Returns:
            A new GodotVersion instance.

        Raises:
            ValueError: If the version string format is invalid.
        """
        match = STRING_PARSE_REGEX.match(version_string.strip())
        if not match:
            raise ValueError(f"Invalid Godot version string: {version_string}")

        version_parts = match.group(1).split(".")
        major = int(version_parts[0])
        minor = int(version_parts[1])
        patch = int(version_parts[2]) if len(version_parts) > 2 else 0

        channel = match.group(2).lower() if match.group(2) else CHANNEL_STABLE
        channel_num = int(match.group(3)) if match.group(3) else 0

        variant_str = match.group(4) or ""
        csharp_enabled = variant_str.strip().lower() in CSHARP_PARSE_VARIANTS

        return cls(major, minor, patch, channel, channel_num, csharp_enabled)

    @classmethod
    def from_tag(cls, tag: str, csharp_enabled: bool = False) -> "GodotVersion":
        """
        Parses a GitHub release tag string into a GodotVersion object.

        Args:
            tag: The string representation of the version tag.
            csharp_enabled: True if this is a Mono/.NET variant build.

        Returns:
            A new GodotVersion instance.

        Raises:
            ValueError: If the version string format is invalid.
        """
        return replace(cls.parse(tag), csharp_enabled=csharp_enabled)

    @classmethod
    def from_url(cls, url: str) -> "GodotVersion":
        """
        Creates a GodotVersion from a GitHub release URL.

        Args:
            url: The full URL of the release asset.

        Returns:
            A new GodotVersion instance.

        Raises:
            ValueError: If the version string cannot be found or parsed from the URL.
        """
        version_match = URL_VERSION_REGEX.search(url)
        if not version_match:
            raise ValueError(f"Could not find version string in URL: {url}")

        version_string_from_url = version_match.group(1)

        match = URL_PARSE_REGEX.match(version_string_from_url)
        if not match:
            raise ValueError(
                f"Invalid version string in URL: {version_string_from_url}"
            )

        version_parts = match.group(1).split(".")
        major = int(version_parts[0])
        minor = int(version_parts[1])
        patch = int(version_parts[2]) if len(version_parts) > 2 else 0

        channel = match.group(2).lower() if match.group(2) else CHANNEL_STABLE
        channel_num = int(match.group(3)) if match.group(3) else 0

        filename_lower = url.split("/")[-1].lower()
        csharp_enabled = any(
            variant in filename_lower for variant in CSHARP_URL_VARIANTS
        )

        return cls(major, minor, patch, channel, channel_num, csharp_enabled)

    def to_tag(self) -> str:
        """
        Returns the GitHub release tag, e.g. "4.3-stable" or "4.4-rc2".

        The tag is the same for the standard and C# builds, so `csharp_enabled`
        is left out. `from_tag(v.to_tag(), v.csharp_enabled)` gives back `v`.
        """
        tag = str(replace(self, csharp_enabled=False))
        return f"{tag}-{CHANNEL_STABLE}" if self.is_stable else tag

    def _key(self) -> tuple[int, int, int, int, int, bool]:
        """
        Returns a tuple suitable for ordering, equality and hashing.

        The C# variant is a deterministic tie-break, not "older": it sorts below the
        standard build so newest-first lists (reverse=True) show standard first.
        """
        return (
            self.major,
            self.minor,
            self.patch,
            RELEASE_CHANNEL_RANKING[self.channel],
            self.channel_num,
            self.is_standard,
        )

    @property
    def variant(self) -> str:
        """
        Returns the variant name (Standard, Mono, or .NET)
        based on C# support and the major version number.

        Godot 3.x uses Mono, Godot 4+ uses .NET.
        """
        if not self.csharp_enabled:
            return VARIANT_STANDARD

        return VARIANT_DOTNET if self.major >= 4 else VARIANT_MONO

    @property
    def is_stable(self) -> bool:
        """Checks if the version is a stable release."""
        return self.channel == CHANNEL_STABLE

    @property
    def is_standard(self) -> bool:
        """Checks if the version is the standard (non-C#) build."""
        return not self.csharp_enabled

    @property
    def is_mono(self) -> bool:
        """Checks if the version is a Mono build (Godot 3.x with C#)."""
        return self.csharp_enabled and self.major < 4

    @property
    def is_dotnet(self) -> bool:
        """Checks if the version is a .NET build (Godot 4+ with C#)."""
        return self.csharp_enabled and self.major >= 4

    @property
    def major_minor(self) -> "GodotVersion":
        """
        Returns the stable, standard major.minor version (e.g. 4.10 for 4.10.2-rc1 (.NET)).
        """
        return GodotVersion(self.major, self.minor)
