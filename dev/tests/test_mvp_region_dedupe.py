from __future__ import annotations

from src.app.controller import (
    ScanItem,
    infer_region_from_name,
    normalize_title_for_dedupe,
    select_preferred_variants,
)


def test_infer_region_from_name_common_tokens() -> None:
    assert infer_region_from_name("Game (Europe).zip") == "Europe"
    assert infer_region_from_name("Game (E).zip") == "Europe"
    assert infer_region_from_name("Game (USA).zip") == "USA"
    assert infer_region_from_name("Game (U).zip") == "USA"
    assert infer_region_from_name("Game (Japan).zip") == "Japan"
    assert infer_region_from_name("Game (J).zip") == "Japan"
    assert infer_region_from_name("Game (World).zip") == "World"
    assert infer_region_from_name("Game (W).zip") == "World"


def test_normalize_title_for_dedupe_strips_tags() -> None:
    a = normalize_title_for_dedupe("Cool Game (Europe) (En,De) (Rev 1).zip")
    b = normalize_title_for_dedupe("Cool Game (Europe).zip")
    c = normalize_title_for_dedupe("Cool Game [b].zip")
    assert a == b == c == "Cool Game"


def test_select_preferred_variants_prefers_europe_over_usa() -> None:
    items = [
        ScanItem(input_path="Game (USA).zip", detected_system="SNES", region="USA"),
        ScanItem(input_path="Game (Europe).zip", detected_system="SNES", region="Europe"),
    ]
    chosen = select_preferred_variants(items)
    assert len(chosen) == 1
    assert "Europe" in chosen[0].input_path


def test_select_preferred_variants_prefers_language_specific_variant() -> None:
    # Same region, one has language tags -> should win
    items = [
        ScanItem(input_path="Game (Europe).zip", detected_system="SNES", region="Europe", languages=()),
        ScanItem(
            input_path="Game (Europe) (En,De).zip",
            detected_system="SNES",
            region="Europe",
            languages=("De", "En"),
        ),
    ]
    chosen = select_preferred_variants(items)
    assert len(chosen) == 1
    assert "En,De" in chosen[0].input_path


def test_select_preferred_variants_prefers_de_over_fr_when_same_region() -> None:
    # When variants differ only by single language, prefer German by default priority.
    items = [
        ScanItem(
            input_path="Game (Europe) (Fr).zip",
            detected_system="SNES",
            region="Europe",
            languages=("Fr",),
        ),
        ScanItem(
            input_path="Game (Europe) (De).zip",
            detected_system="SNES",
            region="Europe",
            languages=("De",),
        ),
    ]
    chosen = select_preferred_variants(items)
    assert len(chosen) == 1
    assert "(De)" in chosen[0].input_path
