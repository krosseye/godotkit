import io
import json
import re
import sys
import tarfile
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from godotkit.engine import (
    AssetNotFoundError,
    GodotVersion,
    ReleaseNotFoundError,
)
from godotkit.engine.release_fetcher import (
    ASSET_SUFFIXES,
    OVERRIDES,
    GodotAsset,
    GodotFetcher,
    GodotRelease,
    detect_architecture,
    detect_platform,
)
from godotkit.exceptions import GodotkitError

SHA = "ab" * 64

MOCK_RELEASES = [
    {
        "tag": "4.1.1-stable",
        "release_date": 1694779200,
        "files": [
            {"filename": "Godot_v4.1.1-stable_win64.exe.zip", "checksum": SHA},
            {"filename": "Godot_v4.1.1-stable_mono_linux_x86_64.zip", "checksum": SHA},
        ],
    },
    {
        "tag": "4.0-rc1",
        "release_date": 1672567200,
        "files": [
            {"filename": "Godot_v4.0-rc1_macos.universal.zip", "checksum": SHA},
        ],
    },
]


def make_archive(releases: list[dict], extra: dict[str, bytes] | None = None) -> bytes:
    """A godot-builds tarball holding `releases` (plus raw `extra` files)."""
    members = {
        f"releases/godot-{r['tag']}.json": json.dumps(
            {k: v for k, v in r.items() if k != "tag"}
        ).encode()
        for r in releases
    }
    members |= extra or {}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, body in members.items():
            info = tarfile.TarInfo(f"godot-builds-main/{name}")
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    return buf.getvalue()


@pytest.fixture
def mock_fetcher(mocker, tmp_path):
    fetcher = GodotFetcher(cache_dir=tmp_path)
    fetcher.client = mocker.MagicMock()
    return fetcher


@pytest.fixture
def godot_release_4_1_1():
    assets = [
        GodotAsset(
            name="Godot_v4.1.1-stable_win64.exe.zip",
            url="http://win64",
            csharp_enabled=False,
        ),
        GodotAsset(
            name="Godot_v4.1.1-stable_mono_linux_x86_64.zip",
            url="http://linux_mono",
            csharp_enabled=True,
        ),
        GodotAsset(
            name="Godot_v4.1.1-stable_linux.x86_64.zip",
            url="http://linux_std",
            csharp_enabled=False,
        ),
    ]
    return GodotRelease(
        tag="4.1.1-stable",
        published_at=date(2023, 9, 15),
        assets=assets,
    )


def setup_mock_response(mock_fetcher, archives):
    responses = []
    for releases in archives:
        mock_response = MagicMock()
        mock_response.content = make_archive(releases)
        responses.append(mock_response)
    mock_fetcher.client.get.side_effect = responses


class TestDetectPlatform:
    @pytest.mark.parametrize(
        "platform_system, expected",
        [("Windows", "windows"), ("Darwin", "macos"), ("Linux", "linux")],
    )
    def test_detect_platform_returns_expected_os(
        self, mocker, platform_system, expected
    ):
        mocker.patch("platform.system", return_value=platform_system)
        assert detect_platform() == expected


class TestDetectArchitecture:
    @pytest.mark.parametrize(
        "platform_machine, expected",
        [
            ("AMD64", "x86_64"),
            ("x86_64", "x86_64"),
            ("aarch64", "arm64"),
            ("armv7l", "arm32"),
            ("i686", "x86"),
        ],
    )
    def test_detect_architecture_returns_expected_arch(
        self, mocker, platform_machine, expected
    ):
        mocker.patch("platform.machine", return_value=platform_machine)
        assert detect_architecture() == expected

    def test_detect_architecture_unsupported_raises_not_implemented(self):
        with (
            patch("platform.machine", return_value="ppc"),
            pytest.raises(NotImplementedError, match="Unsupported CPU architecture"),
        ):
            detect_architecture()


class TestNativeDetection:
    """Unmocked: runs against the OS and CPU of whichever runner executes it."""

    def test_detect_platform_matches_this_os(self):
        expected = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
        assert detect_platform() == expected

    def test_detect_architecture_supports_this_cpu(self):
        assert (detect_platform(), detect_architecture(), False) in ASSET_SUFFIXES

    @pytest.mark.parametrize("csharp", [False, True], ids=["standard", "dotnet"])
    def test_finds_a_build_for_this_machine(self, csharp: bool):
        names = [
            "Godot_v4.3-stable_win64.exe.zip",
            "Godot_v4.3-stable_linux.x86_64.zip",
            "Godot_v4.3-stable_linux.arm64.zip",
            "Godot_v4.3-stable_macos.universal.zip",
            "Godot_v4.3-stable_mono_win64.zip",
            "Godot_v4.3-stable_mono_linux_x86_64.zip",
            "Godot_v4.3-stable_mono_linux_arm64.zip",
            "Godot_v4.3-stable_mono_macos.universal.zip",
        ]
        release = GodotRelease(
            "4.3-stable",
            date(2026, 11, 16),
            [
                GodotAsset(n, f"https://example.com/{n}", csharp_enabled="_mono" in n)
                for n in names
            ],
        )

        asset = release.get_asset(detect_platform(), detect_architecture(), csharp)

        assert asset is not None
        assert asset.csharp_enabled == csharp


class TestGodotRelease:
    def test_get_asset_with_standard_variant_returns_asset(self, godot_release_4_1_1):
        asset = godot_release_4_1_1.get_asset("windows", "x86_64", csharp=False)
        assert asset.name == "Godot_v4.1.1-stable_win64.exe.zip"
        assert asset.csharp_enabled is False

    def test_get_asset_with_csharp_variant_returns_asset(self, godot_release_4_1_1):
        asset = godot_release_4_1_1.get_asset("linux", "x86_64", csharp=True)
        assert asset.name == "Godot_v4.1.1-stable_mono_linux_x86_64.zip"
        assert asset.csharp_enabled is True

    def test_get_asset_defaults_to_this_machine(self, godot_release_4_1_1, mocker):
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_platform", return_value="linux"
        )
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_architecture", return_value="x86_64"
        )
        assert godot_release_4_1_1.get_asset().url == "http://linux_std"

    def test_get_asset_with_unbuilt_combo_returns_none(self, godot_release_4_1_1):
        assert godot_release_4_1_1.get_asset("windows", "arm32") is None

    @pytest.mark.parametrize("platform, arch", [("win", "x86_64"), ("linux", "amd64")])
    def test_get_asset_with_unknown_name_raises(
        self, godot_release_4_1_1, platform, arch
    ):
        with pytest.raises(ValueError, match="Unknown platform or architecture"):
            godot_release_4_1_1.get_asset(platform, arch)


class TestGodotReleaseVersion:
    def test_version_is_parsed_from_tag(self):
        release = GodotRelease("4.4-rc2", date(2025, 2, 20), [])
        assert release.tag == "4.4-rc2"
        assert release.version == GodotVersion(4, 4, channel="rc", channel_num=2)
        assert release.version.csharp_enabled is False

    def test_malformed_tag_raises(self):
        with pytest.raises(ValueError):
            GodotRelease("2.0.4.1-stable", date(2016, 1, 1), [])

    def test_fetch_skips_malformed_tags_at_debug(self, mock_fetcher, caplog):
        malformed = {**MOCK_RELEASES[1], "tag": "3.2-alpha0-unofficial"}
        setup_mock_response(mock_fetcher, [[*MOCK_RELEASES, malformed]])

        with caplog.at_level("DEBUG", logger="godotkit.engine.release_fetcher"):
            releases = mock_fetcher.fetch_releases(stable_only=False)

        assert [r.tag for r in releases] == ["4.1.1-stable", "4.0-rc1"]
        skipped = [r for r in caplog.records if "3.2-alpha0-unofficial" in r.message]
        assert [r.levelname for r in skipped] == ["DEBUG"]


class TestGodotFetcherReleaseFetching:
    def test_fetch_releases_with_stable_only_returns_stable_releases(
        self, mock_fetcher
    ):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        releases = mock_fetcher.fetch_releases(stable_only=True)
        assert [r.tag for r in releases] == ["4.1.1-stable"]
        mock_fetcher.client.get.assert_called_with(GodotFetcher.ARCHIVE_URL)

    def test_switching_stable_only_does_not_refetch(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        mock_fetcher.fetch_releases(stable_only=True)
        mock_fetcher.client.get.reset_mock()

        releases = mock_fetcher.fetch_releases(stable_only=False)

        mock_fetcher.client.get.assert_not_called()
        assert [r.tag for r in releases] == ["4.1.1-stable", "4.0-rc1"]

    def test_same_day_releases_sort_by_version_not_time(self, mock_fetcher):
        # 3.6.1 published later in the day than 4.4, but 4.4 is the newer version
        same_day = [
            {"tag": "4.4-stable", "release_date": 1741000000},  # 11:06 UTC
            {"tag": "3.6.1-stable", "release_date": 1741040000},  # 22:13 UTC
        ]
        setup_mock_response(mock_fetcher, [same_day])

        releases = mock_fetcher.fetch_releases(sort_by="date")

        assert [r.tag for r in releases] == ["4.4-stable", "3.6.1-stable"]
        assert releases[0].published_at == releases[1].published_at

    def test_fetch_releases_with_all_returns_all_releases(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        releases = mock_fetcher.fetch_releases(stable_only=False)
        assert [r.tag for r in releases] == ["4.1.1-stable", "4.0-rc1"]
        mock_fetcher.client.get.assert_called_with(GodotFetcher.ARCHIVE_URL)

    def test_fetch_releases_uses_disk_cache_across_instances(self, mocker, tmp_path):
        first = GodotFetcher(cache_dir=tmp_path)
        first.client = mocker.MagicMock()
        setup_mock_response(first, [MOCK_RELEASES])
        first.fetch_releases(stable_only=False)

        second = GodotFetcher(cache_dir=tmp_path)
        second.client = mocker.MagicMock()
        releases = second.fetch_releases(stable_only=False)
        second.client.get.assert_not_called()
        assert [r.tag for r in releases] == ["4.1.1-stable", "4.0-rc1"]
        assert releases[0].assets[1].csharp_enabled is True

    def test_fetch_releases_ignores_expired_disk_cache(self, mocker, tmp_path):
        first = GodotFetcher(cache_dir=tmp_path)
        first.client = mocker.MagicMock()
        setup_mock_response(first, [MOCK_RELEASES])
        first.fetch_releases(stable_only=False)

        second = GodotFetcher(cache_dir=tmp_path, cache_ttl=-1)
        second.client = mocker.MagicMock()
        setup_mock_response(second, [MOCK_RELEASES])
        second.fetch_releases(stable_only=False)
        assert second.client.get.call_count == 1

    def test_fetch_releases_refresh_cache_bypasses_disk_cache(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES, MOCK_RELEASES])
        mock_fetcher.fetch_releases(stable_only=False)
        mock_fetcher.fetch_releases(stable_only=False, refresh_cache=True)
        assert mock_fetcher.client.get.call_count == 2

    def test_assets_get_checksum_and_download_url(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        release = mock_fetcher.fetch_releases(stable_only=True)[0]
        asset = release.get_asset("windows", "x86_64")
        assert asset.sha512 == SHA
        assert asset.url == (
            "https://github.com/godotengine/godot-builds/releases/download/"
            "4.1.1-stable/Godot_v4.1.1-stable_win64.exe.zip"
        )

    def test_override_adds_unlisted_asset_without_checksum(self, mock_fetcher, mocker):
        name = "Godot_v4.0-rc1_win64.exe.zip"
        mocker.patch.dict(OVERRIDES, {"4.0-rc1": {name: None}}, clear=True)
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])

        release = mock_fetcher.fetch_releases(stable_only=False)[1]

        assert release.get_asset("windows", "x86_64").sha512 is None
        assert release.get_asset("macos", "arm64").sha512 == SHA

    def test_null_override_keeps_listed_hash_but_baked_one_replaces_it(
        self, mock_fetcher, mocker
    ):
        mac, win = "Godot_v4.0-rc1_macos.universal.zip", "Godot_v4.0-rc1_win64.exe.zip"
        baked = "b" * 128
        mocker.patch.dict(OVERRIDES, {"4.0-rc1": {mac: None, win: baked}}, clear=True)
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])

        release = mock_fetcher.fetch_releases(stable_only=False)[1]

        assert release.get_asset("macos", "arm64").sha512 == SHA
        assert release.get_asset("windows", "x86_64").sha512 == baked

    def test_release_without_files_list_gets_its_overrides(self, mock_fetcher, mocker):
        name = "Godot_v3.0-stable_win64.exe.zip"
        mocker.patch.dict(OVERRIDES, {"3.0-stable": {name: None}}, clear=True)
        old = {"tag": "3.0-stable", "release_date": 1518992040}
        setup_mock_response(mock_fetcher, [[old]])

        (release,) = mock_fetcher.fetch_releases()

        assert [a.name for a in release.assets] == [name]

    def test_release_without_date_is_skipped(self, mock_fetcher, caplog):
        undated = {"tag": "4.2-stable", "files": []}
        setup_mock_response(mock_fetcher, [[*MOCK_RELEASES, undated]])

        releases = mock_fetcher.fetch_releases(stable_only=False)

        assert [r.tag for r in releases] == ["4.1.1-stable", "4.0-rc1"]
        assert "4.2-stable" in caplog.text

    def test_unreadable_and_unrelated_files_are_skipped(self, mock_fetcher):
        response = MagicMock()
        response.content = make_archive(
            MOCK_RELEASES,
            {
                "releases/godot-4.2-stable.json": b"{not json",
                "releases/README.md": b"hi",
                "tools/godot-4.3-stable.json": b"{}",
            },
        )
        mock_fetcher.client.get.side_effect = [response]

        releases = mock_fetcher.fetch_releases(stable_only=False)

        assert [r.tag for r in releases] == ["4.1.1-stable", "4.0-rc1"]

    def test_context_manager_closes_client(self, tmp_path):
        with GodotFetcher(cache_dir=tmp_path) as fetcher:
            assert not fetcher.client.is_closed
        assert fetcher.client.is_closed

    def test_close_closes_client(self, tmp_path):
        fetcher = GodotFetcher(cache_dir=tmp_path)
        fetcher.close()
        assert fetcher.client.is_closed

    def test_fetched_at_is_download_time_then_cache_file_time(self, mocker, tmp_path):
        first = GodotFetcher(cache_dir=tmp_path)
        assert first.fetched_at is None
        first.client = mocker.MagicMock()
        setup_mock_response(first, [MOCK_RELEASES])
        before = datetime.now(UTC)
        first.fetch_releases()
        assert before <= first.fetched_at <= datetime.now(UTC)

        second = GodotFetcher(cache_dir=tmp_path)
        second.fetch_releases()
        mtime = (tmp_path / "godot_builds.json").stat().st_mtime
        assert second.fetched_at == datetime.fromtimestamp(mtime, UTC)

    def test_filter_by_target_counts_dotnet_only_builds(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        releases = mock_fetcher.fetch_releases(
            stable_only=False, platform="linux", arch="x86_64"
        )
        assert [r.tag for r in releases] == ["4.1.1-stable"]

    def test_filter_defaults_missing_half_to_this_machine(self, mock_fetcher, mocker):
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_platform", return_value="macos"
        )
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        releases = mock_fetcher.fetch_releases(stable_only=False, arch="arm64")
        assert [r.tag for r in releases] == ["4.0-rc1"]

    def test_filter_with_unknown_name_raises(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        with pytest.raises(ValueError, match="Unknown platform"):
            mock_fetcher.fetch_releases(platform="win", arch="x86_64")

    def test_fetch_releases_with_cache_skips_http_calls(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        mock_fetcher.fetch_releases(stable_only=True)
        mock_fetcher.client.get.reset_mock()
        releases = mock_fetcher.fetch_releases(stable_only=True)
        mock_fetcher.client.get.assert_not_called()
        assert len(releases) == 1
        assert len(mock_fetcher.cache) == 2

    def test_fetch_releases_with_max_releases_limits_after_sorting(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES[::-1]])
        releases = mock_fetcher.fetch_releases(stable_only=False, max_releases=1)
        assert [r.tag for r in releases] == ["4.1.1-stable"]

    def test_fetch_releases_cache_ignores_previous_filters(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        assert len(mock_fetcher.fetch_releases(stable_only=False, max_releases=1)) == 1
        releases = mock_fetcher.fetch_releases(
            stable_only=False, platform="macos", arch="x86_64"
        )
        assert len(releases) == 1

        mock_fetcher.client.get.reset_mock()
        releases = mock_fetcher.fetch_releases(stable_only=False)
        mock_fetcher.client.get.assert_not_called()
        assert [r.tag for r in releases] == ["4.1.1-stable", "4.0-rc1"]

    def test_fetch_releases_returned_list_does_not_alias_cache(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        mock_fetcher.fetch_releases(stable_only=False).clear()
        assert len(mock_fetcher.fetch_releases(stable_only=False)) == 2


class TestGodotFetcherFindAsset:
    @pytest.mark.parametrize("spelling", ["4.1.1", "4.1.1-stable", "v4.1.1-stable"])
    def test_finds_by_any_spelling_of_the_version(
        self, mock_fetcher, godot_release_4_1_1, spelling
    ):
        mock_fetcher.cache = [godot_release_4_1_1]
        asset = mock_fetcher.find_asset(
            GodotVersion.parse(spelling), "windows", "x86_64"
        )
        assert asset.url == "http://win64"

    def test_csharp_flag_picks_the_dotnet_build(
        self, mock_fetcher, godot_release_4_1_1
    ):
        mock_fetcher.cache = [godot_release_4_1_1]
        version = GodotVersion(4, 1, 1, csharp_enabled=True)
        assert mock_fetcher.find_asset(version, "linux", "x86_64").url == (
            "http://linux_mono"
        )

    def test_fetches_when_nothing_is_cached(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_RELEASES])
        asset = mock_fetcher.find_asset(
            GodotVersion(4, 0, channel="rc", channel_num=1), "macos", "arm64"
        )
        assert asset.name == "Godot_v4.0-rc1_macos.universal.zip"

    def test_missing_version_raises_release_not_found(
        self, mock_fetcher, godot_release_4_1_1
    ):
        mock_fetcher.cache = [godot_release_4_1_1]
        with pytest.raises(ReleaseNotFoundError, match="9.9.9"):
            mock_fetcher.find_asset(GodotVersion(9, 9, 9))

    def test_missing_build_raises_asset_not_found(
        self, mock_fetcher, godot_release_4_1_1
    ):
        mock_fetcher.cache = [godot_release_4_1_1]
        with pytest.raises(AssetNotFoundError, match="linux/arm64"):
            mock_fetcher.find_asset(GodotVersion(4, 1, 1), "linux", "arm64")

    def test_lookup_errors_are_godotkit_errors(self):
        assert issubclass(ReleaseNotFoundError, GodotkitError)
        assert issubclass(AssetNotFoundError, GodotkitError)


def test_overrides_are_well_formed():
    bad = [
        (tag, name, sha)
        for tag, builds in OVERRIDES.items()
        for name, sha in builds.items()
        if not name.startswith(f"Godot_v{tag}_")
        or not (sha is None or re.fullmatch(r"[0-9a-fA-F]{128}", sha))
    ]
    assert bad == []
