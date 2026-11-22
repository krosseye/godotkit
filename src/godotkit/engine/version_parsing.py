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

CSHARP_MARKER: str = "mono"

URL_VERSION_REGEX = re.compile(r"/download/([^/]+)/")

PARSE_REGEX = re.compile(
    r"""
    v?(?P<major>[0-9]+)\.(?P<minor>[0-9]+)(?:\.(?P<patch>[0-9]+))?
    (?:[-.](?P<channel>dev|alpha|beta|rc|stable)(?P<channel_num>[1-9][0-9]*)?)?
    (?P<csharp>(?:[-._+]|\s+)(?:mono|dotnet)|\s*\((?:mono|\.net)\))?
    """,
    re.IGNORECASE | re.ASCII | re.VERBOSE,
)


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class GodotVersion:
    """
    An immutable Godot Engine version: major/minor/patch, release channel,
    and C# support (Mono/.NET).

    `str(version)` is the canonical form, Godot's own version string
    (`GODOT_VERSION_FULL_CONFIG`): `4.3.stable`, `4.4.rc2`, `4.3.stable.mono`.
    See the version format page in the docs for the full grammar.

    Args:
        major: The major version number (e.g., 4 in 4.1.0).
        minor: The minor version number (e.g., 1 in 4.1.0).
        patch: The patch version number (e.g., 0 in 4.1.0).
        channel: The release channel: 'dev', 'alpha', 'beta', 'rc' or 'stable'.
        channel_num: The number after the channel (e.g., 2 in 'rc2'); 0 for none.
        csharp_enabled: True if this is a Mono/.NET variant build.

    Raises:
        ValueError: For an unknown channel, a negative number, or a channel
            number on stable.
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
        """The canonical form, e.g. `4.3.stable`, `4.4.rc2` or `3.6.stable.mono`."""
        text = f"{self._number}.{self._status}"
        return f"{text}.{CSHARP_MARKER}" if self.csharp_enabled else text

    @property
    def display_name(self) -> str:
        """
        A name for people, e.g. `4.3`, `4.4-rc2 (.NET)` or `3.6 (Mono)`.

        `parse` accepts it, but store and compare `str(version)` instead.
        """
        text = self._number if self.is_stable else f"{self._number}-{self._status}"
        return f"{text} ({self.variant})" if self.csharp_enabled else text

    @property
    def _number(self) -> str:
        if self.patch:
            return f"{self.major}.{self.minor}.{self.patch}"
        return f"{self.major}.{self.minor}"

    @property
    def _status(self) -> str:
        return f"{self.channel}{self.channel_num or ''}"

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
            "4.3.stable.mono"   the canonical form
            "4.3", "4.3.0"      no channel means stable
            "4.4-rc2", "v4.4.rc2"
            "4.3 mono", "4.3-dotnet", "4.3_mono", "4.3+mono"
            "4.6-dev2 (.NET)", "3.6.2 (Mono)"   the `display_name` form

        Args:
            version_string: The string representation of the version.

        Returns:
            A new GodotVersion instance.

        Raises:
            ValueError: If the string isn't a version, or has an unknown
                channel, a channel number of 0, or a number on stable.
        """
        match = PARSE_REGEX.fullmatch(version_string.strip())
        if not match:
            raise ValueError(f"Invalid Godot version string: {version_string!r}")

        return cls(
            int(match["major"]),
            int(match["minor"]),
            int(match["patch"] or 0),
            match["channel"] or CHANNEL_STABLE,
            int(match["channel_num"] or 0),
            bool(match["csharp"]),
        )

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
        Creates a GodotVersion from a GitHub release asset URL.

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

        filename = url.rsplit("/", 1)[-1].lower()
        return cls.from_tag(version_match.group(1), f"_{CSHARP_MARKER}" in filename)

    def to_tag(self) -> str:
        """
        Returns the GitHub release tag, e.g. "4.3-stable" or "4.4-rc2".

        The tag is the same for the standard and C# builds, so `csharp_enabled`
        is left out. `from_tag(v.to_tag(), v.csharp_enabled)` gives back `v`.
        """
        return f"{self._number}-{self._status}"

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
