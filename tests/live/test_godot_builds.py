"""When this fails, upstream has changed something."""

import json
import re
from pathlib import Path

import pytest

from godotkit.engine import GodotFetcher, GodotVersion
from godotkit.engine.release_fetcher import ASSET_SUFFIXES, GodotRelease

pytestmark = pytest.mark.live

FIXTURE = Path(__file__).parents[1] / "engine" / "data" / "release_assets.json"

KNOWN_MALFORMED_TAGS = {"2.0.4.1-stable", "3.2-alpha0-unofficial"}

KNOWN_SUFFIXES = {s for suffixes in ASSET_SUFFIXES.values() for s in suffixes}

DESKTOP = re.compile(r"win|linux|x11|mac|osx")
NOT_EDITOR = re.compile(r"debug_?symbols|\.dSYM\.|headless|server")
NOT_EDITOR_ONE_OFFS = {
    "Godot_v3.3.1-stable_win32.exe-fix48822.zip",
    "Godot_v3.3.1-stable_win64.exe-fix48822.zip",
}

FIRST_SUPPORTED_MAJOR = 3


def _parse(tag: str) -> GodotVersion | None:
    try:
        return GodotVersion.from_tag(tag)
    except ValueError:
        return None  # reported by test_every_tag_parses


def _suffixes(release: GodotRelease) -> set[str]:
    prefix = f"Godot_v{release.version}_"
    return {
        a.name.removeprefix(prefix) for a in release.assets if a.name.startswith(prefix)
    }


def _names(release: GodotRelease) -> set[str]:
    dotted = release.version.replace("-", ".")
    return {
        a.name.replace(release.version, "{v}").replace(dotted, "{v}")
        for a in release.assets
    }


@pytest.fixture(scope="session")
def fetcher(tmp_path_factory):
    with GodotFetcher(cache_dir=tmp_path_factory.mktemp("releases")) as fetcher:
        yield fetcher


@pytest.fixture(scope="session")
def all_releases(fetcher: GodotFetcher) -> list[GodotRelease]:
    return fetcher.fetch_releases(stable_only=False)


@pytest.fixture(scope="session")
def stable_releases(fetcher: GodotFetcher) -> list[GodotRelease]:
    return fetcher.fetch_releases(stable_only=True)


@pytest.fixture(scope="session")
def supported(all_releases) -> dict[int, list[GodotRelease]]:
    """Releases of each supported major version, oldest first."""
    by_major: dict[int, list[tuple[GodotVersion, GodotRelease]]] = {}
    for release in all_releases:
        version = _parse(release.version)
        if version and version.major >= FIRST_SUPPORTED_MAJOR:
            by_major.setdefault(version.major, []).append((version, release))
    return {
        m: [r for _, r in sorted(rs, key=lambda x: x[0])] for m, rs in by_major.items()
    }


def test_every_tag_parses(all_releases, stable_releases):
    tags = {r.version for r in all_releases + stable_releases}
    unparseable = {tag for tag in tags if _parse(tag) is None}

    assert sorted(unparseable - KNOWN_MALFORMED_TAGS) == []


def test_frozen_fixture_still_exists_upstream(all_releases):
    live = {r.version: {a.name for a in r.assets} for r in all_releases}
    frozen = json.loads(FIXTURE.read_text("utf-8"))

    missing = sorted(
        (tag, name)
        for tag, names in frozen.items()
        for name in names
        if name.removeprefix(f"Godot_v{tag}_") in KNOWN_SUFFIXES
        and name not in live.get(tag, set())
    )
    assert missing == []


def test_newest_stable_builds_not_renamed(supported):
    renamed = []
    for releases in supported.values():
        stables = [r for r in releases if _parse(r.version).is_stable]
        if len(stables) < 2:
            continue
        baseline, newest = stables[-2], stables[-1]
        missing = [
            combo
            for combo in ASSET_SUFFIXES
            if baseline.get_asset(*combo) and not newest.get_asset(*combo)
        ]
        known = {"Godot_v{v}_" + s for s in KNOWN_SUFFIXES}
        new_names = {
            n
            for n in _names(newest) - _names(baseline) - known
            if n.endswith(".zip") and not NOT_EDITOR.search(n)
        }
        if missing and new_names:
            renamed.append((newest.version, missing, sorted(new_names)))

    assert renamed == []


def test_no_unknown_build_appears(supported):
    unknown = []
    for releases in supported.values():
        for release in releases:
            suffixes = _suffixes(release)
            if not suffixes:
                unknown.append(release.version)
            prefix = f"Godot_v{release.version}_"
            unknown += sorted(
                prefix + s
                for s in suffixes - KNOWN_SUFFIXES
                if prefix + s not in NOT_EDITOR_ONE_OFFS
                and DESKTOP.search(s)
                and not NOT_EDITOR.search(s)
            )

    assert unknown == []
