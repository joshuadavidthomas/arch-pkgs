#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["nvchecker"]
# ///
"""Check upstream versions with nvchecker and update PKGBUILDs in place.

Each package directory must have a matching section in nvchecker.toml
(section name == directory name). New versions get pkgver bumped,
pkgrel reset to 1, checksums refreshed via updpkgsums, and .SRCINFO
regenerated.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def pkg_dirs() -> list[Path]:
    return sorted(d for d in ROOT.iterdir() if (d / "PKGBUILD").is_file())


def current_pkgver(pkgbuild: Path) -> str | None:
    m = re.search(r"^pkgver=(.*)$", pkgbuild.read_text(), re.M)
    return m.group(1).strip() if m else None


def run_nvchecker() -> dict[str, str]:
    cmd = ["nvchecker", "-c", str(ROOT / "nvchecker.toml"), "--logger", "json"]
    keyfile = None
    token = os.environ.get("GITHUB_TOKEN")
    try:
        if token:
            keyfile = tempfile.NamedTemporaryFile(
                "w", suffix=".toml", delete=False
            )
            keyfile.write(f'[keys]\ngithub = "{token}"\n')
            keyfile.close()
            cmd += ["-k", keyfile.name]
        proc = subprocess.run(
            cmd, cwd=ROOT, check=True, capture_output=True, text=True
        )
    finally:
        if keyfile:
            os.unlink(keyfile.name)

    results: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("level") == "error":
            print(f":: nvchecker: {event}", file=sys.stderr)
        elif event.get("event") == "updated" and "version" in event:
            results[event["name"]] = event["version"]
    return results


def update_package(d: Path, newver: str) -> None:
    pkgbuild = d / "PKGBUILD"
    text = pkgbuild.read_text()
    text = re.sub(r"^pkgver=.*$", f"pkgver={newver}", text, flags=re.M)
    text = re.sub(r"^pkgrel=.*$", "pkgrel=1", text, flags=re.M)
    pkgbuild.write_text(text)
    subprocess.run(["updpkgsums"], cwd=d, check=True)
    srcinfo = subprocess.run(
        ["makepkg", "--printsrcinfo"],
        cwd=d,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    (d / ".SRCINFO").write_text(srcinfo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="refresh checksums and .SRCINFO even when versions match",
    )
    args = parser.parse_args()

    results = run_nvchecker()
    failures = []
    for d in pkg_dirs():
        name = d.name
        newver = results.get(name)
        if newver is None:
            print(f":: {name}: no version from nvchecker", file=sys.stderr)
            failures.append(name)
            continue
        cur = current_pkgver(d / "PKGBUILD")
        if newver == cur and not args.force:
            print(f"   {name}: up to date ({cur})")
            continue
        print(f"=> {name}: {cur} -> {newver}")
        try:
            update_package(d, newver)
        except subprocess.CalledProcessError as exc:
            print(f":: {name}: update failed: {exc}", file=sys.stderr)
            failures.append(name)

    if failures:
        print(f"Update failed for: {' '.join(failures)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
