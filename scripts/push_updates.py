#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Commit each package changed by update.py and push to the default branch."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = re.compile(r"^[a-z0-9@._+-]+$")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        result.check_returncode()
    return result


def pkgver(pkgbuild: str) -> str:
    match = re.search(r"^pkgver=(.*)$", pkgbuild, re.MULTILINE)
    if match is None:
        raise ValueError("PKGBUILD has no pkgver assignment")
    return match.group(1).strip()


def changed_package_names() -> list[str]:
    untracked = run(
        "git", "ls-files", "--others", "--exclude-standard", "--", "packages"
    ).stdout.splitlines()
    if untracked:
        raise ValueError(f"unexpected untracked package files: {' '.join(untracked)}")

    output = run(
        "git",
        "diff",
        "--name-only",
        "--diff-filter=ACMRTUXB",
        "--",
        "packages",
    ).stdout
    names = set()
    for changed_path in output.splitlines():
        path = PurePosixPath(changed_path)
        if len(path.parts) < 3 or path.parts[0] != "packages":
            raise ValueError(f"unexpected update path: {changed_path}")
        name = path.parts[1]
        if not PACKAGE_NAME.fullmatch(name):
            raise ValueError(f"unsafe package name: {name!r}")
        names.add(name)
    return sorted(names)


def commit_package(name: str) -> None:
    package_path = f"packages/{name}"
    version = pkgver((ROOT / package_path / "PKGBUILD").read_text())
    run("git", "add", "--", package_path)
    run("git", "commit", "-m", f"Update {name} to {version}")
    print(f"Committed {name} {version}")


def main() -> None:
    default_branch = os.environ["DEFAULT_BRANCH"]
    if os.environ["GITHUB_REF_NAME"] != default_branch:
        raise SystemExit("Package updates must run from the default branch")

    run("git", "config", "--global", "--add", "safe.directory", str(ROOT))
    run("git", "config", "user.name", "github-actions[bot]")
    run(
        "git",
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )

    names = changed_package_names()
    if not names:
        print("No package metadata changes.")
        return

    for name in names:
        commit_package(name)

    run("gh", "auth", "setup-git")
    run("git", "push", "origin", f"HEAD:refs/heads/{default_branch}")
    # Pushes made with GITHUB_TOKEN never trigger other workflows, so start
    # the publish run explicitly.
    run(
        "gh",
        "workflow",
        "run",
        "publish.yml",
        "--repo",
        os.environ["GITHUB_REPOSITORY"],
        "--ref",
        default_branch,
    )


if __name__ == "__main__":
    main()
