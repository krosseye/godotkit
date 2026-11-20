import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from godotkit.engine.release_fetcher import (
    ASSET_SUFFIXES,
    RELEASE_DATES,
    GodotAsset,
    GodotFetcher,
    GodotRelease,
    detect_architecture,
    detect_platform,
)

MOCK_GH_RELEASE_DATA = [
    {
        "tag_name": "4.1.1-stable",
        "published_at": "2023-09-15T12:00:00Z",
        "assets": [
            {
                "name": "Godot_v4.1.1-stable_win64.exe.zip",
                "browser_download_url": "http://example.com/win64.exe",
                "size": 100000000,
            },
            {
                "name": "Godot_v4.1.1-stable_mono_linux_x86_64.zip",
                "browser_download_url": "http://example.com/linux_mono.zip",
                "size": 200000000,
            },
        ],
    },
    {
        "tag_name": "4.0-rc1",
        "published_at": "2023-01-01T10:00:00Z",
        "assets": [
            {
                "name": "Godot_v4.0-rc1_macos.universal.zip",
                "browser_download_url": "http://example.com/macos_rc.zip",
                "size": 50000000,
            },
        ],
    },
]


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
            size=100,
            csharp_enabled=False,
        ),
        GodotAsset(
            name="Godot_v4.1.1-stable_mono_linux_x86_64.zip",
            url="http://linux_mono",
            size=200,
            csharp_enabled=True,
        ),
        GodotAsset(
            name="Godot_v4.1.1-stable_linux.x86_64.zip",
            url="http://linux_std",
            size=150,
            csharp_enabled=False,
        ),
    ]
    return GodotRelease(
        version="4.1.1-stable",
        published_at=datetime(2023, 9, 15),
        assets=assets,
    )


def setup_mock_response(mock_fetcher, pages):
    responses = []
    for json_data in pages:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json_data
        mock_response.raise_for_status.return_value = None
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

    def test_detect_architecture_unsupported_raises_runtime_error(self):
        with (
            patch("platform.machine", return_value="ppc"),
            pytest.raises(RuntimeError, match="Unsupported CPU architecture"),
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
            datetime(2026, 11, 16),
            [GodotAsset(n, f"https://example.com/{n}", 1, "_mono" in n) for n in names],
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

    def test_get_asset_with_no_arch_returns_none(self, godot_release_4_1_1):
        asset = godot_release_4_1_1.get_asset("linux", arch=None, csharp=False)
        assert asset is None

    def test_get_asset_with_unsupported_combo_returns_none(self, godot_release_4_1_1):
        assert godot_release_4_1_1.get_asset("windows", "arm32") is None


class TestGodotFetcherVersionParsing:
    def test_version_sort_key_with_stable_tag_returns_correct_key(self):
        key = GodotFetcher.version_sort_key("4.1.2-stable")
        assert key.major == 4
        assert key.channel == "stable"

    def test_version_sort_key_with_malformed_tag_returns_default_key(self):
        key = GodotFetcher.version_sort_key("junk-tag")
        assert key.major == 0
        assert key.channel == "dev"


class TestGodotFetcherReleaseFetching:
    def test_fetch_releases_with_stable_only_returns_stable_releases(
        self, mock_fetcher
    ):
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])
        releases = mock_fetcher.fetch_releases(stable_only=True)
        assert [r.version for r in releases] == ["4.1.1-stable"]
        mock_fetcher.client.get.assert_called_with(
            f"{GodotFetcher.ALL_URL}?page=1&per_page=100"
        )

    def test_switching_stable_only_does_not_refetch(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])
        mock_fetcher.fetch_releases(stable_only=True)
        mock_fetcher.client.get.reset_mock()

        releases = mock_fetcher.fetch_releases(stable_only=False)

        mock_fetcher.client.get.assert_not_called()
        assert [r.version for r in releases] == ["4.1.1-stable", "4.0-rc1"]

    def test_baked_date_replaces_import_date(self, mock_fetcher, mocker):
        mocker.patch.dict(RELEASE_DATES, {"4.0-rc1": "2020-05-05"}, clear=True)
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])

        dates = {
            r.version: r.published_at
            for r in mock_fetcher.fetch_releases(stable_only=False)
        }

        assert dates == {
            "4.1.1-stable": datetime(2023, 9, 15, 12),
            "4.0-rc1": datetime(2020, 5, 5),
        }

    def test_date_sort_breaks_ties_by_version(self, mock_fetcher, mocker):
        mocker.patch.dict(
            RELEASE_DATES, {"4.1.1-stable": "2023-01-01", "4.0-rc1": "2023-01-01"}
        )
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA[::-1], []])

        releases = mock_fetcher.fetch_releases(stable_only=False, sort_by="date")

        assert [r.version for r in releases] == ["4.1.1-stable", "4.0-rc1"]

    def test_fetch_releases_with_all_returns_all_releases(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])
        releases = mock_fetcher.fetch_releases(stable_only=False)
        assert [r.version for r in releases] == ["4.1.1-stable", "4.0-rc1"]
        mock_fetcher.client.get.assert_called_with(
            f"{GodotFetcher.ALL_URL}?page=1&per_page=100"
        )

    def test_fetch_releases_uses_disk_cache_across_instances(self, mocker, tmp_path):
        first = GodotFetcher(cache_dir=tmp_path)
        first.client = mocker.MagicMock()
        setup_mock_response(first, [MOCK_GH_RELEASE_DATA, []])
        first.fetch_releases(stable_only=False)

        second = GodotFetcher(cache_dir=tmp_path)
        second.client = mocker.MagicMock()
        releases = second.fetch_releases(stable_only=False)
        second.client.get.assert_not_called()
        assert [r.version for r in releases] == ["4.1.1-stable", "4.0-rc1"]
        assert releases[0].assets[1].csharp_enabled is True

    def test_fetch_releases_ignores_expired_disk_cache(self, mocker, tmp_path):
        first = GodotFetcher(cache_dir=tmp_path)
        first.client = mocker.MagicMock()
        setup_mock_response(first, [MOCK_GH_RELEASE_DATA, []])
        first.fetch_releases(stable_only=False)

        mocker.patch("godotkit.engine.release_fetcher.RELEASE_CACHE_TTL", -1)
        second = GodotFetcher(cache_dir=tmp_path)
        second.client = mocker.MagicMock()
        setup_mock_response(second, [MOCK_GH_RELEASE_DATA, []])
        second.fetch_releases(stable_only=False)
        assert second.client.get.call_count == 1

    def test_fetch_releases_refresh_cache_bypasses_disk_cache(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, MOCK_GH_RELEASE_DATA])
        mock_fetcher.fetch_releases(stable_only=False)
        mock_fetcher.fetch_releases(stable_only=False, refresh_cache=True)
        assert mock_fetcher.client.get.call_count == 2

    def test_token_from_env_is_sent(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "my_token")
        fetcher = GodotFetcher(cache_dir=tmp_path)
        assert fetcher.client.headers["Authorization"] == "Bearer my_token"

    def test_no_token_sends_no_auth_header(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        fetcher = GodotFetcher(cache_dir=tmp_path)
        assert "Authorization" not in fetcher.client.headers

    def test_context_manager_closes_client(self, tmp_path):
        with GodotFetcher(cache_dir=tmp_path) as fetcher:
            assert not fetcher.client.is_closed
        assert fetcher.client.is_closed

    def test_close_closes_client(self, tmp_path):
        fetcher = GodotFetcher(cache_dir=tmp_path)
        fetcher.close()
        assert fetcher.client.is_closed

    def test_fetch_releases_with_platform_only_filters_by_platform(
        self, mock_fetcher, mocker
    ):
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_platform", return_value="macos"
        )
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_architecture", return_value="x86_64"
        )
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])
        releases = mock_fetcher.fetch_releases(stable_only=False, platform_only=True)
        assert len(releases) == 1
        assert releases[0].version == "4.0-rc1"

    def test_fetch_releases_with_cache_skips_http_calls(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])
        mock_fetcher.fetch_releases(stable_only=True)
        mock_fetcher.client.get.reset_mock()
        releases = mock_fetcher.fetch_releases(stable_only=True)
        mock_fetcher.client.get.assert_not_called()
        assert len(releases) == 1
        assert len(mock_fetcher.cache) == 2

    def test_fetch_releases_with_max_releases_limits_after_sorting(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA[::-1], []])
        releases = mock_fetcher.fetch_releases(stable_only=False, max_releases=1)
        assert [r.version for r in releases] == ["4.1.1-stable"]

    def test_fetch_releases_cache_ignores_previous_filters(self, mock_fetcher, mocker):
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_platform", return_value="macos"
        )
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_architecture", return_value="x86_64"
        )
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])
        assert len(mock_fetcher.fetch_releases(stable_only=False, max_releases=1)) == 1
        assert (
            len(mock_fetcher.fetch_releases(stable_only=False, platform_only=True)) == 1
        )

        mock_fetcher.client.get.reset_mock()
        releases = mock_fetcher.fetch_releases(stable_only=False)
        mock_fetcher.client.get.assert_not_called()
        assert [r.version for r in releases] == ["4.1.1-stable", "4.0-rc1"]

    def test_fetch_releases_returned_list_does_not_alias_cache(self, mock_fetcher):
        setup_mock_response(mock_fetcher, [MOCK_GH_RELEASE_DATA, []])
        mock_fetcher.fetch_releases(stable_only=False).clear()
        assert len(mock_fetcher.fetch_releases(stable_only=False)) == 2


class TestGodotFetcherDownloadURL:
    def test_get_download_url_with_matching_asset_returns_url(
        self, mock_fetcher, godot_release_4_1_1, mocker
    ):
        mock_fetcher.cache = [godot_release_4_1_1]
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_platform", return_value="windows"
        )
        mocker.patch(
            "godotkit.engine.release_fetcher.detect_architecture", return_value="x86_64"
        )
        url = mock_fetcher.get_download_url("4.1.1-stable", mono=False)
        assert url == "http://win64"

    def test_get_download_url_with_missing_version_raises_value_error(
        self, mock_fetcher
    ):
        mock_fetcher.cache = []
        with pytest.raises(ValueError, match="Version 9.9.9-stable not found"):
            mock_fetcher.get_download_url("9.9.9-stable")

    def test_get_download_url_with_no_matching_asset_raises_value_error(
        self, mock_fetcher, godot_release_4_1_1
    ):
        mock_fetcher.cache = [godot_release_4_1_1]
        with pytest.raises(
            ValueError, match="No download found for linux arm64 mono=False"
        ):
            mock_fetcher.get_download_url("4.1.1-stable", "linux", "arm64", mono=False)


def test_release_dates_ship_with_the_package():
    assert len(RELEASE_DATES) == 224
    assert RELEASE_DATES["3.0-stable"] == "2018-01-29"
    assert RELEASE_DATES["3.2.4-beta1"] == "2020-10-21"
