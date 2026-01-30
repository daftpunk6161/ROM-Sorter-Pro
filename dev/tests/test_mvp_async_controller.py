from __future__ import annotations

import asyncio

from src.app.async_controller import run_scan_async, plan_sort_async, execute_sort_async
from src.app.controller import ScanItem, ScanResult


async def _run_async_flow(tmp_path):
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    rom = src_dir / "game.nes"
    rom.write_text("data", encoding="utf-8")

    scan = ScanResult(
        source_path=str(src_dir),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={"total": 1},
        cancelled=False,
    )

    plan = await plan_sort_async(scan, str(dest_dir), mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1

    report = await execute_sort_async(plan)
    assert report.processed >= 1

    scan2 = await run_scan_async(str(src_dir))
    total = scan2.stats.get("total")
    if total is None:
        total = scan2.stats.get("rom_count", 0)
    assert total >= 1


def test_async_controller_flow(tmp_path):
    asyncio.run(_run_async_flow(tmp_path))
