from __future__ import annotations

import shutil
from pathlib import Path

from src.app.api import CancelToken, execute_sort, plan_sort, run_scan
from src.config.io import load_config


def _copy_fixtures(src_dir: Path, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for fixture in src_dir.iterdir():
        if fixture.is_file():
            target = dest_dir / fixture.name
            shutil.copy2(fixture, target)
            copied.append(target)
    return copied


def test_e2e_scan_plan_execute(tmp_path: Path) -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "real_roms"
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"

    copied = _copy_fixtures(fixtures_dir, source_dir)
    assert copied, "No fixtures copied"

    cfg = load_config()
    cancel = CancelToken()

    scan = run_scan(str(source_dir), config=cfg, cancel_token=cancel)
    assert scan.items, "Scan returned no items"

    plan = plan_sort(scan, str(dest_dir), config=cfg, mode="copy", on_conflict="rename", cancel_token=cancel)
    assert plan.actions, "Plan contains no actions"

    report = execute_sort(plan, cancel_token=cancel, conversion_mode="skip")
    assert not report.cancelled

    dest_files = {p.name for p in dest_dir.rglob("*") if p.is_file()}
    for src in copied:
        assert src.name in dest_files
        assert src.exists()
