from typing import cast

from src.core.platform_heuristics import evaluate_platform_candidates


def test_platform_catalog_yaml_loads_candidates():
    result = evaluate_platform_candidates("C:/roms/nes/SuperMario.nes")
    candidates = cast(list[str], result.get("candidate_systems") or [])
    assert "nes" in candidates
