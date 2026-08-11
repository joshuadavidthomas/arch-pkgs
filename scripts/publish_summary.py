#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Write the publish workflow summary and record R2 storage metrics."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class PackagePlan:
    directory: str
    name: str
    version: str


@dataclass(frozen=True)
class RepositoryMetrics:
    bytes: int
    objects: int
    packages: int | None


def format_bytes(value: int) -> str:
    sign = "-" if value < 0 else ""
    size = float(abs(value))
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    unit = units[0]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    if unit == "B":
        rendered = str(int(size))
    elif size >= 10 or size.is_integer():
        rendered = f"{size:.0f}"
    else:
        rendered = f"{size:.1f}"
    return f"{sign}{rendered} {unit}"


def format_delta(value: int, formatter: Callable[[int], str] = str) -> str:
    rendered = formatter(value)
    return f"+{rendered}" if value > 0 else rendered


def read_plan(path: Path) -> list[PackagePlan]:
    if not path.exists():
        return []
    plans = []
    for line in path.read_text().splitlines():
        directory, name, version = line.split("\t")
        plans.append(PackagePlan(directory, name, version))
    return plans


def artifact_size(repo: Path, plan: PackagePlan) -> int | None:
    file_version = plan.version.split(":", maxsplit=1)[-1]
    artifacts = list(repo.glob(f"{plan.name}-{file_version}-*.pkg.tar.zst"))
    if not artifacts:
        return None
    return sum(path.stat().st_size for path in artifacts)


def package_rows(
    plans: list[PackagePlan],
    repo: Path,
    failed_directories: set[str],
    upload_outcome: str,
) -> list[str]:
    rows = []
    for plan in plans:
        size = artifact_size(repo, plan)
        if plan.directory in failed_directories:
            result = "Build failed"
            rendered_size = "—"
        elif size is None:
            result = "Artifact missing"
            rendered_size = "—"
        elif upload_outcome == "success":
            result = "Published"
            rendered_size = format_bytes(size)
        else:
            result = "Built; upload incomplete"
            rendered_size = format_bytes(size)
        rows.append(
            f"| `{plan.name}` | `{plan.version}` | {result} | {rendered_size} |"
        )
    return rows


def run(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        capture_output=True,
        input=input_text,
        text=True,
    )


def remote_package_count(remote: str, repo_name: str, destination: Path) -> int:
    database = subprocess.run(
        ["rclone", "cat", f"{remote}/{repo_name}.db.tar.zst"],
        check=True,
        capture_output=True,
    ).stdout
    destination.write_bytes(database)
    listing = subprocess.run(
        ["bsdtar", "-tf", destination],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return len({line.split("/", maxsplit=1)[0] for line in listing.splitlines()})


def measure_repository(bucket: str, packages: int | None) -> RepositoryMetrics:
    result = run("rclone", "size", bucket, "--exclude", "metrics/**", "--json")
    data = json.loads(result.stdout)
    return RepositoryMetrics(data["bytes"], data["count"], packages)


def read_previous_metric(bucket: str) -> RepositoryMetrics | None:
    try:
        result = run("rclone", "cat", f"{bucket}/metrics/publish-latest.json")
        data = json.loads(result.stdout)
        return RepositoryMetrics(data["bytes"], data["objects"], data.get("packages"))
    except (json.JSONDecodeError, KeyError, subprocess.CalledProcessError):
        return None


def record_metric(bucket: str, metrics: RepositoryMetrics) -> None:
    run_id = os.environ["GITHUB_RUN_ID"]
    data = json.dumps(
        {
            "bytes": metrics.bytes,
            "commit": os.environ["GITHUB_SHA"],
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "objects": metrics.objects,
            "packages": metrics.packages,
            "run_id": run_id,
        },
        separators=(",", ":"),
    )
    options = ("--header-upload", "Cache-Control: private, no-store")
    run(
        "rclone",
        "rcat",
        f"{bucket}/metrics/publish-runs/{run_id}.json",
        *options,
        input_text=data,
    )
    run(
        "rclone",
        "rcat",
        f"{bucket}/metrics/publish-latest.json",
        *options,
        input_text=data,
    )


def render_summary(
    plans: list[PackagePlan],
    rows: list[str],
    metrics: RepositoryMetrics | None,
    previous: RepositoryMetrics | None,
) -> str:
    run_url = (
        f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
        f"/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    )
    commit_url = (
        f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
        f"/commit/{os.environ['GITHUB_SHA']}"
    )
    lines = [
        "## Package publication",
        "",
        f"Run [`{os.environ['GITHUB_RUN_NUMBER']}`]({run_url}) for "
        f"[`{os.environ['GITHUB_SHA'][:8]}`]({commit_url}).",
        "",
        "### Packages",
        "",
    ]
    if plans:
        lines.extend(
            [
                "| Package | Version | Result | Size |",
                "| --- | --- | --- | ---: |",
                *rows,
            ]
        )
    else:
        lines.append("No package versions needed publication.")

    lines.extend(
        [
            "",
            "### Repository",
            "",
            "| Metric | Current | Change since prior run |",
            "| --- | ---: | ---: |",
        ]
    )
    if metrics is None:
        lines.extend(
            [
                "| Packages in database | Unavailable | — |",
                "| R2 storage | Unavailable | Unavailable |",
                "| R2 objects | Unavailable | Unavailable |",
            ]
        )
    else:
        packages = str(metrics.packages) if metrics.packages is not None else "Unavailable"
        if previous is None:
            storage_delta = "Unavailable"
            objects_delta = "Unavailable"
        else:
            storage_delta = format_delta(metrics.bytes - previous.bytes, format_bytes)
            objects_delta = format_delta(metrics.objects - previous.objects)
        lines.extend(
            [
                f"| Packages in database | {packages} | — |",
                f"| R2 storage | {format_bytes(metrics.bytes)} | {storage_delta} |",
                f"| R2 objects | {metrics.objects} | {objects_delta} |",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    runner_temp = Path(os.environ["RUNNER_TEMP"])
    plans = read_plan(runner_temp / "package-plan.tsv")
    failed = set(os.environ.get("FAILED_DIRS", "").split())
    rows = package_rows(
        plans,
        Path("repo"),
        failed,
        os.environ.get("UPLOAD_OUTCOME", "skipped"),
    )

    metrics = None
    previous = None
    try:
        packages = remote_package_count(
            os.environ["R2_REMOTE"],
            os.environ["PACMAN_REPO"],
            runner_temp / "remote-josh.db.tar.zst",
        )
        metrics = measure_repository("r2:pkgs", packages)
        previous = read_previous_metric("r2:pkgs")
        record_metric("r2:pkgs", metrics)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Could not record repository metrics: {exc}")

    summary = render_summary(plans, rows, metrics, previous)
    Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(summary)


if __name__ == "__main__":
    main()
