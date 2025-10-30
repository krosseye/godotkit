import pytest

from godotkit.engine.version_parsing import (
    CHANNEL_STABLE,
    VARIANT_DOTNET,
    VARIANT_MONO,
    VARIANT_STANDARD,
    GodotVersion,
)


@pytest.mark.parametrize(
    "version_str, major, minor, patch, channel, channel_num, csharp, variant",
    [
        ("4.5", 4, 5, 0, CHANNEL_STABLE, 0, False, VARIANT_STANDARD),
        ("3.6.2", 3, 6, 2, CHANNEL_STABLE, 0, False, VARIANT_STANDARD),
        ("4.5.1", 4, 5, 1, CHANNEL_STABLE, 0, False, VARIANT_STANDARD),
        ("4.5.1-rc1", 4, 5, 1, "rc", 1, False, VARIANT_STANDARD),
        (
            "4.5-rc",
            4,
            5,
            0,
            "rc",
            0,
            False,
            VARIANT_STANDARD,
        ),
        ("4.6-dev2 (.NET)", 4, 6, 0, "dev", 2, True, VARIANT_DOTNET),
        ("3.6.2 (Mono)", 3, 6, 2, CHANNEL_STABLE, 0, True, VARIANT_MONO),
    ],
)
def test_parse_version_string(
    version_str, major, minor, patch, channel, channel_num, csharp, variant
):
    """Tests parsing of various Godot version string formats."""
    v = GodotVersion.parse(version_str)

    assert v.major == major
    assert v.minor == minor
    assert v.patch == patch

    assert v.channel == channel
    assert v.channel_num == channel_num
    assert v.csharp_enabled == csharp
    assert v.variant == variant


def test_parse_invalid_string_raises():
    """Ensures parsing an invalid string raises a ValueError."""
    with pytest.raises(ValueError):
        GodotVersion.parse("not-a-version")


@pytest.mark.parametrize(
    "url, major, minor, patch, channel, channel_num, csharp, variant",
    [
        (
            "https://github.com/godotengine/godot-builds/releases/download/3.6.2-stable/Godot_v3.6.2-stable_mono_win64.zip",
            3,
            6,
            2,
            CHANNEL_STABLE,
            0,
            True,
            VARIANT_MONO,
        ),
        (
            "https://github.com/godotengine/godot-builds/releases/download/4.6-dev2/Godot_v4.6-dev2_mono_win64.zip",
            4,
            6,
            0,
            "dev",
            2,
            True,
            VARIANT_DOTNET,
        ),
        (
            "https://github.com/godotengine/godot-builds/releases/download/4.5-stable/Godot_v4.5-stable_win64.exe.zip",
            4,
            5,
            0,
            CHANNEL_STABLE,
            0,
            False,
            VARIANT_STANDARD,
        ),
    ],
)
def test_from_download_url(
    url, major, minor, patch, channel, channel_num, csharp, variant
):
    """Tests parsing a Godot version from a download URL."""
    v = GodotVersion.from_url(url)
    assert v.major == major
    assert v.minor == minor
    assert v.patch == patch
    assert v.channel == channel
    assert v.channel_num == channel_num
    assert v.csharp_enabled == csharp
    assert v.variant == variant


@pytest.mark.parametrize(
    "v1_str, v2_str, is_v1_less_than_v2",
    [
        ("4.5.1-rc1", "4.5.1-rc2", True),
        ("4.5.1-rc2", "4.5.1-rc1", False),
        ("4.5.1-rc2", "4.5.1", True),
        ("3.6.2", "3.6.2 (Mono)", False),
        ("3.6.2 (Mono)", "3.6.2", False),
        ("4.0.0", "4.0.1", True),
        ("4.0.9", "4.1.0", True),
    ],
)
def test_comparison_operators(v1_str, v2_str, is_v1_less_than_v2):
    """Tests the '<' comparison operator for versions."""
    v1 = GodotVersion.parse(v1_str)
    v2 = GodotVersion.parse(v2_str)

    assert (v1 < v2) == is_v1_less_than_v2

    if is_v1_less_than_v2:
        assert not (v1 > v2)
        assert (v1 <= v2) is True
        assert not (v1 >= v2)
    elif v1_str != v2_str:
        assert (v1 > v2) is True


def test_equality():
    """Tests that two identical versions are considered equal."""
    v1 = GodotVersion.parse("4.5.1")
    v2 = GodotVersion.parse("4.5.1")
    v3 = GodotVersion.parse("4.5.1 (Mono)")
    v4 = GodotVersion.parse("4.5.1 (.NET)")

    assert v1 == v2
    assert v1 != v3
    assert v3 == v4

    v_rc_0 = GodotVersion.parse("4.5-rc")
    v_rc_1 = GodotVersion.parse("4.5-rc1")
    assert v_rc_0 != v_rc_1


@pytest.mark.parametrize(
    "version_str",
    [
        "4.6-dev1 (.NET)",
        "3.6.2 (Mono)",
        "4.5",
    ],
)
def test_to_string_representation(version_str):
    """Tests that the string representation of a parsed version matches the input."""
    v = GodotVersion.parse(version_str)
    assert str(v) == version_str


def test_is_properties():
    """Tests the boolean property methods for version characteristics."""
    v_stable = GodotVersion.parse("4.5")
    v_mono = GodotVersion.parse("3.6.2 (Mono)")
    v_dotnet = GodotVersion.parse("4.6-dev1 (.NET)")
    v_rc = GodotVersion.parse("4.5.1-rc1")

    assert v_stable.is_stable
    assert v_mono.is_stable
    assert not v_dotnet.is_stable
    assert not v_rc.is_stable

    assert not v_stable.is_mono
    assert v_mono.is_mono
    assert not v_dotnet.is_mono
    assert not v_rc.is_mono

    assert not v_stable.is_dotnet
    assert not v_mono.is_dotnet
    assert v_dotnet.is_dotnet
    assert not v_rc.is_dotnet

    assert v_stable.is_standard
    assert not v_mono.is_standard
    assert not v_dotnet.is_standard
    assert v_rc.is_standard
