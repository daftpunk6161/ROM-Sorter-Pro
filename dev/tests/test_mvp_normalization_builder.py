import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_normalization_plan_builder_builds_plan():
    from src.core.normalization import NormalizationItem, NormalizationPlanBuilder

    item = NormalizationItem(
        input_path="/tmp/game.bin",
        input_kind="RawRom",
        platform_id=None,
        status="ok",
        issues=(),
        action="copy",
        output_path="/tmp/out.bin",
    )

    builder = NormalizationPlanBuilder().add(item)
    plan = builder.build()
    assert len(plan.items) == 1
    assert plan.items[0].input_path == "/tmp/game.bin"
