from __future__ import annotations

import asyncio

from src.app.progress_streams import run_scan_stream, plan_sort_stream, execute_sort_stream


async def _consume(async_iter):
    items = []
    async for event in async_iter:
        items.append(event)
    return items


def test_progress_streams_end_to_end(tmp_path):
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    rom = src_dir / "game.nes"
    rom.write_text("data", encoding="utf-8")

    scan_events = asyncio.run(_consume(run_scan_stream(str(src_dir))))
    assert any(e.kind == "result" for e in scan_events)
    scan = [e.result for e in scan_events if e.kind == "result"][0]

    plan_events = asyncio.run(_consume(plan_sort_stream(scan, str(dest_dir), mode="copy", on_conflict="rename")))
    assert any(e.kind == "result" for e in plan_events)
    plan = [e.result for e in plan_events if e.kind == "result"][0]

    exec_events = asyncio.run(_consume(execute_sort_stream(plan)))
    assert any(e.kind == "result" for e in exec_events)
