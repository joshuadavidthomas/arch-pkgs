from __future__ import annotations

import importlib.util
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_update", ROOT / "update.py")
assert SPEC and SPEC.loader
UPDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATE)


def test_all_sources_have_checksums() -> None:
    skipped = [
        pkgbuild.relative_to(ROOT).as_posix()
        for pkgbuild in ROOT.glob("packages/*/PKGBUILD")
        if "'SKIP'" in pkgbuild.read_text()
    ]

    assert skipped == []


def test_package_lists_are_alphabetized() -> None:
    sections = list(tomllib.loads((ROOT / "nvchecker.toml").read_text()))
    ignore_patterns = (ROOT / ".gitignore").read_text().splitlines()

    assert sections == sorted(sections)
    assert ignore_patterns == sorted(ignore_patterns)


def test_updates_version_and_resets_release() -> None:
    text = "pkgname=example\npkgver=1.0.0\npkgrel=4\n"

    result = UPDATE.render_updated_pkgbuild(text, "2.0.0_1+build")

    assert result == "pkgname=example\npkgver=2.0.0_1+build\npkgrel=1\n"


@pytest.mark.parametrize(
    "version",
    (
        "1.0$(touch /tmp/pwned)",
        "1.0`touch /tmp/pwned`",
        "1.0;false",
        "1.0-1",
        "~/1.0",
        "1.0 2",
    ),
)
def test_rejects_shell_syntax(version: str) -> None:
    with pytest.raises(ValueError, match="unsafe pkgver"):
        UPDATE.render_updated_pkgbuild("pkgver=1.0.0\npkgrel=1\n", version)


def test_requires_one_version_and_release_assignment() -> None:
    with pytest.raises(ValueError, match="one pkgver and one pkgrel"):
        UPDATE.render_updated_pkgbuild("pkgver=1.0\n", "2.0")

    duplicate = "pkgver=1.0\npkgver=1.1\npkgrel=1\n"
    with pytest.raises(ValueError, match="one pkgver and one pkgrel"):
        UPDATE.render_updated_pkgbuild(duplicate, "2.0")


def test_restores_metadata_when_checksum_refresh_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkgbuild = tmp_path / "PKGBUILD"
    srcinfo = tmp_path / ".SRCINFO"
    original_pkgbuild = "pkgver=1.0\npkgrel=3\n"
    original_srcinfo = "pkgver = 1.0\npkgrel = 3\n"
    pkgbuild.write_text(original_pkgbuild)
    srcinfo.write_text(original_srcinfo)
    monkeypatch.setenv("GITHUB_TOKEN", "secret")

    captured_env = None

    def fail(*args: object, **kwargs: object) -> None:
        nonlocal captured_env
        captured_env = kwargs["env"]
        raise subprocess.CalledProcessError(1, ["updpkgsums"])

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(subprocess.CalledProcessError):
        UPDATE.update_package(tmp_path, "2.0")

    assert captured_env is not None
    assert "GITHUB_TOKEN" not in captured_env
    assert pkgbuild.read_text() == original_pkgbuild
    assert srcinfo.read_text() == original_srcinfo
