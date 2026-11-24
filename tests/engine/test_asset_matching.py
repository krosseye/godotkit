import json
from datetime import date
from pathlib import Path

import pytest

from godotkit.engine.release_fetcher import GodotAsset, GodotRelease

# frozen copy of asset names published in godotengine/godot-builds
ASSETS = json.loads(
    (Path(__file__).parent / "data" / "release_assets.json").read_text("utf-8")
)

COMBOS = [
    ("windows", "x86"),
    ("windows", "x86_64"),
    ("windows", "arm64"),
    ("linux", "x86"),
    ("linux", "x86_64"),
    ("linux", "arm32"),
    ("linux", "arm64"),
    ("macos", "x86"),
    ("macos", "x86_64"),
    ("macos", "arm64"),
]

EXPECTED: dict[str, dict[tuple[str, str], tuple[str | None, str | None]]] = {
    # One fat macOS build covers both Intel architectures.
    "3.0-stable": {
        ("windows", "x86"): ("win32.exe.zip", "mono_win32.zip"),
        ("windows", "x86_64"): ("win64.exe.zip", "mono_win64.zip"),
        ("linux", "x86"): ("x11.32.zip", None),
        ("linux", "x86_64"): ("x11.64.zip", "mono_x11_64.zip"),
        ("macos", "x86"): ("osx.fat.zip", None),
        ("macos", "x86_64"): ("osx.fat.zip", "mono_osx64.zip"),
    },
    # One-off "mono_osx_64"; server/headless builds must be skipped.
    "3.2-beta2": {
        ("windows", "x86"): ("win32.exe.zip", "mono_win32.zip"),
        ("windows", "x86_64"): ("win64.exe.zip", "mono_win64.zip"),
        ("linux", "x86"): ("x11.32.zip", "mono_x11_32.zip"),
        ("linux", "x86_64"): ("x11.64.zip", "mono_x11_64.zip"),
        ("macos", "x86_64"): ("osx.64.zip", "mono_osx_64.zip"),
    },
    # Ships both osx.64 and osx.universal; universal is preferred.
    "3.2.4-beta2": {
        ("windows", "x86"): ("win32.exe.zip", "mono_win32.zip"),
        ("windows", "x86_64"): ("win64.exe.zip", "mono_win64.zip"),
        ("linux", "x86"): ("x11.32.zip", "mono_x11_32.zip"),
        ("linux", "x86_64"): ("x11.64.zip", "mono_x11_64.zip"),
        ("macos", "x86_64"): ("osx.universal.zip", "mono_osx.64.zip"),
        ("macos", "arm64"): ("osx.universal.zip", None),
    },
    "3.3.1-stable": {
        ("windows", "x86"): ("win32.exe.zip", "mono_win32.zip"),
        ("windows", "x86_64"): ("win64.exe.zip", "mono_win64.zip"),
        ("linux", "x86"): ("x11.32.zip", "mono_x11_32.zip"),
        ("linux", "x86_64"): ("x11.64.zip", "mono_x11_64.zip"),
        ("macos", "x86_64"): ("osx.universal.zip", "mono_osx.64.zip"),
        ("macos", "arm64"): ("osx.universal.zip", None),
    },
    "3.6-stable": {
        ("windows", "x86"): ("win32.exe.zip", "mono_win32.zip"),
        ("windows", "x86_64"): ("win64.exe.zip", "mono_win64.zip"),
        ("linux", "x86"): ("x11.32.zip", "mono_x11_32.zip"),
        ("linux", "x86_64"): ("x11.64.zip", "mono_x11_64.zip"),
        ("linux", "arm32"): ("linux.arm32.zip", None),
        ("linux", "arm64"): ("linux.arm64.zip", None),
        ("macos", "x86_64"): ("osx.universal.zip", "mono_osx.universal.zip"),
        ("macos", "arm64"): ("osx.universal.zip", "mono_osx.universal.zip"),
    },
    # Early 4.0 alphas use "linux.32" and "linux.64".
    "4.0-alpha1": {
        ("windows", "x86"): ("win32.exe.zip", None),
        ("windows", "x86_64"): ("win64.exe.zip", None),
        ("linux", "x86"): ("linux.32.zip", None),
        ("linux", "x86_64"): ("linux.64.zip", None),
        ("macos", "x86_64"): ("osx.universal.zip", None),
        ("macos", "arm64"): ("osx.universal.zip", None),
    },
    "4.5.1-stable": {
        ("windows", "x86"): ("win32.exe.zip", "mono_win32.zip"),
        ("windows", "x86_64"): ("win64.exe.zip", "mono_win64.zip"),
        ("windows", "arm64"): ("windows_arm64.exe.zip", "mono_windows_arm64.zip"),
        ("linux", "x86"): ("linux.x86_32.zip", "mono_linux_x86_32.zip"),
        ("linux", "x86_64"): ("linux.x86_64.zip", "mono_linux_x86_64.zip"),
        ("linux", "arm32"): ("linux.arm32.zip", "mono_linux_arm32.zip"),
        ("linux", "arm64"): ("linux.arm64.zip", "mono_linux_arm64.zip"),
        ("macos", "x86_64"): ("macos.universal.zip", "mono_macos.universal.zip"),
        ("macos", "arm64"): ("macos.universal.zip", "mono_macos.universal.zip"),
    },
    # 4.8: per-arch macOS builds, and debug symbols named like every build.
    "4.8-beta3": {
        ("windows", "x86"): ("win32.exe.zip", "mono_win32.zip"),
        ("windows", "x86_64"): ("win64.exe.zip", "mono_win64.zip"),
        ("windows", "arm64"): ("windows_arm64.exe.zip", "mono_windows_arm64.zip"),
        ("linux", "x86"): ("linux.x86_32.zip", "mono_linux_x86_32.zip"),
        ("linux", "x86_64"): ("linux.x86_64.zip", "mono_linux_x86_64.zip"),
        ("linux", "arm32"): ("linux.arm32.zip", "mono_linux_arm32.zip"),
        ("linux", "arm64"): ("linux.arm64.zip", "mono_linux_arm64.zip"),
        ("macos", "x86_64"): ("macos.x86_64.zip", "mono_macos.x86_64.zip"),
        ("macos", "arm64"): ("macos.arm64.zip", "mono_macos.arm64.zip"),
    },
}


def release(tag: str) -> GodotRelease:
    return GodotRelease(
        tag,
        date(2026, 1, 1),
        [
            GodotAsset(n, f"https://example.com/{n}", csharp_enabled="_mono" in n)
            for n in ASSETS[tag]
        ],
    )


def test_fixture_and_expectations_cover_the_same_releases():
    assert EXPECTED.keys() == ASSETS.keys()


@pytest.mark.parametrize("tag", EXPECTED)
@pytest.mark.parametrize("csharp", [False, True], ids=["standard", "dotnet"])
@pytest.mark.parametrize("platform, arch", COMBOS, ids="/".join)
def test_resolves_exact_build(tag: str, platform: str, arch: str, csharp: bool):
    suffix = EXPECTED[tag].get((platform, arch), (None, None))[csharp]

    asset = release(tag).get_asset(platform, arch, csharp)

    if suffix is None:
        assert asset is None
    else:
        assert asset is not None
        assert asset.name == f"Godot_v{tag}_{suffix}"
