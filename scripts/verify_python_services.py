#!/usr/bin/env python3
"""Deterministic verification for Python services in this repository."""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent


def parse_python_file(path: Path) -> ast.Module:
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path))


def ensure_text_markers(path: Path, markers: Iterable[str]) -> None:
    source = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in source]
    if missing:
        joined = ", ".join(missing)
        raise AssertionError(f"{path.relative_to(ROOT)} missing expected markers: {joined}")


def verify_api() -> None:
    os.environ.setdefault("FIELD_ENCRYPTION_KEY", "AM8fqwZVXAwBTH6z3VvxTY2GZ5xlpv39jWMd93C4cvc=")
    sys.path.insert(0, str(ROOT))

    from api.main import app  # noqa: PLC0415
    from tests.compat_client import AppClient  # noqa: PLC0415

    client = AppClient(app)

    health = client.get("/health")
    if health.status_code != 200:
        raise AssertionError(f"api health returned {health.status_code}")
    health_payload = health.json()
    if health_payload.get("status") != "healthy":
        raise AssertionError(f"unexpected api health payload: {health_payload}")

    version = client.get("/version")
    if version.status_code != 200:
        raise AssertionError(f"api version returned {version.status_code}")
    version_payload = version.json()
    if version_payload.get("service") != "iconsai-scraping-api":
        raise AssertionError(f"unexpected api version payload: {version_payload}")

    print("verify-ok api health version")


def verify_pipeline_worker() -> None:
    path = ROOT / "services" / "pipeline-worker" / "main.py"
    parse_python_file(path)
    ensure_text_markers(path, ('@app.get("/health"', '@app.get("/status"', 'FastAPI('))
    print("verify-ok services/pipeline-worker/main.py")


def verify_scheduler() -> None:
    path = ROOT / "scheduler" / "collector.py"
    parse_python_file(path)
    ensure_text_markers(path, ("class DataCollector", "AsyncIOScheduler", "CronTrigger"))
    print("verify-ok scheduler/collector.py")


TARGETS = {
    "api": verify_api,
    "pipeline-worker": verify_pipeline_worker,
    "scheduler": verify_scheduler,
}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    selected = args or list(TARGETS)

    for target in selected:
        verifier = TARGETS.get(target)
        if verifier is None:
            valid = ", ".join(TARGETS)
            raise SystemExit(f"unknown target '{target}'. valid targets: {valid}")
        verifier()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
