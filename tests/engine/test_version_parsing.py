from dataclasses import FrozenInstanceError

import pytest

from godotkit.engine.release_fetcher import RELEASE_DATES
from godotkit.engine.version_parsing import (
    CHANNEL_STABLE,
    VARIANT_DOTNET,
    VARIANT_MONO,
    VARIANT_STANDARD,
    GodotVersion,
)


class TestParseFromString:
    @pytest.mark.parametrize(
        "version_str, major, minor, patch, channel, channel_num, csharp, variant",
        [
            ("4.5", 4, 5, 0, CHANNEL_STABLE, 0, False, VARIANT_STANDARD),
            ("3.6.2", 3, 6, 2, CHANNEL_STABLE, 0, False, VARIANT_STANDARD),
            ("4.5.1", 4, 5, 1, CHANNEL_STABLE, 0, False, VARIANT_STANDARD),
            ("4.5.1-rc1", 4, 5, 1, "rc", 1, False, VARIANT_STANDARD),
            ("4.5-rc", 4, 5, 0, "rc", 0, False, VARIANT_STANDARD),
            ("4.6-dev2 (.NET)", 4, 6, 0, "dev", 2, True, VARIANT_DOTNET),
            ("3.6.2 (Mono)", 3, 6, 2, CHANNEL_STABLE, 0, True, VARIANT_MONO),
        ],
    )
    def test_parse_valid_formats_expected_fields(
        self, version_str, major, minor, patch, channel, channel_num, csharp, variant
    ):
        v = GodotVersion.parse(version_str)

        assert (v.major, v.minor, v.patch) == (major, minor, patch)
        assert (v.channel, v.channel_num) == (channel, channel_num)
        assert v.csharp_enabled == csharp
        assert v.variant == variant

    def test_parse_invalid_string_raises_valueerror(self):
        with pytest.raises(ValueError):
            GodotVersion.parse("not-a-version")


class TestFromUrl:
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
    def test_from_url_valid_formats_expected_fields(
        self, url, major, minor, patch, channel, channel_num, csharp, variant
    ):
        v = GodotVersion.from_url(url)

        assert (v.major, v.minor, v.patch) == (major, minor, patch)
        assert (v.channel, v.channel_num) == (channel, channel_num)
        assert v.csharp_enabled == csharp
        assert v.variant == variant


class TestComparison:
    @pytest.mark.parametrize(
        "v1_str, v2_str, is_v1_less_than_v2",
        [
            ("4.5.1-rc1", "4.5.1-rc2", True),
            ("4.5.1-rc2", "4.5.1-rc1", False),
            ("4.5.1-rc2", "4.5.1", True),
            ("3.6.2", "3.6.2 (Mono)", False),
            ("3.6.2 (Mono)", "3.6.2", True),
            ("4.0.0", "4.0.1", True),
            ("4.0.9", "4.1.0", True),
        ],
    )
    def test_comparison_lt_behavior_expected_result(
        self, v1_str, v2_str, is_v1_less_than_v2
    ):
        v1 = GodotVersion.parse(v1_str)
        v2 = GodotVersion.parse(v2_str)

        assert (v1 < v2) == is_v1_less_than_v2

        if is_v1_less_than_v2:
            assert not (v1 > v2)
            assert v1 <= v2
            assert not (v1 >= v2)
        elif v1_str != v2_str:
            assert v1 > v2

    def test_major_minor_keeps_two_digit_minor(self):
        v = GodotVersion(4, 10, 2, "rc", 1, csharp_enabled=True)

        assert v.major_minor == GodotVersion(4, 10)
        assert str(v.major_minor) == "4.10.stable"
        assert GodotVersion(4, 10).major_minor > GodotVersion(4, 9).major_minor

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"channel": "foo"},
            {"channel": "mono"},
            {"channel": "stable", "channel_num": 2},
            {"channel_num": -1, "channel": "rc"},
            {"patch": -1},
        ],
    )
    def test_invalid_fields_raise(self, kwargs):
        with pytest.raises(ValueError):
            GodotVersion(4, 0, **kwargs)

    @pytest.mark.parametrize(
        "text",
        [
            "4.3-stable2",
            "4.4-rc0",
            "4.3-foo1",
            "٤.٣",
            "4.3-rc1x",
            "4.3.stable.double",
            "4.3.stable.mono.official.77dcf97d8",
            "2.0.4.1-stable",
            "4.3 .NET",
            "4.3mono",
        ],
    )
    def test_parse_rejects_ambiguous_or_lossy_input(self, text):
        with pytest.raises(ValueError):
            GodotVersion.parse(text)

    def test_ordering_is_total_across_variants(self):
        std = GodotVersion(4, 0)
        net = GodotVersion(4, 0, csharp_enabled=True)

        assert std != net
        assert net < std
        assert net <= std and not std <= net
        assert sorted([net, std], reverse=True) == [std, net]

    def test_equality_with_other_type_is_not_implemented(self):
        assert GodotVersion(4, 0).__eq__("4.0") is NotImplemented
        assert GodotVersion(4, 0) != "4.0"

    def test_equality_variants_and_channels_expected_behavior(self):
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


class TestStringAndProperties:
    @pytest.mark.parametrize(
        ("version", "canonical", "display"),
        [
            (GodotVersion(4, 3), "4.3.stable", "4.3"),
            (GodotVersion(4, 3, 1), "4.3.1.stable", "4.3.1"),
            (GodotVersion(4, 4, 0, "rc", 2), "4.4.rc2", "4.4-rc2"),
            (GodotVersion(4, 8, 0, "beta"), "4.8.beta", "4.8-beta"),
            (GodotVersion(3, 2, 4, "beta", 5), "3.2.4.beta5", "3.2.4-beta5"),
            (GodotVersion(4, 3, csharp_enabled=True), "4.3.stable.mono", "4.3 (.NET)"),
            (GodotVersion(3, 6, csharp_enabled=True), "3.6.stable.mono", "3.6 (Mono)"),
            (
                GodotVersion(4, 4, 0, "rc", 2, csharp_enabled=True),
                "4.4.rc2.mono",
                "4.4-rc2 (.NET)",
            ),
        ],
    )
    def test_canonical_and_display_forms_round_trip(self, version, canonical, display):
        assert str(version) == canonical
        assert version.display_name == display
        assert GodotVersion.parse(canonical) == version
        assert GodotVersion.parse(display) == version

    @pytest.mark.parametrize(
        "text",
        [
            "4.3.stable.mono",
            "4.3-stable-mono",
            "4.3_mono",
            "4.3+mono",
            "4.3.0 mono",
            "v4.3 (.NET)",
            "4.3 (Mono)",
            "4.3-DOTNET",
            "  4.3.Stable.Mono\n",
        ],
    )
    def test_parse_accepts_lenient_csharp_spellings(self, text):
        assert GodotVersion.parse(text) == GodotVersion(4, 3, csharp_enabled=True)

    @pytest.mark.parametrize("csharp", [False, True])
    def test_every_release_round_trips_through_str(self, csharp):
        tags = set(RELEASE_DATES) - {"2.0.4.1-stable", "3.2-alpha0-unofficial"}
        versions = [GodotVersion.from_tag(t, csharp) for t in tags]
        assert [v for v in versions if GodotVersion.parse(str(v)) != v] == []

    def test_is_property_flags_expected_truth_values(self):
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


class TestFromTag:
    def test_from_tag_matches_parse_and_sets_variant(self):
        assert GodotVersion.from_tag("4.5.1-stable") == GodotVersion(4, 5, 1)
        assert GodotVersion.from_tag("4.6-rc2", csharp_enabled=True) == GodotVersion(
            4, 6, 0, "rc", 2, csharp_enabled=True
        )
        assert GodotVersion.from_tag("3.6-stable", csharp_enabled=True).is_mono

    def test_from_tag_invalid_raises_valueerror(self):
        with pytest.raises(ValueError):
            GodotVersion.from_tag("junk-tag")


class TestToTag:
    @pytest.mark.parametrize(
        ("version", "tag"),
        [
            (GodotVersion(4, 3), "4.3-stable"),
            (GodotVersion(4, 1, 1), "4.1.1-stable"),
            (GodotVersion(4, 4, 0, "rc", 2), "4.4-rc2"),
            (GodotVersion(3, 2, 4, "beta", 1, csharp_enabled=True), "3.2.4-beta1"),
            (GodotVersion(4, 3, csharp_enabled=True), "4.3-stable"),
        ],
    )
    def test_to_tag(self, version, tag):
        assert version.to_tag() == tag

    def test_round_trips_every_imported_release_tag(self):
        tags = set(RELEASE_DATES) - {"2.0.4.1-stable", "3.2-alpha0-unofficial"}
        assert [t for t in tags if GodotVersion.from_tag(t).to_tag() != t] == []

    def test_round_trip_keeps_csharp_flag(self):
        version = GodotVersion(4, 4, 0, "dev", 7, csharp_enabled=True)
        assert GodotVersion.from_tag(version.to_tag(), True) == version


class TestImmutable:
    def test_assigning_a_field_raises(self):
        version = GodotVersion(4, 3)
        with pytest.raises(FrozenInstanceError):
            version.csharp_enabled = True  # type: ignore[misc]
        assert version.is_standard

    def test_channel_is_normalised_and_hash_follows_equality(self):
        version = GodotVersion(4, 4, channel="RC", channel_num=2)
        assert version.channel == "rc"
        assert {version: 1}[GodotVersion.parse("4.4-rc2")] == 1
        assert repr(version) == (
            "GodotVersion(major=4, minor=4, patch=0, channel='rc', "
            "channel_num=2, csharp_enabled=False)"
        )
