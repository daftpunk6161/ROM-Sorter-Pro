from __future__ import annotations

import asyncio
from pathlib import Path

from src.app.async_api import async_plan_sort, async_run_scan
from src.config.io import load_config
from src.utils.result import is_ok


def test_async_api_scan_plan(tmp_path: Path) -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "real_roms"
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for fixture in fixtures_dir.iterdir():
        if fixture.is_file():
            (source_dir / fixture.name).write_bytes(fixture.read_bytes())

    cfg = load_config()

    scan_result = asyncio.run(async_run_scan(str(source_dir), config=cfg))
    assert is_ok(scan_result)
    scan = scan_result.value
    assert scan.items

    plan_result = asyncio.run(async_plan_sort(scan, str(dest_dir), config=cfg))
    assert is_ok(plan_result)
    plan = plan_result.value
    assert plan.actions
