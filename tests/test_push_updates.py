from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from scripts import push_updates


@pytest.fixture(autouse=True)
def isolate_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def make_repo(tmp_path: Path) -> None:
    git(tmp_path, "init", "--initial-branch", "main")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.com")
    for name in ("alpha", "beta"):
        package = tmp_path / "packages" / name
        package.mkdir(parents=True)
        (package / "PKGBUILD").write_text(f"pkgname={name}\npkgver=1.0\npkgrel=1\n")
        (package / ".SRCINFO").write_text(f"pkgname = {name}\npkgver = 1.0\n")
    git(tmp_path, "add", "packages")
    git(tmp_path, "commit", "-m", "Initial packages")


def bump(tmp_path: Path, name: str, version: str) -> None:
    package = tmp_path / "packages" / name
    (package / "PKGBUILD").write_text(f"pkgname={name}\npkgver={version}\npkgrel=1\n")
    (package / ".SRCINFO").write_text(f"pkgname = {name}\npkgver = {version}\n")


def test_changed_package_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_repo(tmp_path)
    bump(tmp_path, "alpha", "2.0")
    bump(tmp_path, "beta", "2.0")
    monkeypatch.setattr(push_updates, "ROOT", tmp_path)

    assert push_updates.changed_package_names() == ["alpha", "beta"]

    (tmp_path / "packages" / "alpha" / "new-file").write_text("untracked")
    with pytest.raises(ValueError, match="unexpected untracked package files"):
        push_updates.changed_package_names()


def test_commits_one_package_at_a_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_repo(tmp_path)
    bump(tmp_path, "alpha", "2.0")
    bump(tmp_path, "beta", "3.0")
    monkeypatch.setattr(push_updates, "ROOT", tmp_path)

    for name in push_updates.changed_package_names():
        push_updates.commit_package(name)

    subjects = git(tmp_path, "log", "--format=%s", "-2").splitlines()
    assert subjects == ["Update beta to 3.0", "Update alpha to 2.0"]
    assert git(tmp_path, "status", "--porcelain") == ""
