from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publish_summary", ROOT / "scripts" / "publish_summary.py"
)
assert SPEC and SPEC.loader
SUMMARY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUMMARY
SPEC.loader.exec_module(SUMMARY)


def test_formats_bytes_and_deltas() -> None:
    assert SUMMARY.format_bytes(0) == "0 B"
    assert SUMMARY.format_bytes(1536) == "1.5 KiB"
    assert SUMMARY.format_delta(1024, SUMMARY.format_bytes) == "+1 KiB"
    assert SUMMARY.format_delta(-2) == "-2"


def test_reads_package_plan(tmp_path: Path) -> None:
    plan = tmp_path / "package-plan.tsv"
    plan.write_text("packages/example\texample\t2.0-1\n")

    assert SUMMARY.read_plan(plan) == [
        SUMMARY.PackagePlan("packages/example", "example", "2.0-1")
    ]


def test_renders_package_results(tmp_path: Path) -> None:
    plans = [
        SUMMARY.PackagePlan("packages/broken", "broken", "1.0-1"),
        SUMMARY.PackagePlan("packages/example", "example", "2.0-1"),
    ]
    (tmp_path / "example-2.0-1-x86_64.pkg.tar.zst").write_bytes(b"x" * 1536)

    rows = SUMMARY.package_rows(
        plans,
        tmp_path,
        {"packages/broken"},
        "success",
    )

    assert rows == [
        "| `broken` | `1.0-1` | Build failed | — |",
        "| `example` | `2.0-1` | Published | 1.5 KiB |",
    ]


def test_renders_repository_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    environment = {
        "DATABASE_OUTCOME": "success",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_NUMBER": "7",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_SHA": "1234567890abcdef",
        "PRIVACY_OUTCOME": "success",
        "UPLOAD_OUTCOME": "success",
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    current = SUMMARY.RepositoryMetrics(3 * 1024, 12, 27)
    previous = SUMMARY.RepositoryMetrics(2 * 1024, 10, 27)
    rendered = SUMMARY.render_summary([], [], current, previous)

    assert "No package versions needed publication." in rendered
    assert "| Packages in database | 27 | — |" in rendered
    assert "| R2 storage | 3 KiB | +1 KiB |" in rendered
    assert "| R2 objects | 12 | +2 |" in rendered
    assert "- Anonymous access check: success" in rendered
