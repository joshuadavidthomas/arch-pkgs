#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Open one pull request for each package changed by update.py."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = re.compile(r"^[a-z0-9@._+-]+$")


@dataclass(frozen=True)
class PackageChange:
    name: str
    previous_version: str
    updated_version: str
    patch: str


def run(
    *args: str,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        capture_output=True,
        input=input_text,
        text=True,
    )


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


def collect_changes(base: str) -> list[PackageChange]:
    changes = []
    for name in changed_package_names():
        package_path = f"packages/{name}"
        previous_pkgbuild = run("git", "show", f"{base}:{package_path}/PKGBUILD").stdout
        updated_pkgbuild = (ROOT / package_path / "PKGBUILD").read_text()
        patch = run("git", "diff", "--binary", "--", package_path).stdout
        changes.append(
            PackageChange(
                name,
                pkgver(previous_pkgbuild),
                pkgver(updated_pkgbuild),
                patch,
            )
        )
    return changes


def push_branch(branch: str) -> None:
    remote_ref = f"refs/remotes/origin/{branch}"
    fetched = run(
        "git",
        "fetch",
        "origin",
        f"+refs/heads/{branch}:{remote_ref}",
        check=False,
    )
    expected = (
        run("git", "rev-parse", remote_ref).stdout.strip()
        if fetched.returncode == 0
        else ""
    )
    run(
        "git",
        "push",
        f"--force-with-lease=refs/heads/{branch}:{expected}",
        "origin",
        f"HEAD:refs/heads/{branch}",
    )


def open_or_update_pull_request(change: PackageChange, branch: str) -> None:
    title = (
        f"Update {change.name} from {change.previous_version} "
        f"to {change.updated_version}"
    )
    body = (
        f"Updates `{change.name}` from `{change.previous_version}` "
        f"to `{change.updated_version}` via `./update.py`."
    )
    result = run(
        "gh",
        "pr",
        "list",
        "--repo",
        os.environ["GITHUB_REPOSITORY"],
        "--head",
        branch,
        "--state",
        "open",
        "--json",
        "number",
    )
    pulls = json.loads(result.stdout)
    if pulls:
        run(
            "gh",
            "pr",
            "edit",
            str(pulls[0]["number"]),
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
            "--title",
            title,
            "--body",
            body,
        )
    else:
        run(
            "gh",
            "pr",
            "create",
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
            "--base",
            os.environ["DEFAULT_BRANCH"],
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        )


def publish_change(change: PackageChange, base: str) -> None:
    branch = f"automated/update-{change.name}"
    run("git", "checkout", "-B", branch, base)
    run("git", "apply", "--index", input_text=change.patch)
    run(
        "git",
        "commit",
        "-m",
        f"Update {change.name} to {change.updated_version}",
    )
    push_branch(branch)
    open_or_update_pull_request(change, branch)
    print(f"Created {branch}: {change.previous_version} -> {change.updated_version}")


def main() -> None:
    base = os.environ["GITHUB_SHA"]
    if os.environ["GITHUB_REF_NAME"] != os.environ["DEFAULT_BRANCH"]:
        raise SystemExit("Package updates must run from the default branch")

    run("git", "config", "--global", "--add", "safe.directory", str(ROOT))
    run("git", "config", "user.name", "github-actions[bot]")
    run(
        "git",
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )

    changes = collect_changes(base)
    if not changes:
        print("No package metadata changes.")
        return

    run("git", "reset", "--hard", base)
    run("gh", "auth", "setup-git")
    for change in changes:
        publish_change(change, base)


if __name__ == "__main__":
    main()
