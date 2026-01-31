import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.models import SortAction, SortPlan  # noqa: E402
from src.app.plan_stats import compute_plan_stats  # noqa: E402


def test_compute_plan_stats_counts_planned(tmp_path: Path) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    a = source / "a.rom"
    b = source / "b.rom"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")

    plan = SortPlan(
        dest_path=str(dest),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(a),
                detected_system="NES",
                planned_target_path=str(dest / "NES" / "a.rom"),
                action="copy",
                status="planned",
            ),
            SortAction(
                input_path=str(b),
                detected_system="NES",
                planned_target_path=None,
                action="copy",
                status="skipped",
            ),
        ],
    )

    stats = compute_plan_stats(plan)
    assert stats["total_actions"] == 1
    assert stats["total_bytes"] == len("a")
