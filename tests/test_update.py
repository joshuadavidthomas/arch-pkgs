from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

import update

ROOT = Path(__file__).resolve().parents[1]


def test_all_sources_have_checksums() -> None:
    skipped = [
        pkgbuild.relative_to(ROOT).as_posix()
        for pkgbuild in ROOT.glob("packages/*/PKGBUILD")
        if "'SKIP'" in pkgbuild.read_text()
    ]

    assert skipped == []


def test_package_configs_are_local_and_scoped() -> None:
    directories = update.pkg_dirs()
    configs = sorted(ROOT.glob("packages/*/.nvchecker.toml"))

    assert [config.parent for config in configs] == directories
    for config in configs:
        base = update.pkgbase(config.parent)
        entries = tomllib.loads(config.read_text())
        assert base in entries
        assert all(name == base or name.startswith(f"{base}:") for name in entries)


def test_package_config_allows_combiner_stages() -> None:
    config = ROOT / "packages/example/.nvchecker.toml"
    text = '''
["example:github"]
source = "github"

[example]
source = "combiner"
from = ["example:github"]
format = "$1"
'''

    update.validate_nvchecker_config("example", text, config)


def test_run_nvchecker_uses_aggregate_and_keyfile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "packages/example"
    package.mkdir(parents=True)
    (package / ".SRCINFO").write_text("pkgbase = example\n")
    (package / ".nvchecker.toml").write_text(
        '''
["example:stage"]
source = "cmd"
cmd = "printf 2.0"

[example]
source = "combiner"
from = ["example:stage"]
format = "$1"
'''
    )
    monkeypatch.setattr(update, "pkg_dirs", lambda: [package])
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    temporary_paths: list[Path] = []

    def run_nvchecker(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        config = Path(command[command.index("-c") + 1])
        keyfile = Path(command[command.index("-k") + 1])
        temporary_paths.extend((config, keyfile))
        assert tomllib.loads(config.read_text()) == {
            "example:stage": {"source": "cmd", "cmd": "printf 2.0"},
            "example": {
                "source": "combiner",
                "from": ["example:stage"],
                "format": "$1",
            },
        }
        assert tomllib.loads(keyfile.read_text()) == {"keys": {"github": "secret"}}
        assert kwargs["cwd"] == ROOT
        assert "env" not in kwargs
        stdout = "\n".join(
            (
                '{"event":"updated","name":"example:stage","version":"2.0"}',
                '{"event":"updated","name":"example","version":"2.0"}',
            )
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", run_nvchecker)

    assert update.run_nvchecker() == {"example:stage": "2.0", "example": "2.0"}
    assert all(not path.exists() for path in temporary_paths)


def test_ignore_patterns_are_alphabetized() -> None:
    ignore_patterns = (ROOT / ".gitignore").read_text().splitlines()

    assert ignore_patterns == sorted(ignore_patterns)


def test_updates_version_and_resets_release() -> None:
    text = "pkgname=example\npkgver=1.0.0\npkgrel=4\n"

    result = update.render_updated_pkgbuild(text, "2.0.0_1+build")

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
        update.render_updated_pkgbuild("pkgver=1.0.0\npkgrel=1\n", version)


def test_requires_one_version_and_release_assignment() -> None:
    with pytest.raises(ValueError, match="one pkgver and one pkgrel"):
        update.render_updated_pkgbuild("pkgver=1.0\n", "2.0")

    duplicate = "pkgver=1.0\npkgver=1.1\npkgrel=1\n"
    with pytest.raises(ValueError, match="one pkgver and one pkgrel"):
        update.render_updated_pkgbuild(duplicate, "2.0")


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
        update.update_package(tmp_path, "2.0")

    assert captured_env is not None
    assert "GITHUB_TOKEN" not in captured_env
    assert pkgbuild.read_text() == original_pkgbuild
    assert srcinfo.read_text() == original_srcinfo
