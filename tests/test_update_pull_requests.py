from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import update_pull_requests as pull_requests


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_collects_one_change_per_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    base = git(tmp_path, "rev-parse", "HEAD").strip()

    for name in ("alpha", "beta"):
        package = tmp_path / "packages" / name
        (package / "PKGBUILD").write_text(f"pkgname={name}\npkgver=2.0\npkgrel=1\n")
        (package / ".SRCINFO").write_text(f"pkgname = {name}\npkgver = 2.0\n")

    monkeypatch.setattr(pull_requests, "ROOT", tmp_path)

    changes = pull_requests.collect_changes(base)

    assert [
        (change.name, change.previous_version, change.updated_version)
        for change in changes
    ] == [
        ("alpha", "1.0", "2.0"),
        ("beta", "1.0", "2.0"),
    ]
    assert "packages/alpha/PKGBUILD" in changes[0].patch
    assert "packages/beta/PKGBUILD" not in changes[0].patch
    assert "packages/beta/PKGBUILD" in changes[1].patch
    assert "packages/alpha/PKGBUILD" not in changes[1].patch

    (tmp_path / "packages" / "alpha" / "new-file").write_text("untracked")
    with pytest.raises(ValueError, match="unexpected untracked package files"):
        pull_requests.collect_changes(base)
