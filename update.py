#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["nvchecker"]
# ///
"""Check upstream versions with nvchecker and update PKGBUILDs in place.

Each directory under packages/ must contain a .nvchecker.toml whose primary
entry matches the package's pkgbase. New versions get pkgver bumped, pkgrel
reset to 1, checksums refreshed via updpkgsums, and .SRCINFO regenerated.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGES = ROOT / "packages"
VALID_PKGVER = re.compile(r"^[A-Za-z0-9._+]+$")


def pkg_dirs() -> list[Path]:
    return sorted(d for d in PACKAGES.iterdir() if (d / "PKGBUILD").is_file())


def current_pkgver(pkgbuild: Path) -> str | None:
    m = re.search(r"^pkgver=(.*)$", pkgbuild.read_text(), re.M)
    return m.group(1).strip() if m else None


def pkgbase(directory: Path) -> str:
    srcinfo = directory / ".SRCINFO"
    match = re.search(r"^pkgbase = (.+)$", srcinfo.read_text(), re.MULTILINE)
    if match is None:
        raise ValueError(f"{srcinfo.relative_to(ROOT)} has no pkgbase")
    return match.group(1)


def validate_nvchecker_config(base: str, text: str, path: Path) -> set[str]:
    entries = set(tomllib.loads(text))
    if base not in entries:
        raise ValueError(f"{path.relative_to(ROOT)} has no [{base}] entry")
    invalid = [name for name in entries if name != base and not name.startswith(f"{base}:")]
    if invalid:
        names = ", ".join(sorted(invalid))
        raise ValueError(f"{path.relative_to(ROOT)} has unscoped entries: {names}")
    return entries


def render_nvchecker_config(directories: list[Path]) -> str:
    configs = []
    known_entries: set[str] = set()
    for directory in directories:
        path = directory / ".nvchecker.toml"
        text = path.read_text()
        entries = validate_nvchecker_config(pkgbase(directory), text, path)
        duplicates = known_entries & entries
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise ValueError(f"duplicate nvchecker entries: {names}")
        known_entries.update(entries)
        configs.append(text.strip())
    return "\n\n".join(configs) + "\n"


def run_nvchecker() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    with tempfile.TemporaryDirectory() as temp_directory:
        temp = Path(temp_directory)
        config = temp / "nvchecker.toml"
        config.write_text(render_nvchecker_config(pkg_dirs()))
        cmd = ["nvchecker", "-c", str(config), "--logger", "json"]
        if token:
            keyfile = temp / "keyfile.toml"
            keyfile.write_text(f'[keys]\ngithub = "{token}"\n')
            cmd += ["-k", str(keyfile)]
        proc = subprocess.run(
            cmd, cwd=ROOT, check=True, capture_output=True, text=True
        )

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


def render_updated_pkgbuild(text: str, newver: str) -> str:
    if not VALID_PKGVER.fullmatch(newver):
        raise ValueError(f"unsafe pkgver: {newver!r}")

    pkgver_pattern = r"^pkgver=.*$"
    pkgrel_pattern = r"^pkgrel=.*$"
    if len(re.findall(pkgver_pattern, text, re.M)) != 1 or len(
        re.findall(pkgrel_pattern, text, re.M)
    ) != 1:
        raise ValueError("PKGBUILD must contain one pkgver and one pkgrel assignment")

    text = re.sub(pkgver_pattern, lambda _: f"pkgver={newver}", text, flags=re.M)
    return re.sub(pkgrel_pattern, lambda _: "pkgrel=1", text, flags=re.M)


def update_package(d: Path, newver: str) -> None:
    pkgbuild = d / "PKGBUILD"
    srcinfo_path = d / ".SRCINFO"
    original_pkgbuild = pkgbuild.read_text()
    original_srcinfo = srcinfo_path.read_text() if srcinfo_path.exists() else None
    clean_env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}

    try:
        pkgbuild.write_text(render_updated_pkgbuild(original_pkgbuild, newver))
        subprocess.run(["updpkgsums"], cwd=d, check=True, env=clean_env)
        srcinfo = subprocess.run(
            ["makepkg", "--printsrcinfo"],
            cwd=d,
            check=True,
            capture_output=True,
            text=True,
            env=clean_env,
        ).stdout
        srcinfo_path.write_text(srcinfo)
    except Exception:
        pkgbuild.write_text(original_pkgbuild)
        if original_srcinfo is None:
            srcinfo_path.unlink(missing_ok=True)
        else:
            srcinfo_path.write_text(original_srcinfo)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="refresh checksums and .SRCINFO even when versions match",
    )
    parser.add_argument(
        "--failure-file",
        type=Path,
        help="write failed package names here before exiting nonzero",
    )
    args = parser.parse_args()
    if args.failure_file:
        args.failure_file.unlink(missing_ok=True)

    results = run_nvchecker()
    failures = []
    for d in pkg_dirs():
        name = d.name
        newver = results.get(pkgbase(d))
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
        except (OSError, subprocess.CalledProcessError, ValueError) as exc:
            print(f":: {name}: update failed: {exc}", file=sys.stderr)
            failures.append(name)

    if failures:
        failure_text = " ".join(failures)
        if args.failure_file:
            args.failure_file.write_text(failure_text + "\n")
        print(f"Update failed for: {failure_text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
