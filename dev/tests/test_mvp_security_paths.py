import os
import sys
import zipfile
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_validate_file_operation_blocks_outside_base(tmp_path):
    from src.security.security_utils import validate_file_operation

    base = tmp_path / "base"
    base.mkdir()
    allowed = base / "x.txt"
    allowed.write_text("ok")

    validate_file_operation(allowed, base_dir=base, allow_read=True, allow_write=True)

    outside = tmp_path / "outside.txt"
    outside.write_text("no")

    # Should raise because outside base_dir
    try:
        validate_file_operation(outside, base_dir=base, allow_read=True, allow_write=True)
        assert False, "Expected validate_file_operation to raise"
    except Exception:
        assert True


def test_execute_sort_rejects_symlink_source(tmp_path):
    from src.app.controller import SortAction, SortPlan, execute_sort

    source = tmp_path / "source.txt"
    source.write_text("data")

    symlink = tmp_path / "link.txt"
    try:
        os.symlink(source, symlink)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported in this environment")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    plan = SortPlan(
        dest_path=str(dest_root),
        mode="copy",
        on_conflict="overwrite",
        actions=[
            SortAction(
                input_path=str(symlink),
                detected_system="Unknown",
                planned_target_path=str(dest_root / "link.txt"),
                action="copy",
                status="planned",
                error=None,
            )
        ],
    )

    with pytest.raises(Exception):
        execute_sort(plan)


def test_execute_sort_rejects_traversal_target(tmp_path):
    from src.app.controller import SortAction, SortPlan, execute_sort

    source = tmp_path / "source.txt"
    source.write_text("data")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    outside = tmp_path / "outside.txt"

    plan = SortPlan(
        dest_path=str(dest_root),
        mode="copy",
        on_conflict="overwrite",
        actions=[
            SortAction(
                input_path=str(source),
                detected_system="Unknown",
                planned_target_path=str(outside),
                action="copy",
                status="planned",
                error=None,
            )
        ],
    )

    with pytest.raises(Exception):
        execute_sort(plan)


def test_plan_sort_rejects_symlink_parent(tmp_path):
    from src.app.controller import ScanItem, ScanResult, plan_sort

    source = tmp_path / "source"
    source.mkdir()
    rom = source / "game.rom"
    rom.write_text("data")

    dest_real = tmp_path / "dest_real"
    dest_real.mkdir()
    dest_link = tmp_path / "dest_link"

    try:
        os.symlink(dest_real, dest_link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported in this environment")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    with pytest.raises(Exception):
        plan_sort(scan, str(dest_link))


def test_safe_extract_zip_blocks_symlink(tmp_path):
    from src.security.security_utils import safe_extract_zip

    archive_path = tmp_path / "symlink.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        info = zipfile.ZipInfo("link.txt")
        info.external_attr = 0o120777 << 16  # symlink file type
        zf.writestr(info, "target")

    extract_dir = tmp_path / "out"
    with pytest.raises(Exception):
        safe_extract_zip(archive_path, extract_dir)


def test_plan_sort_rejects_destination_file(tmp_path):
    from src.app.controller import ScanItem, ScanResult, plan_sort

    source = tmp_path / "source"
    source.mkdir()
    rom = source / "game.rom"
    rom.write_text("x")

    dest_file = tmp_path / "dest.txt"
    dest_file.write_text("not a dir")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    with pytest.raises(ValueError):
        plan_sort(scan, str(dest_file), mode="copy", on_conflict="rename")


def test_execute_external_tools_rejects_symlink_input(tmp_path):
    from src.app.controller import SortAction, SortPlan, execute_external_tools

    source = tmp_path / "source.txt"
    source.write_text("data")

    symlink = tmp_path / "link.txt"
    try:
        os.symlink(source, symlink)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported in this environment")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    plan = SortPlan(
        dest_path=str(dest_root),
        mode="copy",
        on_conflict="overwrite",
        actions=[
            SortAction(
                input_path=str(symlink),
                detected_system="Unknown",
                planned_target_path=str(dest_root / "out.wud"),
                action="convert",
                status="planned",
                conversion_tool="wudcompress",
                conversion_tool_key="wudcompress",
                conversion_args=["-h"],
                error=None,
            )
        ],
    )

    with pytest.raises(Exception):
        execute_external_tools(plan, output_dir=str(dest_root), temp_dir=str(dest_root / "_temp"), dry_run=True)
